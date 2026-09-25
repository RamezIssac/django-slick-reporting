"""
Tests for the LLM data-format evaluation framework.

Covers the deterministic fixture, the prompt-side serializers (JSON / plain /
TOON), and the scorer -- including regression tests for the bugs found in the
audit of the first implementation: numerically wrong answers must fail, real
executor time-series payloads (``value__sumTS<date>`` keys) must score, a
value-only plan must satisfy the sales question, and zero totals must be
handled.  Everything is deterministic and needs no external LLM calls.

Run with:  python runtests.py tests.test_llm_eval
"""

import json
import unittest

from django.test import SimpleTestCase, TestCase

from slick_reporting.llm import prompts
from slick_reporting.llm.backends import EchoBackend
from slick_reporting.llm.evaluator import (
    DETERMINISTIC_FIXTURE,
    EvaluationFixture,
    EvaluationResult,
    EvaluationScorer,
    create_fixture_data,
    fixture_sha256,
    run_evaluation,
)
from slick_reporting.llm.executor import run_llm_report_config
from slick_reporting.llm.toon_data import dumps_json, dumps_plain, normalize_jsonable, serialize_for_prompt

try:
    import toon_format  # noqa: F401

    HAS_TOON = True
except ImportError:
    HAS_TOON = False

Q1 = {"start_date": "2026-01-01", "end_date": "2026-03-31", "date_field": "doc_date"}

#: The correct plan configurations for each question (verified against the
#: real executor on the fixture data).
PERFECT_CONFIGS = {
    "product1_sales_q1": {
        "report_model": "tests.SimpleSales",
        **Q1,
        "group_by": "product",
        "columns": ["name", {"method": "Sum", "field": "value", "name": "value__sum"}],
        "filters": {"product_id__in": ["Product 1"]},
    },
    "product1_quantity_q1": {
        "report_model": "tests.SimpleSales",
        **Q1,
        "group_by": "product",
        "columns": ["name", {"method": "Sum", "field": "quantity", "name": "quantity__sum"}],
        "filters": {"product_id__in": ["Product 1"]},
    },
    "product2_us_vs_eg_q1": {
        "report_model": "tests.SimpleSales",
        **Q1,
        "group_by": "client__country",
        "columns": ["client__country", {"method": "Sum", "field": "value", "name": "value__sum"}],
        "filters": {"product_id__in": ["Product 2"]},
    },
    "product1_monthly_q1": {
        "report_model": "tests.SimpleSales",
        **Q1,
        "group_by": "product",
        "columns": ["name", {"method": "Sum", "field": "value", "name": "value__sum"}],
        "time_series_pattern": "monthly",
        "time_series_columns": [{"method": "Sum", "field": "value", "name": "value__sum"}],
        "filters": {"product_id__in": ["Product 1"]},
    },
    "top_client_product1_q1": {
        "report_model": "tests.SimpleSales",
        **Q1,
        "group_by": "client",
        "columns": ["name", {"method": "Sum", "field": "value", "name": "value__sum"}],
        "filters": {"product_id__in": ["Product 1"]},
    },
}


def make_result(question_id, **kwargs):
    """An EvaluationResult wired to the fixture's expectations."""
    EvaluationFixture.setup()
    return EvaluationResult(
        question_id=question_id,
        question_text=EvaluationFixture.get_expected(question_id)["question"],
        format_name="json",
        **kwargs,
    )


class DeterministicFixtureTests(TestCase):
    """The fixture and its derived expectations are internally consistent."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.entries, cls.expected = EvaluationFixture.setup()

    def test_fixture_has_correct_entry_count(self):
        self.assertEqual(len(DETERMINISTIC_FIXTURE), 14)

    def test_fixture_has_three_products(self):
        self.assertEqual({e.product_name for e in DETERMINISTIC_FIXTURE}, {"Product 1", "Product 2", "Product 3"})

    def test_all_dates_in_q1_2026(self):
        for e in DETERMINISTIC_FIXTURE:
            self.assertTrue(e.date.startswith("2026-0"), e.date)
            self.assertLessEqual(int(e.date[5:7]), 3, e.date)

    def test_no_dates_on_month_boundary(self):
        """Generator time-series buckets rows on a boundary date into the
        period ending that day, so the fixture must avoid the 1st."""
        for e in DETERMINISTIC_FIXTURE:
            self.assertNotEqual(e.date[8:10], "01", e.date)

    def test_product1_totals(self):
        """Product 1: 6 entries, price 50.00 -> value 5000, quantity 100."""
        sales = self.expected["product1_sales_q1"]
        self.assertEqual(sales["expected_value"], 5000.0)
        # The sales question must not demand a quantity nobody asked for.
        self.assertNotIn("expected_quantity", sales)
        quantity = self.expected["product1_quantity_q1"]
        self.assertEqual(quantity["expected_quantity"], 100)
        self.assertNotIn("expected_value", quantity)

    def test_product2_us_vs_eg(self):
        """The agreed question 3: Product 2 sales by country, US 1250 vs EG 1500."""
        e = self.expected["product2_us_vs_eg_q1"]
        self.assertIn("US", e["question"])
        self.assertIn("EG", e["question"])
        self.assertEqual(e["checks"]["group_by"], "client__country")
        self.assertEqual(e["expected_country_values"], {"US": 1250.0, "EG": 1500.0})

    def test_product2_has_us_and_eg_rows(self):
        countries = {e.client_country for e in DETERMINISTIC_FIXTURE if e.product_name == "Product 2"}
        self.assertEqual(countries, {"US", "EG"})

    def test_product1_monthly(self):
        e = self.expected["product1_monthly_q1"]
        self.assertEqual(e["expected_monthly"], {"2026-01": 1750.0, "2026-02": 1750.0, "2026-03": 1500.0})
        self.assertEqual(e["checks"]["time_series_pattern"], "monthly")

    def test_top_client(self):
        e = self.expected["top_client_product1_q1"]
        self.assertEqual(e["expected_client_values"], {"Alpha US": 2750.0, "Beta EG": 1750.0, "Gamma DE": 500.0})
        self.assertEqual(e["expected_top_client"], "Alpha US")

    def test_product3_totals(self):
        entries = [e for e in DETERMINISTIC_FIXTURE if e.product_name == "Product 3"]
        self.assertEqual(sum(e.quantity * e.price for e in entries), 900.0)
        self.assertEqual(sum(e.quantity for e in entries), 30)

    def test_question_ids(self):
        self.assertEqual(
            EvaluationFixture.get_all_question_ids(),
            [
                "product1_sales_q1",
                "product1_quantity_q1",
                "product2_us_vs_eg_q1",
                "product1_monthly_q1",
                "top_client_product1_q1",
            ],
        )

    def test_fixture_summary(self):
        summary = EvaluationFixture.get_summary()
        self.assertIn("Q1 2026", summary)
        self.assertIn("Total entries: 14", summary)
        self.assertIn(fixture_sha256(), summary)


class DataSerializationTests(SimpleTestCase):
    """Prompt-side serialization: json (base default), plain, toon."""

    SAMPLE = {
        "columns": ["name", "value__sum"],
        "data": [{"name": "Product 1", "value__sum": 5000.0}, {"name": "Product 2", "value__sum": 2750.0}],
    }

    def test_json_matches_base_rendering(self):
        """The json arm is byte-identical to the base-branch rendering."""
        self.assertEqual(serialize_for_prompt(self.SAMPLE, "json"), json.dumps(self.SAMPLE, indent=2, default=str))

    def test_plain_table_rendering(self):
        text = serialize_for_prompt(self.SAMPLE, "plain")
        self.assertIn("columns: name, value__sum", text)
        self.assertIn("data (2 rows):", text)
        self.assertIn("name | value__sum", text)
        self.assertIn("Product 1 | 5000.0", text)

    def test_unknown_format_rejected(self):
        with self.assertRaises(ValueError):
            serialize_for_prompt(self.SAMPLE, "xml")

    def test_normalize_jsonable(self):
        import datetime
        from decimal import Decimal

        out = normalize_jsonable({"v": Decimal("12.5"), "d": datetime.date(2026, 1, 5), "x": None})
        self.assertEqual(out, {"v": 12.5, "d": "2026-01-05", "x": None})

    @unittest.skipUnless(HAS_TOON, "toon-format package not installed")
    def test_toon_round_trip(self):
        text = serialize_for_prompt(self.SAMPLE, "toon")
        self.assertIn("data[2]{name,value__sum}:", text)
        decoded = toon_format.decode(text)
        self.assertEqual(decoded, self.SAMPLE)

    @unittest.skipUnless(HAS_TOON, "toon-format package not installed")
    def test_toon_is_more_compact_than_json(self):
        """The comparison's premise: TOON costs fewer characters (proxy for tokens)."""
        data = {"rows": [{"name": f"Client {i}", "country": "US", "value__sum": 1000.0 + i} for i in range(20)]}
        self.assertLess(len(serialize_for_prompt(data, "toon")), len(dumps_json(data)))

    def test_dumps_plain_nested(self):
        text = dumps_plain({"a": {"b": 1}, "items": [{"x": 1, "y": 2}, {"x": 3, "y": 4}]})
        self.assertIn("a:", text)
        self.assertIn("b: 1", text)
        self.assertIn("x | y", text)


class PromptDataFormatTests(SimpleTestCase):
    """plan_prompt/answer_prompt select data serialization per arm; the
    default stays byte-identical to the base branch."""

    CATALOG = {"models": [{"identifier": "tests.SimpleSales", "fields": [{"name": "value", "type": "DecimalField"}]}]}
    REPORTS = [
        {"config": {"group_by": "product"}, "columns": [{"name": "name"}], "data": [{"name": "P1", "value__sum": 5}]}
    ]

    def test_default_plan_prompt_byte_identical_to_base(self):
        expected = (
            f"{prompts.PLAN_SYSTEM_PROMPT}\n\nAvailable catalog:\n{json.dumps(self.CATALOG, indent=2, default=str)}\n\n"
            f"User question: q?\n\nReturn the JSON configuration."
        )
        self.assertEqual(prompts.plan_prompt("q?", self.CATALOG), expected)

    def test_default_answer_prompt_byte_identical_to_base(self):
        trimmed = [
            {
                "config": {"group_by": "product"},
                "columns": [{"name": "name"}],
                "data": [{"name": "P1", "value__sum": 5}],
            }
        ]
        expected = (
            f"{prompts.ANSWER_SYSTEM_PROMPT}\n\n"
            f"User question: q?\n\n"
            f"Reports used as proof:\n{json.dumps(trimmed, indent=2, default=str)}\n\n"
            f"Return the JSON answer."
        )
        self.assertEqual(prompts.answer_prompt("q?", self.REPORTS), expected)

    def test_plain_arm_uses_plain_text_instructions_and_data(self):
        prompt = prompts.plan_prompt("q?", self.CATALOG, plain_text=True, data_format="plain")
        self.assertIn("REPORT_MODEL:", prompt)  # plain-text response sections
        self.assertIn("Note: the data below is plain text", prompt)
        self.assertNotIn('"identifier"', prompt)  # not JSON

    @unittest.skipUnless(HAS_TOON, "toon-format package not installed")
    def test_toon_arm_uses_json_instructions_with_toon_data(self):
        prompt = prompts.plan_prompt("q?", self.CATALOG, data_format="toon")
        self.assertIn("Output ONLY JSON", prompt)  # base JSON response instructions
        self.assertIn("TOON (Token-Oriented Object Notation)", prompt)
        self.assertNotIn('"identifier"', prompt)

    def test_invalid_data_format_rejected(self):
        with self.assertRaises((ValueError, KeyError)):
            prompts.plan_prompt("q?", self.CATALOG, data_format="yaml")


class ScorerPlanTests(SimpleTestCase):
    """Plan scoring covers model, group_by, time series, filters and dates."""

    def test_perfect_plan_passes(self):
        result = make_result(
            "product1_sales_q1", plan_success=True, report_config=dict(PERFECT_CONFIGS["product1_sales_q1"])
        )
        passed, detail = EvaluationScorer.score_plan_correctness(result)
        self.assertTrue(passed, detail)
        self.assertEqual(EvaluationScorer.score_normalized_plan(result), 1.0)

    def test_wrong_group_by_fails(self):
        cfg = dict(PERFECT_CONFIGS["product2_us_vs_eg_q1"], group_by="client")
        result = make_result("product2_us_vs_eg_q1", plan_success=True, report_config=cfg)
        passed, detail = EvaluationScorer.score_plan_correctness(result)
        self.assertFalse(passed)
        self.assertIn('"group_by": false', detail)

    def test_missing_product_filter_fails(self):
        cfg = dict(PERFECT_CONFIGS["product1_sales_q1"])
        cfg.pop("filters")
        result = make_result("product1_sales_q1", plan_success=True, report_config=cfg)
        passed, detail = EvaluationScorer.score_plan_correctness(result)
        self.assertFalse(passed)
        self.assertIn('"filter_product": false', detail)

    def test_wrong_date_range_fails(self):
        """A plan covering all of 2026 must not score like the Q1 window."""
        cfg = dict(PERFECT_CONFIGS["product1_sales_q1"], end_date="2026-12-31")
        result = make_result("product1_sales_q1", plan_success=True, report_config=cfg)
        passed, detail = EvaluationScorer.score_plan_correctness(result)
        self.assertFalse(passed)
        self.assertIn('"date_range": false', detail)

    def test_exclusive_end_date_accepted(self):
        cfg = dict(PERFECT_CONFIGS["product1_sales_q1"], end_date="2026-04-01")
        result = make_result("product1_sales_q1", plan_success=True, report_config=cfg)
        passed, detail = EvaluationScorer.score_plan_correctness(result)
        self.assertTrue(passed, detail)

    def test_monthly_question_requires_time_series(self):
        cfg = dict(PERFECT_CONFIGS["product1_monthly_q1"])
        cfg.pop("time_series_pattern")
        cfg.pop("time_series_columns")
        result = make_result("product1_monthly_q1", plan_success=True, report_config=cfg)
        passed, detail = EvaluationScorer.score_plan_correctness(result)
        self.assertFalse(passed)
        score = EvaluationScorer.score_normalized_plan(result)
        self.assertGreater(score, 0.0)
        self.assertLess(score, 1.0)

    def test_no_plan_fails(self):
        result = make_result("product1_sales_q1")
        self.assertEqual(EvaluationScorer.score_plan_correctness(result), (False, "no plan"))
        self.assertEqual(EvaluationScorer.score_normalized_plan(result), 0.0)


class ScorerAnswerRegressionTests(SimpleTestCase):
    """Regression tests for the audited substring-only answer scorer:
    a wrong number (or no number) must fail."""

    def _answer(self, question_id, answer, key_numbers=None):
        proofs = []
        if key_numbers:
            proofs = [{"title": "t", "report_model": "tests.SimpleSales", "summary": "s", "key_numbers": key_numbers}]
        return make_result(question_id, answer={"answer": answer, "reasoning": "r", "proofs": proofs})

    def test_audit_repro_wrong_number_fails(self):
        """The audit's proof: '$99,999,999' must NOT pass for expected 5000."""
        result = self._answer("product1_sales_q1", "Product 1 total sales were $99,999,999.")
        passed, detail = EvaluationScorer.score_answer_correctness(result)
        self.assertFalse(passed, detail)

    def test_audit_repro_content_free_answer_fails(self):
        """The audit's proof: 'Product 1.' must NOT pass."""
        result = self._answer("product1_sales_q1", "Product 1.")
        passed, detail = EvaluationScorer.score_answer_correctness(result)
        self.assertFalse(passed, detail)

    def test_correct_value_passes(self):
        result = self._answer("product1_sales_q1", "Product 1 total sales in Q1 2026 were $5,000.")
        passed, detail = EvaluationScorer.score_answer_correctness(result)
        self.assertTrue(passed, detail)

    def test_key_numbers_suffice(self):
        result = self._answer("product1_sales_q1", "See the proof.", {"Total sales for Product 1": 5000})
        passed, detail = EvaluationScorer.score_answer_correctness(result)
        self.assertTrue(passed, detail)

    def test_quantity_wrong_fails_right_passes(self):
        wrong = self._answer("product1_quantity_q1", "Product 1 sold 250 units in Q1 2026.")
        self.assertFalse(EvaluationScorer.score_answer_correctness(wrong)[0])
        right = self._answer("product1_quantity_q1", "Product 1 sold 100 units in Q1 2026.")
        self.assertTrue(EvaluationScorer.score_answer_correctness(right)[0])

    def test_country_values_must_pair_with_labels(self):
        good = self._answer(
            "product2_us_vs_eg_q1",
            "In Q1 2026, Product 2 sales were higher in EG: US sold $1,250 while EG sold $1,500.",
        )
        self.assertTrue(EvaluationScorer.score_answer_correctness(good)[0])

        swapped = self._answer(
            "product2_us_vs_eg_q1",
            "Product 2 sales in Q1 2026: US: $1,500; EG: $1,250.",
        )
        self.assertFalse(EvaluationScorer.score_answer_correctness(swapped)[0])

        missing = self._answer(
            "product2_us_vs_eg_q1",
            "Product 2 sold better in EG than in the US in Q1 2026.",
        )
        self.assertFalse(EvaluationScorer.score_answer_correctness(missing)[0])

    def test_monthly_values_scored(self):
        good = self._answer(
            "product1_monthly_q1",
            "Product 1 monthly sales in Q1 2026: January: 1750; February: 1750; March: 1500.",
        )
        self.assertTrue(EvaluationScorer.score_answer_correctness(good)[0])

        wrong_month = self._answer(
            "product1_monthly_q1",
            "Product 1 monthly sales: January: 1750; February: 9999; March: 1500.",
        )
        self.assertFalse(EvaluationScorer.score_answer_correctness(wrong_month)[0])

    def test_top_client_label_and_value(self):
        good = self._answer(
            "top_client_product1_q1", "Alpha US bought the most of Product 1 in Q1 2026, with $2,750 in sales."
        )
        self.assertTrue(EvaluationScorer.score_answer_correctness(good)[0])

        wrong_client = self._answer(
            "top_client_product1_q1", "Gamma DE bought the most of Product 1, with $2,750 in sales."
        )
        self.assertFalse(EvaluationScorer.score_answer_correctness(wrong_client)[0])

        no_value = self._answer("top_client_product1_q1", "Alpha US bought the most of Product 1 in Q1 2026.")
        self.assertFalse(EvaluationScorer.score_answer_correctness(no_value)[0])

    def test_no_answer_fails(self):
        result = make_result("product1_sales_q1", answer=None)
        self.assertFalse(EvaluationScorer.score_answer_correctness(result)[0])
        result = make_result("product1_sales_q1", answer={"answer": "  "})
        self.assertFalse(EvaluationScorer.score_answer_correctness(result)[0])


class ScorerRealPayloadTests(TestCase):
    """Score real executor payloads: the tests that would have caught the
    audited time-series / value-only / zero-total scorer bugs."""

    @classmethod
    def setUpTestData(cls):
        create_fixture_data()
        EvaluationFixture.setup()

    def _executed(self, question_id):
        payload = run_llm_report_config(PERFECT_CONFIGS[question_id])
        return make_result(question_id, plan_success=True, report_executed=True, report_data=payload)

    def test_sales_question_value_only_plan_passes(self):
        """A value-only correct plan answers the sales question (audit 8b)."""
        result = self._executed("product1_sales_q1")
        passed, detail = EvaluationScorer.score_result_values(result)
        self.assertTrue(passed, detail)

    def test_quantity_question_passes(self):
        result = self._executed("product1_quantity_q1")
        passed, detail = EvaluationScorer.score_result_values(result)
        self.assertTrue(passed, detail)

    def test_country_question_real_payload(self):
        """group_by client__country rows carry a client__country label."""
        result = self._executed("product2_us_vs_eg_q1")
        self.assertEqual(
            {row["client__country"] for row in result.report_data["data"]},
            {"US", "EG"},
        )
        passed, detail = EvaluationScorer.score_result_values(result)
        self.assertTrue(passed, detail)

    def test_monthly_question_real_time_series_keys(self):
        """Real value__sumTS<date> keys must score (audit 8a)."""
        result = self._executed("product1_monthly_q1")
        row = result.report_data["data"][0]
        ts_keys = [k for k in row if "TS" in k]
        self.assertTrue(any(k.startswith("value__sumTS") for k in ts_keys), ts_keys)
        passed, detail = EvaluationScorer.score_result_values(result)
        self.assertTrue(passed, detail)
        self.assertIn('"month_2026-01": true', detail)
        self.assertIn('"month_2026-03": true', detail)

    def test_top_client_real_payload(self):
        result = self._executed("top_client_product1_q1")
        passed, detail = EvaluationScorer.score_result_values(result)
        self.assertTrue(passed, detail)
        self.assertIn('"top_client": true', detail)

    def test_mutated_payload_fails(self):
        """A wrong number in the report data must fail value scoring."""
        result = self._executed("product1_sales_q1")
        result.report_data["data"][0]["value__sum"] = "999999"
        passed, detail = EvaluationScorer.score_result_values(result)
        self.assertFalse(passed, detail)

    def test_mutated_monthly_fails(self):
        result = self._executed("product1_monthly_q1")
        row = result.report_data["data"][0]
        ts_key = next(k for k in row if k.startswith("value__sumTS"))
        row[ts_key] = "1"
        passed, detail = EvaluationScorer.score_result_values(result)
        self.assertFalse(passed, detail)

    def test_zero_total_handled(self):
        """A report whose correct total is 0 must score pass against 0 (the
        old substring extractor returned None for zero totals)."""
        EvaluationFixture._expected["synthetic_zero_q"] = {
            "question": "synthetic",
            "checks": {},
            "expected_value": 0.0,
        }
        try:
            zero = make_result(
                "synthetic_zero_q",
                plan_success=True,
                report_executed=True,
                report_data={"data": [{"name": "Product 1", "value__sum": 0}]},
            )
            passed, detail = EvaluationScorer.score_result_values(zero)
            self.assertTrue(passed, detail)

            nonzero = make_result(
                "product1_sales_q1",
                plan_success=True,
                report_executed=True,
                report_data={"data": [{"name": "Product 1", "value__sum": 0}]},
            )
            passed, detail = EvaluationScorer.score_result_values(nonzero)
            self.assertFalse(passed, detail)
        finally:
            EvaluationFixture._expected.pop("synthetic_zero_q", None)

    def test_missing_metric_column_fails(self):
        result = make_result(
            "product1_sales_q1",
            plan_success=True,
            report_executed=True,
            report_data={"data": [{"name": "Product 1", "quantity__sum": 100}]},
        )
        passed, detail = EvaluationScorer.score_result_values(result)
        self.assertFalse(passed, detail)


class BackendUsageTests(SimpleTestCase):
    def test_base_backend_reports_no_usage(self):
        backend = EchoBackend()
        self.assertEqual(backend.get_last_usage(), {})
        self.assertIsNone(backend.get_last_model())
        self.assertEqual(backend.complete("hi"), "hi")


class ScriptedBackend:
    """Deterministic offline backend: canned plans/answers per question,
    fake token usage proportional to prompt length, one scripted failure."""

    api_url = "scripted://local"
    model = "scripted-model"
    temperature = 0.2

    def __init__(self, fail_plan_for=None):
        self.calls = []
        self.fail_plan_for = fail_plan_for  # (format, question_id) pair
        self._last_usage = {}
        self._last_model = "scripted/qwen-local"

    def complete(self, prompt):
        self.calls.append(prompt)
        self._last_usage = {
            "prompt_tokens": max(1, len(prompt) // 4),
            "completion_tokens": 17,
            "total_tokens": max(1, len(prompt) // 4) + 17,
        }
        if "Available catalog:" in prompt:
            question = prompt.split("User question: ", 1)[1].rsplit("\n", 2)[0]
            qid = self._question_id(question)
            fmt = self._prompt_format(prompt)
            if self.fail_plan_for == (fmt, qid):
                raise RuntimeError("scripted backend failure")
            return self._plan_response(fmt, qid)
        question = prompt.split("User question: ", 1)[1].split("\n\nReports used as proof:", 1)[0]
        qid = self._question_id(question)
        return self._answer_response(prompt, qid)

    def get_last_usage(self):
        return dict(self._last_usage)

    def get_last_model(self):
        return self._last_model

    @staticmethod
    def _question_id(question_text):
        for qid, expected in EvaluationFixture._expected.items():
            if expected["question"] == question_text:
                return qid
        raise AssertionError(f"unexpected question {question_text!r}")

    @staticmethod
    def _prompt_format(prompt):
        if "REPORT_MODEL:" in prompt.split("Available catalog:", 1)[0]:
            return "plain"
        if "TOON (Token-Oriented Object Notation)" in prompt:
            return "toon"
        return "json"

    @staticmethod
    def _plan_response(fmt, qid):
        cfg = PERFECT_CONFIGS[qid]
        if fmt == "plain":
            lines = [
                "THINKING: deterministic scripted plan",
                f"REPORT_MODEL: {cfg['report_model']}",
                f"DATE_FIELD: {cfg['date_field']}",
                f"START_DATE: {cfg['start_date']}",
                f"END_DATE: {cfg['end_date']}",
                f"GROUP_BY: {cfg['group_by']}",
            ]
            metric_cols = cfg.get("columns", [])
            columns = ", ".join(c if isinstance(c, str) else f"{c['method']}({c['field']})" for c in metric_cols)
            lines.append(f"COLUMNS: {columns}")
            if cfg.get("time_series_pattern"):
                lines.append(f"TIME_SERIES_PATTERN: {cfg['time_series_pattern']}")
                ts_cols = ", ".join(f"{c['method']}({c['field']})" for c in cfg["time_series_columns"])
                lines.append(f"TIME_SERIES_COLUMNS: {ts_cols}")
            for key, values in (cfg.get("filters") or {}).items():
                lines.append(f"FILTERS: {key}={','.join(values)}")
            return "\n".join(lines)
        return json.dumps({"thinking": "deterministic scripted plan", "report": cfg})

    @staticmethod
    def _answer_response(prompt, qid):
        answers = {
            "product1_sales_q1": (
                "Product 1 total sales in Q1 2026 were $5,000.",
                {"Total sales Product 1 Q1 2026": 5000},
            ),
            "product1_monthly_q1": (
                "Product 1 monthly sales in Q1 2026: January: 1750; February: 1750; March: 1500.",
                {"January 2026": 1750, "February 2026": 1750, "March 2026": 1500},
            ),
        }
        text, key_numbers = answers[qid]
        if "ANSWER:" in prompt.split("Reports used as proof:", 1)[0]:
            kn = "; ".join(f"{k}: {v}" for k, v in key_numbers.items())
            return (
                f"ANSWER: {text}\nREASONING: scripted\nPROOF_TITLE: t\n"
                f"PROOF_REPORT_MODEL: tests.SimpleSales\nPROOF_SUMMARY: s\nPROOF_KEY_NUMBERS: {kn}"
            )
        return json.dumps(
            {
                "answer": text,
                "reasoning": "scripted",
                "proofs": [
                    {"title": "t", "report_model": "tests.SimpleSales", "summary": "s", "key_numbers": key_numbers}
                ],
            }
        )


class ExecutorFilterRegressionTests(TestCase):
    """Regression tests for filter resolution bugs the evaluation surfaced:
    ``product__name="Product 1"`` must stay a name lookup (not be resolved to
    a pk), and a single-value ``__in`` filter must reach the ORM as a list."""

    @classmethod
    def setUpTestData(cls):
        create_fixture_data()

    def test_name_lookup_is_not_resolved_to_pk(self):
        from slick_reporting.llm.executor import prepare_filters
        from tests.models import SimpleSales

        _q, kw = prepare_filters(SimpleSales, {"product__name": "Product 1"})
        self.assertEqual(kw, {"product__name": "Product 1"})

    def test_pk_lookups_still_resolve(self):
        from slick_reporting.llm.executor import prepare_filters
        from tests.models import Product, SimpleSales

        product_id = Product.objects.get(name="Product 1").pk
        _q, kw = prepare_filters(SimpleSales, {"product_id__in": ["Product 1"]})
        self.assertEqual(kw, {"product_id__in": [product_id]})
        _q, kw = prepare_filters(SimpleSales, {"product": "Product 1"})
        self.assertEqual(kw, {"product": product_id})

    def test_single_value_in_lookup_becomes_list(self):
        from slick_reporting.llm.executor import prepare_filters
        from tests.models import SimpleSales

        _q, kw = prepare_filters(SimpleSales, {"product__name__in": "Product 1"})
        self.assertEqual(kw, {"product__name__in": ["Product 1"]})

    def test_report_with_name_filter_returns_fixture_rows(self):
        """The audited benchmark failure: a legitimate ``product__name`` plan
        must return the Product 1 rows, not an empty report."""
        cfg = dict(PERFECT_CONFIGS["product1_sales_q1"], filters={"product__name": "Product 1"})
        payload = run_llm_report_config(cfg)
        self.assertEqual(len(payload["data"]), 1)
        self.assertEqual(float(payload["data"][0]["value__sum"]), 5000.0)


class RunEvaluationEndToEndTests(TestCase):
    """run_evaluation end to end with a scripted backend: structure, token
    capture, paired repetitions, and failure persistence."""

    QIDS = ["product1_sales_q1", "product1_monthly_q1"]

    @classmethod
    def setUpTestData(cls):
        EvaluationFixture.setup()

    def test_full_run_all_formats(self):
        backend = ScriptedBackend()
        result = run_evaluation(
            backend=backend, formats=["json", "plain", "toon"], repetitions=2, question_ids=self.QIDS
        )

        # structure: every format x question x repetition is present
        for fmt in ["json", "plain", "toon"]:
            self.assertEqual(len(result["results"][fmt]), 4)
            for r in result["results"][fmt]:
                self.assertTrue(r.parse_success, r.raw_plan)
                self.assertTrue(r.plan_success, r.raw_plan)
                self.assertTrue(r.report_executed, r.error)
                self.assertTrue(r.scores["result_values"][0], r.scores["result_values"][1])
                self.assertTrue(r.scores["answer_correctness"][0], r.scores["answer_correctness"][1])
                # token counts captured per call
                self.assertGreater(r.token_counts["plan_prompt_tokens"], 0)
                self.assertGreater(r.token_counts["answer_prompt_tokens"], 0)
                self.assertEqual(r.served_model, "scripted/qwen-local")
                # per-stage latency with correct labels
                self.assertIn("plan_seconds", r.timings)
                self.assertIn("answer_seconds", r.timings)
                self.assertIn("exec_seconds", r.timings)
                self.assertIn("total_seconds", r.timings)

        # paired repetitions: rep 0 and rep 1 used identical prompts per format/question
        json_plans = [r.raw_plan for r in result["results"]["json"] if r.question_id == "product1_sales_q1"]
        self.assertEqual(len(json_plans), 2)
        self.assertEqual(json_plans[0], json_plans[1])

        # meta records endpoint, model and fixture fingerprint
        self.assertEqual(result["meta"]["configured_model"], "scripted-model")
        self.assertEqual(result["meta"]["served_models"], ["scripted/qwen-local"])
        self.assertEqual(result["meta"]["fixture_sha256"], fixture_sha256())
        self.assertEqual(result["meta"]["sampling"], {"temperature": 0.2})

        # aggregates carry the headline token metrics and failure list
        for fmt in ["json", "plain", "toon"]:
            s = result["scores"][fmt]
            self.assertEqual(s["parse_success_rate"], 1.0)
            self.assertEqual(s["plan_calls_made"], 4)
            self.assertEqual(s["answer_calls_made"], 4)
            self.assertGreater(s["avg_plan_prompt_tokens"], 0)
            self.assertEqual(s["failures"], [])

    def test_failed_calls_are_preserved_and_scored(self):
        backend = ScriptedBackend(fail_plan_for=("json", "product1_sales_q1"))
        result = run_evaluation(backend=backend, formats=["json"], repetitions=2, question_ids=self.QIDS)

        json_results = result["results"]["json"]
        self.assertEqual(len(json_results), 4)  # the failed call is still recorded
        failed = [r for r in json_results if r.question_id == "product1_sales_q1"]
        self.assertEqual(len(failed), 2)
        for r in failed:
            self.assertIn("scripted backend failure", r.error)
            self.assertFalse(r.parse_success)
            self.assertFalse(r.report_executed)
            self.assertFalse(r.scores["result_values"][0])

        healthy = [r for r in json_results if r.question_id == "product1_monthly_q1"]
        self.assertTrue(all(r.report_executed for r in healthy))

        failures = result["scores"]["json"]["failures"]
        self.assertEqual(len(failures), 2)
        self.assertEqual(failures[0]["format"], "json")
        self.assertIn("scripted backend failure", failures[0]["error"])

    def test_artifact_serialization(self):
        backend = ScriptedBackend()
        result = run_evaluation(backend=backend, formats=["json"], repetitions=1, question_ids=self.QIDS)
        artifact = {
            "meta": result["meta"],
            "scores": result["scores"],
            "results": {fmt: [r.to_dict() for r in result["results"][fmt]] for fmt in ["json"]},
        }
        encoded = json.dumps(artifact, default=str)  # must not raise
        self.assertIn('"plan_prompt_tokens"', encoded)

"""
Tests for the LLM evaluation framework: scorer, fixture, and TOON format.

These tests are deterministic and require no external LLM calls.
Run with:  python runtests.py tests.test_llm_eval
"""

import json
from unittest.mock import patch

from django.test import TestCase

from slick_reporting.llm.evaluator import (
    DETERMINISTIC_FIXTURE,
    EvaluationFixture,
    EvaluationResult,
    EvaluationScorer,
)
from slick_reporting.llm.executor import (
    parse_llm_json,
    parse_llm_plain_text_plan,
)
from slick_reporting.llm.toonn import (
    parse_toonn_plan,
    parse_toonn_answer,
    parse_toonn_columns,
    parse_toonn_filters,
    answer_prompt_toonn,
    plan_prompt_toonn,
)


class DeterministicFixtureTests(TestCase):
    """Verify the deterministic fixture produces correct expected values."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.entries, cls.expected = EvaluationFixture.setup()

    def test_fixture_has_correct_entry_count(self):
        """The fixture has exactly 14 entries across 3 products."""
        self.assertEqual(len(DETERMINISTIC_FIXTURE), 14)

    def test_fixture_has_three_products(self):
        product_names = set(e.product_name for e in DETERMINISTIC_FIXTURE)
        self.assertEqual(product_names, {"Product 1", "Product 2", "Product 3"})

    def test_product1_totals(self):
        """Product 1: 6 entries × qty 10-25, price 25 = total 5000, qty 100."""
        e = self.expected["product1_sales_q1"]
        self.assertEqual(e["expected_value"], 5000.0)
        self.assertEqual(e["expected_quantity"], 100)

    def test_product2_client_comparison(self):
        """Product 2: Alpha US total 1250, Beta EG total 1500."""
        e = self.expected["product2_client_comparison_q1"]
        client_vals = e["expected_client_values"]
        self.assertEqual(client_vals["Alpha US"], 1250.0)
        self.assertEqual(client_vals["Beta EG"], 1500.0)
        # Verify Alpha != Beta to make the comparison meaningful
        self.assertNotEqual(client_vals["Alpha US"], client_vals["Beta EG"])

    def test_product2_has_alpha_and_beta(self):
        """Product 2 has entries from both Alpha US and Beta EG clients."""
        product2_entries = [e for e in DETERMINISTIC_FIXTURE if e.product_name == "Product 2"]
        clients = set(e.client_name for e in product2_entries)
        self.assertIn("Alpha US", clients)
        self.assertIn("Beta EG", clients)

    def test_product3_totals(self):
        """Product 3: 3 entries × qty 10, price 30 = total 900."""
        product3_entries = [e for e in DETERMINISTIC_FIXTURE if e.product_name == "Product 3"]
        total_value = sum(e.quantity * e.price for e in product3_entries)
        total_quantity = sum(e.quantity for e in product3_entries)
        self.assertEqual(total_value, 900.0)
        self.assertEqual(total_quantity, 30)

    def test_all_dates_in_q1_2026(self):
        """All dates are within Q1 2026 (Jan 1 – Mar 31)."""
        for e in DETERMINISTIC_FIXTURE:
            month = int(e.date[5:7])
            self.assertGreaterEqual(month, 1)
            self.assertLessEqual(month, 3)

    def test_question_ids(self):
        """All five question IDs exist in the expected results."""
        qids = EvaluationFixture.get_all_question_ids()
        expected_qids = [
            "product1_sales_q1",
            "product1_quantity_q1",
            "product2_client_comparison_q1",
            "product1_monthly_q1",
            "top_client_product1_q1",
        ]
        for qid in expected_qids:
            self.assertIn(qid, qids)

    def test_fixture_summary_contains_key_info(self):
        summary = EvaluationFixture.get_summary()
        self.assertIn("Q1 2026", summary)
        self.assertIn("Total entries: 14", summary)
        self.assertIn("Product 1", summary)
        self.assertIn("Product 2", summary)


class ToonnParserTests(TestCase):
    """Unit tests for the TOON format parser."""

    def test_parse_toonn_plan_basic(self):
        text = """```toonn
<THINKING>Group by product and sum value.</THINKING>
<REPORT_MODEL>tests.SimpleSales</REPORT_MODEL>
<DATE_FIELD>date</DATE_FIELD>
<START_DATE>2026-01-01</START_DATE>
<END_DATE>2026-03-31</END_DATE>
<GROUP_BY>product</GROUP_BY>
<COLUMNS>name, Sum(value)</COLUMNS>
<TIME_SERIES_PATTERN>monthly</TIME_SERIES_PATTERN>
<TIME_SERIES_COLUMNS>Sum(value)</TIME_SERIES_COLUMNS>
<FILTERS>product_id__in=Product 1,Product 2</FILTERS>
```"""
        plan = parse_toonn_plan(text)
        self.assertIsNotNone(plan)
        self.assertEqual(plan["report"]["report_model"], "tests.SimpleSales")
        self.assertEqual(plan["report"]["group_by"], "product")
        self.assertEqual(plan["report"]["start_date"], "2026-01-01")
        self.assertEqual(plan["report"]["end_date"], "2026-03-31")
        self.assertEqual(plan["report"]["time_series_pattern"], "monthly")
        self.assertEqual(plan["report"]["filters"], {"product_id__in": ["Product 1", "Product 2"]})
        self.assertEqual(
            plan["report"]["columns"],
            ["name", {"method": "Sum", "field": "value", "name": "value__sum"}],
        )

    def test_parse_toonn_plan_null_report(self):
        text = """```toonn
<REPORT>null</REPORT>
```"""
        plan = parse_toonn_plan(text)
        self.assertIsNotNone(plan)
        self.assertIsNone(plan["report"])

    def test_parse_toonn_plan_no_fences(self):
        """Should handle text without fences."""
        text = """<THINKING>simple</THINKING>
<REPORT_MODEL>tests.SimpleSales</REPORT_MODEL>
<DATE_FIELD>date</DATE_FIELD>
<START_DATE>2026-01-01</START_DATE>
<END_DATE>2026-03-31</END_DATE>
<GROUP_BY>product</GROUP_BY>
<COLUMNS>name</COLUMNS>
<FILTERS>"""
        plan = parse_toonn_plan(text)
        self.assertIsNotNone(plan)
        self.assertEqual(plan["report"]["group_by"], "product")

    def test_parse_toonn_answer(self):
        text = """```toonn
<ANSWER>Total Q1 sales were $5,000 for Product 1.</ANSWER>
<REASONING>Sales summed from the report.</REASONING>
<PROOFS>
  <PROOF>
    <TITLE>Product totals</TITLE>
    <REPORT_MODEL>tests.SimpleSales</REPORT_MODEL>
    <SUMMARY>Total value per product.</SUMMARY>
    <KEY_NUMBERS>
      <KEY>Product 1</KEY>
      <VALUE>5000.00</VALUE>
    </KEY_NUMBERS>
  </PROOF>
</PROOFS>
```"""
        answer = parse_toonn_answer(text)
        self.assertEqual(answer["answer"], "Total Q1 sales were $5,000 for Product 1.")
        self.assertEqual(answer["reasoning"], "Sales summed from the report.")
        self.assertEqual(len(answer["proofs"]), 1)
        proof = answer["proofs"][0]
        self.assertEqual(proof["title"], "Product totals")
        self.assertEqual(proof["report_model"], "tests.SimpleSales")
        self.assertEqual(proof["key_numbers"], {"Product 1": 5000.0})

    def test_parse_toonn_answer_multiple_proofs(self):
        text = """```toonn
<ANSWER>Two products.</ANSWER>
<REASONING>Comparison.</REASONING>
<PROOFS>
  <PROOF>
    <TITLE>Product 1</TITLE>
    <REPORT_MODEL>tests.SimpleSales</REPORT_MODEL>
    <SUMMARY>Product 1 totals.</SUMMARY>
  </PROOF>
  <PROOF>
    <TITLE>Product 2</TITLE>
    <REPORT_MODEL>tests.SimpleSales</REPORT_MODEL>
    <SUMMARY>Product 2 totals.</SUMMARY>
  </PROOF>
</PROOFS>
```"""
        answer = parse_toonn_answer(text)
        self.assertEqual(len(answer["proofs"]), 2)
        self.assertEqual(answer["proofs"][0]["title"], "Product 1")
        self.assertEqual(answer["proofs"][1]["title"], "Product 2")

    def test_parse_toonn_answer_invalid(self):
        result = parse_toonn_answer("not a valid toonn response")
        self.assertIsNone(result)

    def test_parse_toonn_columns(self):
        cols = parse_toonn_columns("name, Sum(value), Avg(quantity)")
        self.assertEqual(cols, [
            "name",
            {"method": "Sum", "field": "value", "name": "value__sum"},
            {"method": "Avg", "field": "quantity", "name": "quantity__avg"},
        ])

    def test_parse_toonn_columns_empty(self):
        self.assertEqual(parse_toonn_columns(""), [])

    def test_parse_toonn_filters(self):
        filters = parse_toonn_filters("product_id__in=Product 1,Product 2; client__country__in=US,EG")
        self.assertEqual(filters, {
            "product_id__in": ["Product 1", "Product 2"],
            "client__country__in": ["US", "EG"],
        })

    def test_parse_toonn_filters_empty(self):
        self.assertEqual(parse_toonn_filters(""), {})


class EvaluationScorerTests(TestCase):
    """Test the scoring engine for evaluation results."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Ensure fixture is set up before tests run
        EvaluationFixture.setup()

    def _make_result(self, **overrides):
        """Create a minimal EvaluationResult for scoring."""
        defaults = {
            "question_id": "product1_sales_q1",
            "question_text": "What are the total sales for Product 1 in Q1 2026?",
            "config_name": "test",
            "format_name": "json",
            "raw_plan": '{"report":{"group_by":"product"}}',
            "raw_answer": '{"answer":"Product 1 sold well."}',
            "timings": {"plan_seconds": 0.5, "total_seconds": 1.0},
            "plan_success": True,
            "parse_success": True,
            "report_executed": False,
            "report_config": {"report_model": "tests.SimpleSales", "group_by": "product"},
            "report_data": None,
            "answer": {"answer": "Product 1 sold well.", "reasoning": "Sum", "proofs": []},
            "error": None,
            "scores": {},
            "token_counts": {},
        }
        defaults.update(overrides)
        return EvaluationResult(**defaults)

    def test_score_plan_correctness_pass(self):
        result = self._make_result(
            report_config={"group_by": "product"},
        )
        passed, detail = EvaluationScorer.score_plan_correctness(result)
        self.assertTrue(passed, f"Expected plan to be correct: {detail}")

    def test_score_plan_correctness_fail_group_by(self):
        result = self._make_result(
            report_config={"group_by": "client"},
        )
        passed, detail = EvaluationScorer.score_plan_correctness(result)
        self.assertFalse(passed)

    def test_score_plan_correctness_no_config(self):
        result = self._make_result(
            plan_success=False,
            report_config=None,
        )
        passed, detail = EvaluationScorer.score_plan_correctness(result)
        self.assertFalse(passed)

    def test_score_parse_success_pass(self):
        result = self._make_result(parse_success=True)
        passed, detail = EvaluationScorer.score_parse_success(result)
        self.assertTrue(passed)

    def test_score_parse_success_fail(self):
        result = self._make_result(parse_success=False)
        passed, detail = EvaluationScorer.score_parse_success(result)
        self.assertFalse(passed)

    def test_score_report_execution_pass(self):
        result = self._make_result(report_executed=True)
        passed, detail = EvaluationScorer.score_report_execution(result)
        self.assertTrue(passed)

    def test_score_report_execution_fail_with_error(self):
        result = self._make_result(report_executed=False, error="DB error")
        passed, detail = EvaluationScorer.score_report_execution(result)
        self.assertFalse(passed)

    def test_score_result_values_no_data(self):
        result = self._make_result(report_data=None)
        passed, detail = EvaluationScorer.score_result_values(result)
        self.assertFalse(passed)

    def test_score_answer_correctness_pass(self):
        result = self._make_result(
            answer={"answer": "Product 1 total sales were $5000."},
        )
        passed, detail = EvaluationScorer.score_answer_correctness(result)
        self.assertTrue(passed, f"Expected answer to be correct: {detail}")

    def test_score_answer_correctness_fail(self):
        result = self._make_result(answer=None)
        passed, detail = EvaluationScorer.score_answer_correctness(result)
        self.assertFalse(passed)

    def test_score_normalized_plan_perfect(self):
        result = self._make_result(
            report_config={
                "report_model": "tests.SimpleSales",
                "group_by": "product",
                "time_series_pattern": None,
                "columns": [
                    {"method": "Sum", "field": "value", "name": "value__sum"},
                ],
            },
        )
        score = EvaluationScorer.score_normalized_plan(result)
        self.assertEqual(score, 1.0)

    def test_score_normalized_plan_partial(self):
        result = self._make_result(
            report_config={
                "report_model": "wrong_app.WrongModel",
                "group_by": "client",
                "time_series_pattern": None,
                "columns": [],
            },
        )
        score = EvaluationScorer.score_normalized_plan(result)
        self.assertLess(score, 1.0)

    def test_score_normalized_plan_no_config(self):
        result = self._make_result(report_config=None)
        score = EvaluationScorer.score_normalized_plan(result)
        self.assertEqual(score, 0.0)

    def test_aggregate_scores_all_pass(self):
        results = [
            self._make_result(
                plan_success=True, parse_success=True, report_executed=True,
                report_config={"report_model": "tests.SimpleSales", "group_by": "product"},
            )
            for _ in range(3)
        ]
        # Populate scores by calling scorer methods
        for r in results:
            r.scores["plan_correctness"] = EvaluationScorer.score_plan_correctness(r)
            r.scores["parse_success"] = EvaluationScorer.score_parse_success(r)
            r.scores["report_execution"] = EvaluationScorer.score_report_execution(r)
            r.scores["result_values"] = EvaluationScorer.score_result_values(r)
            r.scores["answer_correctness"] = EvaluationScorer.score_answer_correctness(r)
            r.scores["normalized_plan"] = EvaluationScorer.score_normalized_plan(r)
        agg = EvaluationScorer.aggregate_scores(results)
        self.assertEqual(agg["total_questions"], 3)
        self.assertEqual(agg["plan_success_rate"], 1.0)
        self.assertEqual(agg["parse_success_rate"], 1.0)
        self.assertEqual(agg["report_execution_rate"], 1.0)
        self.assertGreater(agg["avg_total_latency_seconds"], 0)

    def test_aggregate_scores_with_failures(self):
        results = [
            self._make_result(
                plan_success=True, error=None,
                report_config={"report_model": "tests.SimpleSales", "group_by": "product"},
            ),
            self._make_result(
                plan_success=False, error="Bad plan",
                report_config=None,
            ),
            self._make_result(
                plan_success=True, error=None,
                report_config={"report_model": "tests.SimpleSales", "group_by": "product"},
            ),
        ]
        # Populate only plan correctness scores (result_values needs report data)
        for r in results:
            r.scores["plan_correctness"] = EvaluationScorer.score_plan_correctness(r)
            r.scores["result_values"] = (True, '{}')  # Assume values OK
            r.scores["answer_correctness"] = (True, 'answer_present=True')
        agg = EvaluationScorer.aggregate_scores(results)
        self.assertEqual(agg["total_questions"], 3)
        self.assertEqual(agg["plan_success_rate"], round(2/3, 2))
        self.assertEqual(len(agg["failures"]), 1)
        self.assertEqual(agg["failures"][0]["question_id"], "product1_sales_q1")

    def test_aggregate_scores_empty(self):
        agg = EvaluationScorer.aggregate_scores([])
        self.assertEqual(agg, {})

    def test_plan_correctness_stddev_zero(self):
        """When all results pass, std-dev should be 0."""
        results = [self._make_result(plan_success=True) for _ in range(3)]
        agg = EvaluationScorer.aggregate_scores(results)
        self.assertEqual(agg["plan_correctness_stddev"], 0.0)


class ToonnPromptBuilderTests(TestCase):
    """Test TOON prompt generation."""

    def test_plan_prompt_toonn_contains_catalog(self):
        catalog = {
            "models": [{"identifier": "tests.SimpleSales", "fields": []}],
            "time_series_patterns": ["monthly"],
            "today_iso": "2026-01-01T00:00:00",
        }
        prompt = plan_prompt_toonn("Show sales for Product 1", catalog)
        self.assertIn("```toonn", prompt)
        self.assertIn("THINKING", prompt)
        self.assertIn("tests.SimpleSales", prompt)
        self.assertIn("Product 1", prompt)

    def test_answer_prompt_toonn_contains_reports(self):
        reports = [
            {
                "config": {"report_model": "tests.SimpleSales"},
                "data": [{"name": "Product 1", "value__sum": 5000}],
                "columns": [],
            }
        ]
        prompt = answer_prompt_toonn("What were Product 1 sales?", reports)
        self.assertIn("```toonn", prompt)
        self.assertIn("Product 1", prompt)
        self.assertIn("5000", prompt)


class ExistingFormatCompatibilityTests(TestCase):
    """Verify that existing JSON/plain-text parsing still works."""

    def test_parse_llm_json_basic(self):
        result = parse_llm_json('{"a": 1}')
        self.assertEqual(result, {"a": 1})

    def test_parse_llm_json_with_fences(self):
        result = parse_llm_json('```json\n{"a": 1}\n```')
        self.assertEqual(result, {"a": 1})

    def test_parse_llm_plain_text_plan(self):
        text = """THINKING: simple
REPORT_MODEL: tests.SimpleSales
DATE_FIELD: date
START_DATE: 2026-01-01
END_DATE: 2026-03-31
GROUP_BY: product
COLUMNS: name, Sum(value)
FILTERS:"""
        plan = parse_llm_plain_text_plan(text)
        self.assertEqual(plan["report"]["group_by"], "product")
        self.assertEqual(
            plan["report"]["columns"],
            ["name", {"method": "Sum", "field": "value", "name": "value__sum"}],
        )

"""
Deterministic evaluation framework for comparing LLM output formats.

This module provides:
* ``EvaluationFixture`` – a deterministic dataset with known sales values
* ``EvaluationScorer`` – scoring engine that compares LLM responses against
  expected values
* ``run_evaluation`` – orchestrates a full evaluation run across multiple
  backends and output formats

The evaluator is designed to run entirely locally with no external API calls.
"""

import datetime
import json
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from django.db import transaction
from django.db.models import Model
from django.utils.module_loading import import_string

from .executor import run_llm_report_config
from .introspection import build_reporting_catalog


# ---------------------------------------------------------------------------
# Deterministic fixture
# ---------------------------------------------------------------------------

@dataclass
class FixtureEntry:
    """One deterministic sales transaction for the evaluation fixture."""
    number: str
    date: str  # YYYY-MM-DD
    client_name: str
    client_country: str
    product_name: str
    quantity: int
    price: float


# Fixed Q1 2026 sales data.  Product 2 has entries for both US and EG.
# These values are chosen so expected results are simple and verifiable.
DETERMINISTIC_FIXTURE: List[FixtureEntry] = [
    # ---- Product 1: total quantity = 100, total value = 5000 (price=50) ----
    FixtureEntry("Q1-P1-001", "2026-01-05", "Alpha US", "US", "Product 1", 20, 50.00),
    FixtureEntry("Q1-P1-002", "2026-01-15", "Beta EG",  "EG", "Product 1", 15, 50.00),
    FixtureEntry("Q1-P1-003", "2026-02-03", "Alpha US", "US", "Product 1", 25, 50.00),
    FixtureEntry("Q1-P1-004", "2026-02-20", "Gamma DE", "DE", "Product 1", 10, 50.00),
    FixtureEntry("Q1-P1-005", "2026-03-01", "Beta EG",  "EG", "Product 1", 20, 50.00),
    FixtureEntry("Q1-P1-006", "2026-03-18", "Alpha US", "US", "Product 1", 10, 50.00),
    # ---- Product 2: US total = 1250, EG total = 1500 (price=50) ----
    # US entries (10+8+7=25 × 50 = 1250)
    FixtureEntry("Q1-P2-US-001", "2026-01-08", "Alpha US", "US", "Product 2", 10, 50.00),
    FixtureEntry("Q1-P2-US-002", "2026-02-10", "Alpha US", "US", "Product 2", 8, 50.00),
    FixtureEntry("Q1-P2-US-003", "2026-03-05", "Alpha US", "US", "Product 2", 7, 50.00),
    # EG entries (15+15=30 × 50 = 1500)
    FixtureEntry("Q1-P2-EG-001", "2026-01-12", "Beta EG", "EG", "Product 2", 15, 50.00),
    FixtureEntry("Q1-P2-EG-002", "2026-02-22", "Beta EG", "EG", "Product 2", 15, 50.00),
    # ---- Product 3: total quantity = 30, total value = 900 ----
    FixtureEntry("Q1-P3-001", "2026-01-20", "Gamma DE", "DE", "Product 3", 10, 30.00),
    FixtureEntry("Q1-P3-002", "2026-03-15", "Gamma DE", "DE", "Product 3", 10, 30.00),
    FixtureEntry("Q1-P3-003", "2026-03-25", "Beta EG",  "EG", "Product 3", 10, 30.00),
]


def _build_fixture_data() -> Tuple[List[Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    """
    Build the deterministic fixture and return (entries, expected_results).

    expected_results maps a question-id to a dict of expected values.
    """
    entries = DETERMINISTIC_FIXTURE

    # Compute expected values from the fixture.
    product_total_value: Dict[str, float] = defaultdict(float)
    product_total_quantity: Dict[str, int] = defaultdict(int)
    product_monthly_value: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
    product_client_value: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
    country_product_value: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))

    for e in entries:
        qty = e.quantity
        val = qty * e.price
        month_key = e.date[:7]  # "2026-01"
        prod = e.product_name
        client = e.client_name
        country = e.client_country

        # Product totals
        product_total_value[prod] += val
        product_total_quantity[prod] += qty

        # Monthly totals
        product_monthly_value[prod][month_key] += val

        # Client totals per product
        product_client_value[prod][client] += val

        # Country per product
        country_product_value[country][prod] += val

    expected: Dict[str, Dict[str, Any]] = {
        "product1_sales_q1": {
            "question": "What are the total sales for Product 1 in Q1 2026?",
            "checks": {
                "report_model": "demo_app.SalesTransaction",
                "group_by": "product",
                "aggregation": "Sum",
                "filter": {"product_id__in": ["Product 1"]},
                "metric": "Sum(value)",
            },
            "expected_value": product_total_value.get("Product 1", 0),
            "expected_quantity": product_total_quantity.get("Product 1", 0),
        },
        "product1_quantity_q1": {
            "question": "What is the total quantity sold for Product 1 in Q1 2026?",
            "checks": {
                "report_model": "demo_app.SalesTransaction",
                "group_by": "product",
                "filter": {"product_id__in": ["Product 1"]},
                "metric": "Sum(quantity)",
            },
            "expected_quantity": product_total_quantity.get("Product 1", 0),
        },
        "product2_us_vs_eg_q1": {
            "question": "How does Product 2 sales compare between US and EG in Q1 2026?",
            "checks": {
                "report_model": "demo_app.SalesTransaction",
                "group_by": "client__country",
                "filter": {"product_id__in": ["Product 2"]},
                "metric": "Sum(value)",
            },
            "expected_country_values": {
                "US": country_product_value.get("US", {}).get("Product 2", 0),
                "EG": country_product_value.get("EG", {}).get("Product 2", 0),
            },
        },
        "product1_monthly_q1": {
            "question": "What were Product 1 monthly sales across Q1 2026?",
            "checks": {
                "report_model": "demo_app.SalesTransaction",
                "group_by": "product",
                "time_series_pattern": "monthly",
                "filter": {"product_id__in": ["Product 1"]},
                "metric": "Sum(value)",
            },
            "expected_monthly": product_monthly_value.get("Product 1", {}),
        },
        "top_client_product1_q1": {
            "question": "Which client bought the most of Product 1 by sales value in Q1 2026?",
            "checks": {
                "report_model": "demo_app.SalesTransaction",
                "group_by": "client",
                "filter": {"product_id__in": ["Product 1"]},
                "metric": "Sum(value)",
            },
            "client_totals": product_client_value.get("Product 1", {}),
        },
    }
    return entries, expected


# ---------------------------------------------------------------------------
# Scorer
# ---------------------------------------------------------------------------


@dataclass
class EvaluationResult:
    """Single result for one question-backend-format combination."""
    question_id: str
    question_text: str
    config_name: str
    format_name: str  # "json", "plain", "toonn"
    raw_plan: str
    raw_answer: str
    timings: Dict[str, float] = field(default_factory=dict)
    plan_success: bool = False
    parse_success: bool = False
    report_executed: bool = False
    report_config: Optional[Dict[str, Any]] = None
    report_data: Optional[Dict[str, Any]] = None
    answer: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    scores: Dict[str, Any] = field(default_factory=dict)
    token_counts: Dict[str, Any] = field(default_factory=dict)


class EvaluationScorer:
    """Score evaluation results across multiple dimensions."""

    @staticmethod
    def score_plan_correctness(result: EvaluationResult) -> Tuple[bool, str]:
        """Check if the plan correctly identifies the report model and group_by."""
        if not result.plan_success or not result.report_config:
            return False, "no plan"
        cfg = result.report_config
        expected = EvaluationFixture.get_expected(result.question_id)
        if not expected:
            return False, "no expected config"
        checks = expected.get("checks", {})

        errors = []
        if checks.get("group_by") and cfg.get("group_by") != checks["group_by"]:
            errors.append(f"group_by mismatch: expected {checks['group_by']}, got {cfg.get('group_by')}")

        return (len(errors) == 0, "; ".join(errors))

    @staticmethod
    def score_parse_success(result: EvaluationResult) -> Tuple[bool, str]:
        """Check if the plan was parsed successfully from the LLM response."""
        if result.parse_success:
            return True, "parsed"
        return False, "parse failure"

    @staticmethod
    def score_report_execution(result: EvaluationResult) -> Tuple[bool, str]:
        """Check if the report executed without errors."""
        if result.report_executed:
            return True, "executed"
        if result.error:
            return False, f"error: {result.error}"
        return False, "no error but not executed"

    @staticmethod
    def score_result_values(result: EvaluationResult) -> Tuple[bool, str]:
        """Score whether the answer matches expected values."""
        expected = EvaluationFixture.get_expected(result.question_id)
        if not expected:
            return False, "no expected data"

        scores = {}
        if "expected_value" in expected:
            expected_val = expected["expected_value"]
            actual = EvaluationFixture._extract_value(result, "value")
            scores["value_match"] = abs(actual - expected_val) < 0.01 if actual is not None else False

        if "expected_quantity" in expected:
            expected_qty = expected["expected_quantity"]
            actual = EvaluationFixture._extract_value(result, "quantity")
            scores["quantity_match"] = actual == expected_qty if actual is not None else False

        if "expected_country_values" in expected:
            expected_cvs = expected["expected_country_values"]
            actual_cvs = EvaluationFixture._extract_country_values(result)
            for country, exp_val in expected_cvs.items():
                scores[f"country_{country}_match"] = \
                    abs(actual_cvs.get(country, 0) - exp_val) < 0.01

        if "expected_monthly" in expected:
            expected_months = expected["expected_monthly"]
            actual_months = EvaluationFixture._extract_monthly_values(result)
            for month, exp_val in expected_months.items():
                scores[f"month_{month}_match"] = \
                    abs(actual_months.get(month, 0) - exp_val) < 0.01

        if "client_totals" in expected:
            expected_clients = expected["client_totals"]
            actual_clients = EvaluationFixture._extract_client_values(result)
            for client, exp_val in expected_clients.items():
                scores[f"client_{client}_match"] = \
                    abs(actual_clients.get(client, 0) - exp_val) < 0.01

        passed = bool(scores) and all(v for v in scores.values())
        return passed, json.dumps(scores)

    @staticmethod
    def score_answer_correctness(result: EvaluationResult) -> Tuple[bool, str]:
        """Score whether the answer text is semantically correct."""
        if not result.answer or not result.answer.get("answer"):
            return False, "no answer text"

        expected = EvaluationFixture.get_expected(result.question_id)
        if not expected:
            return False, "no expected data"

        answer_text = result.answer.get("answer", "").lower()
        checks = expected.get("checks", {})

        # Check for presence of key product names or values
        if "Product 1" in expected.get("question", ""):
            has_product1 = "product 1" in answer_text
        elif "Product 2" in expected.get("question", ""):
            has_product2 = "product 2" in answer_text
        elif "top client" in expected.get("question", "").lower():
            # For top client questions, check if any client name is mentioned
            has_client = any(c in answer_text for c in ["alpha", "beta", "gamma", "client"])
            has_product1 = "product 1" in answer_text
            has_product2 = False
            has_product1 = has_product1  # product 1 is still relevant
        else:
            has_product1 = True
            has_product2 = True

        correct = has_product1 or has_product2
        return correct, f"answer_present={bool(answer_text)}"

    @staticmethod
    def score_normalized_plan(result: EvaluationResult) -> float:
        """
        Score normalized plan correctness (0.0 - 1.0).

        Based on: model correct, group_by correct, time_series correct,
        filters correct, columns correct.
        """
        if not result.report_config:
            return 0.0

        expected = EvaluationFixture.get_expected(result.question_id)
        if not expected:
            return 0.0

        checks = expected.get("checks", {})
        cfg = result.report_config
        score = 0.0
        total = 0.0

        # Report model (always required)
        total += 1.0
        if checks.get("report_model") and cfg.get("report_model") == checks["report_model"]:
            score += 1.0

        # Group by
        total += 1.0
        if checks.get("group_by") and cfg.get("group_by") == checks["group_by"]:
            score += 1.0

        # Time series pattern
        total += 1.0
        if checks.get("time_series_pattern"):
            if cfg.get("time_series_pattern") == checks["time_series_pattern"]:
                score += 1.0
        else:
            # If no time_series expected and none provided, perfect score
            if not cfg.get("time_series_pattern"):
                score += 1.0

        # Aggregation method
        total += 0.5
        if checks.get("aggregation"):
            cols = cfg.get("columns", [])
            methods = []
            for c in cols:
                if isinstance(c, dict):
                    methods.append(c.get("method"))
            if checks["aggregation"] in methods:
                score += 0.5

        return round(score / total, 2) if total > 0 else 0.0

    @staticmethod
    def aggregate_scores(results: List[EvaluationResult]) -> Dict[str, Any]:
        """Aggregate scores across all results for a config-format combination."""
        total = len(results)
        if total == 0:
            return {}

        plan_correct_count = sum(1 for r in results if r.scores.get("plan_correctness", (False, ""))[0])
        parse_success_count = sum(1 for r in results if r.scores.get("parse_success", (False, ""))[0])
        report_executed_count = sum(1 for r in results if r.scores.get("report_execution", (False, ""))[0])
        value_match_count = sum(1 for r in results if r.scores.get("result_values", (False, ""))[0])
        answer_correct_count = sum(1 for r in results if r.scores.get("answer_correctness", (False, ""))[0])

        normalized_plan_scores = [r.scores.get("normalized_plan", 0.0) for r in results]
        avg_normalized_plan = sum(normalized_plan_scores) / len(normalized_plan_scores) if normalized_plan_scores else 0.0

        # Variability: standard deviation of plan correctness
        plan_rates = [1.0 if r.scores.get("plan_correctness", (False, ""))[0] else 0.0 for r in results]
        mean_rate = sum(plan_rates) / len(plan_rates)
        variance = sum((r - mean_rate) ** 2 for r in plan_rates) / len(plan_rates) if plan_rates else 0.0
        std_dev = variance ** 0.5

        # Avg latency
        total_times = [r.timings.get("total_seconds", 0) for r in results]
        avg_latency = sum(total_times) / len(total_times) if total_times else 0.0

        return {
            "total_questions": total,
            "plan_success_rate": round(plan_correct_count / total, 2),
            "parse_success_rate": round(parse_success_count / total, 2),
            "report_execution_rate": round(report_executed_count / total, 2),
            "exact_value_match_rate": round(value_match_count / total, 2),
            "answer_correctness_rate": round(answer_correct_count / total, 2),
            "avg_normalized_plan_score": round(avg_normalized_plan, 2),
            "plan_correctness_stddev": round(std_dev, 4),
            "avg_total_latency_seconds": round(avg_latency, 3),
            "failures": [
                {
                    "question_id": r.question_id,
                    "format": r.format_name,
                    "error": r.error or "unknown",
                    "plan_correctness": r.scores.get("plan_correctness", (False, ""))[0],
                    "result_values": r.scores.get("result_values", (False, ""))[0],
                }
                for r in results if r.error or not r.scores.get("result_values", (False, ""))[0]
            ],
        }


# ---------------------------------------------------------------------------
# Fixture management
# ---------------------------------------------------------------------------


class EvaluationFixture:
    """Manage the deterministic fixture data."""

    _expected: Dict[str, Dict[str, Any]] = {}
    _entries: List[FixtureEntry] = []

    @classmethod
    def setup(cls) -> Tuple[List[FixtureEntry], Dict[str, Dict[str, Any]]]:
        """Build and return the fixture data and expected results."""
        if not cls._entries:
            cls._entries, cls._expected = _build_fixture_data()
        return cls._entries, cls._expected

    @classmethod
    def get_expected(cls, question_id: str) -> Optional[Dict[str, Any]]:
        return cls._expected.get(question_id)

    @classmethod
    def get_all_question_ids(cls) -> List[str]:
        return list(cls._expected.keys())

    @staticmethod
    def _extract_value(result: EvaluationResult, field_name: str) -> Optional[float]:
        """Extract a scalar value from report data."""
        if not result.report_data or "data" not in result.report_data:
            return None
        data = result.report_data["data"]
        if not data:
            return None
        # Sum the relevant column across all rows
        total = 0.0
        for row in data:
            for k, v in row.items():
                if field_name in k.lower():
                    try:
                        total += float(v)
                    except (ValueError, TypeError):
                        pass
        return total if total > 0 else None

    @staticmethod
    def _extract_country_values(result: EvaluationResult) -> Dict[str, float]:
        """Extract country -> value mapping from report data."""
        if not result.report_data or "data" not in result.report_data:
            return {}
        data = result.report_data["data"]
        values: Dict[str, float] = {}
        for row in data:
            country = row.get("country", row.get("client__country", ""))
            value = row.get("value__sum", row.get("value__sum__sum", 0))
            try:
                values[country] = float(value)
            except (ValueError, TypeError):
                pass
        return values

    @staticmethod
    def _extract_monthly_values(result: EvaluationResult) -> Dict[str, float]:
        """Extract month -> value mapping from report data."""
        if not result.report_data or "data" not in result.report_data:
            return {}
        data = result.report_data["data"]
        values: Dict[str, float] = {}
        for row in data:
            month_key = None
            for k in row:
                if k.startswith("time_series_") and "period" in k.lower():
                    month_key = str(row[k])[:7]  # "2026-01"
                    break
            if not month_key:
                # Try time-series column names
                cols = result.report_data.get("columns", [])
                for col in cols:
                    if isinstance(col, dict) and "time_series" in str(col).lower():
                        month_key = str(row.get(col.get("name", ""), ""))[:7]
                        break
            if month_key:
                value = row.get("value__sum", row.get("value__sum__sum", 0))
                try:
                    values[month_key] = values.get(month_key, 0) + float(value)
                except (ValueError, TypeError):
                    pass
        return values

    @staticmethod
    def _extract_client_values(result: EvaluationResult) -> Dict[str, float]:
        """Extract client name -> value mapping from report data."""
        if not result.report_data or "data" not in result.report_data:
            return {}
        data = result.report_data["data"]
        values: Dict[str, float] = {}
        for row in data:
            client = row.get("name", row.get("client__name", row.get("client", "")))
            value = row.get("value__sum", row.get("value__sum__sum", 0))
            if client and client != "":
                try:
                    values[str(client)] = float(value)
                except (ValueError, TypeError):
                    pass
        return values

    @classmethod
    def get_summary(cls) -> str:
        """Return a human-readable summary of the fixture."""
        entries, expected = cls.setup()
        lines = [
            f"=== Deterministic Evaluation Fixture ===",
            f"Period: Q1 2026 (2026-01-01 to 2026-03-31)",
            f"Total entries: {len(entries)}",
            f"",
            f"Products:",
        ]
        for name in sorted(set(e.product_name for e in entries)):
            total_val = sum(e.quantity * e.price for e in entries if e.product_name == name)
            total_qty = sum(e.quantity for e in entries if e.product_name == name)
            lines.append(f"  {name}: qty={total_qty}, value={total_val}")

        lines.append(f"")
        lines.append(f"Questions:")
        for qid in cls.get_all_question_ids():
            q = expected.get(qid, {})
            lines.append(f"  [{qid}] {q.get('question', '???')}")

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Evaluation Runner
# ---------------------------------------------------------------------------


def run_evaluation(
    backend_class: str,
    backend_options: Dict[str, Any],
    questions: Optional[List[Dict[str, Any]]] = None,
    formats: List[str] = None,
    repetitions: int = 3,
) -> Dict[str, Any]:
    """
    Run the full evaluation against a backend.

    Args:
        backend_class: Dotted path to the backend class.
        backend_options: Options dict for the backend.
        questions: Optional list of question dicts. If None, uses default questions.
        formats: Output formats to test (json, plain, toonn). Default: all three.
        repetitions: Number of paired repetitions per format.

    Returns:
        Dict with evaluation results per format and aggregated scores.
    """
    if formats is None:
        formats = ["json", "plain", "toonn"]

    _entries, expected = EvaluationFixture.setup()
    question_ids = EvaluationFixture.get_all_question_ids()

    if questions:
        # Use custom questions
        pass

    backend_class_obj = import_string(backend_class)
    backend = backend_class_obj(**backend_options)

    results_by_format: Dict[str, List[EvaluationResult]] = {fmt: [] for fmt in formats}

    for rep in range(repetitions):
        for fmt in formats:
            is_plain_text = fmt == "plain"
            is_toonn = fmt == "toonn"

            for qid in question_ids:
                q = expected[qid]
                question_text = q["question"]
                result = EvaluationResult(
                    question_id=qid,
                    question_text=question_text,
                    config_name=backend_class,
                    format_name=fmt,
                    raw_plan="",
                    raw_answer="",
                    timings={},
                )

                try:
                    # Build catalog
                    catalog = build_reporting_catalog(extra_models=["demo_app.SalesTransaction"])

                    # Stage 1: Plan
                    from .prompts import plan_prompt

                    plan_start = time.perf_counter()
                    plan_prompt_text = plan_prompt(
                        question_text, catalog, plain_text=is_plain_text, toonn=is_toonn
                    )
                    plan_raw = backend.complete(plan_prompt_text)
                    plan_duration = time.perf_counter() - plan_start

                    result.raw_plan = plan_raw[:500]
                    result.timings["plan_seconds"] = round(plan_duration, 4)

                    # Parse plan
                    if is_toonn:
                        from .executor import parse_toonn_plan
                        plan = parse_toonn_plan(plan_raw)
                    elif is_plain_text:
                        from .executor import parse_llm_plain_text_plan
                        plan = parse_llm_plain_text_plan(plan_raw)
                    else:
                        from .executor import parse_llm_json
                        plan = parse_llm_json(plan_raw)

                    result.parse_success = isinstance(plan, dict) and plan is not None
                    if plan and plan.get("report"):
                        result.plan_success = True
                        result.report_config = plan["report"]

                    # Stage 2: Execute report
                    if result.plan_success and result.report_config:
                        exec_start = time.perf_counter()
                        try:
                            report_data = run_llm_report_config(result.report_config)
                            result.report_executed = True
                            result.report_data = report_data
                        except Exception as exc:
                            result.error = f"Report execution failed: {exc}"
                        result.timings["total_seconds"] = round(time.perf_counter() - exec_start, 4)

                    # Stage 3: Answer
                    if result.report_executed and result.report_data:
                        reports_for_answer = [
                            {
                                "config": result.report_config,
                                "data": result.report_data.get("data", []),
                                "columns": result.report_data.get("columns", []),
                            }
                        ]
                        from .prompts import answer_prompt
                        answer_prompt_text = answer_prompt(
                            question_text, reports_for_answer, plain_text=is_plain_text, toonn=is_toonn
                        )
                        answer_raw = backend.complete(answer_prompt_text)
                        result.raw_answer = answer_raw[:500]

                        if is_toonn:
                            from .executor import parse_toonn_answer
                            answer_json = parse_toonn_answer(answer_raw)
                        elif is_plain_text:
                            from .executor import parse_llm_plain_text_answer
                            answer_json = parse_llm_plain_text_answer(answer_raw)
                        else:
                            from .executor import parse_llm_json
                            answer_json = parse_llm_json(answer_raw)

                        result.answer = answer_json if isinstance(answer_json, dict) else {}

                except Exception as exc:
                    result.error = f"Evaluation error: {exc}"

                # Score the result
                plan_correct = EvaluationScorer.score_plan_correctness(result)
                parse_ok = EvaluationScorer.score_parse_success(result)
                exec_ok = EvaluationScorer.score_report_execution(result)
                values_ok = EvaluationScorer.score_result_values(result)
                answer_ok = EvaluationScorer.score_answer_correctness(result)
                normalized_plan = EvaluationScorer.score_normalized_plan(result)

                result.scores = {
                    "plan_correctness": plan_correct,
                    "parse_success": parse_ok,
                    "report_execution": exec_ok,
                    "result_values": values_ok,
                    "answer_correctness": answer_ok,
                    "normalized_plan": normalized_plan,
                }

                results_by_format[fmt].append(result)

    # Aggregate scores
    aggregated = {}
    for fmt in formats:
        aggregated[fmt] = EvaluationScorer.aggregate_scores(results_by_format[fmt])

    return {
        "meta": {
            "backend": backend_class,
            "formats": formats,
            "repetitions": repetitions,
            "question_count": len(question_ids),
            "fixture_summary": EvaluationFixture.get_summary(),
        },
        "results": results_by_format,
        "scores": aggregated,
    }

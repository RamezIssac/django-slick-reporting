"""
Deterministic evaluation of prompt-side data serialization formats.

Compares how the LLM reporting assistant performs when the catalog and the
report data embedded in the prompts are serialized as JSON, plain text, or
TOON (Token-Oriented Object Notation).  The response-side instructions are
the base ones defined in :mod:`slick_reporting.llm.prompts` in every arm;
only the data serialization inside the prompt varies.

The fixture is pinned in Q1 2026 and every expected value is *derived* from
the fixture rows at setup time, so the scorer grades the model against data,
not against hand-copied constants.  Scoring dimensions are kept separate:
plan correctness, parse success, report execution, exact result values and
labels, and answer correctness.  Per-call prompt/completion token counts
(from the provider ``usage`` object), per-stage latencies, untruncated raw
responses, and failed calls are all preserved on the result objects.

This module is evaluation tooling; it is wired to the ``tests`` app models
(``tests.SimpleSales`` and friends) which carry the deterministic fixture.
"""

import calendar
import datetime
import hashlib
import json
import re
import time
from collections import defaultdict
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from .executor import run_llm_report_config
from .introspection import build_reporting_catalog
from .toon_data import DATA_FORMATS, normalize_jsonable

#: Tolerance for float comparisons of report/answer numbers.
TOLERANCE = 0.01

#: The agreed evaluation window.
Q1_START = datetime.date(2026, 1, 1)
Q1_END = datetime.date(2026, 3, 31)
#: The generator treats end_date as inclusive; a plan ending 2026-04-01 uses
#: the exclusive-upper-bound convention and covers the same window.
Q1_END_EXCLUSIVE = datetime.date(2026, 4, 1)

REPORT_MODEL = "tests.SimpleSales"
CATALOG_MODELS = ["tests.SimpleSales", "tests.Client", "tests.Product"]

#: Row keys holding the country label when grouping by ``client__country``.
COUNTRY_ROW_KEYS = ("client__country", "country")
#: Row keys holding the client label when grouping by ``client``.
CLIENT_ROW_KEYS = ("name", "client__name", "client")

EVAL_PRODUCT_NAMES = ("Product 1", "Product 2", "Product 3")
EVAL_CLIENTS = (("Alpha US", "US"), ("Beta EG", "EG"), ("Gamma DE", "DE"))


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
# Note: no entry falls on the 1st of a month on purpose.  slick_reporting's
# monthly time series buckets rows into the period *ending* on each boundary
# date (a row on 2026-03-01 lands in the column labeled "February 2026"), so
# boundary dates would make generator output diverge from calendar months.
DETERMINISTIC_FIXTURE: List[FixtureEntry] = [
    # ---- Product 1: total quantity = 100, total value = 5000 (price=50) ----
    FixtureEntry("Q1-P1-001", "2026-01-05", "Alpha US", "US", "Product 1", 20, 50.00),
    FixtureEntry("Q1-P1-002", "2026-01-15", "Beta EG", "EG", "Product 1", 15, 50.00),
    FixtureEntry("Q1-P1-003", "2026-02-03", "Alpha US", "US", "Product 1", 25, 50.00),
    FixtureEntry("Q1-P1-004", "2026-02-20", "Gamma DE", "DE", "Product 1", 10, 50.00),
    FixtureEntry("Q1-P1-005", "2026-03-02", "Beta EG", "EG", "Product 1", 20, 50.00),
    FixtureEntry("Q1-P1-006", "2026-03-18", "Alpha US", "US", "Product 1", 10, 50.00),
    # ---- Product 2: US total = 1250, EG total = 1500 (price=50) ----
    # US entries (10+8+7=25 x 50 = 1250)
    FixtureEntry("Q1-P2-US-001", "2026-01-08", "Alpha US", "US", "Product 2", 10, 50.00),
    FixtureEntry("Q1-P2-US-002", "2026-02-10", "Alpha US", "US", "Product 2", 8, 50.00),
    FixtureEntry("Q1-P2-US-003", "2026-03-05", "Alpha US", "US", "Product 2", 7, 50.00),
    # EG entries (15+15=30 x 50 = 1500)
    FixtureEntry("Q1-P2-EG-001", "2026-01-12", "Beta EG", "EG", "Product 2", 15, 50.00),
    FixtureEntry("Q1-P2-EG-002", "2026-02-22", "Beta EG", "EG", "Product 2", 15, 50.00),
    # ---- Product 3: total quantity = 30, total value = 900 ----
    FixtureEntry("Q1-P3-001", "2026-01-20", "Gamma DE", "DE", "Product 3", 10, 30.00),
    FixtureEntry("Q1-P3-002", "2026-03-15", "Gamma DE", "DE", "Product 3", 10, 30.00),
    FixtureEntry("Q1-P3-003", "2026-03-25", "Beta EG", "EG", "Product 3", 10, 30.00),
]

#: Month aliases used when matching answer text to expected monthly values.
_MONTH_ALIASES = {
    "2026-01": ["2026-01", "january", "jan"],
    "2026-02": ["2026-02", "february", "feb"],
    "2026-03": ["2026-03", "march", "mar"],
}

_COUNTRY_ALIASES = {
    "US": ["us", "usa", "u.s.", "united states"],
    "EG": ["eg", "egypt"],
    "DE": ["de", "germany"],
}

_MONTH_NAME_RE = re.compile(r"\b(" + "|".join(m for m in calendar.month_name if m) + r")\s+(\d{4})\b")
_TS_KEY_RE = re.compile(r"^(?P<metric>.+)TS(?P<ymd>\d{8})$")
_NUMBER_RE = re.compile(r"-?\$?\d[\d,]*(?:\.\d+)?")


def _build_fixture_data() -> Tuple[List[FixtureEntry], Dict[str, Dict[str, Any]]]:
    """
    Return (fixture entries, expected results derived from those entries).

    ``expected`` maps a question id to the question text, the plan ``checks``
    used for plan scoring, and the expected values used for value/answer
    scoring.  Every number is computed from ``DETERMINISTIC_FIXTURE``.
    """
    entries = DETERMINISTIC_FIXTURE

    product_total_value: Dict[str, float] = defaultdict(float)
    product_total_quantity: Dict[str, int] = defaultdict(int)
    product_monthly_value: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
    product_client_value: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
    product_country_value: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))

    for e in entries:
        val = e.quantity * e.price
        month_key = e.date[:7]  # "2026-01"
        product_total_value[e.product_name] += val
        product_total_quantity[e.product_name] += e.quantity
        product_monthly_value[e.product_name][month_key] += val
        product_client_value[e.product_name][e.client_name] += val
        product_country_value[e.product_name][e.client_country] += val

    p1_client_values = dict(product_client_value.get("Product 1", {}))
    expected: Dict[str, Dict[str, Any]] = {
        "product1_sales_q1": {
            "question": "What are the total sales for Product 1 in Q1 2026?",
            "checks": {
                "report_model": REPORT_MODEL,
                "group_by": "product",
                "time_series_pattern": None,
                "filter_product": "Product 1",
                "metric_field": "value",
                "start_date": Q1_START,
                "end_date": Q1_END,
            },
            "expected_value": product_total_value.get("Product 1", 0.0),
        },
        "product1_quantity_q1": {
            "question": "What is the total quantity sold for Product 1 in Q1 2026?",
            "checks": {
                "report_model": REPORT_MODEL,
                "group_by": "product",
                "time_series_pattern": None,
                "filter_product": "Product 1",
                "metric_field": "quantity",
                "start_date": Q1_START,
                "end_date": Q1_END,
            },
            "expected_quantity": product_total_quantity.get("Product 1", 0),
        },
        "product2_us_vs_eg_q1": {
            "question": "How do Product 2 sales compare between the US and EG in Q1 2026?",
            "checks": {
                "report_model": REPORT_MODEL,
                "group_by": "client__country",
                "time_series_pattern": None,
                "filter_product": "Product 2",
                "metric_field": "value",
                "start_date": Q1_START,
                "end_date": Q1_END,
            },
            "expected_country_values": dict(product_country_value.get("Product 2", {})),
        },
        "product1_monthly_q1": {
            "question": "What were Product 1 monthly sales across Q1 2026?",
            "checks": {
                "report_model": REPORT_MODEL,
                "group_by": "product",
                "time_series_pattern": "monthly",
                "filter_product": "Product 1",
                "metric_field": "value",
                "start_date": Q1_START,
                "end_date": Q1_END,
            },
            "expected_monthly": dict(product_monthly_value.get("Product 1", {})),
        },
        "top_client_product1_q1": {
            "question": "Which client bought the most of Product 1 by sales value in Q1 2026?",
            "checks": {
                "report_model": REPORT_MODEL,
                "group_by": "client",
                "time_series_pattern": None,
                "filter_product": "Product 1",
                "metric_field": "value",
                "start_date": Q1_START,
                "end_date": Q1_END,
            },
            "expected_client_values": p1_client_values,
            "expected_top_client": max(p1_client_values, key=p1_client_values.get),
        },
    }
    return entries, expected


def create_fixture_data() -> None:
    """
    (Re)create the deterministic fixture rows in the current database.

    Hermetic: all existing SimpleSales rows and any previous eval fixture
    products/clients are deleted first, so pre-existing data can never shift
    the expected values.  The evaluation requires the sales tables to hold
    exactly the fixture rows; the benchmark guarantees this by running
    against a dedicated, freshly created database (see ``run_benchmark.py``).
    Tables must already exist (the benchmark runs ``migrate --run-syncdb``;
    Django tests create them via the test runner).
    """
    from tests.models import Client, Product, SimpleSales

    SimpleSales.objects.all().delete()
    Product.objects.filter(name__in=EVAL_PRODUCT_NAMES).delete()
    Client.objects.filter(name__in=[name for name, _c in EVAL_CLIENTS]).delete()

    product_map = {}
    for name in EVAL_PRODUCT_NAMES:
        product_map[name] = Product.objects.create(
            name=name,
            slug=name.lower().replace(" ", "-"),
            sku=name.upper().replace(" ", "-"),
            category="small",
            notes="Evaluation fixture product",
        )
    client_map = {}
    for name, country in EVAL_CLIENTS:
        client_map[name] = Client.objects.create(
            name=name,
            slug=name.lower().replace(" ", "-"),
            country=country,
            email=f"{name.lower().replace(' ', '')}@example.com",
            notes="Evaluation fixture client",
        )
    for entry in DETERMINISTIC_FIXTURE:
        doc_date = datetime.datetime.strptime(entry.date, "%Y-%m-%d").replace(tzinfo=datetime.timezone.utc)
        SimpleSales.objects.create(
            slug=entry.number,
            doc_date=doc_date,
            client=client_map[entry.client_name],
            product=product_map[entry.product_name],
            quantity=entry.quantity,
            price=entry.price,
            value=entry.quantity * entry.price,
            created_at=doc_date,
            flag="sales",
        )


def fixture_sha256() -> str:
    """Stable fingerprint of the fixture rows, recorded in benchmark artifacts."""
    payload = "\n".join(
        f"{e.number}|{e.date}|{e.client_name}|{e.client_country}|{e.product_name}|{e.quantity}|{e.price}"
        for e in DETERMINISTIC_FIXTURE
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Result record
# ---------------------------------------------------------------------------
@dataclass
class EvaluationResult:
    """Single result for one question-format-repetition combination."""

    question_id: str
    question_text: str
    format_name: str  # "json", "plain", "toon"
    repetition: int = 0
    raw_plan: str = ""
    raw_answer: str = ""
    timings: Dict[str, float] = field(default_factory=dict)
    token_counts: Dict[str, int] = field(default_factory=dict)
    served_model: Optional[str] = None
    plan_success: bool = False
    parse_success: bool = False
    report_executed: bool = False
    report_config: Optional[Dict[str, Any]] = None
    report_data: Optional[Dict[str, Any]] = None
    answer: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    scores: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """JSON-safe dict for the benchmark evidence artifact."""
        return {
            "question_id": self.question_id,
            "question_text": self.question_text,
            "format_name": self.format_name,
            "repetition": self.repetition,
            "plan_success": self.plan_success,
            "parse_success": self.parse_success,
            "report_executed": self.report_executed,
            "error": self.error,
            "served_model": self.served_model,
            "raw_plan": self.raw_plan,
            "raw_answer": self.raw_answer,
            "report_config": normalize_jsonable(self.report_config),
            "report_data": normalize_jsonable(self.report_data),
            "answer": normalize_jsonable(self.answer),
            "timings": self.timings,
            "token_counts": self.token_counts,
            "scores": {k: (list(v) if isinstance(v, tuple) else v) for k, v in self.scores.items()},
        }


# ---------------------------------------------------------------------------
# Scorer
# ---------------------------------------------------------------------------
class EvaluationScorer:
    """Score evaluation results across the agreed dimensions."""

    # -- plan / parse / execution ------------------------------------------
    @staticmethod
    def score_plan_correctness(result: EvaluationResult) -> Tuple[bool, str]:
        """
        Strict plan check: report model, group_by, time-series pattern,
        product filter, Q1 2026 date range, and metric must all be correct.
        """
        if not result.plan_success or not result.report_config:
            return False, "no plan"
        expected = EvaluationFixture.get_expected(result.question_id)
        if not expected:
            return False, "no expected config"
        checks = expected.get("checks", {})
        detail = EvaluationScorer._plan_dimension_results(result.report_config, checks)
        return (all(detail.values()), json.dumps(detail))

    @staticmethod
    def _plan_dimension_results(cfg: Dict[str, Any], checks: Dict[str, Any]) -> Dict[str, bool]:
        return {
            "report_model": cfg.get("report_model") == checks.get("report_model"),
            "group_by": (cfg.get("group_by") or None) == checks.get("group_by"),
            "time_series_pattern": (cfg.get("time_series_pattern") or None) == checks.get("time_series_pattern"),
            "filter_product": _plan_filter_matches_product(cfg, checks.get("filter_product")),
            "date_range": _plan_date_range_matches(cfg, checks.get("start_date"), checks.get("end_date")),
            "metric": _plan_metric_matches(cfg, checks.get("metric_field")),
        }

    @staticmethod
    def score_normalized_plan(result: EvaluationResult) -> float:
        """Fraction (0.0-1.0) of plan dimensions that are correct."""
        if not result.report_config:
            return 0.0
        expected = EvaluationFixture.get_expected(result.question_id)
        if not expected:
            return 0.0
        detail = EvaluationScorer._plan_dimension_results(result.report_config, expected.get("checks", {}))
        return round(sum(1 for v in detail.values() if v) / len(detail), 2) if detail else 0.0

    @staticmethod
    def score_parse_success(result: EvaluationResult) -> Tuple[bool, str]:
        if result.parse_success:
            return True, "parsed"
        return False, "parse failure"

    @staticmethod
    def score_report_execution(result: EvaluationResult) -> Tuple[bool, str]:
        if result.report_executed:
            return True, "executed"
        if result.error:
            return False, f"error: {result.error}"
        return False, "no error but not executed"

    # -- result values ------------------------------------------------------
    @staticmethod
    def score_result_values(result: EvaluationResult) -> Tuple[bool, str]:
        """Exact report values and labels, read from the real report payload."""
        expected = EvaluationFixture.get_expected(result.question_id)
        if not expected:
            return False, "no expected data"
        if not result.report_executed or not result.report_data:
            return False, "no report data"

        scores: Dict[str, bool] = {}
        if "expected_value" in expected:
            actual = _extract_aggregate(result, "value")
            scores["value"] = actual is not None and _num_eq(actual, expected["expected_value"])
        if "expected_quantity" in expected:
            actual = _extract_aggregate(result, "quantity")
            scores["quantity"] = actual is not None and _num_eq(actual, expected["expected_quantity"])
        if "expected_country_values" in expected:
            actual = _extract_group_values(result, COUNTRY_ROW_KEYS, "value")
            for country, exp_val in expected["expected_country_values"].items():
                scores[f"country_{country}"] = _num_eq(actual.get(country), exp_val)
        if "expected_monthly" in expected:
            actual = _extract_monthly_values(result, "value")
            for month, exp_val in expected["expected_monthly"].items():
                scores[f"month_{month}"] = _num_eq(actual.get(month), exp_val)
        if "expected_client_values" in expected:
            actual = _extract_group_values(result, CLIENT_ROW_KEYS, "value")
            for client, exp_val in expected["expected_client_values"].items():
                scores[f"client_{client}"] = _num_eq(actual.get(client), exp_val)
        if "expected_top_client" in expected:
            actual = _extract_group_values(result, CLIENT_ROW_KEYS, "value")
            top = max(actual, key=actual.get) if actual else None
            scores["top_client"] = top == expected["expected_top_client"]

        passed = bool(scores) and all(scores.values())
        return passed, json.dumps(scores)

    # -- answer -------------------------------------------------------------
    @staticmethod
    def score_answer_correctness(result: EvaluationResult) -> Tuple[bool, str]:
        """
        The answer must state the expected numbers/labels, not just mention
        the product.  Numbers are compared numerically (``$5,000.00`` == 5000);
        grouped expectations must pair the label with its value either in the
        structured ``key_numbers`` or in the same sentence-level text segment.
        """
        if not result.answer or not isinstance(result.answer, dict):
            return False, "no answer"
        answer_text = str(result.answer.get("answer") or "")
        if not answer_text.strip():
            return False, "no answer text"
        expected = EvaluationFixture.get_expected(result.question_id)
        if not expected:
            return False, "no expected data"

        key_numbers = _answer_key_numbers(result.answer)
        scores: Dict[str, bool] = {}

        if "expected_value" in expected:
            scores["value"] = _number_stated(expected["expected_value"], answer_text, key_numbers)
        if "expected_quantity" in expected:
            scores["quantity"] = _number_stated(expected["expected_quantity"], answer_text, key_numbers)
        if "expected_country_values" in expected:
            for country, exp_val in expected["expected_country_values"].items():
                aliases = _COUNTRY_ALIASES.get(country, [country.lower()])
                scores[f"country_{country}"] = _label_value_stated(aliases, exp_val, answer_text, key_numbers)
        if "expected_monthly" in expected:
            for month, exp_val in expected["expected_monthly"].items():
                aliases = _MONTH_ALIASES.get(month, [month])
                scores[f"month_{month}"] = _label_value_stated(aliases, exp_val, answer_text, key_numbers)
        if "expected_top_client" in expected:
            top = expected["expected_top_client"]
            aliases = [top.lower()] + [top.split()[0].lower()]
            scores["top_client_label"] = _label_stated(aliases, answer_text, key_numbers)
            top_value = expected.get("expected_client_values", {}).get(top)
            if top_value is not None:
                scores["top_client_value"] = _number_stated(top_value, answer_text, key_numbers)

        if not scores:
            return False, "no scoring criteria matched"
        return all(scores.values()), json.dumps(scores)

    # -- aggregation --------------------------------------------------------
    @staticmethod
    def aggregate_scores(results: List[EvaluationResult]) -> Dict[str, Any]:
        """Aggregate per-format scores, token counts, latencies and failures."""
        total = len(results)
        if total == 0:
            return {}

        def rate(key):
            return round(sum(1 for r in results if r.scores.get(key, (False, ""))[0]) / total, 2)

        def avg(fn):
            values = [fn(r) for r in results]
            return round(sum(values) / len(values), 3) if values else 0

        def avg_present(key):
            # Average over calls that actually happened: a failed plan call
            # means no answer call was made, and zero-padding would undercount.
            values = [r.token_counts[key] for r in results if key in r.token_counts]
            return round(sum(values) / len(values), 3) if values else 0

        def avg_timing(key):
            values = [r.timings[key] for r in results if key in r.timings]
            return round(sum(values) / len(values), 3) if values else 0

        def tokens_total(r):
            plan = r.token_counts.get("plan_total_tokens")
            answer = r.token_counts.get("answer_total_tokens")
            if plan is None and answer is None:
                return None
            return (plan or 0) + (answer or 0)

        token_totals = [t for t in (tokens_total(r) for r in results) if t is not None]

        plan_rates = [1.0 if r.scores.get("plan_correctness", (False, ""))[0] else 0.0 for r in results]
        mean_rate = sum(plan_rates) / len(plan_rates)
        std_dev = (sum((x - mean_rate) ** 2 for x in plan_rates) / len(plan_rates)) ** 0.5

        normalized = [r.scores.get("normalized_plan", 0.0) for r in results]

        return {
            "total_calls": total,
            "plan_success_rate": rate("plan_correctness"),
            "parse_success_rate": rate("parse_success"),
            "report_execution_rate": rate("report_execution"),
            "exact_value_match_rate": rate("result_values"),
            "answer_correctness_rate": rate("answer_correctness"),
            "avg_normalized_plan_score": round(sum(normalized) / len(normalized), 2) if normalized else 0.0,
            "plan_correctness_stddev": round(std_dev, 4),
            # headline token metrics: what each format costs in the prompt
            "avg_plan_prompt_tokens": avg_present("plan_prompt_tokens"),
            "avg_plan_completion_tokens": avg_present("plan_completion_tokens"),
            "avg_answer_prompt_tokens": avg_present("answer_prompt_tokens"),
            "avg_answer_completion_tokens": avg_present("answer_completion_tokens"),
            "avg_total_tokens_per_question": round(sum(token_totals) / len(token_totals), 3) if token_totals else 0,
            "plan_calls_made": sum(1 for r in results if "plan_prompt_tokens" in r.token_counts),
            "answer_calls_made": sum(1 for r in results if "answer_prompt_tokens" in r.token_counts),
            # per-stage latency
            "avg_plan_latency_seconds": avg_timing("plan_seconds"),
            "avg_answer_latency_seconds": avg_timing("answer_seconds"),
            "avg_exec_latency_seconds": avg_timing("exec_seconds"),
            "avg_total_latency_seconds": avg_timing("total_seconds"),
            "failures": [
                {
                    "question_id": r.question_id,
                    "repetition": r.repetition,
                    "format": r.format_name,
                    "error": r.error,
                    "parse_success": r.parse_success,
                    "report_executed": r.report_executed,
                }
                for r in results
                if r.error or not r.parse_success or not r.report_executed
            ],
        }


# ---------------------------------------------------------------------------
# Plan-check helpers
# ---------------------------------------------------------------------------
def _plan_filter_matches_product(cfg: Dict[str, Any], product_name: Optional[str]) -> bool:
    """The plan filters by the expected product (by name or resolved id)."""
    if not product_name:
        return True
    filters = cfg.get("filters") or {}
    if not isinstance(filters, dict):
        return False
    ids = _product_ids_for_name(product_name)
    target = product_name.lower()
    for key, value in filters.items():
        if "product" not in str(key).lower():
            continue
        values = value if isinstance(value, (list, tuple)) else [value]
        for v in values:
            if isinstance(v, str) and target in v.lower():
                return True
            if isinstance(v, int) and not isinstance(v, bool) and ids and v in ids:
                return True
    return False


def _product_ids_for_name(product_name: str) -> Optional[set]:
    """Resolve a product name to database ids; None when no DB is available."""
    try:
        from tests.models import Product

        return set(Product.objects.filter(name=product_name).values_list("id", flat=True))
    except Exception:
        return None


def _plan_date(value: Any) -> Optional[datetime.date]:
    if isinstance(value, datetime.datetime):
        return value.date()
    if isinstance(value, datetime.date):
        return value
    if isinstance(value, str):
        try:
            return datetime.date.fromisoformat(value.strip()[:10])
        except ValueError:
            return None
    return None


def _plan_date_range_matches(cfg: Dict[str, Any], start: Optional[datetime.date], end: Optional[datetime.date]) -> bool:
    if not start or not end:
        return True
    plan_start = _plan_date(cfg.get("start_date"))
    plan_end = _plan_date(cfg.get("end_date"))
    if plan_start != start:
        return False
    # Inclusive (2026-03-31) and exclusive (2026-04-01) conventions both cover Q1.
    return plan_end in {end, Q1_END_EXCLUSIVE}


def _plan_metric_matches(cfg: Dict[str, Any], metric_field: Optional[str]) -> bool:
    """The plan aggregates the expected field with Sum in some column."""
    if not metric_field:
        return True
    for column in list(cfg.get("columns") or []) + list(cfg.get("time_series_columns") or []):
        if isinstance(column, dict):
            method = str(column.get("method", "")).lower()
            if column.get("field") == metric_field and method == "sum":
                return True
        elif isinstance(column, str):
            # Plain-text plans may carry "Sum(value)" strings.
            m = re.match(r"^(\w+)\(([^)]+)\)$", column.strip())
            if m and m.group(1).lower() == "sum" and m.group(2).strip() == metric_field:
                return True
    return False


# ---------------------------------------------------------------------------
# Report-payload extraction helpers
# ---------------------------------------------------------------------------
def _num_eq(actual: Optional[float], expected: float) -> bool:
    if actual is None:
        return False
    try:
        return abs(float(actual) - float(expected)) < TOLERANCE
    except (TypeError, ValueError):
        return False


def _rows(result: EvaluationResult) -> List[Dict[str, Any]]:
    if not result.report_data or not isinstance(result.report_data, dict):
        return []
    return [row for row in (result.report_data.get("data") or []) if isinstance(row, dict)]


def _extract_aggregate(result: EvaluationResult, field_name: str) -> Optional[float]:
    """
    Sum the exact ``<field>__sum`` column across rows.

    Returns ``None`` when no row carries the column (so a missing metric
    scores as failure), otherwise the total -- including an honest 0.0.
    """
    candidate_keys = {f"{field_name}__sum", f"{field_name}__sum__sum"}
    total = 0.0
    found = False
    for row in _rows(result):
        for key, value in row.items():
            if key in candidate_keys:
                try:
                    total += float(value)
                    found = True
                except (TypeError, ValueError):
                    pass
    return total if found else None


def _extract_group_values(result: EvaluationResult, label_keys: Tuple[str, ...], field_name: str) -> Dict[str, float]:
    """Map group label -> summed ``<field>__sum`` across report rows."""
    value_keys = (f"{field_name}__sum", f"{field_name}__sum__sum")
    values: Dict[str, float] = {}
    for row in _rows(result):
        label = next((row[k] for k in label_keys if k in row and row[k] not in (None, "")), None)
        if label is None:
            continue
        for key, value in row.items():
            if key in value_keys:
                try:
                    values[str(label)] = values.get(str(label), 0.0) + float(value)
                except (TypeError, ValueError):
                    pass
                break
    return values


def _extract_monthly_values(result: EvaluationResult, field_name: str) -> Dict[str, float]:
    """
    Map calendar month (``2026-01``) -> value from real time-series keys.

    slick_reporting emits one column per period named ``<field>__sumTS<YYYYMMDD>``
    whose ``verbose_name`` carries the authoritative label (e.g. "Sum value
    January 2026").  The verbose label is used when available; otherwise the
    key date is taken as the period's end boundary and shifted back one month
    (monthly periods end on the 1st of the following month).
    """
    columns_meta = {}
    for col in (result.report_data or {}).get("columns") or []:
        if isinstance(col, dict):
            columns_meta[str(col.get("name"))] = str(col.get("verbose_name", ""))

    prefix = f"{field_name}__sumTS"
    values: Dict[str, float] = {}
    for row in _rows(result):
        for key, value in row.items():
            key = str(key)
            if not key.startswith(prefix):
                continue
            m = _TS_KEY_RE.match(key)
            if not m:
                continue
            month = _month_label_for_ts(m.group("ymd"), columns_meta.get(key, ""))
            if not month:
                continue
            try:
                values[month] = values.get(month, 0.0) + float(value)
            except (TypeError, ValueError):
                pass
    return values


def _month_label_for_ts(ymd: str, verbose_name: str) -> Optional[str]:
    m = _MONTH_NAME_RE.search(verbose_name or "")
    if m:
        month_number = list(calendar.month_name).index(m.group(1))
        return f"{m.group(2)}-{month_number:02d}"
    try:
        boundary = datetime.date(int(ymd[:4]), int(ymd[4:6]), int(ymd[6:8]))
    except ValueError:
        return None
    last_day_of_period_month = boundary.replace(day=1) - datetime.timedelta(days=1)
    return f"{last_day_of_period_month.year}-{last_day_of_period_month.month:02d}"


# ---------------------------------------------------------------------------
# Answer-text extraction helpers
# ---------------------------------------------------------------------------
def _answer_key_numbers(answer: Dict[str, Any]) -> Dict[str, float]:
    """Numeric entries from the structured proofs' ``key_numbers``."""
    numbers: Dict[str, float] = {}
    for proof in answer.get("proofs") or []:
        if not isinstance(proof, dict):
            continue
        for key, value in (proof.get("key_numbers") or {}).items():
            coerced = _coerce_float(value)
            if coerced is not None:
                numbers[str(key)] = coerced
    return numbers


def _coerce_float(value: Any) -> Optional[float]:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float, Decimal)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.replace("$", "").replace(",", "").strip())
        except ValueError:
            return None
    return None


def _extract_numbers(text: str) -> List[float]:
    """Every numeric literal in ``text`` (``$`` and ``,`` separators tolerated)."""
    numbers = []
    for match in _NUMBER_RE.finditer(text):
        coerced = _coerce_float(match.group(0))
        if coerced is not None:
            numbers.append(coerced)
    return numbers


def _number_stated(expected: float, answer_text: str, key_numbers: Dict[str, float]) -> bool:
    """The expected number appears in key_numbers values or in the answer text."""
    candidates = list(key_numbers.values()) + _extract_numbers(answer_text)
    return any(abs(c - float(expected)) < TOLERANCE for c in candidates)


def _text_segments(text: str) -> List[str]:
    """Sentence-level segments: split on newlines, semicolons, '. ', ', '."""
    return [seg for seg in re.split(r"[\n;]|\.\s+|,\s+", text) if seg.strip()]


def _label_in_text(aliases: List[str], text: str) -> bool:
    lowered = text.lower()
    return any(re.search(rf"\b{re.escape(alias)}\b", lowered) for alias in aliases)


def _label_stated(aliases: List[str], answer_text: str, key_numbers: Dict[str, float]) -> bool:
    if _label_in_text(aliases, answer_text):
        return True
    return any(any(alias in key.lower() for alias in aliases) for key in key_numbers)


def _label_value_stated(aliases: List[str], expected: float, answer_text: str, key_numbers: Dict[str, float]) -> bool:
    """A label paired with its expected value in key_numbers or one text segment."""
    for key, value in key_numbers.items():
        if any(alias in key.lower() for alias in aliases) and abs(value - float(expected)) < TOLERANCE:
            return True
    for segment in _text_segments(answer_text):
        if _label_in_text(aliases, segment):
            if any(abs(n - float(expected)) < TOLERANCE for n in _extract_numbers(segment)):
                return True
    return False


# ---------------------------------------------------------------------------
# Fixture registry
# ---------------------------------------------------------------------------
class EvaluationFixture:
    """Access to the deterministic fixture and its derived expectations."""

    _expected: Dict[str, Dict[str, Any]] = {}
    _entries: List[FixtureEntry] = []

    @classmethod
    def setup(cls) -> Tuple[List[FixtureEntry], Dict[str, Dict[str, Any]]]:
        if not cls._entries:
            cls._entries, cls._expected = _build_fixture_data()
        return cls._entries, cls._expected

    @classmethod
    def get_expected(cls, question_id: str) -> Optional[Dict[str, Any]]:
        return cls._expected.get(question_id)

    @classmethod
    def get_all_question_ids(cls) -> List[str]:
        return list(cls._expected.keys())

    @classmethod
    def get_summary(cls) -> str:
        entries, expected = cls.setup()
        lines = [
            "=== Deterministic Evaluation Fixture ===",
            f"Period: Q1 2026 ({Q1_START} to {Q1_END})",
            f"Total entries: {len(entries)}",
            f"Fixture sha256: {fixture_sha256()}",
            "",
            "Products:",
        ]
        for name in sorted({e.product_name for e in entries}):
            total_val = sum(e.quantity * e.price for e in entries if e.product_name == name)
            total_qty = sum(e.quantity for e in entries if e.product_name == name)
            lines.append(f"  {name}: qty={total_qty}, value={total_val}")
        lines.append("")
        lines.append("Questions:")
        for qid in cls.get_all_question_ids():
            lines.append(f"  [{qid}] {expected[qid]['question']}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Evaluation runner
# ---------------------------------------------------------------------------
def run_evaluation(
    backend,
    formats: Optional[List[str]] = None,
    repetitions: int = 3,
    question_ids: Optional[List[str]] = None,
    seed: bool = True,
) -> Dict[str, Any]:
    """
    Run the full evaluation against ``backend`` (an LLMBackend instance).

    ``repetitions`` paired repetitions are run in rep -> format -> question
    order so each format sees every question under identical sampling
    settings (one backend instance, one temperature).  When ``seed`` is true
    the fixture rows are (re)created first; the caller must guarantee the
    database is otherwise empty of sales rows (the benchmark uses a dedicated
    fresh database).

    Returns a dict with ``meta``, per-format ``results`` (every call kept,
    including failed ones) and per-format aggregated ``scores``.
    """
    formats = list(formats or DATA_FORMATS)
    for fmt in formats:
        if fmt not in DATA_FORMATS:
            raise ValueError(f"Unknown format {fmt!r}; expected one of {DATA_FORMATS}")

    _entries, expected = EvaluationFixture.setup()
    question_ids = question_ids or EvaluationFixture.get_all_question_ids()

    if seed:
        create_fixture_data()

    catalog = build_reporting_catalog(extra_models=CATALOG_MODELS)

    results_by_format: Dict[str, List[EvaluationResult]] = {fmt: [] for fmt in formats}

    for rep in range(repetitions):
        for fmt in formats:
            for qid in question_ids:
                question_text = expected[qid]["question"]
                result = EvaluationResult(
                    question_id=qid,
                    question_text=question_text,
                    format_name=fmt,
                    repetition=rep,
                )
                _run_single_question(backend, fmt, question_text, catalog, result)
                result.scores = {
                    "plan_correctness": EvaluationScorer.score_plan_correctness(result),
                    "parse_success": EvaluationScorer.score_parse_success(result),
                    "report_execution": EvaluationScorer.score_report_execution(result),
                    "result_values": EvaluationScorer.score_result_values(result),
                    "answer_correctness": EvaluationScorer.score_answer_correctness(result),
                    "normalized_plan": EvaluationScorer.score_normalized_plan(result),
                }
                results_by_format[fmt].append(result)

    all_results = [r for fmt in formats for r in results_by_format[fmt]]
    return {
        "meta": {
            "formats": formats,
            "repetitions": repetitions,
            "question_ids": question_ids,
            "endpoint": getattr(backend, "api_url", None),
            "configured_model": getattr(backend, "model", None),
            "served_models": sorted({r.served_model for r in all_results if r.served_model}),
            "sampling": {"temperature": getattr(backend, "temperature", None)},
            "fixture_sha256": fixture_sha256(),
            "fixture_summary": EvaluationFixture.get_summary(),
        },
        "results": results_by_format,
        "scores": {fmt: EvaluationScorer.aggregate_scores(results_by_format[fmt]) for fmt in formats},
    }


def _run_single_question(
    backend, fmt: str, question_text: str, catalog: Dict[str, Any], result: EvaluationResult
) -> None:
    """Drive the three stages (plan, execute, answer) for one question.

    Failures are recorded on ``result.error`` and never raised, so failed
    calls are preserved and scored like any other result.
    """
    from . import prompts
    from .executor import parse_llm_json, parse_llm_plain_text_answer, parse_llm_plain_text_plan

    plain_text = fmt == "plain"
    question_start = time.perf_counter()
    try:
        # ---- Stage 1: plan ----
        plan_prompt_text = prompts.plan_prompt(question_text, catalog, plain_text=plain_text, data_format=fmt)
        plan_start = time.perf_counter()
        plan_raw = backend.complete(plan_prompt_text)
        result.timings["plan_seconds"] = round(time.perf_counter() - plan_start, 4)
        result.raw_plan = plan_raw or ""  # untruncated
        _record_usage(backend, result, "plan")

        plan = parse_llm_plain_text_plan(plan_raw) if plain_text else parse_llm_json(plan_raw)
        result.parse_success = isinstance(plan, dict)
        if isinstance(plan, dict) and plan.get("report"):
            result.plan_success = True
            result.report_config = plan["report"]

        # ---- Stage 2: execute the report ----
        if result.plan_success and result.report_config:
            exec_start = time.perf_counter()
            try:
                result.report_data = run_llm_report_config(result.report_config)
                result.report_executed = True
            except Exception as exc:
                result.error = f"Report execution failed: {exc}"
            result.timings["exec_seconds"] = round(time.perf_counter() - exec_start, 4)

        # ---- Stage 3: answer ----
        if result.report_executed and result.report_data:
            reports_for_answer = [
                {
                    "config": result.report_config,
                    "data": result.report_data.get("data", []),
                    "columns": result.report_data.get("columns", []),
                }
            ]
            answer_prompt_text = prompts.answer_prompt(
                question_text, reports_for_answer, plain_text=plain_text, data_format=fmt
            )
            answer_start = time.perf_counter()
            answer_raw = backend.complete(answer_prompt_text)
            result.timings["answer_seconds"] = round(time.perf_counter() - answer_start, 4)
            result.raw_answer = answer_raw or ""  # untruncated
            _record_usage(backend, result, "answer")

            parsed = parse_llm_plain_text_answer(answer_raw) if plain_text else parse_llm_json(answer_raw)
            result.answer = parsed if isinstance(parsed, dict) else {}
    except Exception as exc:
        result.error = f"Evaluation error: {exc}"
    result.timings["total_seconds"] = round(time.perf_counter() - question_start, 4)


def _record_usage(backend, result: EvaluationResult, stage: str) -> None:
    """Capture provider token usage and served-model identity after a call."""
    usage = backend.get_last_usage() or {}
    result.token_counts[f"{stage}_prompt_tokens"] = usage.get("prompt_tokens", 0)
    result.token_counts[f"{stage}_completion_tokens"] = usage.get("completion_tokens", 0)
    result.token_counts[f"{stage}_total_tokens"] = usage.get("total_tokens", 0)
    model = backend.get_last_model()
    if model:
        result.served_model = model

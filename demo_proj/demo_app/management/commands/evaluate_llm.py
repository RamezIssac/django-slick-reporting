"""
CLI evaluator for the "Ask the data" LLM assistant.

Run a single configured backend:

    python demo_proj/manage.py evaluate_llm \
        --questions-file demo_proj/demo_app/fixtures/llm_eval_questions.json

Override the model/endpoint for one run:

    python demo_proj/manage.py evaluate_llm \
        --api-url http://localhost:8080/v1/chat/completions \
        --model my-model \
        --questions-file ...

Run the same questions against several models and compare them:

    python demo_proj/manage.py evaluate_llm \
        --configs-file demo_proj/demo_app/fixtures/llm_eval_configs.json \
        --questions-file demo_proj/demo_app/fixtures/llm_eval_questions.json

The resulting JSON report contains per-question timings, the generated report
config, the final answer, and pass/fail checks.
"""

import json
import logging
import os
import sys
import time
from pathlib import Path
from unittest.mock import patch

from django.core.management.base import BaseCommand
from django.test import RequestFactory
from django.utils.module_loading import import_string

from slick_reporting.app_settings import SLICK_REPORTING_SETTINGS
from slick_reporting.llm.executor import parse_llm_json, parse_llm_plain_text_plan
from slick_reporting.llm.introspection import build_reporting_catalog
from slick_reporting.llm.prompts import plan_prompt
from slick_reporting.llm.views import AskLLMView

DEFAULT_QUESTIONS = [
    {
        "id": "product-total",
        "question": "What are the total sales per product this year?",
        "checks": {
            "report_model": "demo_app.SalesTransaction",
            "group_by": "product",
            "metric_field": "value",
            "aggregation": "Sum",
        },
    },
    {
        "id": "country-total",
        "question": "Show total sales value grouped by client country.",
        "checks": {
            "report_model": "demo_app.SalesTransaction",
            "group_by": "client__country",
            "metric_field": "value",
            "aggregation": "Sum",
        },
    },
    {
        "id": "monthly-trend",
        "question": "How did Product 1 sales evolve month by month?",
        "checks": {
            "report_model": "demo_app.SalesTransaction",
            "group_by": "product",
            "time_series_pattern": "monthly",
            "metric_field": "value",
            "aggregation": "Sum",
        },
    },
    {
        "id": "product-filter",
        "question": "What is the total quantity sold for Product 2?",
        "checks": {
            "report_model": "demo_app.SalesTransaction",
            "group_by": "product",
            "metric_field": "quantity",
            "aggregation": "Sum",
        },
    },
]


def _configure_logging(verbosity):
    level = logging.WARNING if verbosity < 2 else logging.DEBUG
    logging.getLogger("slick_reporting").setLevel(level)
    logging.getLogger("slick_reporting.llm").setLevel(level)


class Command(BaseCommand):
    help = "Evaluate the 'Ask the data' LLM assistant end-to-end."

    def add_arguments(self, parser):
        parser.add_argument(
            "--questions-file",
            type=str,
            default=None,
            help="Path to a JSON file with question fixtures. Falls back to built-in defaults.",
        )
        parser.add_argument(
            "--configs-file",
            type=str,
            default=None,
            help=(
                "Path to a JSON file with a list of backend configs. "
                "Each item must contain 'name' and 'backend_options'."
            ),
        )
        parser.add_argument(
            "--output",
            type=str,
            default=None,
            help="Where to write the JSON evaluation report.",
        )
        parser.add_argument(
            "--api-url",
            type=str,
            default=None,
            help="Override SLICK_REPORTING_SETTINGS['LLM_BACKEND_OPTIONS']['api_url'].",
        )
        parser.add_argument(
            "--api-key",
            type=str,
            default=None,
            help="Override the API key for this run.",
        )
        parser.add_argument(
            "--model",
            type=str,
            default=None,
            help="Override the model name for this run.",
        )
        parser.add_argument(
            "--backend",
            type=str,
            default=None,
            help="Dotted path to an LLM backend class (default: OpenAICompatibleBackend).",
        )
        parser.add_argument(
            "--timeout",
            type=int,
            default=None,
            help="Override the backend HTTP timeout for this run.",
        )
        parser.add_argument(
            "--enable-thinking",
            action="store_true",
            default=False,
            help="Send enable_thinking=True in the chat payload (default: False).",
        )
        parser.add_argument(
            "--reasoning-budget",
            type=int,
            default=None,
            help="llama.cpp reasoning_budget token cap for thinking (0=off, -1=unrestricted).",
        )
        parser.add_argument(
            "--catalog-models",
            type=str,
            default=None,
            help="Comma-separated list of app_label.ModelName to restrict the LLM catalog.",
        )
        parser.add_argument(
            "--print-prompts",
            action="store_true",
            help="Print planning and answer prompt lengths per question.",
        )
        parser.add_argument(
            "--only",
            type=str,
            default=None,
            help="Comma-separated list of question IDs to run.",
        )
        parser.add_argument(
            "--plain-text",
            action="store_true",
            help=(
                "Use plain-text prompts/responses instead of JSON. "
                "Can also be set via SLICK_REPORTING_SETTINGS['LLM_PLAIN_TEXT_RESPONSE']."
            ),
        )

    def handle(self, *args, **options):
        # Ensure Django settings are available when the command is invoked
        # without going through manage.py.
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "demo_proj.settings")
        _configure_logging(options["verbosity"])

        questions = self._load_questions(options["questions_file"])
        if options["only"]:
            allowed = {q.strip() for q in options["only"].split(",")}
            questions = [q for q in questions if q.get("id") in allowed]

        configs = self._load_backend_configs(options)
        access_check = self._build_access_check()

        run_summaries = []
        overall_start = time.perf_counter()
        for config in configs:
            self.stdout.write(self.style.NOTICE(f"\n=== Running config: {config['name']} ==="))
            backend = self._build_backend(config)
            results = []
            for question in questions:
                result = self._evaluate_question(question, backend, access_check, options)
                results.append(result)
                self._print_progress(result, config["name"])

            run_summaries.append(
                {
                    "config_name": config["name"],
                    "backend_class": backend.__class__.__name__,
                    "api_url": getattr(backend, "api_url", None),
                    "model": getattr(backend, "model", None),
                    "catalog_models": self._catalog_models(options),
                    "results": results,
                    "scores": self._score_results(results),
                }
            )
        overall_duration = time.perf_counter() - overall_start

        summary = {
            "meta": {
                "total_questions": len(questions),
                "total_duration_seconds": round(overall_duration, 3),
                "catalog_models": self._catalog_models(options),
            },
            "runs": run_summaries,
        }

        report_json = json.dumps(summary, indent=2, default=str)
        self.stdout.write("\n" + report_json)

        if options["output"]:
            out_path = Path(options["output"])
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(report_json)
            self.stdout.write(self.style.SUCCESS(f"Wrote evaluation report to {out_path}"))

        # Exit non-zero if no config managed to produce any plans.
        all_plan_rates = [run["scores"].get("plan_success_rate", 0) for run in run_summaries]
        if questions and (not all_plan_rates or max(all_plan_rates) == 0):
            sys.exit(1)

    def _load_questions(self, questions_file):
        if not questions_file:
            return DEFAULT_QUESTIONS

        path = Path(questions_file)
        if not path.exists():
            raise FileNotFoundError(f"Questions file not found: {path}")

        data = json.loads(path.read_text())
        if isinstance(data, dict):
            return data.get("questions", [])
        return data

    def _load_backend_configs(self, options):
        """Return a list of {name, backend_path, backend_options} dicts."""
        if options["configs_file"]:
            path = Path(options["configs_file"])
            if not path.exists():
                raise FileNotFoundError(f"Configs file not found: {path}")

            data = json.loads(path.read_text())
            configs = data if isinstance(data, list) else data.get("configs", [])
            for cfg in configs:
                if "name" not in cfg or "backend_options" not in cfg:
                    raise ValueError("Each config must contain 'name' and 'backend_options'.")
                cfg.setdefault(
                    "backend_path",
                    SLICK_REPORTING_SETTINGS.get("LLM_BACKEND")
                    or "slick_reporting.llm.backends.OpenAICompatibleBackend",
                )
            return configs

        # Single implicit config from CLI / settings.
        return [
            {
                "name": options["model"] or "default",
                "backend_path": options["backend"]
                or SLICK_REPORTING_SETTINGS.get("LLM_BACKEND")
                or "slick_reporting.llm.backends.OpenAICompatibleBackend",
                "backend_options": self._single_config_options(options),
            }
        ]

    def _single_config_options(self, options):
        user_options = dict(SLICK_REPORTING_SETTINGS.get("LLM_BACKEND_OPTIONS") or {})
        # Pass through every settings key the backend understands (api_url,
        # base_url, api_key, api_key_env, model, temperature, max_tokens,
        # timeout, enable_thinking, reasoning_budget, extra_headers,
        # extra_payload, ...); the backend raises a clear error if it is
        # missing something it needs.
        run_options = {k: v for k, v in user_options.items() if k in self.PASSTHROUGH_OPTION_KEYS}

        if options["api_url"]:
            run_options["api_url"] = options["api_url"]
        if options["api_key"] is not None:
            run_options["api_key"] = options["api_key"]
        if options["model"] is not None:
            run_options["model"] = options["model"]
        run_options["temperature"] = float(run_options.get("temperature", 0.2))
        # CLI --enable-thinking takes precedence; then fall back to settings (default False).
        if "enable_thinking" not in run_options:
            run_options["enable_thinking"] = bool(options["enable_thinking"])
        if options["reasoning_budget"] is not None:
            run_options["reasoning_budget"] = options["reasoning_budget"]
        if options["timeout"] is not None:
            run_options["timeout"] = options["timeout"]
        return run_options

    PASSTHROUGH_OPTION_KEYS = {
        "api_url",
        "base_url",
        "api_key",
        "api_key_env",
        "model",
        "temperature",
        "max_tokens",
        "timeout",
        "enable_thinking",
        "reasoning_budget",
        "extra_headers",
        "extra_payload",
        "site_url",
        "app_name",
    }

    def _catalog_models(self, options):
        if options["catalog_models"]:
            return [m.strip() for m in options["catalog_models"].split(",")]
        return SLICK_REPORTING_SETTINGS.get("LLM_CATALOG_MODELS")

    def _build_backend(self, config):
        backend_class = import_string(config["backend_path"])
        return backend_class(**config["backend_options"])

    def _build_access_check(self):
        from slick_reporting.app_settings import get_access_function

        access_function = get_access_function()
        return lambda request: access_function(None, request)

    def _evaluate_question(self, question, backend, access_check, options):
        qid = question.get("id", "unknown")
        qtext = question.get("question", "")
        result = {
            "id": qid,
            "question": qtext,
            "timings": {},
            "report_config": None,
            "answer": None,
            "checks": {},
            "error": None,
        }

        request = RequestFactory().post("/dashboard/ask/", data={"question": qtext}, content_type="application/json")
        if not access_check(request):
            result["error"] = "Access check failed for evaluator request"
            return result

        # Stage 1: planning. We call the backend directly so we can capture
        # prompt length and timing without also running the report.
        plain_text = bool(
            options.get("plain_text") or SLICK_REPORTING_SETTINGS.get("LLM_PLAIN_TEXT_RESPONSE")
        )
        catalog = build_reporting_catalog(extra_models=None)
        plan_prompt_text = plan_prompt(qtext, catalog, plain_text=plain_text)
        if options["print_prompts"]:
            self.stdout.write(f"[{qid}] plan prompt length: {len(plan_prompt_text)} chars")

        planning_start = time.perf_counter()
        try:
            plan_response_text = backend.complete(plan_prompt_text)
        except Exception as exc:
            result["error"] = f"Planning failed: {exc}"
            result["timings"]["plan_seconds"] = round(time.perf_counter() - planning_start, 3)
            return result
        planning_duration = time.perf_counter() - planning_start
        result["timings"]["plan_seconds"] = round(planning_duration, 3)
        result["raw_plan"] = plan_response_text[:500] if isinstance(plan_response_text, str) else ""

        if plain_text:
            plan = parse_llm_plain_text_plan(plan_response_text)
        else:
            plan = parse_llm_json(plan_response_text)
        if not isinstance(plan, dict) or not plan.get("report"):
            result["error"] = "LLM did not return a usable report plan"
            return result

        report_config = plan["report"]
        result["report_config"] = report_config

        # Stage 2 + 3: execute the report and get the answer. We use a backend
        # wrapper that records the answer prompt and skips the repeated planning
        # call the view would otherwise make.
        full_start = time.perf_counter()
        try:
            wrapping_backend = _CachingBackend(backend, plan_response_text)
            view_settings = SLICK_REPORTING_SETTINGS.copy()
            view_settings["LLM_PLAIN_TEXT_RESPONSE"] = plain_text
            with patch("slick_reporting.llm.views.get_llm_backend", return_value=wrapping_backend):
                with patch("slick_reporting.llm.views.SLICK_REPORTING_SETTINGS", view_settings):
                    view = AskLLMView()
                    response = view.post(request)

            if wrapping_backend.answer_prompt_text and options["print_prompts"]:
                self.stdout.write(f"[{qid}] answer prompt length: {len(wrapping_backend.answer_prompt_text)} chars")
        except Exception as exc:
            result["error"] = f"Execution/answer failed: {exc}"
            result["timings"]["total_seconds"] = round(time.perf_counter() - full_start, 3)
            return result

        total_duration = time.perf_counter() - full_start
        result["timings"]["total_seconds"] = round(total_duration, 3)

        data = json.loads(response.content.decode("utf-8"))
        if "error" in data:
            result["error"] = data["error"]
            result["report_config"] = data.get("report_config")
            return result

        result["answer"] = {
            "answer": data.get("answer", ""),
            "reasoning": data.get("reasoning", ""),
            "proofs": data.get("proofs", []),
        }
        result["report_data"] = {
            "row_count": len(data.get("report_data", {}).get("data", [])),
            "columns": data.get("report_data", {}).get("columns", []),
        }
        result["checks"] = self._run_checks(report_config, data, question.get("checks", {}))
        return result

    def _run_checks(self, report_config, response, checks):
        outcomes = {}
        if not report_config:
            outcomes["has_report_config"] = (False, "no report config")
            return outcomes

        outcomes["has_report_config"] = (True, None)

        if "report_model" in checks:
            expected = checks["report_model"]
            outcomes["report_model"] = (
                report_config.get("report_model") == expected,
                f"expected {expected}, got {report_config.get('report_model')}",
            )

        if "group_by" in checks:
            expected = checks["group_by"]
            actual = report_config.get("group_by")
            outcomes["group_by"] = (
                actual == expected,
                f"expected {expected}, got {actual}",
            )

        if "time_series_pattern" in checks:
            expected = checks["time_series_pattern"]
            actual = report_config.get("time_series_pattern")
            outcomes["time_series_pattern"] = (
                actual == expected,
                f"expected {expected}, got {actual}",
            )

        if "metric_field" in checks or "aggregation" in checks:
            cols = report_config.get("columns", [])
            fields = []
            methods = []
            for col in cols:
                if isinstance(col, dict):
                    fields.append(col.get("field"))
                    methods.append(col.get("method"))

            if "metric_field" in checks:
                expected = checks["metric_field"]
                outcomes["metric_field"] = (
                    expected in fields,
                    f"expected metric field {expected} in {fields}",
                )

            if "aggregation" in checks:
                expected = checks["aggregation"]
                outcomes["aggregation"] = (
                    expected in methods,
                    f"expected aggregation {expected} in {methods}",
                )

        if "answer_contains" in checks:
            expected = checks["answer_contains"]
            answer = (response.get("answer") or "").lower()
            outcomes["answer_contains"] = (
                expected.lower() in answer,
                f"expected '{expected}' in answer",
            )

        return outcomes

    def _score_results(self, results):
        if not results:
            return {}

        total = len(results)
        with_plan = sum(1 for r in results if r["report_config"] is not None)
        with_data = sum(1 for r in results if r.get("answer") is not None and r.get("error") is None)

        check_scores = {}
        for key in {
            "report_model",
            "group_by",
            "time_series_pattern",
            "metric_field",
            "aggregation",
            "answer_contains",
        }:
            key_checks = [r["checks"].get(key) for r in results if key in r["checks"]]
            if key_checks:
                passed = sum(1 for ok, _ in key_checks if ok)
                check_scores[key] = {"passed": passed, "total": len(key_checks)}

        return {
            "plan_success_rate": round(with_plan / total, 2),
            "end_to_end_success_rate": round(with_data / total, 2),
            "check_scores": check_scores,
        }

    def _print_progress(self, result, config_name):
        status = "OK" if result.get("error") is None else "FAIL"
        style = self.style.SUCCESS if status == "OK" else self.style.ERROR
        timings = result.get("timings", {})
        plan_s = timings.get("plan_seconds", "-")
        total_s = timings.get("total_seconds", "-")
        self.stdout.write(
            style(
                f"[{config_name}] [{status}] {result['id']}: plan={plan_s}s total={total_s}s "
                f"rows={result.get('report_data', {}).get('row_count', 0)}"
            )
        )
        if result.get("error"):
            self.stdout.write(self.style.ERROR(f"       error: {result['error']}"))


class _CachingBackend:
    """
    Wrap a real backend so the view's first planning call is answered from a
    cached plan while the second answer-prompt call is forwarded to the real
    backend. This lets the evaluator time the two stages separately without
    paying for planning twice.
    """

    def __init__(self, real_backend, cached_plan_response):
        self._real = real_backend
        self._cached = cached_plan_response
        self._used_cache = False
        self.answer_prompt_text = None

    def complete(self, prompt):
        # The planning prompt contains the catalog; the answer prompt does not.
        if not self._used_cache and "Available catalog" in prompt:
            self._used_cache = True
            return self._cached
        self.answer_prompt_text = prompt
        return self._real.complete(prompt)

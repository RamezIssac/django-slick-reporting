"""
Dashboard API endpoints for the natural-language reporting assistant.

* ``ask``  POST  /dashboard/ask/  (configurable URL)
    Body: {"question": "..."}
    Response: {"answer": "...", "proofs": [...], "report": {...}, "raw_data": {...}}
"""

import json
import logging
import time

from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from ..app_settings import SLICK_REPORTING_SETTINGS, get_access_function
from .backends import get_llm_backend
from .executor import parse_llm_json, run_llm_report_config
from .introspection import build_reporting_catalog
from .prompts import answer_prompt, plan_prompt

logger = logging.getLogger(__name__)


def llm_access_check(request):
    """Re-use the reporting access function if configured."""
    access_function = get_access_function()
    return access_function(None, request)


@method_decorator(csrf_exempt, name="dispatch")
class AskLLMView(View):
    """
    Accept a natural-language business question and return an answer
    supported by the report data that was generated.
    """

    http_method_names = ["post", "head", "options"]

    def post(self, request, *args, **kwargs):
        started_at = time.perf_counter()
        if not llm_access_check(request):
            return JsonResponse({"error": "Forbidden"}, status=403)

        try:
            payload = json.loads(request.body.decode("utf-8"))
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        question = (payload.get("question") or "").strip()
        if not question:
            return JsonResponse({"error": "question is required"}, status=400)

        backend = get_llm_backend()
        if backend.__class__.__name__ == "EchoBackend" and not SLICK_REPORTING_SETTINGS.get("LLM_BACKEND"):
            return JsonResponse(
                {
                    "error": (
                        "No LLM backend configured. Set SLICK_REPORTING_SETTINGS['LLM_BACKEND'] "
                        "and ['LLM_BACKEND_OPTIONS'] to enable the assistant."
                    )
                },
                status=400,
            )

        # Stage 1: plan the report configuration.
        catalog = build_reporting_catalog(extra_models=None)
        plan_prompt_text = plan_prompt(question, catalog)
        logger.debug("Planning prompt length: %d", len(plan_prompt_text))

        plan_response_text = backend.complete(plan_prompt_text)
        logger.debug("Plan response text: %s", plan_response_text)
        plan = parse_llm_json(plan_response_text)
        if plan is None:
            return JsonResponse(
                {
                    "error": "Could not parse LLM plan response",
                    "llm_response": plan_response_text,
                },
                status=502,
            )

        report_config = plan.get("report") if isinstance(plan, dict) else None
        if not report_config:
            return JsonResponse(
                {
                    "error": "The assistant could not build a report for this question",
                    "thinking": plan.get("thinking", "") if isinstance(plan, dict) else "",
                    "llm_response": plan_response_text,
                },
                status=400,
            )

        # Stage 2: execute the report.
        try:
            report_data = run_llm_report_config(report_config)
        except Exception as exc:
            logger.exception("Failed to execute LLM report config: %s", report_config)
            return JsonResponse(
                {
                    "error": str(exc),
                    "report_config": report_config,
                },
                status=400,
            )

        # Stage 3: ask the LLM to answer with proofs.
        reports_for_answer = [
            {
                "config": report_config,
                "data": report_data["data"],
                "columns": report_data["columns"],
            }
        ]
        answer_prompt_text = answer_prompt(question, reports_for_answer)
        answer_response_text = backend.complete(answer_prompt_text)
        logger.debug("Answer response text: %s", answer_response_text)
        answer_json = parse_llm_json(answer_response_text)
        if answer_json is None:
            answer_json = {
                "answer": "The assistant returned an unreadable answer.",
                "reasoning": "",
                "proofs": [],
            }

        duration = time.perf_counter() - started_at
        response_data = {
            "answer": answer_json.get("answer", ""),
            "reasoning": answer_json.get("reasoning", ""),
            "proofs": answer_json.get("proofs", []),
            "report_config": report_config,
            "report_data": report_data,
            "duration": round(duration, 3),
        }
        logger.debug("AskLLMView completed in %.3fs", duration)
        return JsonResponse(response_data)

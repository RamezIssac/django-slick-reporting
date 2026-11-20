"""
Example deterministic backend for smoke-testing the LLM evaluator.

Use it with:

    python demo_proj/manage.py evaluate_llm \
        --backend demo_app.eval_backends.FakeBackend \
        --questions-file demo_proj/demo_app/fixtures/llm_eval_questions.json

It returns a sensible demo report plan when the prompt contains the catalog,
and a canned JSON answer otherwise. No network required.
"""

import json


class FakeBackend:
    def __init__(self, **options):
        pass

    def complete(self, prompt):
        plain_text = "Return the plain-text configuration." in prompt or "Return the plain-text answer." in prompt
        if "Available catalog" in prompt:
            if plain_text:
                return (
                    "THINKING: Use SalesTransaction grouped by product and sum value.\n"
                    "REPORT_MODEL: demo_app.SalesTransaction\n"
                    "DATE_FIELD: date\n"
                    "START_DATE: 2026-01-01\n"
                    "END_DATE: 2026-12-31\n"
                    "GROUP_BY: product\n"
                    "COLUMNS: name, Sum(value)\n"
                    "TIME_SERIES_PATTERN:\n"
                    "TIME_SERIES_COLUMNS:\n"
                    "CROSSTAB_FIELD:\n"
                    "CROSSTAB_COLUMNS:\n"
                    "FILTERS:"
                )
            return json.dumps(
                {
                    "thinking": "Use SalesTransaction grouped by product and sum value.",
                    "report": {
                        "report_model": "demo_app.SalesTransaction",
                        "date_field": "date",
                        "start_date": "2026-01-01",
                        "end_date": "2026-12-31",
                        "group_by": "product",
                        "columns": [
                            "name",
                            {"method": "Sum", "field": "value", "name": "value__sum"},
                        ],
                    },
                }
            )
        if plain_text:
            return (
                "ANSWER: Total sales per product are shown in the report.\n"
                "REASONING: Summed value grouped by product.\n"
                "PROOF_TITLE: Product totals\n"
                "PROOF_REPORT_MODEL: demo_app.SalesTransaction\n"
                "PROOF_SUMMARY: Total value sold per product.\n"
                "PROOF_KEY_NUMBERS:"
            )
        return json.dumps(
            {
                "answer": "Total sales per product are shown in the report.",
                "reasoning": "Summed value grouped by product.",
                "proofs": [
                    {
                        "title": "Product totals",
                        "report_model": "demo_app.SalesTransaction",
                        "summary": "Total value sold per product.",
                        "key_numbers": {},
                    }
                ],
            }
        )

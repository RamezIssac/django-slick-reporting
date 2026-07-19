"""
Prompt builders for the natural-language reporting assistant.

Two-stage flow:
1. plan_prompt: ask the LLM to output a JSON report configuration.
2. answer_prompt: ask the LLM to answer the user question with
   reasoning and references to the report(s) it used as proof.
"""

import json

PLAN_SYSTEM_PROMPT = """You are a senior data analyst. Translate a business question into a JSON report configuration.

Use this exact JSON structure:
{
  "thinking": "short reasoning",
  "report": {
    "report_model": "demo_app.SalesTransaction",
    "date_field": "date",
    "start_date": "YYYY-MM-DD",
    "end_date": "YYYY-MM-DD",
    "group_by": "product",
    "columns": ["name", {"method": "Sum", "field": "value", "name": "value__sum"}],
    "time_series_pattern": "quarterly",
    "time_series_columns": [{"method": "Sum", "field": "value", "name": "value__sum"}],
    "filters": {"product_id__in": [1, 2]}
  }
}

Rules:
* Only use fields/models that exist in the catalog.
* Column entry: a string field name OR {"method": "Sum", "field": "value", "name": "value__sum"}.
* Use time_series_pattern (monthly/quarterly/annually) and time_series_columns for values over time.
* Filters are Django ORM kwargs (e.g. product_id__in, client__country__in).
* When the user refers to a related object by its human-readable name (e.g. "Product 1"), use the name string in the filter value (e.g. "product_id__in": ["Product 1"]) and the system will resolve it to the database primary key.
* date_field is required when start_date/end_date are used.
* Use today_iso for relative dates. Q3 = July 1 to September 30. This year = the current year in today_iso.
* If the request cannot be answered, set "report": null.
* Output ONLY JSON. No markdown code fences.
"""


ANSWER_SYSTEM_PROMPT = """You are a helpful data analyst. You have already run one or more reports to answer a business question. You will be given:
1. The user's original question.
2. A list of reports you requested, including their configuration and the data they returned.

Produce a JSON object with this shape:

{
  "answer": "concise business-friendly answer",
  "reasoning": "short explanation of how the data was interpreted",
  "proofs": [
    {
      "title": "human readable title for this proof",
      "report_model": "app_label.ModelName",
      "summary": "what this report shows in one sentence",
      "key_numbers": {"Total value for Product 1 Q3 this year": 12345.67}
    }
  ]
}

Rules:
* The answer should be based strictly on the provided report data.
* When you reference numbers, prefer totals that can be derived from the displayed columns.
* Keep the answer concise but mention any important caveats (missing data, filtered ranges, etc.).
* Do not invent numbers that are not in report_data.
* Return ONLY the JSON object; no markdown code fences.
"""


def _catalog_to_text(catalog):
    return json.dumps(catalog, indent=2, default=str)


def _report_data_to_text(reports_with_data):
    """Keep only the first 100 rows of each report so local LLMs stay fast."""
    output = []
    for report in reports_with_data:
        copy = {
            "config": report.get("config"),
            "columns": report.get("columns"),
            "data": (report.get("data") or [])[:100],
        }
        output.append(copy)
    return json.dumps(output, indent=2, default=str)


def plan_prompt(question, catalog):
    """Return the full prompt text for stage 1 (config generation)."""
    return (
        f"{PLAN_SYSTEM_PROMPT}\n\nAvailable catalog:\n{_catalog_to_text(catalog)}\n\n"
        f"User question: {question}\n\nReturn the JSON configuration."
    )


def answer_prompt(question, reports_with_data):
    """Return the full prompt text for stage 2 (answer generation)."""
    return (
        f"{ANSWER_SYSTEM_PROMPT}\n\n"
        f"User question: {question}\n\n"
        f"Reports used as proof:\n{_report_data_to_text(reports_with_data)}\n\n"
        "Return the JSON answer."
    )

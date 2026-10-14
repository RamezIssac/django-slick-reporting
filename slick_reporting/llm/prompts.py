"""
Prompt builders for the natural-language reporting assistant.

Two-stage flow:
1. plan_prompt: ask the LLM to output a report configuration.
2. answer_prompt: ask the LLM to answer the user question with
   reasoning and references to the report(s) it used as proof.

Both stages can work in JSON (default) or plain-text mode. Plain-text mode
is controlled by SLICK_REPORTING_SETTINGS["LLM_PLAIN_TEXT_RESPONSE"].
"""

from .toon_data import serialize_for_prompt

#: One-line note describing the prompt-side data serialization to the model.
#: Empty for "json" so default prompts stay byte-identical to previous behavior.
_DATA_FORMAT_NOTES = {
    "json": "",
    "plain": (
        "Note: the data below is plain text: 'key: value' lines, and uniform record "
        "lists rendered as tables with ' | ' column separators.\n"
    ),
    "toon": (
        "Note: the data below is TOON (Token-Oriented Object Notation): 'key: value' lines; "
        "uniform record lists are tabular arrays written as 'key[N]{field1,field2}:' "
        "followed by N rows of comma-separated values.\n"
    ),
}

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

PLAN_PLAIN_TEXT_SYSTEM_PROMPT = """You are a senior data analyst. Translate a business question into a plain-text report configuration.

Return a structured plain-text answer with these exact sections, each on its own line, in this order:

THINKING: <short reasoning about how to answer the question>
REPORT_MODEL: <app_label.ModelName>
DATE_FIELD: <field name or leave empty>
START_DATE: <YYYY-MM-DD or leave empty>
END_DATE: <YYYY-MM-DD or leave empty>
GROUP_BY: <field name or leave empty>
COLUMNS: <comma-separated list. Each item is a field name or METHOD(FIELD), e.g. "name, Sum(value)">
TIME_SERIES_PATTERN: <daily/weekly/monthly/quarterly/annually or leave empty>
TIME_SERIES_COLUMNS: <same format as COLUMNS, or leave empty>
CROSSTAB_FIELD: <field name or leave empty>
CROSSTAB_COLUMNS: <same format as COLUMNS, or leave empty>
FILTERS: <Django ORM kwargs as key=value pairs separated by semicolons. Example: "product_id__in=Product 1,Product 2; client__country__in=USA">

Rules:
* Only use fields/models that exist in the catalog.
* Use the columns format "METHOD(field)" for computed columns, e.g. "Sum(value)", "Avg(quantity)", "Count(id)".
* Use TIME_SERIES_PATTERN + TIME_SERIES_COLUMNS for values over time.
* Filters are Django ORM kwargs. When the user refers to a related object by its human-readable name (e.g. "Product 1"), use the name string in the filter value and the system will resolve it to the database primary key.
* DATE_FIELD is required when START_DATE/END_DATE are used.
* Use today_iso for relative dates. This year = the current year in today_iso.
* If the request cannot be answered, write only "REPORT: null".
* Output ONLY the plain-text sections. No JSON, no markdown code fences.
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


ANSWER_PLAIN_TEXT_SYSTEM_PROMPT = """You are a helpful data analyst. You have already run one or more reports to answer a business question. You will be given:
1. The user's original question.
2. A list of reports you requested, including their configuration and the data they returned.

Return a structured plain-text answer with these exact sections, each on its own line, in this order:

ANSWER: <concise business-friendly answer>
REASONING: <short explanation of how the data was interpreted>
PROOF_TITLE: <human readable title for the proof>
PROOF_REPORT_MODEL: <app_label.ModelName>
PROOF_SUMMARY: <what this report shows in one sentence>
PROOF_KEY_NUMBERS: <key-value pairs in "Key: value" format, separated by semicolons>

Rules:
* The answer should be based strictly on the provided report data.
* When you reference numbers, prefer totals that can be derived from the displayed columns.
* Keep the answer concise but mention any important caveats (missing data, filtered ranges, etc.).
* Do not invent numbers that are not in report_data.
* Output ONLY the plain-text sections. No JSON, no markdown code fences.
"""


def _catalog_to_text(catalog, data_format="json"):
    return serialize_for_prompt(catalog, data_format)


def _report_data_to_text(reports_with_data, data_format="json"):
    """Keep only the first 100 rows of each report so local LLMs stay fast."""
    output = []
    for report in reports_with_data:
        copy = {
            "config": report.get("config"),
            "columns": report.get("columns"),
            "data": (report.get("data") or [])[:100],
        }
        output.append(copy)
    return serialize_for_prompt(output, data_format)


def plan_prompt(question, catalog, plain_text=False, data_format="json"):
    """Return the full prompt text for stage 1 (config generation).

    ``plain_text`` selects the response-side instructions (JSON vs plain-text
    sections). ``data_format`` selects how the catalog is serialized inside
    the prompt: "json" (default), "plain" or "toon".
    """
    system = PLAN_PLAIN_TEXT_SYSTEM_PROMPT if plain_text else PLAN_SYSTEM_PROMPT
    instruction = "Return the plain-text configuration." if plain_text else "Return the JSON configuration."
    note = _DATA_FORMAT_NOTES[data_format]
    return (
        f"{system}\n\nAvailable catalog:\n{note}{_catalog_to_text(catalog, data_format=data_format)}\n\n"
        f"User question: {question}\n\n{instruction}"
    )


def answer_prompt(question, reports_with_data, plain_text=False, data_format="json"):
    """Return the full prompt text for stage 2 (answer generation).

    ``plain_text`` selects the response-side instructions (JSON vs plain-text
    sections). ``data_format`` selects how report data is serialized inside
    the prompt: "json" (default), "plain" or "toon".
    """
    system = ANSWER_PLAIN_TEXT_SYSTEM_PROMPT if plain_text else ANSWER_SYSTEM_PROMPT
    instruction = "Return the plain-text answer." if plain_text else "Return the JSON answer."
    note = _DATA_FORMAT_NOTES[data_format]
    return (
        f"{system}\n\n"
        f"User question: {question}\n\n"
        f"Reports used as proof:\n{note}{_report_data_to_text(reports_with_data, data_format=data_format)}\n\n"
        f"{instruction}"
    )

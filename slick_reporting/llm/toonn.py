"""
TOON (Thought-Operate-Observe-Navigate) format for LLM reporting responses.

TOON is a structured plain-text format designed for both human readability and
reliable machine parsing. It uses XML-like section tags wrapped in triple-backtick
fences, making it unambiguous to both humans and parsers.

Two TOON variants exist:
  * TOON plan  – report configuration (THINKING, REPORT_MODEL, etc.)
  * TOON answer – final answer with proofs (ANSWER, REASONING, PROOFS, ...)

Example plan::

  ```toonn
  <THINKING>Group sales by product for Q1 2026 and sum values.</THINKING>
  <REPORT_MODEL>demo_app.SalesTransaction</REPORT_MODEL>
  <DATE_FIELD>date</DATE_FIELD>
  <START_DATE>2026-01-01</START_DATE>
  <END_DATE>2026-03-31</END_DATE>
  <GROUP_BY>product</GROUP_BY>
  <COLUMNS>name, Sum(value), Sum(quantity)</COLUMNS>
  <TIME_SERIES_PATTERN>monthly</TIME_SERIES_PATTERN>
  <TIME_SERIES_COLUMNS>Sum(value)</TIME_SERIES_COLUMNS>
  <FILTERS>product_id__in=Product 1,Product 2</FILTERS>
  ```

Example answer::

  ```toonn
  <ANSWER>Total Q1 2026 sales were $12,345.67 across 3 products.</ANSWER>
  <REASONING>Sales were summed from the product-level report.</REASONING>
  <PROOFS>
    <PROOF>
      <TITLE>Product totals</TITLE>
      <REPORT_MODEL>demo_app.SalesTransaction</REPORT_MODEL>
      <SUMMARY>Total value per product in Q1.</SUMMARY>
      <KEY_NUMBERS>
        <KEY>Product 1</KEY>
        <VALUE>5000.00</VALUE>
        <KEY>Product 2</KEY>
        <VALUE>7345.67</VALUE>
      </KEY_NUMBERS>
    </PROOF>
  </PROOFS>
  ```
"""

import re
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# TOON Plan Parser
# ---------------------------------------------------------------------------

TOON_PLAN_TAGS = {
    "THINKING",
    "REPORT_MODEL",
    "DATE_FIELD",
    "START_DATE",
    "END_DATE",
    "GROUP_BY",
    "COLUMNS",
    "TIME_SERIES_PATTERN",
    "TIME_SERIES_COLUMNS",
    "CROSSTAB_FIELD",
    "CROSSTAB_COLUMNS",
    "CROSSTAB_IDS",
    "FILTERS",
}


def _extract_toonn_block(text: str) -> str:
    """Extract the content between triple-backtick ``toonn`` fences."""
    match = re.search(r"```toonn\s*\n(.*?)```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    # Fallback: strip outer markdown fences if present
    for fence in ("```json", "```"):
        if text.startswith(fence):
            text = text[len(fence) :].lstrip()
            if text.endswith("```"):
                text = text[:-3].rstrip()
            return text
    return text


def _parse_toonn_sections(text: str) -> Dict[str, str]:
    """Parse XML-like tag sections from TOON plan text."""
    sections: Dict[str, str] = {}
    # Strip the outer toonn fences if still present
    text = _extract_toonn_block(text)

    # Match <TAG>...</TAG> (case-insensitive tag names, preserve content casing)
    for match in re.finditer(
        r"<(\w+)>(.*?)</\1>", text, re.DOTALL | re.IGNORECASE
    ):
        tag = match.group(1).upper()
        value = match.group(2).strip()
        # Keep the first non-empty value for each tag.
        if value and tag not in sections:
            sections[tag] = value

    return sections


def parse_toonn_plan(text: str, default: Optional[Any] = None) -> Dict[str, Any]:
    """
    Parse a TOON plan response into the dict structure expected by the
    LLM pipeline (compatible with ``parse_llm_json`` and ``parse_llm_plain_text_plan``).

    Returns ``{"thinking": ..., "report": {...}}`` or ``default`` on failure.
    """
    try:
        sections = _parse_toonn_sections(text)
    except Exception:
        return default

    thinking = sections.get("THINKING", "")

    # Check for explicit null report
    if sections.get("REPORT") and sections["REPORT"].lower() == "null":
        return {"thinking": thinking, "report": None}

    report = {
        "report_model": sections.get("REPORT_MODEL"),
        "date_field": sections.get("DATE_FIELD") or None,
        "start_date": sections.get("START_DATE") or None,
        "end_date": sections.get("END_DATE") or None,
        "group_by": sections.get("GROUP_BY") or None,
        "columns": parse_toonn_columns(sections.get("COLUMNS", "")),
        "time_series_pattern": sections.get("TIME_SERIES_PATTERN") or None,
        "time_series_columns": parse_toonn_columns(
            sections.get("TIME_SERIES_COLUMNS", "")
        ),
        "crosstab_field": sections.get("CROSSTAB_FIELD") or None,
        "crosstab_columns": parse_toonn_columns(
            sections.get("CROSSTAB_COLUMNS", "")
        ),
        "crosstab_ids": sections.get("CROSSTAB_IDS") or None,
        "filters": parse_toonn_filters(sections.get("FILTERS", "")),
    }
    report = {k: v for k, v in report.items() if v not in (None, [], {})}
    return {"thinking": thinking, "report": report}


def parse_toonn_columns(value: str) -> List:
    """Parse 'name, Sum(value), Avg(quantity)' into list of strings/dicts."""
    columns: List = []
    if not value:
        return columns
    for part in re.split(r",(?![^()]*\))", value):
        part = part.strip()
        if not part:
            continue
        match = re.match(r"^(\w+)\(([^)]+)\)$", part)
        if match:
            method, field = match.groups()
            columns.append(
                {
                    "method": method.capitalize(),
                    "field": field.strip(),
                    "name": f"{field.strip()}__{method.lower()}",
                }
            )
        else:
            columns.append(part)
    return columns


def parse_toonn_filters(value: str) -> Dict[str, Any]:
    """Parse 'key1=val1,val2; key2=val3' into a dict."""
    filters: Dict[str, Any] = {}
    if not value:
        return filters
    for part in value.split(";"):
        part = part.strip()
        if "=" not in part:
            continue
        key, val = part.split("=", 1)
        key = key.strip()
        values = [v.strip() for v in val.split(",") if v.strip()]
        filters[key] = values if len(values) > 1 else values[0]
    return filters


# ---------------------------------------------------------------------------
# TOON Answer Parser
# ---------------------------------------------------------------------------


def parse_toonn_answer(text: str, default: Optional[Any] = None) -> Optional[Dict[str, Any]]:
    """
    Parse a TOON answer response into the dict structure expected by the
    LLM pipeline.

    Returns ``{"answer": ..., "reasoning": ..., "proofs": [...]}`` or ``default`` on failure.
    """
    try:
        sections = _parse_toonn_sections(text)
    except Exception:
        return default

    # Must have at least an ANSWER or REASONING section to be valid.
    # Without these, the response is not a valid TOON answer.
    if "ANSWER" not in sections and "REASONING" not in sections:
        return default

    answer = sections.get("ANSWER", "")
    reasoning = sections.get("REASONING", "")

    # Extract PROOFS block – may contain multiple <PROOF>...</PROOF> entries.
    proofs = _parse_toonn_proofs(text)

    return {
        "answer": answer,
        "reasoning": reasoning,
        "proofs": proofs,
    }


def _parse_toonn_proofs(text: str) -> List[Dict[str, Any]]:
    """Extract all <PROOF>...</PROOF> blocks from TOON text."""
    proofs: List[Dict[str, Any]] = []
    text = _extract_toonn_block(text)

    for proof_match in re.finditer(
        r"<PROOF>(.*?)</PROOF>", text, re.DOTALL
    ):
        proof_text = proof_match.group(1).strip()
        proof = {}
        for tag in ("TITLE", "REPORT_MODEL", "SUMMARY"):
            match = re.search(
                rf"<{tag}>(.*?)</{tag}>", proof_text, re.DOTALL
            )
            if match:
                proof[tag.lower()] = match.group(1).strip()

        # Parse KEY_NUMBERS block
        kn_match = re.search(
            r"<KEY_NUMBERS>(.*?)</KEY_NUMBERS>", proof_text, re.DOTALL
        )
        if kn_match:
            kn_text = kn_match.group(1).strip()
            key_numbers: Dict[str, Any] = {}
            # Parse alternating <KEY>...</KEY> <VALUE>...</VALUE> pairs
            keys = re.findall(r"<KEY>(.*?)</KEY>", kn_text, re.DOTALL)
            values = re.findall(r"<VALUE>(.*?)</VALUE>", kn_text, re.DOTALL)
            for key, value in zip(keys, values):
                key = key.strip()
                value = value.strip()
                # Try numeric coercion
                try:
                    if "." in value:
                        value = float(value)
                    else:
                        value = int(value)
                except ValueError:
                    pass
                key_numbers[key] = value
            proof["key_numbers"] = key_numbers

        if proof:
            proofs.append(proof)

    return proofs


# ---------------------------------------------------------------------------
# TOON Prompt Builders (for the LLM)
# ---------------------------------------------------------------------------

TOON_PLAN_SYSTEM_PROMPT = """You are a senior data analyst. Translate a business question into a TOON report configuration.

Return the response wrapped in triple-backtick ``toonn`` fences with XML-like section tags, like this:

```toonn
<THINKING>short reasoning about how to answer the question</THINKING>
<REPORT_MODEL>app_label.ModelName</REPORT_MODEL>
<DATE_FIELD>field name or leave empty</DATE_FIELD>
<START_DATE>YYYY-MM-DD or leave empty</START_DATE>
<END_DATE>YYYY-MM-DD or leave empty</END_DATE>
<GROUP_BY>field name or leave empty</GROUP_BY>
<COLUMNS>comma-separated list. Use METHOD(field) for computed columns, e.g. "name, Sum(value)"</COLUMNS>
<TIME_SERIES_PATTERN>daily/weekly/monthly/quarterly/semiannually/annually/custom or leave empty</TIME_SERIES_PATTERN>
<TIME_SERIES_COLUMNS>same format as COLUMNS, or leave empty</TIME_SERIES_COLUMNS>
<CROSSTAB_FIELD>field name or leave empty</CROSSTAB_FIELD>
<CROSSTAB_COLUMNS>same format as COLUMNS, or leave empty</CROSSTAB_COLUMNS>
<CROSSTAB_IDS>leave empty or specify IDs</CROSSTAB_IDS>
<FILTERS>Django ORM kwargs as key=value pairs separated by semicolons. Example: "product_id__in=Product 1,Product 2"</FILTERS>
```

Rules:
* Only use fields/models that exist in the catalog.
* Use the format "METHOD(field)" for computed columns, e.g. "Sum(value)", "Avg(quantity)", "Count(id)".
* Use TIME_SERIES_PATTERN + TIME_SERIES_COLUMNS for values over time.
* Filters are Django ORM kwargs. When the user refers to a related object by its human-readable name (e.g. "Product 1"), use the name string in the filter value and the system will resolve it to the database primary key.
* DATE_FIELD is required when START_DATE/END_DATE are used.
* Use today_iso for relative dates. This year = the current year in today_iso. Q3 = July 1 to September 30.
* If the request cannot be answered, output only `````toonn\n<REPORT>null</REPORT>\n`````.
* Wrap the ENTIRE response in ```toonn fences with no extra text.
"""


TOON_ANSWER_SYSTEM_PROMPT = """You are a helpful data analyst. You have already run one or more reports to answer a business question. You will be given:
1. The user's original question.
2. A list of reports you requested, including their configuration and the data they returned.

Return the response wrapped in triple-backtick ``toonn`` fences with XML-like section tags, like this:

```toonn
<ANSWER>concise business-friendly answer</ANSWER>
<REASONING>short explanation of how the data was interpreted</REASONING>
<PROOFS>
  <PROOF>
    <TITLE>human readable title for this proof</TITLE>
    <REPORT_MODEL>app_label.ModelName</REPORT_MODEL>
    <SUMMARY>what this report shows in one sentence</SUMMARY>
    <KEY_NUMBERS>
      <KEY>Product 1 Q1 total</KEY>
      <VALUE>12345.67</VALUE>
    </KEY_NUMBERS>
  </PROOF>
</PROOFS>
```

Rules:
* The answer should be based strictly on the provided report data.
* When you reference numbers, prefer totals that can be derived from the displayed columns.
* Keep the answer concise but mention any important caveats (missing data, filtered ranges, etc.).
* Do not invent numbers that are not in report_data.
* Wrap the ENTIRE response in ```toonn fences with no extra text.
"""


def plan_prompt_toonn(question: str, catalog: Dict[str, Any]) -> str:
    """Return the full prompt text for stage 1 (config generation) in TOON format."""
    import json

    catalog_text = json.dumps(catalog, indent=2, default=str)
    return (
        f"{TOON_PLAN_SYSTEM_PROMPT}\n\n"
        f"Available catalog:\n{catalog_text}\n\n"
        f"User question: {question}\n\n"
        f"Return the TOON configuration wrapped in ```toonn fences."
    )


def answer_prompt_toonn(question: str, reports_with_data: List[Dict[str, Any]]) -> str:
    """Return the full prompt text for stage 2 (answer generation) in TOON format."""
    import json

    reports_text = json.dumps(reports_with_data, indent=2, default=str)
    return (
        f"{TOON_ANSWER_SYSTEM_PROMPT}\n\n"
        f"User question: {question}\n\n"
        f"Reports used as proof:\n{reports_text}\n\n"
        f"Return the TOON answer wrapped in ```toonn fences."
    )

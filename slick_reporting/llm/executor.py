"""
Execute a JSON report configuration produced by the LLM.

The executor takes a plain dictionary and constructs a
``slick_reporting.generator.ReportGenerator`` from it.  It also provides
name-to-ID resolution helpers so the LLM can refer to human-readable labels
(e.g. ``Product 1``) while the executor converts them to database primary keys.
"""

import datetime
import json
import logging
import re

from django.db.models import Model
from django.utils.module_loading import import_string

from ..fields import ComputationField
from ..generator import ReportGenerator
from .introspection import resolve_aggregation_method

__all__ = [
    "run_llm_report_config",
    "prepare_filters",
    "parse_llm_json",
    "parse_llm_plain_text_plan",
    "parse_llm_plain_text_answer",
    "clean_json_output",
]

logger = logging.getLogger(__name__)


def _resolve_model(identifier):
    if isinstance(identifier, type) and issubclass(identifier, Model):
        return identifier
    if isinstance(identifier, str):
        if "." in identifier:
            try:
                return import_string(identifier)
            except ImportError:
                pass
        try:
            from django.apps import apps

            return apps.get_model(identifier)
        except (LookupError, ValueError):
            pass
    return None


def _parse_date(value):
    """Parse an ISO date/datetime string or date object."""
    if value is None:
        return None
    if isinstance(value, datetime.datetime):
        return value
    if isinstance(value, datetime.date):
        return datetime.datetime.combine(value, datetime.time.min)
    if isinstance(value, str):
        value = value.strip()
        if "T" in value:
            return datetime.datetime.fromisoformat(value)
        return datetime.datetime.strptime(value, "%Y-%m-%d")
    raise ValueError(f"Cannot parse date {value!r}")


def _resolve_labels_to_ids(report_model, field_name, values):
    """
    Try to convert a list of string labels/names to primary keys.

    The filter key may be a foreign-key ID filter (``product_id__in``), a
    relation filter (``product__in``), or a direct field filter. We derive the
    model that owns the searched value from ``report_model`` and the key.
    """
    if not values:
        return values

    target_model = _target_model_for_kwarg(report_model, field_name)

    result = []
    for val in values:
        if isinstance(val, (int, float)) and not isinstance(val, bool):
            result.append(val)
            continue
        if isinstance(val, str) and val.isdigit():
            result.append(int(val))
            continue
        resolved = _resolve_single_label_to_id(target_model, val)
        result.append(resolved if resolved is not None else val)
    return result


def _resolve_single_label_to_id(model, val):
    """Resolve one human-readable label to a primary key on ``model``."""
    if isinstance(val, (int, float)) and not isinstance(val, bool):
        return val
    if isinstance(val, str) and val.isdigit():
        return int(val)

    candidate_fields = [
        f.name
        for f in model._meta.get_fields()
        if f.name in {"name", "title", "slug", "reference", "code"}
        or f.get_internal_type() in {"CharField", "TextField"}
    ]

    for candidate in candidate_fields:
        try:
            match = model.objects.filter(**{f"{candidate}__iexact": str(val)}).first()
            if match:
                return match.pk
        except Exception:
            continue
    return None


def _build_computation_field(column_config):
    """Convert a dict config into a ComputationField class."""
    if isinstance(column_config, str):
        return column_config
    method = resolve_aggregation_method(column_config.get("method", "Sum"))
    if method is None:
        raise ValueError(f"Unknown aggregation method {column_config.get('method')}")
    return ComputationField.create(
        method=method,
        field=column_config["field"],
        name=column_config.get("name") or f"{method.__name__.lower()}__{column_config['field']}",
        verbose_name=column_config.get("verbose_name", ""),
        is_summable=column_config.get("is_summable", True),
    )


def _target_model_for_kwarg(report_model, key):
    """
    Return the model whose primary key should be used when resolving label
    values for ``key``.  For FK filters like product__in or product_id__in
    we need the Product model, not SalesTransaction.
    """
    suffixes = ("__in", "__exact", "__iexact", "__isnull")
    base_field = key
    for suffix in suffixes:
        if base_field.endswith(suffix):
            base_field = base_field[: -len(suffix)]
            break

    relation_path = None
    if base_field.endswith("_id") and base_field != "id":
        relation_path = base_field[:-3]
    elif "__" not in base_field and base_field != "id":
        # A bare relation name like "product"
        relation_path = base_field
    elif "__" in base_field:
        relation_path = base_field
    else:
        return report_model

    try:
        from django.db.models import ForeignKey

        rel_model = report_model
        for part in relation_path.split("__"):
            field = rel_model._meta.get_field(part)
            if isinstance(field, ForeignKey):
                rel_model = field.related_model
            else:
                return rel_model
        return rel_model
    except Exception:
        return report_model


def prepare_filters(report_model, filters):
    """Split filters into Q objects and kwargs, resolving labels to IDs."""
    q_filters = []
    kw_filters = {}
    filters = filters or {}
    if not isinstance(filters, dict):
        raise ValueError("filters must be a dict of Django ORM kwargs filters")

    for key, value in filters.items():
        if key.lower().startswith("q_"):
            # Allow advanced configs to pass raw Q objects; not encouraged for LLM.
            continue
        if isinstance(value, list):
            value = _resolve_labels_to_ids(report_model, key, value)
        elif isinstance(value, str):
            target_model = _target_model_for_kwarg(report_model, key)
            resolved = _resolve_single_label_to_id(target_model, value)
            if resolved is not None:
                value = resolved
        # ``__in`` lookups need an iterable even for a single value (plain-text
        # plans parse "product_id__in=Product 1" to a single scalar).
        if key.endswith("__in") and not isinstance(value, (list, tuple)):
            value = [value]
        kw_filters[key] = value
    return q_filters, kw_filters


def _normalize_llm_columns(columns, group_by):
    """
    Fix common LLM mistakes when group_by points to a ForeignKey.

    Only when group_by is a bare relation name (no "__") does slick_reporting
    re-point the queryset at the related model, in which case an echo of the
    group_by (e.g. "product" or "product__name") is replaced with "name", the
    related model's display field. When group_by is a field path such as
    "client__country", the queryset stays on the report model, so the column
    must be left untouched.
    """
    if not group_by or "__" in group_by:
        return list(columns or [])
    normalized = []
    for col in columns or []:
        if col == group_by or str(col).startswith(f"{group_by}__"):
            col = "name"
        normalized.append(col)
    return normalized


def run_llm_report_config(config):
    """
    Run a report configuration dict and return the full slick_reporting
    response dictionary.

    ``config`` follows the JSON schema returned by the LLM planner, for example:

        {
            "report_model": "demo_app.SalesTransaction",
            "date_field": "date",
            "start_date": "2024-07-01",
            "end_date": "2024-10-01",
            "group_by": "product",
            "columns": ["name", {"method": "Sum", "field": "value", "name": "value__sum"}],
            "time_series_pattern": "quarterly",
            "time_series_columns": [{"method": "Sum", "field": "value", "name": "value__sum"}],
            "filters": {"product_id__in": [1, 2]},
        }
    """
    report_model = _resolve_model(config["report_model"])
    if report_model is None:
        raise ValueError(f"Could not resolve report_model {config['report_model']!r}")

    group_by = config.get("group_by") or None
    columns = _normalize_llm_columns(config.get("columns", []), group_by)
    columns = [_build_computation_field(c) for c in columns]
    time_series_columns = [_build_computation_field(c) for c in config.get("time_series_columns", [])]
    crosstab_columns = [_build_computation_field(c) for c in config.get("crosstab_columns", [])]

    q_filters, kw_filters = prepare_filters(report_model, config.get("filters"))

    generator = ReportGenerator(
        report_model=report_model,
        start_date=_parse_date(config.get("start_date")),
        end_date=_parse_date(config.get("end_date")),
        date_field=config.get("date_field"),
        group_by=config.get("group_by") or None,
        columns=columns,
        time_series_pattern=config.get("time_series_pattern") or None,
        time_series_columns=time_series_columns or None,
        crosstab_field=config.get("crosstab_field") or None,
        crosstab_columns=crosstab_columns or None,
        crosstab_ids=config.get("crosstab_ids") or None,
        crosstab_compute_remainder=config.get("crosstab_compute_remainder", False),
        q_filters=q_filters,
        kwargs_filters=kw_filters,
    )
    data = generator.get_report_data()
    return generator.get_full_response(
        data=data,
        report_slug="llm_report",
        chart_settings=[],
        default_chart_title="LLM Report",
    )


def clean_json_output(text):
    """Strip markdown fences and fix common LLM JSON mistakes."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
    if text.endswith("```"):
        text = text.rsplit("\n", 1)[0]
    text = text.strip()
    return text


def parse_llm_json(text, default=None):
    """Safely parse JSON from an LLM response."""
    try:
        return json.loads(clean_json_output(text))
    except json.JSONDecodeError:
        logger.debug("Failed to parse LLM JSON: %s", text[:500])
        return default


def parse_llm_plain_text_plan(text):
    """
    Convert a plain-text plan response into the JSON-shaped dict that the
    rest of the LLM pipeline expects.

    Expected sections (case-insensitive keys, any order):
    REPORT_MODEL, DATE_FIELD, START_DATE, END_DATE, GROUP_BY, COLUMNS,
    TIME_SERIES_PATTERN, TIME_SERIES_COLUMNS, CROSSTAB_FIELD,
    CROSSTAB_COLUMNS, FILTERS.
    """
    lines = clean_json_output(text).splitlines()
    sections = {}
    for line in lines:
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip().upper()
        value = value.strip()
        # Keep the first non-empty value for each key.
        if value and key not in sections:
            sections[key] = value

    if sections.get("REPORT", "").lower() == "null":
        return {"thinking": sections.get("THINKING", ""), "report": None}

    report = {
        "report_model": sections.get("REPORT_MODEL"),
        "date_field": sections.get("DATE_FIELD") or None,
        "start_date": sections.get("START_DATE") or None,
        "end_date": sections.get("END_DATE") or None,
        "group_by": sections.get("GROUP_BY") or None,
        "columns": _parse_plain_text_columns(sections.get("COLUMNS", "")),
        "time_series_pattern": sections.get("TIME_SERIES_PATTERN") or None,
        "time_series_columns": _parse_plain_text_columns(sections.get("TIME_SERIES_COLUMNS", "")),
        "crosstab_field": sections.get("CROSSTAB_FIELD") or None,
        "crosstab_columns": _parse_plain_text_columns(sections.get("CROSSTAB_COLUMNS", "")),
        "filters": _parse_plain_text_filters(sections.get("FILTERS", "")),
    }
    # Remove empty optional values.
    report = {k: v for k, v in report.items() if v not in (None, [], {})}
    return {"thinking": sections.get("THINKING", ""), "report": report}


def parse_llm_plain_text_answer(text):
    """
    Convert a plain-text answer response into the JSON-shaped dict that the
    rest of the LLM pipeline expects.

    Expected sections: ANSWER, REASONING, PROOF_TITLE, PROOF_REPORT_MODEL,
    PROOF_SUMMARY, PROOF_KEY_NUMBERS.
    """
    lines = clean_json_output(text).splitlines()
    sections = {}
    for line in lines:
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip().upper()
        value = value.strip()
        if value and key not in sections:
            sections[key] = value

    return {
        "answer": sections.get("ANSWER", ""),
        "reasoning": sections.get("REASONING", ""),
        "proofs": [
            {
                "title": sections.get("PROOF_TITLE", ""),
                "report_model": sections.get("PROOF_REPORT_MODEL", ""),
                "summary": sections.get("PROOF_SUMMARY", ""),
                "key_numbers": _parse_plain_text_key_numbers(sections.get("PROOF_KEY_NUMBERS", "")),
            }
        ],
    }


def _parse_plain_text_columns(value):
    """Parse 'name, Sum(value), Avg(quantity)' into list of strings/dicts."""
    columns = []
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


def _parse_plain_text_filters(value):
    """Parse 'k1=v1,v2; k2=v3' into a dict of lists/strings."""
    filters = {}
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


def _parse_plain_text_key_numbers(value):
    """Parse 'Key: 123; Another: 456' into a dict."""
    out = {}
    if not value:
        return out
    for part in value.split(";"):
        part = part.strip()
        if ":" not in part:
            continue
        key, val = part.split(":", 1)
        key = key.strip()
        raw_val = val.strip()
        # Try to coerce numeric-looking values.
        try:
            if "." in raw_val:
                out[key] = float(raw_val)
            else:
                out[key] = int(raw_val)
        except ValueError:
            out[key] = raw_val
    return out

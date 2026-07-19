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

from django.db.models import Model
from django.utils.module_loading import import_string

from ..fields import ComputationField
from ..generator import ReportGenerator
from .introspection import resolve_aggregation_method

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


def _resolve_labels_to_ids(model, field_name, values):
    """
    Try to convert a list of string labels/names to primary keys on ``model``.

    * If ``field_name`` ends with ``_id`` or ``_id__in`` we are already dealing
      with IDs; return as-is.
    * Otherwise search for the first Char/Text-ish field on ``model`` that
      matches one of the values and return its primary key.
    """
    if not values:
        return values

    base_field = field_name.replace("__in", "").replace("__exact", "").replace("__iexact", "").replace("__isnull", "")
    if base_field.endswith("_id") and base_field != "id":
        return [int(v) if isinstance(v, str) and v.isdigit() else v for v in values]

    candidate_fields = [
        f.name
        for f in model._meta.get_fields()
        if f.name in {"name", "title", "slug", "reference", "code"}
        or f.get_internal_type() in {"CharField", "TextField"}
    ]

    result = []
    for val in values:
        if isinstance(val, (int, float)) and not isinstance(val, bool):
            result.append(val)
            continue
        # Already numeric string?
        try:
            result.append(int(val))
            continue
        except (ValueError, TypeError):
            pass
        try:
            result.append(float(val))
            continue
        except (ValueError, TypeError):
            pass

        for candidate in candidate_fields:
            try:
                match = model.objects.filter(**{f"{candidate}__iexact": str(val)}).first()
                if match:
                    result.append(match.pk)
                    break
            except Exception:
                continue
        else:
            # Could not resolve; keep the original value and let the filter fail
            # noisily if invalid.
            result.append(val)
    return result


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
        kw_filters[key] = value
    return q_filters, kw_filters


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

    columns = [_build_computation_field(c) for c in config.get("columns", [])]
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

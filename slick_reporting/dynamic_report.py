"""
Run an ad-hoc report from a JSON spec.

The spec uses the keys of ``slick_reporting.llm.executor.run_llm_report_config``. Every model and field path in it
is checked against an allowlist of models and the user's view permission before any query runs.
"""

import re

from django import forms
from django.apps import apps
from django.core.exceptions import (
    FieldDoesNotExist,
    FieldError,
    ImproperlyConfigured,
    PermissionDenied,
    ValidationError,
)
from django.db.models import Model

from .app_settings import get_end_date, get_start_date
from .generator import TIME_SERIES_DELTAS, ListViewReportGenerator, ReportGenerator
from .helpers import NUMBER_COLUMN_TYPES
from .llm.executor import _build_computation_field, prepare_filters
from .llm.introspection import REPORTABLE_METHODS, _model_to_catalog
from .registry import field_registry

__all__ = [
    "DYNAMIC_REPORT_SPEC_SCHEMA",
    "describe_dynamic_report_models",
    "run_dynamic_report",
]

MAX_TIME_SERIES_PERIODS = 120
MAX_CROSSTAB_IDS = 50
FILTER_LOOKUPS = {
    "exact",
    "iexact",
    "in",
    "gt",
    "gte",
    "lt",
    "lte",
    "range",
    "isnull",
    "contains",
    "icontains",
    "startswith",
    "istartswith",
    "endswith",
    "iendswith",
    "year",
    "month",
    "day",
}
SUMMABLE_METHODS = {"Sum", "Count"}
NUMERIC_ONLY_METHODS = {"Sum", "Avg"}
COLUMN_NAME_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

_computation_schema = {
    "type": "object",
    "properties": {
        "method": {"enum": sorted(REPORTABLE_METHODS)},
        "field": {"type": "string", "description": "Field path on report_model, e.g. 'value' or 'order__total'."},
        "name": {"type": "string", "pattern": COLUMN_NAME_PATTERN.pattern},
        "verbose_name": {"type": "string"},
    },
    "required": ["method", "field"],
    "additionalProperties": False,
}
_computation_column_schema = {
    "oneOf": [
        _computation_schema,
        {"type": "string", "description": "A registered computation field name, e.g. '__total__'."},
    ]
}
_scalar_schema = {"type": ["string", "number", "integer", "boolean", "null"]}

DYNAMIC_REPORT_SPEC_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Dynamic report spec",
    "type": "object",
    "properties": {
        "report_model": {"type": "string", "description": "The model holding the rows, as 'app_label.ModelName'."},
        "kind": {
            "enum": ["aggregate", "list"],
            "default": "aggregate",
            "description": "'aggregate' computes columns per group_by value (one total row without group_by); "
            "'list' returns the matching report_model rows.",
        },
        "title": {"type": "string"},
        "group_by": {"type": "string", "description": "Field path on report_model to group rows by."},
        "columns": {
            "type": "array",
            "description": "Field paths (on the group_by related model when group_by is a foreign key, else on "
            "report_model) and computation columns. A 'list' report takes field paths only.",
            "items": {"oneOf": [{"type": "string"}, _computation_schema]},
        },
        "date_field": {"type": "string", "description": "Date or datetime field path used by the date range."},
        "start_date": {"type": "string", "format": "date-time"},
        "end_date": {"type": "string", "format": "date-time"},
        "time_series_pattern": {"enum": sorted(TIME_SERIES_DELTAS)},
        "time_series_columns": {"type": "array", "items": _computation_column_schema},
        "crosstab_field": {"type": "string", "description": "Field path on report_model to pivot on."},
        "crosstab_ids": {"type": "array", "items": _scalar_schema, "maxItems": MAX_CROSSTAB_IDS},
        "crosstab_columns": {"type": "array", "items": _computation_column_schema},
        "crosstab_compute_remainder": {"type": "boolean", "default": False},
        "filters": {
            "type": "object",
            "description": "ORM filters: '<field path>[__<lookup>]' to a value; '__in' and '__range' take a list. "
            f"Lookups: {', '.join(sorted(FILTER_LOOKUPS))}.",
            "additionalProperties": {"oneOf": [_scalar_schema, {"type": "array", "items": _scalar_schema}]},
        },
    },
    "required": ["report_model"],
    "additionalProperties": False,
}


def _resolve_model(identifier):
    if isinstance(identifier, type) and issubclass(identifier, Model):
        return identifier
    try:
        return apps.get_model(identifier)
    except (LookupError, ValueError, TypeError):
        return None


def _label(model):
    return f"{model._meta.app_label}.{model._meta.object_name}"


class _SpecValidator:
    """Collects the errors of one spec, keyed by spec key."""

    def __init__(self, spec, request, allowed_models):
        self.spec = spec
        self.user = getattr(request, "user", None) if request is not None else None
        self.check_permissions = request is not None
        self.allowed_models = None
        if allowed_models is not None:
            self.allowed_models = set()
            for identifier in allowed_models:
                model = _resolve_model(identifier)
                if model is None:
                    raise ImproperlyConfigured(f"allowed_models: could not resolve {identifier!r}")
                self.allowed_models.add(model)
        self.errors = {}

    def add_error(self, key, message, code="invalid"):
        self.errors.setdefault(key, []).append(ValidationError(message, code=code))

    def check_model(self, model, key):
        if self.allowed_models is not None and model not in self.allowed_models:
            self.add_error(key, f"Model {_label(model)} is not available for reports.", code="model_not_allowed")
            return False
        if self.check_permissions:
            opts = model._meta
            user = self.user
            if not (
                user
                and (
                    user.has_perm(f"{opts.app_label}.view_{opts.model_name}")
                    or user.has_perm(f"{opts.app_label}.change_{opts.model_name}")
                )
            ):
                raise PermissionDenied(f"No view permission on {_label(model)}.")
        return True

    def resolve_path(self, model, path, key):
        """Return the concrete field at the end of ``path``, or None after recording an error."""
        if not isinstance(path, str) or not path:
            self.add_error(key, f"Expected a field path, got {path!r}.")
            return None
        parts = path.split("__")
        for index, part in enumerate(parts):
            try:
                field = model._meta.get_field(part)
            except FieldDoesNotExist:
                self.add_error(key, f"Unknown field '{part}' on {_label(model)} (in '{path}').", code="unknown_field")
                return None
            related_model = getattr(field, "related_model", None)
            if related_model is not None and not self.check_model(related_model, key):
                return None
            if index < len(parts) - 1:
                if related_model is None:
                    self.add_error(key, f"'{part}' in '{path}' is not a relation.", code="unknown_field")
                    return None
                model = related_model
            elif not getattr(field, "concrete", False):
                self.add_error(key, f"'{path}' is not a database column.", code="unknown_field")
                return None
        return field

    def computation(self, report_model, column, key):
        """Validate a computation column; return a ComputationField class name or config dict."""
        if isinstance(column, str):
            if column not in field_registry.get_all_report_fields_names():
                self.add_error(key, f"'{column}' is not a registered computation field.", code="unknown_field")
                return None
            self.resolve_path(report_model, field_registry.get_field_by_name(column).calculation_field, key)
            return column
        if not isinstance(column, dict):
            self.add_error(key, f"Expected a computation object, got {column!r}.")
            return None
        unknown = set(column) - set(_computation_schema["properties"])
        if unknown:
            self.add_error(key, f"Unknown computation keys: {', '.join(sorted(unknown))}.")
            return None
        method = column.get("method")
        if method not in REPORTABLE_METHODS:
            self.add_error(key, f"Unknown method {method!r}; use one of {', '.join(sorted(REPORTABLE_METHODS))}.")
            return None
        field = self.resolve_path(report_model, column.get("field"), key)
        if field is None:
            return None
        if method in NUMERIC_ONLY_METHODS and field.get_internal_type() not in NUMBER_COLUMN_TYPES:
            self.add_error(key, f"{method} needs a numeric field; '{column['field']}' is not numeric.")
            return None
        name = column.get("name") or f"{method.lower()}__{column['field']}"
        if not COLUMN_NAME_PATTERN.match(name):
            self.add_error(key, f"Column name {name!r} must be a Python identifier.")
            return None
        return {**column, "name": name, "is_summable": method in SUMMABLE_METHODS}

    def computations(self, report_model, key, required=False):
        columns = self.spec.get(key) or []
        if not isinstance(columns, list):
            self.add_error(key, "Expected a list.")
            return []
        if required and not columns:
            self.add_error(key, "At least one computation column is required.", code="required")
        return [self.computation(report_model, column, key) for column in columns]

    def date(self, key):
        value = self.spec.get(key)
        if value in (None, ""):
            return None
        try:
            return forms.DateTimeField().clean(value)
        except ValidationError as error:
            self.errors.setdefault(key, []).extend(error.error_list)
            return None

    def filters(self, report_model):
        filters = self.spec.get("filters") or {}
        if not isinstance(filters, dict):
            self.add_error("filters", "Expected an object of field lookups.")
            return {}
        for name, value in filters.items():
            path, _, lookup = name.rpartition("__")
            if lookup not in FILTER_LOOKUPS or not path:
                path, lookup = name, "exact"
            if self.resolve_path(report_model, path, "filters") is None:
                continue
            if lookup == "range" and not (isinstance(value, list) and len(value) == 2):
                self.add_error("filters", f"'{name}' takes a list of two values.")
            elif lookup == "isnull" and not isinstance(value, bool):
                self.add_error("filters", f"'{name}' takes true or false.")
            elif lookup not in ("in", "range") and isinstance(value, (list, dict)):
                self.add_error("filters", f"'{name}' takes a single value.")
        return filters


def _clean_spec(spec, request, allowed_models, max_time_series_periods):
    """Validate ``spec`` and return the keyword arguments of the report generator."""
    if not isinstance(spec, dict):
        raise ValidationError({"spec": ValidationError("Expected a JSON object.", code="invalid")})
    validator = _SpecValidator(spec, request, allowed_models)
    unknown = set(spec) - set(DYNAMIC_REPORT_SPEC_SCHEMA["properties"])
    for key in sorted(unknown):
        validator.add_error(key, "Unknown spec key.", code="unknown_key")

    report_model = _resolve_model(spec.get("report_model") or "")
    if report_model is None:
        validator.add_error("report_model", f"Unknown model {spec.get('report_model')!r}; use 'app_label.ModelName'.")
        raise ValidationError(validator.errors)
    if not validator.check_model(report_model, "report_model"):
        raise ValidationError(validator.errors)

    kind = spec.get("kind") or "aggregate"
    if kind not in ("aggregate", "list"):
        validator.add_error("kind", "Use 'aggregate' or 'list'.")

    date_field = spec.get("date_field") or None
    if date_field:
        field = validator.resolve_path(report_model, date_field, "date_field")
        if field is not None and field.get_internal_type() not in ("DateField", "DateTimeField"):
            validator.add_error("date_field", f"'{date_field}' is not a date or datetime field.")
    start_date, end_date = validator.date("start_date"), validator.date("end_date")
    if (start_date or end_date) and not date_field:
        validator.add_error("date_field", "start_date and end_date need a date_field.", code="required")
    if date_field and not validator.errors:
        # Defaults go through the same field so both dates share the USE_TZ awareness.
        start_date = start_date or forms.DateTimeField().clean(get_start_date())
        end_date = end_date or forms.DateTimeField().clean(get_end_date())
        if start_date > end_date:
            validator.add_error("end_date", "end_date is before start_date.")
    filters = validator.filters(report_model)

    config = {
        "report_model": report_model,
        "date_field": date_field,
        "start_date": start_date,
        "end_date": end_date,
        "kwargs_filters": filters,
    }
    columns = spec.get("columns") or []
    if not isinstance(columns, list):
        validator.add_error("columns", "Expected a list.")
        columns = []

    if kind == "list":
        for key in ("group_by", "time_series_pattern", "time_series_columns", "crosstab_field", "crosstab_columns"):
            if spec.get(key):
                validator.add_error(key, "A 'list' report takes columns, dates and filters only.")
        if not columns:
            validator.add_error("columns", "At least one column is required.", code="required")
        for column in columns:
            if not isinstance(column, str):
                validator.add_error("columns", f"A 'list' report takes field paths only, got {column!r}.")
            else:
                validator.resolve_path(report_model, column, "columns")
        config["columns"] = columns
    else:
        group_by = spec.get("group_by") or None
        group_by_field = validator.resolve_path(report_model, group_by, "group_by") if group_by else None
        # As in ReportGenerator.check_columns: plain columns live on the group_by related model, if any.
        column_model = getattr(group_by_field, "related_model", None) or report_model
        cleaned_columns = []
        for column in columns:
            is_plain = isinstance(column, str) and column not in field_registry.get_all_report_fields_names()
            if column in ("__time_series__", "__crosstab__"):
                cleaned_columns.append(column)
            elif is_plain and not group_by:
                validator.add_error("columns", f"Field column '{column}' needs a group_by.")
            elif is_plain:
                validator.resolve_path(column_model, column, "columns")
                cleaned_columns.append(column)
            else:
                cleaned_columns.append(validator.computation(report_model, column, "columns"))
        config.update(group_by=group_by, columns=cleaned_columns)

        pattern = spec.get("time_series_pattern") or None
        if pattern:
            if pattern not in TIME_SERIES_DELTAS:
                validator.add_error("time_series_pattern", f"Use one of {', '.join(sorted(TIME_SERIES_DELTAS))}.")
            elif not date_field:
                validator.add_error("date_field", "A time series needs a date_field.", code="required")
            elif start_date and end_date:
                period_start, periods = start_date, 0
                while period_start < end_date and periods <= max_time_series_periods:
                    period_start, periods = period_start + TIME_SERIES_DELTAS[pattern], periods + 1
                if periods > max_time_series_periods:
                    validator.add_error(
                        "time_series_pattern",
                        f"More than {max_time_series_periods} periods; use a longer pattern or a shorter date range.",
                        code="too_many_periods",
                    )
            config.update(
                time_series_pattern=pattern,
                time_series_columns=validator.computations(report_model, "time_series_columns", required=True),
            )

        crosstab_field = spec.get("crosstab_field") or None
        if crosstab_field:
            validator.resolve_path(report_model, crosstab_field, "crosstab_field")
            crosstab_ids = spec.get("crosstab_ids") or []
            if not isinstance(crosstab_ids, list) or len(crosstab_ids) > MAX_CROSSTAB_IDS:
                validator.add_error("crosstab_ids", f"Expected a list of at most {MAX_CROSSTAB_IDS} values.")
            remainder = spec.get("crosstab_compute_remainder", False)
            if not isinstance(remainder, bool):
                validator.add_error("crosstab_compute_remainder", "Expected true or false.")
            config.update(
                crosstab_field=crosstab_field,
                crosstab_ids=crosstab_ids,
                crosstab_compute_remainder=remainder,
                crosstab_columns=validator.computations(report_model, "crosstab_columns", required=True),
            )

    if validator.errors:
        raise ValidationError(validator.errors)
    return kind, config


def run_dynamic_report(spec, request, allowed_models=None, max_time_series_periods=MAX_TIME_SERIES_PERIODS):
    """
    Validate ``spec`` (see ``DYNAMIC_REPORT_SPEC_SCHEMA``) and run it; return the report full response.

    ``allowed_models`` lists the models (classes or 'app_label.ModelName') the spec may read or traverse, None
    allows every installed model. With a ``request``, ``request.user`` needs the view (or change) permission on
    each of those models, else ``PermissionDenied``; pass ``request=None`` to skip that check. A bad spec, or a
    model outside ``allowed_models``, raises ``ValidationError`` with an ``error_dict`` keyed by spec key.
    """
    kind, config = _clean_spec(spec, request, allowed_models, max_time_series_periods)
    report_model = config["report_model"]
    try:
        q_filters, config["kwargs_filters"] = prepare_filters(report_model, config["kwargs_filters"])
        for key in ("columns", "time_series_columns", "crosstab_columns"):
            if key in config:
                config[key] = [_build_computation_field(column) for column in config[key]]
        generator_class = ListViewReportGenerator if kind == "list" else ReportGenerator
        generator = generator_class(q_filters=q_filters, **config)
        data = generator.get_report_data()
        return generator.get_full_response(
            data=data,
            report_slug="dynamic_report",
            chart_settings=[],
            default_chart_title=spec.get("title") or report_model._meta.verbose_name_plural,
        )
    except (FieldDoesNotExist, FieldError, ImproperlyConfigured, KeyError, ValueError, TypeError) as error:
        raise ValidationError({"spec": ValidationError(str(error), code="invalid_spec")}) from error


def describe_dynamic_report_models(request=None, allowed_models=None):
    """
    Describe the models a spec may use: fields with their types and relations, in the shape of the llm catalog.

    Relations to models outside ``allowed_models`` or without the user's view permission are left out.
    """
    validator = _SpecValidator({}, request, allowed_models)
    candidates = validator.allowed_models if allowed_models is not None else apps.get_models()

    def usable(model):
        try:
            return validator.check_model(model, "model")
        except PermissionDenied:
            return False

    usable_labels = {_label(model) for model in candidates if usable(model)}
    catalog = []
    for model in sorted(candidates, key=_label):
        if _label(model) not in usable_labels:
            continue
        entry = _model_to_catalog(model)
        entry["fields"] = [
            field
            for field in entry["fields"]
            if not field["is_relation"] or field.get("related_model") in usable_labels
        ]
        catalog.append(entry)
    return catalog

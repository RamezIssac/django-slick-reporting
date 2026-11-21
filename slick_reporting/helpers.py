import datetime
import re
from collections import OrderedDict
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.utils.encoding import force_str


def get_calculation_annotation(calculation_field, calculation_method):
    """
    Returns the default django annotation
    @param calculation_field: the field to calculate ex 'value'
    @param calculation_method: the aggregation method ex: Sum
    @return: the annotation ex value__sum
    """

    return f"{calculation_field.lower()}__{calculation_method.name.lower()}"


def get_foreign_keys(model):
    """
    Scans a model and return an Ordered Dictionary with the foreign keys found
    :param model: the model to scan
    :return: Ordered Dict
    """
    from django.db import models

    fields = model._meta.get_fields()
    fkeys = OrderedDict()
    for f in fields:
        if (
            f.is_relation
            and type(f) is not models.OneToOneRel
            and type(f) is not models.ManyToOneRel
            and type(f) is not models.ManyToManyRel
            and type(f) is not GenericForeignKey
        ):
            fkeys[f.attname] = f
    return fkeys


def get_field_from_query_text(path, model):
    """
    return the field of a query text
    `modelA__modelB__foo_field` would return foo_field on modelsB
    :param path:
    :param model:
    :return:
    """
    relations = path.split("__")
    _rel = model
    field = None
    for i, m in enumerate(relations):
        field = _rel._meta.get_field(m)
        if i == len(relations) - 1:
            return field
        _rel = field.related_model
    return field


def user_test_function(report_view, request=None):
    """
    A default test function return True on DEBUG, otherwise return the user.is_superuser
    :param report_view: the report view being accessed, or None for non-view contexts
    :param request: optional request object (used by the LLM assistant endpoint)
    :return:
    """
    # In test mode without an actual request, allow access.
    if request is None and report_view is not None:
        request = getattr(report_view, "request", None)

    if request is None:
        return settings.DEBUG

    user = getattr(request, "user", None)
    if not settings.DEBUG:
        return bool(user and getattr(user, "is_superuser", False))
    return True


DATE_ONLY_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
NUMBER_COLUMN_TYPES = {
    "number",
    "AutoField",
    "BigAutoField",
    "SmallAutoField",
    "IntegerField",
    "BigIntegerField",
    "SmallIntegerField",
    "PositiveIntegerField",
    "PositiveSmallIntegerField",
    "PositiveBigIntegerField",
    "FloatField",
    "DecimalField",
}
COLUMN_TYPE_ALIASES = {
    "DateField": "date",
    "DateTimeField": "datetime",
    "BooleanField": "boolean",
    "NullBooleanField": "boolean",
}


def end_of_day_if_date_only(value):
    """Turn a date-only end date ("2026-03-31" or a ``date``) into the last second of that day; leave others."""
    if isinstance(value, str) and DATE_ONLY_PATTERN.match(value.strip()):
        return f"{value.strip()}T23:59:59"
    if isinstance(value, datetime.date) and not isinstance(value, datetime.datetime):
        return datetime.datetime.combine(value, datetime.time(23, 59, 59))
    return value


def normalize_column_type(column_type):
    """Map a report column ``type`` (a model field internal type or a computation field type) to
    one of ``number``, ``text``, ``date``, ``datetime`` or ``boolean``."""
    if column_type in NUMBER_COLUMN_TYPES:
        return "number"
    return COLUMN_TYPE_ALIASES.get(column_type, "text")


def _compact_value(value):
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, float):
        value = Decimal(str(value))
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, int):
        return str(value)
    if isinstance(value, (datetime.date, datetime.time)):
        return value.isoformat()
    return force_str(value)


def _to_decimal(value):
    if isinstance(value, float):
        return Decimal(str(value))
    return Decimal(value)


def compact_response(full_response, max_rows=None):
    """
    Turn a report full response (``ReportGenerator.get_full_response()``) into a compact,
    JSON-safe result: visible columns, positional rows, and totals computed over all rows.

    Numbers are strings (Decimal safe), dates are ISO strings and empty cells are ``None``.
    """
    columns = [col for col in full_response["columns"] if col.get("visible", True) is not False]
    data = full_response["data"]
    metadata = full_response.get("metadata", {})
    built_rows = len(data.get(columns[0]["name"], [])) if columns else 0
    row_count = metadata.get("row_count", built_rows)
    database_totals = metadata.get("totals", {})

    declared_totals = set(metadata.get("total_columns") or [])
    compact_columns = []
    totals = {}
    for col in columns:
        col_type = normalize_column_type(col.get("type"))
        compact_columns.append({"name": col["name"], "label": force_str(col["verbose_name"]), "type": col_type})
        if col["name"] in database_totals:
            totals[col["name"]] = format(_to_decimal(database_totals[col["name"]]), "f")
        elif col["name"] in declared_totals or (col_type == "number" and col.get("is_summable") is True):
            values = data.get(col["name"], [])
            try:
                total = sum(
                    (_to_decimal(v) for v in values if v not in (None, "") and not isinstance(v, bool)), Decimal(0)
                )
            except (InvalidOperation, TypeError, ValueError):
                continue
            totals[col["name"]] = format(total, "f")

    shown = built_rows if max_rows is None else min(built_rows, max_rows)
    column_values = [data.get(col["name"], []) for col in columns]
    rows = [[_compact_value(values[index]) for values in column_values] for index in range(shown)]

    date_window = metadata.get("date_window") or {}
    return {
        "columns": compact_columns,
        "rows": rows,
        "totals": totals,
        "row_count": row_count,
        "truncated": shown < row_count,
        "date_window": {
            "start": _compact_value(date_window.get("start")),
            "end": _compact_value(date_window.get("end")),
            "label": _compact_value(date_window.get("label")),
        },
    }

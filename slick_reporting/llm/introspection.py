"""
Build a JSON-serializable catalog describing all of the reporting building
blocks available to the LLM assistant.

The catalog includes:
* registered Django models relevant to reporting (with fields, types, relations)
* available ComputationField classes
* time series patterns
* common aggregation methods exposed by django.db.models
"""

import datetime

from django.apps import apps
from django.db import models
from django.db.models import Avg, Count, Max, Min, Sum
from django.utils.module_loading import import_string

from ..app_settings import SLICK_REPORTING_SETTINGS
from ..registry import field_registry

NUMBER_FIELD_TYPES = {
    "AutoField",
    "BigAutoField",
    "IntegerField",
    "BigIntegerField",
    "SmallIntegerField",
    "PositiveIntegerField",
    "PositiveSmallIntegerField",
    "PositiveBigIntegerField",
    "FloatField",
    "DecimalField",
}

DATE_FIELD_TYPES = {
    "DateField",
    "DateTimeField",
}

RELATION_FIELD_TYPES = {
    "ForeignKey",
    "OneToOneField",
    "ManyToManyField",
}


def _is_numeric(field):
    return field.get_internal_type() in NUMBER_FIELD_TYPES


def _is_date(field):
    return field.get_internal_type() in DATE_FIELD_TYPES


def _is_relation(field):
    return field.get_internal_type() in RELATION_FIELD_TYPES


def _resolve_model(model_identifier):
    """
    Resolve a model from ``app_label.ModelName`` or a model class.
    Return ``None`` if the identifier cannot be resolved.
    """
    if isinstance(model_identifier, type) and issubclass(model_identifier, models.Model):
        return model_identifier
    if isinstance(model_identifier, str):
        try:
            return import_string(model_identifier)
        except ImportError:
            pass
        try:
            return apps.get_model(model_identifier)
        except (LookupError, ValueError, AttributeError):
            return None
    return None


def _model_to_catalog(model):
    fields = []
    for field in model._meta.get_fields():
        info = {
            "name": field.name,
            "type": field.get_internal_type(),
            "verbose_name": str(getattr(field, "verbose_name", field.name)),
            "is_numeric": _is_numeric(field),
            "is_date": _is_date(field),
            "is_relation": _is_relation(field),
        }
        if _is_relation(field):
            try:
                related = field.related_model
                info["related_model"] = f"{related._meta.app_label}.{related._meta.object_name}"
                info["related_verbose_name"] = str(related._meta.verbose_name)
            except AttributeError:
                pass
        fields.append(info)
    return {
        "identifier": f"{model._meta.app_label}.{model._meta.object_name}",
        "verbose_name": str(model._meta.verbose_name),
        "fields": fields,
    }


def _computation_fields_catalog():
    """List all registered ComputationField classes."""
    names = field_registry.get_all_report_fields_names()
    output = []
    for name in names:
        klass = field_registry.get_field_by_name(name)
        output.append(
            {
                "name": name,
                "verbose_name": getattr(klass, "verbose_name", name) or name,
                "calculation_field": getattr(klass, "calculation_field", ""),
                "calculation_method": getattr(klass, "calculation_method", "").__name__,
                "type": getattr(klass, "type", "number"),
                "is_summable": getattr(klass, "is_summable", True),
            }
        )
    return output


def _aggregation_methods_catalog():
    """Map aggregation method names to their import paths."""
    return [
        {"name": "Sum", "path": "django.db.models.Sum", "numeric_only": True},
        {"name": "Avg", "path": "django.db.models.Avg", "numeric_only": True},
        {"name": "Count", "path": "django.db.models.Count", "numeric_only": False},
        {"name": "Min", "path": "django.db.models.Min", "numeric_only": False},
        {"name": "Max", "path": "django.db.models.Max", "numeric_only": False},
    ]


def _model_id_map():
    """Return app_label.ModelName -> pk-type for value mapping in filters."""
    return {f"{m._meta.app_label}.{m._meta.object_name}": m._meta.pk.get_internal_type() for m in apps.get_models()}


REPORTABLE_METHODS = {"Sum": Sum, "Avg": Avg, "Count": Count, "Min": Min, "Max": Max}

TIME_SERIES_PATTERNS = [
    "daily",
    "weekly",
    "bi-weekly",
    "monthly",
    "quarterly",
    "semiannually",
    "annually",
    "custom",
]


def build_reporting_catalog(extra_models=None):
    """
    Build and return the catalog dictionary sent to the LLM.

    By default all installed models are scanned.  Set
    ``SLICK_REPORTING_SETTINGS["LLM_CATALOG_MODELS"]`` to a list of
    ``app_label.ModelName`` strings to restrict the catalog.
    """
    configured_models = SLICK_REPORTING_SETTINGS.get("LLM_CATALOG_MODELS")
    if configured_models is not None:
        models_list = []
        for identifier in configured_models:
            model = _resolve_model(identifier)
            if model:
                models_list.append(model)
    else:
        models_list = apps.get_models()

    if extra_models:
        for identifier in extra_models:
            model = _resolve_model(identifier)
            if model and model not in models_list:
                models_list.append(model)

    return {
        "models": [_model_to_catalog(m) for m in models_list],
        "model_id_map": _model_id_map(),
        "computation_fields": _computation_fields_catalog(),
        "aggregation_methods": _aggregation_methods_catalog(),
        "time_series_patterns": TIME_SERIES_PATTERNS,
        "today_iso": datetime.datetime.now().isoformat(),
    }


def resolve_aggregation_method(name):
    """Resolve a string like 'Sum' to the django aggregation class."""
    if isinstance(name, type):
        return name
    method = REPORTABLE_METHODS.get(name)
    if method is None:
        method = REPORTABLE_METHODS.get(getattr(name, "name", ""))
    return method

from collections import OrderedDict

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey


def get_calculation_annotation(calculation_field, calculation_method):
    """
    Returns the default django annotation
    @param calculation_field: the field to calculate ex 'value'
    @param calculation_method: the aggregation method ex: Sum
    @return: the annotation ex value__sum
    """

    return "__".join([calculation_field.lower(), calculation_method.name.lower()])


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

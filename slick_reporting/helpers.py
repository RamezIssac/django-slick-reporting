import logging
from collections import OrderedDict

from django.apps import apps
from django.conf import settings
from django.db import models

get_model = apps.get_model

User = settings.AUTH_USER_MODEL

logger = logging.getLogger(__name__)


def get_calculation_annotation(calculation_field, calculation_method):
    '''
    Returns the default django annotation
    @param calculation_field: the field to calculate ex 'value'
    @param calculation_method: the aggregation method ex: Sum
    @return: the annotation ex value__sum
    '''

    return '__'.join([calculation_field.lower(), calculation_method.name.lower()])


def apply_order_to_list(lst, order_list):
    values = []
    unordered = list(lst)
    for o in order_list:
        o = o.strip()
        if o in lst:
            values.append(o)
            try:
                unordered.remove(o)
            except ValueError:
                pass
    values += unordered
    return values


def get_foreign_keys(model):
    fields = model._meta.get_fields()
    fkeys = OrderedDict()
    for f in fields:
        if f.is_relation and type(f) is not models.OneToOneRel \
                and type(f) is not models.ManyToOneRel and type(f) is not models.ManyToManyRel:
            fkeys[f.attname] = f

    return fkeys


def get_field_from_query_text(path, model):
    relations = path.split('__')
    _rel = model
    field = None
    for i, m in enumerate(relations):
        field = _rel._meta.get_field(m)
        if i == len(relations) - 1:
            return field
        _rel = field.related_model
    return field

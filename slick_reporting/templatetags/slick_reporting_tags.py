import simplejson as json

from django import template
from django.core.serializers import serialize
from django.db.models import QuerySet
from django.utils.encoding import force_text
from django.utils.functional import Promise
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag
def get_data(row, column):
    return row[column['name']]


def jsonify(object):
    def date_handler(obj):
        if hasattr(obj, 'isoformat'):
            return obj.isoformat()
        elif isinstance(obj, Promise):
            return force_text(obj)

    if isinstance(object, QuerySet):
        return serialize('json', object)

    return mark_safe(json.dumps(object, use_decimal=True, default=date_handler))


register.filter('jsonify', jsonify)

import datetime

import simplejson as json

from django import template
from django.utils.encoding import force_text
from django.utils.functional import Promise
from django.utils.html import format_html
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag
def get_data(row, column):
    return row[column['name']]




_js_escapes = {
    ord('\\'): '\\u005C',
    ord('\''): '\\u0027',
    ord('"'): '\\u0022',
    ord('>'): '\\u003E',
    ord('<'): '\\u003C',
    ord('&'): '\\u0026',
    ord('='): '\\u003D',
    ord('-'): '\\u002D',
    ord(';'): '\\u003B',
    ord('`'): '\\u0060',
    ord('\u2028'): '\\u2028',
    ord('\u2029'): '\\u2029'
}


_json_script_escapes = {
    ord('>'): '\\u003E',
    ord('<'): '\\u003C',
    ord('&'): '\\u0026',
}


def date_handler(obj):
    if type(obj) is datetime.datetime:
        return obj.strftime('%Y-%m-%d %H:%M')
    elif hasattr(obj, 'isoformat'):
        return obj.isoformat()
    elif isinstance(obj, Promise):
        return force_text(obj)



@register.filter
def serialize_to_json(value, element_id):
    """
    Escape all the HTML/XML special characters with their unicode escapes, so
    value is safe to be output anywhere except for inside a tag attribute. Wrap
    the escaped JSON in a script tag.
    """
    json_str = json.dumps(value, use_decimal=True, default=date_handler).translate(_json_script_escapes)
    return format_html(
        '<script id="{}" type="application/json">{}</script>',
        element_id, mark_safe(json_str)
    )

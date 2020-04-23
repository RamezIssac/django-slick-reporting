from django import template

from ra.utils.permissions import has_report_permission_permission

register = template.Library()


@register.simple_tag
def get_data(row, column):
    return row[column['name']]

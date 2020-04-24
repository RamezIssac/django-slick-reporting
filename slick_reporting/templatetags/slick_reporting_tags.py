from django import template

register = template.Library()


@register.simple_tag
def get_data(row, column):
    return row[column['name']]

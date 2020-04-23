from django import template

from ra.utils.permissions import has_report_permission_permission

register = template.Library()



@register.simple_tag(takes_context=True)
def can_print_report(context, report):
    return has_report_permission_permission(context['request'], report.get_base_model_name(), report.get_report_slug())

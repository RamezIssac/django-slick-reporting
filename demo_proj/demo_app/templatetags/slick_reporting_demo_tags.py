import inspect

from django import template
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe

register = template.Library()


def get_section(section):
    from ..helpers import TUTORIAL, GROUP_BY, TIME_SERIES, CROSSTAB, PIVOT
    to_use = []

    if section == "tutorial":
        to_use = TUTORIAL
    elif section == "group_by":
        to_use = GROUP_BY
    elif section == "timeseries":
        to_use = TIME_SERIES
    elif section == "crosstab":
        to_use = CROSSTAB
    elif section == "pivot":
        to_use = PIVOT
    return to_use


@register.simple_tag(takes_context=True)
def get_menu(context, section):
    request = context['request']
    to_use = get_section(section)
    menu = []
    for link, report in to_use:
        is_active = "active" if f"/{link}/" in request.path else ""

        menu.append(format_html(
            '<a class="dropdown-item {active}" href="{href}">{text}</a>', active=is_active,
            href=reverse(link), text=report.report_title or link)
        )

    return mark_safe("".join(menu))


@register.simple_tag
def get_report_source(report):
    try:
        return inspect.getsource(report.__class__)
    except (OSError, TypeError):
        return "# Source code not available"


@register.simple_tag
def get_report_class_label(report):
    cls = report.__class__
    return f"{cls.__module__}.{cls.__name__}"


@register.simple_tag(takes_context=True)
def should_show(context, section):
    request = context["request"]
    to_use = get_section(section)
    for link, report in to_use:
        if f"/{link}/" in request.path:
            return "show"
    return ""

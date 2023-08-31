from django import template
from django.template.defaultfilters import capfirst
from django.template.loader import get_template, render_to_string
from django.urls import reverse
from django.utils.html import format_html
from django.utils.module_loading import import_string
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag(takes_context=True)
def get_menu(context, section):
    from ..helpers import TUTORIAL, GROUP_BY, TIME_SERIES, CROSSTAB
    request = context['request']
    to_use = None
    menu = []
    if section == "tutorial":
        to_use = TUTORIAL
    elif section == "group_by":
        to_use = GROUP_BY
    elif section == "timeseries":
        to_use = TIME_SERIES
    elif section == "crosstab":
        to_use = CROSSTAB

    for link, report in to_use:
        is_active = "active" if f"/{link}/" in request.path else ""

        menu.append(format_html(
            '<a class="dropdown-item {active}" href="{href}">{text}</a>', active=is_active,
            href=reverse(link), text=report.report_title or link)
        )

    return mark_safe("".join(menu))

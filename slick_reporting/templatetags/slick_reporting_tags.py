from django import template
from django.template.loader import get_template
from django.forms import Media
from django.urls import reverse, resolve
from django.utils.safestring import mark_safe

from ..app_settings import SLICK_REPORTING_JQUERY_URL, SLICK_REPORTING_SETTINGS, get_media

register = template.Library()


@register.simple_tag
def get_widget_from_url(url_name=None, url=None, **kwargs):
    _url = ""
    if not (url_name or url):
        raise ValueError("url_name or url must be provided")
    if url_name:
        url = reverse(url_name)
    view = resolve(url)
    kwargs["report"] = view.func.view_class
    kwargs["report_url"] = url
    return get_widget(**kwargs)


@register.simple_tag
def get_widget(report, template_name="", url_name="", report_url=None, **kwargs):
    kwargs["report"] = report
    if not report:
        raise ValueError("report argument is empty. Are you sure you're using the correct report name")
    if not (report_url or url_name):
        raise ValueError("report_url or url_name must be provided")

    # if not report.chart_settings:
    kwargs.setdefault("display_chart", bool(report.chart_settings))
    kwargs.setdefault("display_table", True)

    kwargs.setdefault("display_chart_selector", kwargs["display_chart"])
    kwargs.setdefault("display_title", True)

    passed_title = kwargs.get("title", None)
    kwargs["title"] = passed_title or report.get_report_title()
    kwargs["report_url"] = report_url
    if not report_url:
        kwargs["report_url"] = reverse(url_name)

    kwargs.setdefault("extra_params", "")

    template = get_template(template_name or "slick_reporting/widget_template.html")

    return template.render(context=kwargs)


@register.simple_tag
def add_jquery():
    if SLICK_REPORTING_JQUERY_URL:
        return mark_safe(f'<script src="{SLICK_REPORTING_JQUERY_URL}"></script>')
    return ""


@register.simple_tag
def get_charts_media(chart_settings):
    charts_dict = SLICK_REPORTING_SETTINGS["CHARTS"]
    media = Media()
    if chart_settings == "all":
        available_types = charts_dict.keys()
    else:
        available_types = [chart["engine_name"] for chart in chart_settings]
        available_types = set(available_types)

    for type in available_types:
        media += Media(css=charts_dict.get(type, {}).get("css", {}), js=charts_dict.get(type, {}).get("js", []))
    return media


@register.simple_tag
def get_slick_reporting_media():
    from django.forms import Media

    media = get_media()
    return Media(css=media["css"], js=media["js"])


@register.simple_tag
def get_slick_reporting_settings():
    return dict(SLICK_REPORTING_SETTINGS)

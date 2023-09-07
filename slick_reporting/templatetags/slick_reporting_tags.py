import simplejson as json

from django import template
from django.core.serializers import serialize
from django.db.models import QuerySet
from django.template.loader import get_template
from django.urls import reverse, resolve
from django.utils.encoding import force_str
from django.utils.functional import Promise
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag
def get_data(row, column):
    return row[column["name"]]


def jsonify(object):
    def date_handler(obj):
        if hasattr(obj, "isoformat"):
            return obj.isoformat()
        elif isinstance(obj, Promise):
            return force_str(obj)

    if isinstance(object, QuerySet):
        return serialize("json", object)

    return mark_safe(json.dumps(object, use_decimal=True, default=date_handler))


register.filter("jsonify", jsonify)


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

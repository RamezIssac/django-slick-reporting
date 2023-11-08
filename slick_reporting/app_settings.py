from django.conf import settings
from django.urls import get_callable
from django.utils.functional import lazy
from django.utils.translation import gettext_lazy as _

import datetime


def get_first_of_this_year():
    d = datetime.datetime.today()
    return datetime.datetime(d.year, 1, 1, 0, 0)


def get_end_of_this_year():
    d = datetime.datetime.today()
    return datetime.datetime(d.year + 1, 1, 1, 0, 0)


def get_start_date():
    start_date = getattr(settings, "SLICK_REPORTING_DEFAULT_START_DATE", False)
    return start_date or get_first_of_this_year()


def get_end_date():
    end_date = getattr(settings, "SLICK_REPORTING_DEFAULT_END_DATE", False)
    return end_date or datetime.datetime.today()


SLICK_REPORTING_DEFAULT_START_DATE = lazy(get_start_date, datetime.datetime)()
SLICK_REPORTING_DEFAULT_END_DATE = lazy(get_end_date, datetime.datetime)()


SLICK_REPORTING_DEFAULT_CHARTS_ENGINE = getattr(settings, "SLICK_REPORTING_DEFAULT_CHARTS_ENGINE", "highcharts")


SLICK_REPORTING_JQUERY_URL = getattr(
    settings, "SLICK_REPORTING_JQUERY_URL", "https://code.jquery.com/jquery-3.7.0.min.js"
)


SLICK_REPORTING_SETTINGS_DEFAULT = {
    "JQUERY_URL": SLICK_REPORTING_JQUERY_URL,
    "DEFAULT_START_DATE_TIME": get_start_date(),
    "DEFAULT_END_DATE_TIME": get_end_date(),
    "DEFAULT_CHARTS_ENGINE": SLICK_REPORTING_DEFAULT_CHARTS_ENGINE,
    "MEDIA": {
        "override": False,
        "js": (
            "https://cdn.jsdelivr.net/momentjs/latest/moment.min.js",
            "https://cdn.jsdelivr.net/npm/select2@4.1.0-rc.0/dist/js/select2.min.js",
            "https://cdn.datatables.net/1.13.4/js/jquery.dataTables.min.js",
            "https://cdn.datatables.net/1.13.4/js/dataTables.bootstrap5.min.js",
            "slick_reporting/slick_reporting.js",
            "slick_reporting/slick_reporting.report_loader.js",
            "slick_reporting/slick_reporting.datatable.js",
        ),
        "css": {
            "all": (
                "https://cdn.jsdelivr.net/npm/select2@4.1.0-rc.0/dist/css/select2.min.css",
                "https://cdn.datatables.net/1.13.4/css/dataTables.bootstrap5.min.css",
            )
        },
    },
    "FONT_AWESOME": {
        "CSS_URL": "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.3/css/all.min.css",
        "ICONS": {
            "pie": "fas fa-chart-pie",
            "bar": "fas fa-chart-bar",
            "line": "fas fa-chart-line",
            "area": "fas fa-chart-area",
            "column": "fas fa-chart-bar",
        },
    },
    "CHARTS": {
        "highcharts": {
            "entryPoint": "$.slick_reporting.highcharts.displayChart",
            "js": ("https://code.highcharts.com/highcharts.js", "slick_reporting/slick_reporting.highchart.js"),
        },
        "chartsjs": {
            "entryPoint": "$.slick_reporting.chartsjs.displayChart",
            "js": ("https://cdn.jsdelivr.net/npm/chart.js", "slick_reporting/slick_reporting.chartsjs.js"),
        },
    },
    "MESSAGES": {
        "total": _("Total"),
        "export_to_csv": _("Export to CSV"),
    },
    "REPORT_VIEW_ACCESS_FUNCTION": "slick_reporting.helpers.user_test_function",
}


def get_slick_reporting_settings():
    slick_settings = SLICK_REPORTING_SETTINGS_DEFAULT.copy()
    slick_chart_settings = slick_settings["CHARTS"].copy()

    user_settings = getattr(settings, "SLICK_REPORTING_SETTINGS", {})
    user_chart_settings = user_settings.get("CHARTS", {})

    user_media_settings = user_settings.get("MEDIA", {})
    override_media = user_media_settings.get("override", False)
    if override_media:
        slick_settings["MEDIA"] = user_media_settings
    else:
        slick_settings["MEDIA"]["js"] = slick_settings["MEDIA"]["js"] + user_media_settings.get("js", ())
        slick_settings["MEDIA"]["css"]["all"] = slick_settings["MEDIA"]["css"]["all"] + user_media_settings.get(
            "css", {}
        ).get("all", ())

    slick_chart_settings.update(user_chart_settings)
    slick_settings.update(user_settings)
    slick_settings["CHARTS"] = slick_chart_settings

    # slick_settings = {**SLICK_REPORTING_SETTINGS_DEFAULT, **getattr(settings, "SLICK_REPORTING_SETTINGS", {})}
    start_date = getattr(settings, "SLICK_REPORTING_DEFAULT_START_DATE", False)
    end_date = getattr(settings, "SLICK_REPORTING_DEFAULT_END_DATE", False)
    # backward compatibility, todo remove in next major release
    if start_date:
        slick_settings["DEFAULT_START_DATE_TIME"] = start_date
    if end_date:
        slick_settings["DEFAULT_END_DATE_TIME"] = end_date

    return slick_settings


SLICK_REPORTING_SETTINGS = lazy(get_slick_reporting_settings, dict)()


def get_media():
    return SLICK_REPORTING_SETTINGS["MEDIA"]


def get_access_function():
    return get_callable(SLICK_REPORTING_SETTINGS["REPORT_VIEW_ACCESS_FUNCTION"])

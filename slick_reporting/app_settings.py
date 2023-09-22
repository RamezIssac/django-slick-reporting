from django.conf import settings
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

SLICK_REPORTING_FORM_MEDIA_DEFAULT = {
    # "css": {
    #     "all": (
    #         "https://cdn.datatables.net/v/bs4/dt-1.10.20/datatables.min.css",
    #         "https://cdnjs.cloudflare.com/ajax/libs/Chart.js/2.9.3/Chart.min.css",
    #     )
    # },
    # "js": (
    #     "https://code.jquery.com/jquery-3.3.1.slim.min.js",
    #     "https://cdn.datatables.net/v/bs4/dt-1.10.20/datatables.min.js",
    #     "https://cdnjs.cloudflare.com/ajax/libs/Chart.js/2.9.3/Chart.bundle.min.js",
    #     "https://cdnjs.cloudflare.com/ajax/libs/Chart.js/2.9.3/Chart.min.js",
    #     "https://code.highcharts.com/highcharts.js",
    # ),
}

SLICK_REPORTING_FORM_MEDIA = getattr(settings, "SLICK_REPORTING_FORM_MEDIA", SLICK_REPORTING_FORM_MEDIA_DEFAULT)
SLICK_REPORTING_DEFAULT_CHARTS_ENGINE = getattr(settings, "SLICK_REPORTING_DEFAULT_CHARTS_ENGINE", "highcharts")


SLICK_REPORTING_JQUERY_URL = getattr(
    settings, "SLICK_REPORTING_JQUERY_URL", "https://code.jquery.com/jquery-3.7.0.min.js"
)

SLICK_REPORTING_SETTINGS = getattr(settings, "SLICK_REPORTING_SETTINGS", {})

SLICK_REPORTING_SETTINGS_DEFAULT = {
    "JQUERY_URL": SLICK_REPORTING_JQUERY_URL,
    "DEFAULT_START_DATE_TIME": SLICK_REPORTING_DEFAULT_START_DATE,
    "DEFAULT_END_DATE_TIME": SLICK_REPORTING_DEFAULT_END_DATE,
    "FONT_AWESOME": {
        "CSS_URL": "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.3/css/all.min.css",
        "ICONS": {
            "pie": "fas fa-chart-pie",
            "bar": "fas fa-chart-bar",
            "line": "fas fa-chart-line",
            "area": "fas fa-chart-area",
            "column": "fas fa-chart-column",
        },
    },
    "CHARTS": {
        "highcharts": "$.slick_reporting.highcharts.displayChart",
        "chartjs": "$.slick_reporting.chartjs.displayChart",
    },
    "MESSAGES": {
        "total": _("Total"),
    },
}

SLICK_REPORTING_SETTINGS = {**SLICK_REPORTING_SETTINGS_DEFAULT, **SLICK_REPORTING_SETTINGS}

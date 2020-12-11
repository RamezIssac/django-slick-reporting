import pytz
from django.conf import settings
from django.utils.functional import lazy

import datetime


def get_first_of_this_year():
    d = datetime.datetime.today()
    return datetime.datetime(d.year, 1, 1, 0, 0)


def get_end_of_this_year():
    d = datetime.datetime.today()
    return datetime.datetime(d.year + 1, 1, 1, 0, 0)


SLICK_REPORTING_DEFAULT_START_DATE = getattr(settings, '', lazy(get_first_of_this_year, datetime.datetime)())
SLICK_REPORTING_DEFAULT_END_DATE = getattr(settings, '', lazy(get_end_of_this_year, datetime.datetime)())

SLICK_REPORTING_FORM_MEDIA_DEFAULT = {
    'css': {
        'all': (
            'https://cdn.datatables.net/v/bs4/dt-1.10.20/datatables.min.css',
            'https://cdnjs.cloudflare.com/ajax/libs/Chart.js/2.9.3/Chart.min.css',
        )
    },
    'js': (
        'https://code.jquery.com/jquery-3.3.1.slim.min.js',
        'https://cdn.datatables.net/v/bs4/dt-1.10.20/datatables.min.js',
        'https://cdnjs.cloudflare.com/ajax/libs/Chart.js/2.9.3/Chart.bundle.min.js',
        'https://cdnjs.cloudflare.com/ajax/libs/Chart.js/2.9.3/Chart.min.js',
        'https://code.highcharts.com/highcharts.js',
    )
}

SLICK_REPORTING_FORM_MEDIA = getattr(settings, 'SLICK_REPORTING_FORM_MEDIA', SLICK_REPORTING_FORM_MEDIA_DEFAULT)
SLICK_REPORTING_DEFAULT_CHARTS_ENGINE = getattr(settings, 'SLICK_REPORTING_DEFAULT_CHARTS_ENGINE', 'highcharts')

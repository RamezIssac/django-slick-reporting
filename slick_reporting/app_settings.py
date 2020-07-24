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

from django.conf import settings


def dashboard_edit_allowed():
    """
    Whether users may edit dashboards (open the configurator, build/save widgets).

    Controlled by ``settings.SLICK_REPORTING_DASHBOARD_ALLOW_EDIT`` (default True).
    Set it to False to expose dashboards as read-only.
    """
    return getattr(settings, "SLICK_REPORTING_DASHBOARD_ALLOW_EDIT", True)

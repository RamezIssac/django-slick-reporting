Time Series Reports
==================


Here is a quick recipe to what you want to do

.. code-block:: python

    from django.utils.translation import gettext_lazy as _
    from django.db.models import Sum
    from slick_reporting.views import SlickReportView

    class MyReport(SlickReportView):

        time_series_pattern = "monthly"
        # options are : "daily", "weekly", "monthly", "yearly", "custom"

        # if time_series_pattern is "custom", then you can specify the dates like so
        # time_series_custom_dates = [
        #   (datetime.date(2020, 1, 1), datetime.date(2020, 1, 14)),
        #   (datetime.date(2020, 2, 1), datetime.date(2020, 2, 14)),
        #   (datetime.date(2020, 3, 1), datetime.date(2020, 3,14)),
        ]


        time_series_columns = [
            SlickReportField.create(Sum, "value", verbose_name=_("Value")),
        ]
        # These columns will be calculated for each period in the time series.



        columns = ['some_optional_field',
            '__time_series__',
            # You can customize where the time series columns are displayed in relation to the other columns

            SlickReportField.create(Sum, "value", verbose_name=_("Value")),
            # This is the same as the time_series_columns, but this one will be on the whole set

        ]




        time_series_selector = True
        # This will display a selector to change the time series pattern

        # settings for the time series selector
        # ----------------------------------

        time_series_selector_choices=None  # A list Choice tuple [(value, label), ...]
        time_series_selector_default = "monthly"  # The initial value for the time series selector
        time_series_selector_label = _("Period Pattern)  # The label for the time series selector
        time_series_selector_allow_empty = False  # Allow the user to select an empty time series



Links to demo
-------------

Time series Selector pattern Demo `Demo <https://my-shop.django-erp-framework.com/reports/profitability/profitabilityreportmonthly/>`_
and here is the `Code on github <https://github.com/RamezIssac/my-shop/blob/main/general_reports/reports.py#L44>`_ for the report.

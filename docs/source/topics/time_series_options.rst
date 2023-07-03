.. _time_series:

Time Series Reports
===================

A Time series report is a report that is generated for a periods of time.
The period can be daily, weekly, monthly, yearly or custom, calculations will be performed for each period in the time series.

Here is a quick recipe to what you want to do

.. code-block:: python

        from django.utils.translation import gettext_lazy as _
        from django.db.models import Sum
        from slick_reporting.views import ReportView


        class MyReport(ReportView):

            # options are : "daily", "weekly", "monthly", "yearly", "custom"
            time_series_pattern = "monthly"


            # if time_series_pattern is "custom", then you can specify the dates like so
            time_series_custom_dates = [
              (datetime.date(2020, 1, 1), datetime.date(2020, 1, 14)),
              (datetime.date(2020, 2, 1), datetime.date(2020, 2, 14)),
              (datetime.date(2020, 3, 1), datetime.date(2020, 3,14)),
            ]

            # These columns will be calculated for each period in the time series.
            time_series_columns = [
                SlickReportField.create(Sum, "value", verbose_name=_("Value")),
            ]


            columns = [
                "product_sku",

                # You can customize where the time series columns are displayed in relation to the other columns
                "__time_series__",

                # This is the same as the time_series_columns, but this one will be on the whole set
                SlickReportField.create(Sum, "value", verbose_name=_("Value")),

            ]

            # This will display a selector to change the time series pattern
            time_series_selector = True

            # settings for the time series selector
            # ----------------------------------
            time_series_selector_choices = None  # A list Choice tuple [(value, label), ...]
            time_series_selector_default = (
                "monthly"  # The initial value for the time series selector
            )
            # The label for the time series selector
            time_series_selector_label = _("Period Pattern")
            # Allow the user to select an empty time series
            time_series_selector_allow_empty = False


.. _time_series_options:

Time Series Options
-------------------

.. attribute:: ReportView.time_series_pattern

            the time series pattern to be used in the report, it can be one of the following:
            Possible options are: daily, weekly, semimonthly, monthly, quarterly, semiannually, annually and custom.
            if `custom` is set, you'd need to override  `time_series_custom_dates`

.. attribute:: ReportView.time_series_custom_dates

            A list of tuples of (start_date, end_date) pairs indicating the start and end of each period.

.. attribute:: ReportView.time_series_columns

            a list of Calculation Field names which will be included in the series calculation.

            .. code-block:: python

                    class MyReport(ReportView):

                        time_series_columns = [
                            SlickReportField.create(
                                Sum, "value", verbose_name=_("Value"), is_summable=True, name="sum__value"
                            ),
                            SlickReportField.create(
                                Avg, "Price", verbose_name=_("Avg Price"), is_summable=False
                            ),
                        ]





Links to demo
''''''''''''''

Time series Selector pattern `Demo <https://my-shop.django-erp-framework.com/reports/general_reports/profitabilityreportmonthly/>`_
and the `Code on github <https://github.com/RamezIssac/my-shop/blob/main/general_reports/reports.py#L44>`_ for it.

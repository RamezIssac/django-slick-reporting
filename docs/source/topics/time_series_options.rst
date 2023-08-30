.. _time_series:

Time Series Reports
===================

A Time series report is a report that is generated for a periods of time.
The period can be daily, weekly, monthly, yearly or custom, calculations will be performed for each period in the time series.

General use case
----------------

Here is a quick look at the general use case


.. code-block:: python

        from django.utils.translation import gettext_lazy as _
        from django.db.models import Sum
        from slick_reporting.views import ReportView

        class TimeSeriesReport(ReportView):
            report_model = SalesTransaction
            group_by = "client"

            time_series_pattern = "monthly"
            # options are: "daily", "weekly", "bi-weekly", "monthly", "quarterly", "semiannually", "annually" and "custom"

            date_field = "date"

            # These columns will be calculated for each period in the time series.
            time_series_columns = [
                SlickReportField.create(Sum, "value", verbose_name=_("Sales For Month")),
            ]

            columns = [
                "name",
                "__time_series__",

                # This is the same as the time_series_columns, but this one will be on the whole set
                SlickReportField.create(Sum, "value", verbose_name=_("Total Sales")),

            ]

            chart_settings = [
                Chart("Client Sales",
                      Chart.BAR,
                      data_source=["sum__value"],
                      title_source=["name"],
                      ),
                Chart("Total Sales Monthly",
                      Chart.PIE,
                      data_source=["sum__value"],
                      title_source=["name"],
                      plot_total=True,
                      ),
                Chart("Total Sales [Area chart]",
                      Chart.AREA,
                      data_source=["sum__value"],
                      title_source=["name"],
                      )
            ]


Allowing the User to Choose the time series pattern
---------------------------------------------------

You can allow the User to Set the Pattern for the report , Let's create another version of the above report
where the user can choose the pattern

.. code-block:: python

        class TimeSeriesReportWithSelector(TimeSeriesReport):
            report_title = _("Time Series Report With Pattern Selector")
            time_series_selector = True
            time_series_selector_choices = (
                ("daily", _("Daily")),
                ("weekly", _("Weekly")),
                ("bi-weekly", _("Bi-Weekly")),
                ("monthly", _("Monthly")),
            )
            time_series_selector_default = "bi-weekly"

            time_series_selector_label = _("Period Pattern")
            # The label for the time series selector

            time_series_selector_allow_empty = True
            # Allow the user to select an empty time series, in which case no time series will be applied to the report.


Set Custom Dates for the Time Series
------------------------------------

You might want to set irregular pattern for the time series,
Like first 10 days of each month , or the 3 summer month of every year.

Let's see how you can do that, inheriting from teh same Time series we did first.

.. code-block:: python


        def get_current_year():
            return datetime.datetime.now().year


        class TimeSeriesReportWithCustomDates(TimeSeriesReport):
            report_title = _("Time Series Report With Custom Dates")
            time_series_pattern = "custom"
            time_series_custom_dates = (
                (datetime.datetime(get_current_year(), 1, 1), datetime.datetime(get_current_year(), 1, 10)),
                (datetime.datetime(get_current_year(), 2, 1), datetime.datetime(get_current_year(), 2, 10)),
                (datetime.datetime(get_current_year(), 3, 1), datetime.datetime(get_current_year(), 3, 10)),
            )



Customize the Computation Field label
-------------------------------------
Maybe you want to customize how the title of the time series computation field.
For this you want to Subclass ``SlickReportField``, where you can customize
how the title is created and use it in the time_series_column instead of the one created on the fly.

Example:

.. code-block:: python


    class SumOfFieldValue(SlickReportField):
        # A custom computation Field identical to the one created like this
        # Similar to `SlickReportField.create(Sum, "value", verbose_name=_("Total Sales"))`

        calculation_method = Sum
        calculation_field = "value"
        name = "sum_of_value"

        @classmethod
        def get_time_series_field_verbose_name(cls, date_period, index, dates, pattern):
            # date_period: is a tuple (start_date, end_date)
            # index is the  index of the current pattern in the patterns on the report
            # dates: the whole dates we have on the reports
            # pattern it's the pattern name, ex: monthly, daily, custom
            return f"First 10 days sales {date_period[0].month}-{date_period[0].year}"


    class TimeSeriesReportWithCustomDatesAndCustomTitle(TimeSeriesReportWithCustomDates):
        report_title = _("Time Series Report With Custom Dates and custom Title")

        time_series_columns = [
            SumOfFieldValue,  # Use our newly created SlickReportField with the custom time series verbose name
        ]

        chart_settings = [
            Chart("Client Sales",
                  Chart.BAR,
                  data_source=["sum_of_value"],  # Note:  This is the name of our `TotalSalesField` `field
                  title_source=["name"],
                  ),
            Chart("Total Sales [Pie]",
                  Chart.PIE,
                  data_source=["sum_of_value"],
                  title_source=["name"],
                  plot_total=True,
                  ),
        ]



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

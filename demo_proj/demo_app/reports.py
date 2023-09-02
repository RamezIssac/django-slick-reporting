import datetime

from django.db.models import Sum, Q
from django.utils.translation import gettext_lazy as _

from slick_reporting.fields import SlickReportField
from slick_reporting.views import ListReportView
from slick_reporting.views import ReportView, Chart
from .forms import TotalSalesFilterForm
from .models import SalesTransaction, Product


class ProductSales(ReportView):
    report_title = _("Product Sales")
    report_model = SalesTransaction
    date_field = "date"
    group_by = "product"

    columns = [
        "name",
        SlickReportField.create(
            method=Sum, field="value", name="value__sum", verbose_name="Total sold $", is_summable=True,
        ),
    ]

    # Charts
    chart_settings = [
        Chart(
            "Total sold $",
            Chart.BAR,
            data_source=["value__sum"],
            title_source=["name"],
        ),
    ]


class TotalProductSales(ReportView):
    report_title = _("Product Sales Quantity and Value [no auto load]")
    report_model = SalesTransaction
    date_field = "date"
    group_by = "product"
    columns = [
        "name",
        SlickReportField.create(Sum, "quantity", verbose_name="Total quantity sold", is_summable=False),
        SlickReportField.create(Sum, "value", name="sum__value", verbose_name="Total Value sold $"),
    ]
    auto_load = False  # require the user to press the filter, useful if the report is resource demanding

    chart_settings = [
        Chart(
            "Total sold $",
            Chart.BAR,
            data_source=["sum__value"],
            title_source=["name"],
        ),
        Chart(
            "Total sold $ [PIE]",
            Chart.PIE,
            data_source=["sum__value"],
            title_source=["name"],
        ),
    ]


class TotalProductSalesByCountry(ReportView):
    report_title = _("Product Sales by Country")

    report_model = SalesTransaction
    date_field = "date"
    group_by = "client__country"  # notice the double underscore
    columns = [
        "client__country",
        SlickReportField.create(Sum, "value", name="sum__value", verbose_name="Total Value sold by country $"),
    ]

    chart_settings = [
        Chart(
            "Total sold by country $",
            Chart.PIE,  # A Pie Chart
            data_source=["sum__value"],
            title_source=["client__country"],
        ),
    ]


class SumValueComputationField(SlickReportField):
    computation_method = Sum
    computation_field = "value"
    verbose_name = _("Sales Value")
    name = "my_value_sum"


class MonthlyProductSales(ReportView):
    report_title = _("Product Sales Monthly")
    report_model = SalesTransaction
    date_field = "date"
    group_by = "product"
    columns = ["name", "sku"]

    time_series_pattern = "monthly"
    time_series_columns = [
        SumValueComputationField,
    ]

    chart_settings = [
        Chart(
            _("Total Sales Monthly"),
            Chart.PIE,
            data_source=["my_value_sum"],
            title_source=["name"],
            plot_total=True,
        ),
        Chart(
            _("Sales Monthly [Bar]"),
            Chart.COLUMN,
            data_source=["my_value_sum"],
            title_source=["name"],
        ),
    ]


class ProductSalesPerClientCrosstab(ReportView):
    report_title = _("Product Sales Per Client Crosstab")
    report_model = SalesTransaction
    date_field = "date"
    group_by = "product"
    crosstab_field = "client"

    crosstab_columns = [
        SumValueComputationField,
    ]

    # crosstab_ids = ["US", "KW", "EG", "DE"]
    crosstab_compute_remainder = True

    columns = [
        "name",
        "sku",
        "__crosstab__",
        SumValueComputationField,
    ]


class ProductSalesPerCountryCrosstab(ReportView):
    report_title = _("Product Sales Per Country Crosstab")
    report_model = SalesTransaction
    date_field = "date"
    group_by = "product"
    crosstab_field = "client__country"
    crosstab_columns = [
        SumValueComputationField,
    ]

    crosstab_ids = ["US", "KW", "EG", "DE"]
    crosstab_compute_remainder = True

    columns = [
        "name",
        "sku",
        "__crosstab__",
        SumValueComputationField,
    ]


class LastTenSales(ListReportView):
    report_model = SalesTransaction
    report_title = "Last 10 sales"
    date_field = "date"
    filters = ["client"]
    columns = [
        "product",
        "date",
        "quantity",
        "price",
        "value",
    ]
    default_order_by = "-date"
    limit_records = 10


class TotalProductSalesWithCustomForm(TotalProductSales):
    report_title = _("Total Product Sales with Custom Form")
    form_class = TotalSalesFilterForm
    columns = [
        "name",
        "size",
        SlickReportField.create(Sum, "quantity", verbose_name="Total quantity sold", is_summable=False),
        SlickReportField.create(Sum, "value", name="sum__value", verbose_name="Total Value sold $"),
    ]


class GroupByReport(ReportView):
    report_model = SalesTransaction
    report_title = _("Group By Report")
    date_field = "date"
    group_by = "product"

    columns = [
        "name",
        SlickReportField.create(
            method=Sum, field="value", name="value__sum", verbose_name="Total sold $", is_summable=True,
        ),
    ]

    # Charts
    chart_settings = [
        Chart(
            "Total sold $",
            Chart.BAR,
            data_source=["value__sum"],
            title_source=["name"],
        ),
    ]


class GroupByTraversingFieldReport(GroupByReport):
    report_title = _("Group By Traversing Field")
    group_by = "product__product_category"


class GroupByCustomQueryset(ReportView):
    report_model = SalesTransaction
    report_title = _("Group By Custom Queryset")
    date_field = "date"

    group_by_custom_querysets = [
        SalesTransaction.objects.filter(product__size__in=["big", "extra_big"]),
        SalesTransaction.objects.filter(product__size__in=["small", "extra_small"]),
        SalesTransaction.objects.filter(product__size="medium"),
    ]
    group_by_custom_querysets_column_verbose_name = _("Product Size")

    columns = [
        "__index__",
        SlickReportField.create(Sum, "value", verbose_name=_("Total Sold $"), name="value"),
    ]

    chart_settings = [
        Chart(
            title="Total sold By Size $",
            type=Chart.PIE,
            data_source=["value"],
            title_source=["__index__"],
        ),
        Chart(
            title="Total sold By Size $",
            type=Chart.BAR,
            data_source=["value"],
            title_source=["__index__"],
        ),
    ]

    def format_row(self, row_obj):
        # Put the verbose names we need instead of the integer index
        index = row_obj['__index__']
        if index == 0:
            row_obj["__index__"] = "Big"
        elif index == 1:
            row_obj['__index__'] = "Small"
        elif index == 2:
            row_obj['__index__'] = "Medium"
        return row_obj


class NoGroupByReport(ReportView):
    report_model = SalesTransaction
    report_title = _("No-Group-By Report")
    date_field = "date"
    group_by = ""

    columns = [
        SlickReportField.create(
            method=Sum, field="value", name="value__sum", verbose_name="Total sold $", is_summable=True,
        ),
    ]


class TimeSeriesReport(ReportView):
    report_title = _("Time Series Report")
    report_model = SalesTransaction
    group_by = "client"
    time_series_pattern = "monthly"
    # options are : "daily", "weekly", "bi-weekly", "monthly", "quarterly", "semiannually", "annually" and "custom"

    date_field = "date"
    time_series_columns = [
        SlickReportField.create(Sum, "value", verbose_name=_("Sales For ")),
    ]
    # These columns will be calculated for each period in the time series.

    columns = [
        "name",
        "__time_series__",
        # placeholder for the generated time series columns

        SlickReportField.create(Sum, "value", verbose_name=_("Total Sales")),
        # This is the same as the time_series_columns, but this one will be on the whole set

    ]

    chart_settings = [
        Chart("Client Sales",
              Chart.BAR,
              data_source=["sum__value"],
              title_source=["name"],
              ),
        Chart("Total Sales [Pie]",
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


class TimeSeriesReportWithCustomGroupByQueryset(ReportView):
    report_title = _("Time Series Report")
    report_model = SalesTransaction
    group_by_custom_querysets = (
        SalesTransaction.objects.filter(client__country='US'),
        SalesTransaction.objects.filter(client__country__in=['RS', 'DE']),
    )

    time_series_pattern = "monthly"

    date_field = "date"
    time_series_columns = [
        SlickReportField.create(Sum, "value", verbose_name=_("Sales For ")),
        # "__total__"
    ]

    columns = [
        "__index__",
        "__time_series__",
        # placeholder for the generated time series columns

        SlickReportField.create(Sum, "value", verbose_name=_("Total Sales")),
        # This is the same as the time_series_columns, but this one will be on the whole set

    ]

    chart_settings = [
        Chart("Client Sales",
              Chart.BAR,
              data_source=["sum__value"],
              title_source=["__index__"],
              ),
        Chart("Total Sales [Pie]",
              Chart.PIE,
              data_source=["sum__value"],
              title_source=["__index__"],
              plot_total=True,
              ),
        Chart("Total Sales [Area chart]",
              Chart.AREA,
              data_source=["sum__value"],
              title_source=["name"],
              )
    ]


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


class TimeSeriesWithoutGroupBy(ReportView):
    report_title = _("Time Series without a group by")
    report_model = SalesTransaction
    time_series_pattern = "monthly"
    date_field = "date"
    time_series_columns = [
        SlickReportField.create(Sum, "value", verbose_name=_("Sales For ")),
    ]

    columns = [
        "__time_series__",
        SlickReportField.create(Sum, "value", verbose_name=_("Total Sales")),
    ]

    chart_settings = [
        Chart("Total Sales [Bar]",
              Chart.BAR,
              data_source=["sum__value"],
              title_source=["name"],
              ),
        Chart("Total Sales [Pie]",
              Chart.PIE,
              data_source=["sum__value"],
              title_source=["name"],
              ),
    ]


class CrosstabReport(ReportView):
    report_title = _("Cross tab Report")
    report_model = SalesTransaction
    group_by = "client"
    date_field = "date"

    columns = [
        "name",
        "__crosstab__",
        # You can customize where the crosstab columns are displayed in relation to the other columns

        SlickReportField.create(Sum, "value", verbose_name=_("Total Value")),
        # This is the same as the calculation in the crosstab,
        # but this one will be on the whole set. IE total value.
    ]

    crosstab_field = "product"
    crosstab_columns = [
        SlickReportField.create(Sum, "value", verbose_name=_("Value")),
    ]


class CrosstabWithTraversingField(CrosstabReport):
    report_title = _("Cross tab Report With Traversing Field")
    crosstab_field = "product__size"


class CrosstabWithIds(CrosstabReport):
    report_title = _("Cross tab Report With Pre-set Ids")

    def get_crosstab_ids(self):
        return [Product.objects.first().pk, Product.objects.last().pk]


class CrosstabWithIdsCustomFilter(CrosstabReport):
    report_title = _("Crosstab with Custom Filters")
    crosstab_ids_custom_filters = [
        (~Q(product__size__in=["extra_big", "big"]), dict()),

        (None, dict(product__size__in=["extra_big", "big"])),
    ]
    # Note:
    # if crosstab_ids_custom_filters is set, these settings has NO EFFECT
    # crosstab_field = "client"
    # crosstab_ids = [1, 2]
    # crosstab_compute_remainder = True


class CustomCrossTabTotalField(SlickReportField):
    calculation_field = "value"
    calculation_method = Sum
    verbose_name = _("Sales for")
    name = "sum__value"

    @classmethod
    def get_crosstab_field_verbose_name(cls, model, id):
        if id == "----":  # 4 dashes: the remainder column
            return _("Rest of Products")

        name = Product.objects.get(pk=id).name
        return f"{cls.verbose_name} {name}"


class CrossTabReportWithCustomVerboseName(CrosstabReport):
    report_title = _("Crosstab with customized verbose name")
    crosstab_columns = [
        CustomCrossTabTotalField
    ]


class CustomCrossTabTotalField2(CustomCrossTabTotalField):
    @classmethod
    def get_crosstab_field_verbose_name(cls, model, id):
        print(model, id)
        if id == 0:
            return f"{cls.verbose_name} Big and Extra Big"
        return f"{cls.verbose_name} all other sizes"

    @classmethod
    def get_time_series_field_verbose_name(cls, date_period, index, dates, pattern):
        print("time series verbose name")
        return super().get_time_series_field_verbose_name(date_period, index, dates, pattern)


class CrossTabReportWithCustomVerboseNameCustomFilter(CrosstabWithIdsCustomFilter):
    report_title = _("Crosstab customized verbose name with custom filter")

    crosstab_columns = [
        CustomCrossTabTotalField2
    ]


class CrossTabWithTimeSeries(CrossTabReportWithCustomVerboseNameCustomFilter):
    report_title = _("Crosstab with time series")
    time_series_pattern = "monthly"

    columns = [
        "name",
        "__time_series__"
    ]

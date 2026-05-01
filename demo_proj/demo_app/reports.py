import datetime

from django.db.models import Sum, Q
from django.http import HttpResponse
from django.utils.translation import gettext_lazy as _

from slick_reporting.fields import ComputationField
from slick_reporting.views import ListReportView
from slick_reporting.views import ReportView, Chart
from .forms import TotalSalesFilterForm
from .models import SalesTransaction, Product, MonthlySalesSummary


class ProductSales(ReportView):
    report_title = _("Product Sales")
    report_description = _("Given a typical 'Sale Item' model, this report demonstrate a total of product sold. "
                           "With a bar and a pie charts.")
    report_model = SalesTransaction
    date_field = "date"
    group_by = "product"

    columns = [
        "name",
        ComputationField.create(
            method=Sum,
            field="value",
            name="value__sum",
            verbose_name="Total sold $",
            is_summable=True,
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
    report_description = _("We compute the report over *two* fields `quantity and `value`."
                           "Results only load after you press Filter")
    report_model = SalesTransaction
    date_field = "date"
    group_by = "product"
    columns = [
        "name",
        ComputationField.create(Sum, "quantity", verbose_name="Total quantity sold", is_summable=False),
        ComputationField.create(Sum, "value", name="sum__value", verbose_name="Total Value sold $"),
    ]
    auto_load = False  # Require the user to press the filter, useful if the report is resource demanding

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
    report_description = _("Group by using Django's double-underscore traversal (group_by='client__country').")

    report_model = SalesTransaction
    date_field = "date"
    group_by = "client__country"  # notice the double underscore
    columns = [
        "client__country",
        ComputationField.create(Sum, "value", name="sum__value", verbose_name="Total Value sold by country $"),
    ]

    chart_settings = [
        Chart(
            "Total sold by country $",
            Chart.PIE,  # A Pie Chart
            data_source=["sum__value"],
            title_source=["client__country"],
        ),
    ]


class SumValueComputationField(ComputationField):
    calculation_method = Sum
    calculation_field = "value"
    verbose_name = _("Sales Value")
    name = "my_value_sum"


class MonthlyProductSales(ReportView):
    report_title = _("Product Sales Monthly")
    report_description = _("Breaks product sales into one column per month using a Time Series, "
                           "also demonstrates defining a reusable ComputationField.")
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
    report_description = _("A crosstab matrix with products as rows and clients as columns. "
                           "The remainder column (crosstab_compute_remainder=True) "
                           "captures sales not tied to a said clients.")
    report_model = SalesTransaction
    date_field = "date"
    group_by = "product"
    crosstab_field = "client"

    crosstab_columns = [
        SumValueComputationField,
    ]

    crosstab_compute_remainder = True  # Add a extra column to the report, capturing the value all other clients

    columns = [
        "name",
        "sku",  # a field that exists on the `Product` model
        "__crosstab__",
        SumValueComputationField,
    ]


class ProductSalesPerCountryCrosstab(ReportView):
    report_title = _("Product Sales Per Country Crosstab")
    report_description = _("Demonstrate a crosstab/pivot on pre-set IDs (US, KW, EG, DE). "
                           "The remainder column collects sales from all other countries.")
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
    report_description = ("A list view (no aggregation) showing the ten most recent individual sale records."
                          "Uses ListReportView for row-level data instead of grouped summaries.")
    date_field = "date"
    filters = ["product", "client", "date"]
    columns = [
        "product__name",
        "client__name",
        "date",
        "quantity",
        "price",
        "value",
    ]
    default_order_by = "-date"
    limit_records = 10


class TotalProductSalesWithCustomForm(TotalProductSales):
    report_title = _("Total Product Sales with Custom Form")
    report_description = _("Demonstrates a custom Form (form_class) that adds a product-size filter "
                           "alongside the standard date range filters.")
    form_class = TotalSalesFilterForm
    columns = [
        "name",
        "size",
        ComputationField.create(Sum, "quantity", verbose_name="Total quantity sold", is_summable=False),
        ComputationField.create(Sum, "value", name="sum__value", verbose_name="Total Value sold $"),
    ]


class GroupByReport(ReportView):
    report_model = SalesTransaction
    report_title = _("Group By Report")
    report_description = _("Groups sales by product with no date_field set. "
                           "Shows that it's optional — omitting it gives all-time totals "
                           "regardless of the date pickers.")
    # date_field = "date"
    group_by = "product"

    columns = [
        "name",
        ComputationField.create(
            method=Sum,
            field="value",
            name="value__sum",
            verbose_name="Total sold $",
            is_summable=True,
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
    report_description = _(
        "Groups by a related model field using Django's double-underscore traversal (group_by='product__product_category'). No date filtering is applied.")
    group_by = "product__product_category"


class GroupByCustomQueryset(ReportView):
    report_model = SalesTransaction
    report_title = _("Group By Custom Queryset")
    report_description = _("Replaces automatic group-by with three crafted querysets (big, small, medium)."
                           "`format_row()` substitutes readable labels for the row's numeric index.")
    date_field = "date"

    group_by_custom_querysets = [
        SalesTransaction.objects.filter(product__size__in=["big", "extra_big"]),
        SalesTransaction.objects.filter(product__size__in=["small", "extra_small"]),
        SalesTransaction.objects.filter(product__size="medium"),
    ]
    group_by_custom_querysets_column_verbose_name = _("Product Size")

    columns = [
        "__index__",
        ComputationField.create(Sum, "value", verbose_name=_("Total Sold $"), name="value"),
    ]

    chart_settings = [
        Chart(
            title="Total sold By Size $",
            type=Chart.BAR,
            data_source=["value"],
            title_source=["__index__"],
        ),
    ]

    def format_row(self, row_obj):
        # Put the verbose names we need instead of the integer index
        index = row_obj["__index__"]
        if index == 0:
            row_obj["__index__"] = "Big"
        elif index == 1:
            row_obj["__index__"] = "Small"
        elif index == 2:
            row_obj["__index__"] = "Medium"
        return row_obj


class NoGroupByReport(ReportView):
    report_model = SalesTransaction
    report_title = _("No-Group-By Report")
    report_description = _("Produces a single summary row for the whole dataset with no grouping."
                           "Useful when you need a grand total over a date range rather than a breakdown.")
    date_field = "date"
    group_by = ""

    columns = [
        ComputationField.create(
            method=Sum,
            field="value",
            name="value__sum",
            verbose_name="Total sold $",
            is_summable=True,
        ),
    ]


class TimeSeriesReport(ReportView):
    report_title = _("Time Series Report")
    report_description = _(
        "Groups clients as rows and generates one column per month across the date range. The time_series_columns list defines what is computed for each period.")
    report_model = SalesTransaction
    group_by = "client"
    date_field = "date"

    # options are : "daily", "weekly", "bi-weekly", "monthly", "quarterly", "semiannually", "annually" and "custom"
    time_series_pattern = "monthly"

    # These columns will be calculated for each period in the time series.
    time_series_columns = [
        ComputationField.create(Sum, "value", verbose_name=_("Sales For ")),
    ]

    columns = [
        "name",
        # placeholder for the generated time series columns
        "__time_series__",
        # This is the same as the time_series_columns, but this one will be on the whole set
        ComputationField.create(Sum, "value", verbose_name=_("Total Sales")),
    ]

    chart_settings = [
        Chart(
            "Client Sales",
            Chart.BAR,
            data_source=["sum__value"],
            title_source=["name"],
        ),
        Chart(
            "Total Sales [Pie]",
            Chart.PIE,
            data_source=["sum__value"],
            title_source=["name"],
            plot_total=True,
        ),
        Chart(
            "Total Sales [Area chart]",
            Chart.AREA,
            data_source=["sum__value"],
            title_source=["name"],
        ),
    ]


class TimeSeriesReportWithSelector(TimeSeriesReport):
    report_title = _("Time Series Report With Pattern Selector")
    report_description = _("Adds a pattern selector (daily / weekly / bi-weekly / monthly) to the filter form."
                           "users can switch time granularity without changing report code.")
    time_series_selector = True
    time_series_selector_choices = (
        ("daily", _("Daily")),
        ("weekly", _("Weekly")),
        ("bi-weekly", _("Bi-Weekly")),
        ("monthly", _("Monthly")),
    )
    time_series_selector_default = "bi-weekly"

    # The label for the time series selector
    time_series_selector_label = _("Period Pattern")

    # Allow the user to select an empty time series, in which case no time series will be applied to the report.
    time_series_selector_allow_empty = True


def get_current_year():
    return datetime.datetime.now().year


class TimeSeriesReportWithCustomDates(TimeSeriesReport):
    report_title = _("Time Series Report With Custom Dates")
    report_description = _("Demonstrates a 'custom' time_series_pattern"
                           "here: first 10 days of Jan, Feb and Mar. "
                           "Useful for non-standard or irregular periods.")
    time_series_pattern = "custom"
    time_series_custom_dates = (
        (datetime.datetime(get_current_year(), 1, 1), datetime.datetime(get_current_year(), 1, 10)),
        (datetime.datetime(get_current_year(), 2, 1), datetime.datetime(get_current_year(), 2, 10)),
        (datetime.datetime(get_current_year(), 3, 1), datetime.datetime(get_current_year(), 3, 10)),
    )


class TimeSeriesReportWithCustomGroupByQueryset(ReportView):
    report_title = _("Time Series Report")
    report_description = _("Combines custom querysets (US clients vs. RS+DE clients) with time series. "
                           "Each queryset becomes a named row in the resulting matrix.")
    report_model = SalesTransaction
    date_field = "date"
    group_by_custom_querysets = (
        SalesTransaction.objects.filter(client__country="US"),
        SalesTransaction.objects.filter(client__country__in=["RS", "DE"]),
    )

    time_series_pattern = "monthly"
    time_series_columns = [
        ComputationField.create(Sum, "value", verbose_name=_("Sales For ")),
    ]

    columns = [
        "__index__",
        # placeholder for the generated time series columns
        "__time_series__",
        # This is the same as the time_series_columns, but this one will be on the whole set
        ComputationField.create(Sum, "value", verbose_name=_("Total Sales")),
    ]

    chart_settings = [
        Chart(
            "Client Sales",
            Chart.BAR,
            data_source=["sum__value"],
            title_source=["__index__"],
        ),
        Chart(
            "Total Sales [Pie]",
            Chart.PIE,
            data_source=["sum__value"],
            title_source=["__index__"],
            plot_total=True,
        ),
        Chart(
            "Total Sales [Area chart]",
            Chart.AREA,
            data_source=["sum__value"],
            title_source=["name"],
        ),
    ]


class SumOfFieldValue(ComputationField):
    # A custom computation Field with custom verbose names
    # Similar to `ComputationField.create(Sum, "value", verbose_name=_("Total Sales"))`

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
    report_description = _(
        "Extends custom date ranges with get_time_series_field_verbose_name() "
        "to give each period column a human-readable heading like 'First 10 days sales 1-2024'.")

    time_series_columns = [
        SumOfFieldValue,  # Use our newly created ComputationField with the custom time series verbose name
    ]

    chart_settings = [
        Chart(
            "Client Sales",
            Chart.BAR,
            data_source=["sum_of_value"],  # Note:  This is the name of our `TotalSalesField` computation field
            title_source=["name"],
        ),
        Chart(
            "Total Sales [Pie]",
            Chart.PIE,
            data_source=["sum_of_value"],
            title_source=["name"],
            plot_total=True,
        ),
    ]


class TimeSeriesWithoutGroupBy(ReportView):
    report_title = _("Time Series without a group by")
    report_description = _("A time series with no group_by: "
                           "the entire dataset becomes one summary row split into pattern (here monthly) columns.")
    report_model = SalesTransaction
    time_series_pattern = "monthly"
    date_field = "date"
    time_series_columns = [
        ComputationField.create(Sum, "value", verbose_name=_("Sales For ")),
    ]

    columns = [
        "__time_series__",
        ComputationField.create(Sum, "value", verbose_name=_("Total Sales")),
    ]

    chart_settings = [
        Chart(
            "Total Sales [Bar]",
            Chart.BAR,
            data_source=["sum__value"],
            title_source=["name"],
        ),
        Chart(
            "Total Sales [Pie]",
            Chart.PIE,
            data_source=["sum__value"],
            title_source=["name"],
        ),
    ]


class CrosstabReport(ReportView):
    report_title = _("Cross tab Report")
    report_description = _("A basic crosstab: clients as rows, products as columns. "
                           "Each cell holds the sales value for that client–product combination, "
                           "with a total column on the right.")
    report_model = SalesTransaction
    group_by = "client"
    # date_field = "date"

    columns = [
        "name",
        # You can customize where the crosstab columns are displayed in relation to the other columns
        "__crosstab__",

        # This is the same as the calculation in the crosstab,
        # but this one will be on the whole set. IE total value.
        ComputationField.create(Sum, "value", verbose_name=_("Total Value")),
    ]

    crosstab_field = "product"
    crosstab_columns = [
        ComputationField.create(Sum, "value", verbose_name=_("Value")),
    ]


class CrosstabWithTraversingField(CrosstabReport):
    report_title = _("Cross tab Report With Traversing Field")
    report_description = _("Uses a traversed field (product__size) as the crosstab axis.")
    crosstab_field = "product__size"


class CrosstabWithIds(CrosstabReport):
    report_title = _("Cross tab Report With Pre-set Ids")
    report_description = _("Pre-sets the crosstab column IDs to the first and last product via get_crosstab_ids(). "
                           "Useful when you want a known set of columns resolved at request time.")

    def get_crosstab_ids(self):
        return [Product.objects.first().pk, Product.objects.last().pk]


class CrosstabWithIdsCustomFilter(CrosstabReport):
    report_title = _("Crosstab with Custom Filters")
    report_description = _("Replaces per-ID filters with two arbitrary Q-object filters (big vs 'not' big)."
                           "Demonstrates flexibility in breaking down crosstab columns ")
    crosstab_ids_custom_filters = [
        (~Q(product__size__in=["extra_big", "big"]), dict()),
        (None, dict(product__size__in=["extra_big", "big"])),
    ]
    # Note:
    # if crosstab_ids_custom_filters is set, these settings has NO EFFECT
    # crosstab_field = "client"
    # crosstab_ids = [1, 2]
    # crosstab_compute_remainder = True


class CustomCrossTabTotalField(ComputationField):
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
    report_description = _("Demonstrates how to customize the verbose name"
                           "Here, in each column header, we show 'Sales for Widget A' instead of the raw PK .")
    crosstab_columns = [CustomCrossTabTotalField]


class CustomCrossTabTotalPerSize(CustomCrossTabTotalField):
    @classmethod
    def get_crosstab_field_verbose_name(cls, model, id):
        if id == 0:
            return f"{cls.verbose_name} Big and Extra Big"
        return f"{cls.verbose_name} all other sizes"

    @classmethod
    def get_time_series_field_verbose_name(cls, date_period, index, dates, pattern):
        return super().get_time_series_field_verbose_name(date_period, index, dates, pattern)


class CrossTabReportWithCustomVerboseNameCustomFilter(CrosstabWithIdsCustomFilter):
    report_title = _("Crosstab customized verbose name with custom filter")
    report_description = _("Combines Q-object filters with custom verbose names, "
                           "labelling columns 'Big and Extra Big' and 'All other sizes'.")

    crosstab_columns = [CustomCrossTabTotalPerSize]


class CrossTabWithTimeSeries(CrossTabReportWithCustomVerboseNameCustomFilter):
    report_title = _("Crosstab with time series")
    report_description = _("Layers a monthly time series on top of the crosstab, producing columns for each filter × period combination. "
                           "Demonstrates the most complex report configuration available.")
    date_field = "date"
    time_series_pattern = "monthly"
    crosstab_columns = [CustomCrossTabTotalPerSize]
    columns = ["name", "__time_series__"]


class ChartJSExample(TimeSeriesReport):
    report_title = _("ChartJS Examples ")
    report_description = _("The same time-series data visualised with Chart.js. "
                           "Switching chart engines requires only setting"
                           "chart_engine='chartsjs' on the report class.")

    chart_engine = "chartsjs"
    chart_settings = [
        Chart(
            "Client Sales",
            Chart.BAR,
            data_source=["sum__value"],
            title_source=["name"],
        ),
        Chart(
            "Total Sales [Pie]",
            Chart.PIE,
            data_source=["sum__value"],
            title_source=["name"],
            plot_total=True,
        ),
        Chart(
            "Total Sales [Line total]",
            Chart.LINE,
            data_source=["sum__value"],
            title_source=["name"],
            plot_total=True,
        ),
    ]


class HighChartExample(TimeSeriesReport):
    chart_engine = "highcharts"
    report_title = _("Highcharts Examples ")
    report_description = _("Renders the same time-series data with all supported Highcharts chart types."
                           ": column, bar, line, area, pie — including stacked and plot-total variants.")

    chart_settings = [
        Chart("Client Sales [Column]", Chart.COLUMN, data_source=["sum__value"], title_source=["name"]),
        Chart(
            "Stacking Client Sales [Column]",
            Chart.COLUMN,
            data_source=["sum__value"],
            title_source=["name"],
            stacking=True,
        ),
        Chart(
            "Total Client Sales[Column]",
            Chart.COLUMN,
            data_source=["sum__value"],
            title_source=["name"],
            plot_total=True,
        ),
        Chart(
            "Stacking Total Client Sales [Column]",
            Chart.COLUMN,
            data_source=["sum__value"],
            title_source=["name"],
            plot_total=True,
            stacking=True,
        ),
        Chart(
            "Client Sales [Bar]",
            Chart.BAR,
            data_source=["sum__value"],
            title_source=["name"],
        ),
        Chart(
            "Total Client Sales [Bar]", Chart.BAR, data_source=["sum__value"], title_source=["name"], plot_total=True
        ),
        Chart(
            "Client Sales [Line]",
            Chart.LINE,
            data_source=["sum__value"],
            title_source=["name"],
            # plot_total=True,
        ),
        Chart(
            "Total Client Sales [Line]",
            Chart.LINE,
            data_source=["sum__value"],
            title_source=["name"],
            plot_total=True,
        ),
        Chart(
            "Total Sales [Pie]",
            Chart.PIE,
            data_source=["sum__value"],
            title_source=["name"],
            plot_total=True,
        ),
        Chart(
            "Client Sales [Area]",
            Chart.AREA,
            data_source=["sum__value"],
            title_source=["name"],
        ),
    ]


class ProductSalesApexChart(ReportView):
    report_title = _("Product Sales Apex Charts")
    report_description = _(
        "Demonstrates the ApexCharts engine with a custom template and "
        "a custom JS entry point (displayChartCustomEntryPoint) for fully bespoke chart initialisation.")
    report_model = SalesTransaction
    date_field = "date"
    group_by = "product"
    chart_engine = "apexcharts"
    template_name = "demo/apex_report.html"

    columns = [
        "name",
        ComputationField.create(
            method=Sum,
            field="value",
            name="value__sum",
            verbose_name="Total sold $",
            is_summable=True,
        ),
    ]

    chart_settings = [
        Chart(
            "Total sold $",
            type="pie",
            data_source=["value__sum"],
            title_source=["name"],
        ),
        Chart(
            "Total sold $",
            type="bar",
            data_source=["value__sum"],
            title_source=["name"],
        ),
        Chart(
            "A custom Entry Point $",
            type="bar",
            data_source=["value__sum"],
            title_source=["name"],
            entryPoint="displayChartCustomEntryPoint", # a custom entry point to control the chart
        ),
    ]


class CustomExportReport(GroupByReport):
    report_title = _("Custom Export Report")
    report_description = _("Demonstrates adding custom action (here export_pdf) action alongside the built-ins"
                           "Also shows how to customize buttons label and css class")
    export_actions = ["export_pdf"]

    def export_pdf(self, report_data):
        return HttpResponse(f"Dummy PDF Exported \n {report_data}")

    export_pdf.title = _("Export PDF") # The label for the export action button
    export_pdf.css_class = "btn btn-secondary" # the button classes

    def export_csv(self, report_data):
        return super().export_csv(report_data)

    export_csv.title = _("My Custom CSV export Title")
    export_csv.css_class = "btn btn-primary"


class ReportWithFormInitial(ReportView):
    report_title = _("Report With Form Initial")
    report_description = _("Pre-populates the client filter with the first and last client using get_initial(). "
                           "Shows how to set dynamic default filter values based on live data.")
    report_model = SalesTransaction
    date_field = "date"
    group_by = "product"

    columns = [
        "name",
        ComputationField.create(
            method=Sum,
            field="value",
            name="value__sum",
            verbose_name="Total sold $",
            is_summable=True,
        ),
    ]

    def get_initial(self):
        from .models import Client
        initial = super().get_initial()
        initial["client_id"] = [Client.objects.first().pk, Client.objects.last().pk]
        return initial


class PreComputedMonthlySales(ReportView):
    report_title = _("Crosstab Precomputed: Monthly Sales")
    report_description = _("Uses crosstab_precomputed=True on a model whose rows are already aggregated. "
                           "Columns are the distinct month values discovered at query time — no aggregation needed.")
    report_model = MonthlySalesSummary
    date_field = "month"
    group_by = "product"
    crosstab_field = "month"
    crosstab_precomputed = True # signals that data is already aggregated
    crosstab_columns = ["total_sales", "total_quantity"] # These fields are already computed/aggregated in database
    columns = ["name", "__crosstab__"]

    chart_settings = [
        Chart(
            _("Monthly Sales by Product"),
            Chart.BAR,
            data_source=["total_sales"],
            title_source=["name"],
        ),
        Chart(
            _("Monthly Quantity by Product"),
            Chart.LINE,
            data_source=["total_quantity"],
            title_source=["name"],
        ),
    ]


class DynamicModelSalesByCountry(ReportView):
    report_title = _("Raw SQL Table / Dynamic Model Sales by Country")
    report_description = _("Here we're acting on raw SQL table (table_name='regional_sales_summary'). "
                           "No Django model is involved — the schema is introspected at runtime."
                           "Demonstrating it with Pre-computed crosstab, but we can use it with any type of reports")
    table_name = "regional_sales_summary"
    group_by = "product_name"
    crosstab_field = "country"
    crosstab_columns = ["total_sales", "total_quantity"]
    crosstab_precomputed = True
    columns = ["product_name", "__crosstab__"]

    chart_settings = [
        Chart(
            _("Sales by Country"),
            Chart.BAR,
            data_source=["total_sales"],
            title_source=["product_name"],
        ),
        Chart(
            _("Sales by Country [Pie]"),
            Chart.PIE,
            data_source=["total_sales"],
            title_source=["product_name"],
        ),
    ]

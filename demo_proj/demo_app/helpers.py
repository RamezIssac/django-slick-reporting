from django.urls import path

from . import reports

TUTORIAL = [
    ("product-sales", reports.ProductSales),
    ("total-product-sales", reports.TotalProductSales),
    ("total-product-sales-by-country", reports.TotalProductSalesByCountry),
    ("monthly-product-sales", reports.MonthlyProductSales),
    ("product-sales-per-client-crosstab", reports.ProductSalesPerClientCrosstab),
    ("product-sales-per-country-crosstab", reports.ProductSalesPerCountryCrosstab),
    ("last-10-sales", reports.LastTenSales),
    ("total-product-sales-with-custom-form", reports.TotalProductSalesWithCustomForm),
]

GROUP_BY = [
    ("group-by-report", reports.GroupByReport),
    ("group-by-traversing-field", reports.GroupByTraversingFieldReport),
    ("group-by-custom-queryset", reports.GroupByCustomQueryset),
    ("no-group-by", reports.NoGroupByReport),
]

TIME_SERIES = [
    ("time-series-report", reports.TimeSeriesReport),
    ("time-series-with-selector", reports.TimeSeriesReportWithSelector),
    ("time-series-with-custom-dates", reports.TimeSeriesReportWithCustomDates),
    ("time-series-with-custom-dates-and-title", reports.TimeSeriesReportWithCustomDatesAndCustomTitle),
    ("time-series-without-group-by", reports.TimeSeriesWithoutGroupBy),
    ("time-series-with-group-by-custom-queryset", reports.TimeSeriesReportWithCustomGroupByQueryset),
]

CROSSTAB = [
    ("crosstab-report", reports.CrosstabReport),
    ("crosstab-report-with-ids", reports.CrosstabWithIds),
    ("crosstab-report-traversing-field", reports.CrosstabWithTraversingField),
    ("crosstab-report-custom-filter", reports.CrosstabWithIdsCustomFilter),
    ("crosstab-report-custom-verbose-name", reports.CrossTabReportWithCustomVerboseName),
    ("crosstab-report-custom-verbose-name-2", reports.CrossTabReportWithCustomVerboseNameCustomFilter),
    ("crosstab-report-with-time-series", reports.CrossTabWithTimeSeries),
]
OTHER = [
    ("chartjs-examples", reports.ChartJSExample),
]


def get_urls_patterns():
    urls = []
    for name, report in TUTORIAL + GROUP_BY + TIME_SERIES + CROSSTAB + OTHER:
        urls.append(path(f"{name}/", report.as_view(), name=name))
    return urls

"""
URL configuration for demo_proj project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path

from demo_app.reports import ProductSales, TotalProductSales, TotalProductSalesByCountry, MonthlyProductSales, \
    ProductSalesPerCountryCrosstab, ProductSalesPerClientCrosstab, LastTenSales, TotalProductSalesWithCustomForm, \
    GroupByReport, GroupByTraversingFieldReport, GroupByCustomQueryset, TimeSeriesReport

from demo_app import reports
from demo_app import views

urlpatterns = [

    path("", views.HomeView.as_view(), name="home"),


    # tutorial
    path("product-sales/", ProductSales.as_view(), name="product-sales"),
    path("total-product-sales/", TotalProductSales.as_view(), name="total-product-sales"),
    path("total-product-sales-by-country/", TotalProductSalesByCountry.as_view(),
         name="total-product-sales-by-country"),
    path("monthly-product-sales/", MonthlyProductSales.as_view(), name="monthly-product-sales"),
    path("product-sales-per-client-crosstab/", ProductSalesPerClientCrosstab.as_view(),
         name="product-sales-per-client-crosstab"),
    path("product-sales-per-country-crosstab/", ProductSalesPerCountryCrosstab.as_view(),
         name="product-sales-per-country-crosstab"),
    path("last-10-sales/", LastTenSales.as_view(), name="last-10-sales"),
    path("total-product-sales-with-custom-form/", TotalProductSalesWithCustomForm.as_view(),
         name="total-product-sales-with-custom-form"),

    # Group by
    path("group-by-report/", GroupByReport.as_view(), name="group-by-report"),
    path("group-by-traversing-field/", GroupByTraversingFieldReport.as_view(), name="group-by-traversing-field"),
    path("group-by-custom-queryset/", GroupByCustomQueryset.as_view(), name="group-by-custom-queryset"),
    path("no-group-by/", reports.NoGroupByReport.as_view(), name="no-group-by"),

    # Time Series
    path("time-series-report/", TimeSeriesReport.as_view(), name="time-series-report"),
    path("time-series-with-selector/", reports.TimeSeriesReportWithSelector.as_view(),
         name="time-series-with-selector"),
    path("time-series-with-custom-dates/", reports.TimeSeriesReportWithCustomDates.as_view(),
         name="time-series-with-custom-dates"),
    path("time-series-with-custom-dates-and-title/", reports.TimeSeriesReportWithCustomDatesAndCustomTitle.as_view(),
         name="time-series-with-custom-dates-and-title"),
    path("time-series-without-group-by/", reports.TimeSeriesWithoutGroupBy.as_view(),
         name="time-series-without-group-by"),

    # Crosstab
    path("crosstab-report/", reports.CrosstabReport.as_view(), name="crosstab-report"),
    path("crosstab-report-with-ids/", reports.CrosstabWithIds.as_view(), name="crosstab-report0with-ids"),
    path("crosstab-report-traversing-field/", reports.CrosstabWithTraversingField.as_view(),
         name="crosstab-report-with-traversing_field"),
    path("crosstab-report-custom-filter/", reports.CrosstabWithIdsCustomFilter.as_view(),
         name="crosstab-report-with-custom-filter"),
    path("crosstab-report-custom-verbose-name/", reports.CrossTabReportWithCustomVerboseName.as_view(),
         name="crosstab-report-custom-verbose-name"),
    path("crosstab-report-custom-verbose-name-2/", reports.CrossTabReportWithCustomVerboseNameCustomFilter.as_view(),
         name="crosstab-report-custom-verbose-name-2"),
    path("crosstab-report-with-time-series/", reports.CrossTabWithTimeSeries.as_view(),
         name="crosstab-report-with-time-series"),



    path("admin/", admin.site.urls),
]

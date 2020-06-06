from slick_reporting.views import SampleReportView
from .models import SimpleSales


class MonthlyProductSales(SampleReportView):
    report_model = SimpleSales
    date_field = 'doc_date'
    group_by = 'client'
    columns = ['slug', 'name']
    time_series_pattern = 'monthly'
    time_series_columns = ['__total__', '__balance__']


class ProductClientSalesMatrix(SampleReportView):
    report_title = 'awesome report title'
    report_model = SimpleSales
    date_field = 'doc_date'

    group_by = 'product'
    columns = ['slug', 'name']

    crosstab_model = 'client'
    crosstab_columns = ['__total__']

    chart_settings = [
        {
            'type': 'pie',
            'date_source': '__total__',
            'title_source': '__total__',
        }
    ]

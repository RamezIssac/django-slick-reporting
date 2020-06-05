from slick_reporting.views import SampleReportView
from .models import SimpleSales


class MonthlyProductSales(SampleReportView):
    report_model = SimpleSales
    date_field = 'doc_date'
    group_by = 'client'
    columns = ['slug', 'name']
    time_series_pattern = 'monthly'
    time_series_columns = ['__total__', '__balance__']

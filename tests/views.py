from slick_reporting.views import SampleReportView
from .models import OrderLine


class MonthlyProductSales(SampleReportView):
    report_model = OrderLine
    date_field = 'date_placed'  # or 'order__date_placed'
    group_by = 'product'
    columns = ['name', 'sku']
    time_series_pattern = 'monthly'
    time_series_columns = ['__total_quantity__']

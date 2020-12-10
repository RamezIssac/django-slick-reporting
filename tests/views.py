from slick_reporting.views import SlickReportView
from slick_reporting.fields import SlickReportField
from django.db.models import Sum
from .models import SimpleSales
from django.utils.translation import ugettext_lazy as _


class MonthlyProductSales(SlickReportView):
    report_model = SimpleSales
    date_field = 'doc_date'
    group_by = 'client'
    columns = ['slug', 'name']
    time_series_pattern = 'monthly'
    time_series_columns = ['__total__', '__balance__']


class ProductClientSalesMatrix(SlickReportView):
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


class CrossTabColumnOnFly(SlickReportView):
    report_title = 'awesome report title'
    report_model = SimpleSales
    date_field = 'doc_date'

    group_by = 'product'
    columns = ['slug', 'name']

    crosstab_model = 'client'
    crosstab_columns = [SlickReportField.create(Sum, 'value', name='value__sum', verbose_name=_('Sales'))]

    chart_settings = [
        {
            'type': 'pie',
            'date_source': 'value__sum',
            'title_source': 'name',
        }
    ]

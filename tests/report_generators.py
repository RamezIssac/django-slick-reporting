import datetime

from django.db.models import Sum
from django.utils.translation import gettext_lazy as _

from slick_reporting.fields import SlickReportField, PercentageToBalance
from slick_reporting.generator import ReportGenerator
from .models import Client, SimpleSales, Product, SalesWithFlag
from .models import OrderLine, GeneralLedger


class GenericGenerator(ReportGenerator):
    report_model = OrderLine
    date_field = 'order__date_placed'

    # here is the meat and potatos of the report,
    # we group the sales per client , we display columns slug and title (of the `base_model` defied above
    # and we add the magic field `__balance__` we compute the client balance.
    group_by = 'client'
    columns = ['slug', 'name']


class GeneratorWithAttrAsColumn(GenericGenerator):
    group_by = 'client'

    columns = ['get_data', 'slug', 'name']

    def get_data(self, obj):
        return ''

    get_data.verbose_name = 'get_data_verbose_name'


class CrosstabOnClient(GenericGenerator):
    group_by = 'product'
    columns = ['name', '__total_quantity__']
    crosstab_model = 'client'
    # crosstab_columns = ['__total_quantity__']
    crosstab_columns = [SlickReportField.create(Sum, 'quantity', name='value__sum', verbose_name=_('Sales'))]


#

class ClientTotalBalance(ReportGenerator):
    report_model = SimpleSales
    date_field = 'doc_date'
    group_by = 'client'
    columns = ['slug', 'name', '__balance__', '__total__']


class GroupByCharField(ReportGenerator):
    report_model = SalesWithFlag
    date_field = 'doc_date'
    group_by = 'flag'
    columns = ['flag', '__balance__', SlickReportField.create(Sum, 'quantity')]


class GroupByCharFieldPlusTimeSeries(ReportGenerator):
    report_model = SalesWithFlag
    date_field = 'doc_date'
    group_by = 'flag'
    columns = ['flag', SlickReportField.create(Sum, 'quantity')]

    time_series_pattern = 'monthly'
    time_series_columns = [SlickReportField.create(Sum, 'quantity')]


class ClientTotalBalancesOrdered(ClientTotalBalance):
    report_slug = None
    default_order_by = '__balance__'


class ClientTotalBalancesOrderedDESC(ClientTotalBalance):
    report_slug = None
    default_order_by = '-__balance__'


class ProductTotalSales(ReportGenerator):
    report_model = SimpleSales
    date_field = 'doc_date'
    group_by = 'product'
    columns = ['slug', 'name', '__balance__', '__balance_quantity__']


class ProductTotalSalesWithPercentage(ReportGenerator):
    report_model = SimpleSales
    date_field = 'doc_date'
    group_by = 'client'
    columns = ['slug', 'name',
               '__balance__',
               '__balance_quantity__', PercentageToBalance]


class ClientList(ReportGenerator):
    report_title = _('Our Clients')

    # report_slug = 'client_list'
    base_model = Client
    report_model = SimpleSales

    group_by = 'client'
    columns = ['slug', 'name']


class ProductClientSales(ReportGenerator):
    report_model = SimpleSales

    report_slug = 'client_sales_of_products'
    report_title = _('Client net sales for each product')
    must_exist_filter = 'client_id'
    header_report = ClientList

    group_by = 'product'
    columns = ['slug', 'name', '__balance_quantity__', '__balance__', 'get_data']

    def get_data(self, obj):
        return ''


class ProductSalesMonthlySeries(ReportGenerator):
    base_model = Product
    report_model = SimpleSales
    report_title = _('Product Sales Monthly')

    group_by = 'product'
    columns = ['slug', 'name']
    time_series_pattern = 'monthly',
    time_series_columns = ['__balance_quantity__', '__balance__']

    chart_settings = [
        {
            'id': 'movement_column',
            'name': _('comparison - column'),
            'settings': {
                'chart_type': 'column',
                'name': _('{product} Avg. purchase price '),
                'sub_title': _('{date_verbose}'),
                'y_sources': ['__balance__'],
                'series_names': [_('Avg. purchase price')],
            }
        },
        {
            'id': 'movement_line',
            'name': _('comparison - line'),
            'settings': {
                'chart_type': 'line',
                'name': _('{product} Avg. purchase price '),
                'sub_title': _('{date_verbose}'),
                'y_sources': ['__balance__'],
                'series_names': [_('Avg. purchase price')],
            }
        },
    ]


class TimeSeriesCustomDates(ReportGenerator):
    report_model = SimpleSales
    report_title = _('Product Sales Monthly')
    date_field = 'doc_date'
    # group_by = 'product'
    # columns = ['slug', 'name']
    time_series_pattern = 'custom'
    time_series_columns = ['__total__']
    time_series_custom_dates = [
        (datetime.date(2020, 1, 1), datetime.date(2020, 1, 17)),
        (datetime.date(2020, 4, 17), datetime.date(2020, 5, 1)),
        (datetime.date(2020, 8, 8), datetime.date(2020, 9, 9)),
    ]


class TimeSeriesWithOutGroupBy(ReportGenerator):
    report_model = SimpleSales
    report_title = _('Product Sales Monthly')
    date_field = 'doc_date'
    # group_by = 'product'
    # columns = ['slug', 'name']
    time_series_pattern = 'monthly'
    time_series_columns = ['__total__']


class ClientReportMixin:
    base_model = Client
    report_model = SimpleSales


class ClientSalesMonthlySeries(ReportGenerator):
    report_model = SimpleSales
    date_field = 'doc_date'

    group_by = 'client'
    columns = ['slug', 'name']
    time_series_pattern = 'monthly'
    time_series_columns = ['__debit__', '__credit__', '__balance__', '__total__']


#


class ClientDetailedStatement(ReportGenerator):
    report_model = SimpleSales
    date_field = 'doc_date'
    group_by = None
    columns = ['slug', 'doc_date', 'product__name', 'quantity', 'price', 'value']


class ClientDetailedStatement2(ReportGenerator):
    report_title = _('client statement')
    base_model = Client
    report_model = SimpleSales

    header_report = ClientList
    must_exist_filter = 'client_id'

    form_settings = {
        'group_by': '',
        'group_columns': ['slug', 'doc_date', 'doc_type', 'product__title', 'quantity', 'price', 'value'],
    }
    group_by = None
    columns = ['slug', 'doc_date', 'doc_type', 'product__title', 'quantity', 'price', 'value']


class ProductClientSalesMatrix(ReportGenerator):
    report_model = SimpleSales
    date_field = 'doc_date'

    group_by = 'product'
    columns = ['slug', 'name']

    crosstab_model = 'client'
    crosstab_columns = ['__total__']


class ProductClientSalesMatrix2(ReportGenerator):
    report_model = SimpleSales
    date_field = 'doc_date'

    group_by = 'product'
    columns = ['slug', 'name']

    crosstab_model = 'client'
    crosstab_columns = [SlickReportField.create(Sum, 'value', name='value__sum', verbose_name=_('Sales'))]


class GeneratorClassWithAttrsAs(ReportGenerator):
    columns = ['get_icon', 'slug', 'name']


class ClientTotalBalancesWithShowEmptyFalse(ClientTotalBalance):
    report_slug = None
    default_order_by = '-__balance__'
    show_empty_records = False


class TotalDebit(SlickReportField):
    base_kwargs_filters = {'account_name': 'debit'}


class TotalCredit(SlickReportField):
    base_kwargs_filters = {'account_name': 'credit'}


class NetValue(SlickReportField):
    requires = [TotalDebit, TotalCredit]

    def final_calculation(self, debit, credit, dep_dict):
        debit = dep_dict.get('TotalDebit')
        credit = dep_dict.get('TotalCredit')
        return debit - credit



class TRowsGenerator(ReportGenerator):
    custom_rows = [TotalDebit, TotalCredit]
    report_model = GeneralLedger
    date_field = 'doc_date'
    # t_row_columns = ['__trow__name__', '__trow_verbose_name__', '__trow_value__']


class TRowsGeneratorTimeSeries(ReportGenerator):
    custom_rows = [TotalDebit, TotalCredit,
                   # NetValue
                   ]
    report_model = GeneralLedger
    date_field = 'doc_date'
    time_series_pattern = 'monthly'

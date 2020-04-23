from reporting.generator import ReportGenerator
from .models import Order, OrderLine


class GenericGenerator(ReportGenerator):
    report_model = OrderLine
    date_field = 'order__date_placed'

    # here is the meat and potatos of the report,
    # we group the sales per client , we display columns slug and title (of the `base_model` defied above
    # and we add the magic field `__balance__` we compute the client balance.
    group_by = 'client'
    columns = ['slug', 'name', '__balance__']


class GeneratorWithAttrAsColumn(GenericGenerator):
    group_by = 'client'

    columns = ['get_data', 'slug', 'name']

    def get_data(self, obj):
        return ''

    get_data.verbose_name = 'get_data_verbose_name'


class CrosstabOnClient(GenericGenerator):
    group_by = 'product'
    columns = ['name', '__total_quan__']
    crosstab_model = 'client'
    crosstab_columns = ['__total_quan__']


#
from django.utils.translation import ugettext_lazy as _
from reporting.form_factory import report_form_factory

from reporting.generator import ReportGenerator
from .models import Client, SimpleSales, Product


class ClientTotalBalance(ReportGenerator):
    report_title = _('Clients Balances')

    # that's the report url endpoint
    # So this report ajax request will be sent reports/<namespace>/<report_slug>
    # this should be unique to the namespace
    report_slug = 'balances'

    # here we define basic information for the report
    base_model = Client

    # Where is the data to compute
    report_model = SimpleSales
    group_by = 'client'
    columns = ['slug', 'name', '__balance__', '__total__']


class ClientTotalBalancesOrdered(ClientTotalBalance):
    report_slug = None
    default_order_by = '__balance__'


class ClientTotalBalancesOrderedDESC(ClientTotalBalance):
    report_slug = None
    default_order_by = '-__balance__'


class ProductTotalSales(ReportGenerator):
    report_title = _('Product Sales')

    # identifier of the report
    # This report ajax request will be sent reports/<namespace>/<report_slug>
    # `report_slug` should be unique to the namespace
    report_slug = 'total_sales'

    # here we define basic information for the report
    base_model = Product

    # Where is the data to compute
    report_model = SimpleSales

    group_by = 'product'
    columns = ['slug', 'name', '__balance__', '__balance_quan__']


class ClientList(ReportGenerator):
    report_title = _('Our Clients')

    # report_slug = 'client_list'
    base_model = Client
    report_model = SimpleSales

    group_by = 'client'
    columns = ['slug', 'name']


class ProductClientSales(ReportGenerator):
    base_model = Client
    report_model = SimpleSales

    report_slug = 'client_sales_of_products'
    report_title = _('Client net sales for each product')
    must_exist_filter = 'client_id'
    header_report = ClientList

    group_by = 'product'
    columns = ['slug', 'name', '__balance_quan__', '__balance__']


class ProductSalesMonthlySeries(ReportGenerator):
    base_model = Product
    report_model = SimpleSales
    report_title = _('Product Sales Monthly')

    form_settings = {
        'group_by': 'product',
        'group_columns': ['slug', 'name'],

        'time_series_pattern': 'monthly',
        'time_series_columns': ['__balance_quan__', '__balance__'],
    }

    group_by = 'product'
    columns = ['slug', 'name']
    time_series_pattern = 'monthly',
    time_series_columns = ['__balance_quan__', '__balance__']

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
    base_model = Product
    report_model = SimpleSales
    date_field = 'doc_date'
    report_title = _('Matrix')

    swap_sign = True

    group_by = 'client'
    columns = ['slug', 'name']

    crosstab_model = 'client'
    crosstab_columns = ['__total__']


class GeneratorClassWithAttrsAs(ReportGenerator):
    columns = ['get_icon', 'slug', 'name']


class ClientTotalBalancesWithShowEmptyFalse(ClientTotalBalance):
    report_slug = None
    default_order_by = '-__balance__'
    show_empty_records = False

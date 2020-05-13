import datetime
from unittest import skip
from urllib.parse import urljoin

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from django.utils.timezone import now

from slick_reporting.generator import ReportGenerator
from slick_reporting.fields import BaseReportField
from tests.report_generators import ClientTotalBalance
from .models import Client, Product, SimpleSales, OrderLine
from slick_reporting.registry import field_registry

User = get_user_model()
SUPER_LOGIN = dict(username='superlogin', password='password')
year = now().year

from . import report_generators


class ReportRegistryTest(SimpleTestCase):
    pass


class BaseTestData:
    databases = '__all__'

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        User.objects.create_superuser('super', None, 'secret')

        user = User.objects.create(is_superuser=True, is_staff=True, **SUPER_LOGIN)
        limited_user = User.objects.create_user(is_superuser=False, is_staff=True, username='limited',
                                                password='password')
        cls.user = user
        cls.limited_user = limited_user
        cls.client1 = Client.objects.create(name='Client 1')
        cls.client2 = Client.objects.create(name='Client 2')
        cls.client3 = Client.objects.create(name='Client 3')
        cls.clientIdle = Client.objects.create(name='Client Idle')

        cls.product1 = Product.objects.create(name='Product 1')
        cls.product2 = Product.objects.create(name='Product 2')
        cls.product3 = Product.objects.create(name='Product 3')

        SimpleSales.objects.create(
            doc_date=datetime.datetime(year, 1, 2), client=cls.client1,
            product=cls.product1, quantity=10, price=10)
        SimpleSales.objects.create(
            doc_date=datetime.datetime(year, 2, 2), client=cls.client1,
            product=cls.product1, quantity=10, price=10)

        SimpleSales.objects.create(
            doc_date=datetime.datetime(year, 3, 2), client=cls.client1,
            product=cls.product1, quantity=10, price=10)

        # client 2
        SimpleSales.objects.create(
            doc_date=datetime.datetime(year, 1, 2), client=cls.client2,
            product=cls.product1, quantity=20, price=10)
        SimpleSales.objects.create(
            doc_date=datetime.datetime(year, 2, 2), client=cls.client2,
            product=cls.product1, quantity=20, price=10)

        SimpleSales.objects.create(
            doc_date=datetime.datetime(year, 3, 2), client=cls.client2,
            product=cls.product1, quantity=20, price=10)

        # client 3
        SimpleSales.objects.create(
            doc_date=datetime.datetime(year, 1, 2), client=cls.client3,
            product=cls.product1, quantity=30, price=10)
        SimpleSales.objects.create(
            doc_date=datetime.datetime(year, 2, 2), client=cls.client3,
            product=cls.product1, quantity=30, price=10)

        SimpleSales.objects.create(
            doc_date=datetime.datetime(year, 3, 2), client=cls.client3,
            product=cls.product1, quantity=30, price=10)


# @override_settings(ROOT_URLCONF='reporting_tests.urls', RA_CACHE_REPORTS=False, USE_TZ=False)
class ReportTest(BaseTestData, TestCase):

    def test_client_balance(self):
        report = report_generators.ClientTotalBalance()
        data = report.get_report_data()

        self.assertEqual(data[0].get('__balance__'), 300, data[0])

    def test_product_total_sales(self):
        report = report_generators.ProductTotalSales()
        data = report.get_report_data()
        self.assertEqual(data[0]['__balance__'], 1800)

    def test_client_client_sales_monthly(self):
        report = report_generators.ClientSalesMonthlySeries()

        data = report.get_report_data()

        self.assertEqual(data[0].get('__balance__TS%s0301' % year), 200, data[0])
        self.assertEqual(data[0]['__balance__TS%s0201' % year], 100)

        self.assertEqual(data[0]['__total__TS%s0401' % year], 100)
        self.assertEqual(data[0]['__total__TS%s0301' % year], 100)
        self.assertEqual(data[0]['__total__TS%s0201' % year], 100)

        # todo add __fb__ to time series and check the balance

    def test_client_statement_detail(self):
        """
        Test the detail statement
        This is do pass by making a document slug clickable (<a> elem)
        and it also passes by the slug search of the model admin
        :return:
        """
        report = report_generators.ClientDetailedStatement()
        data = report.get_report_data()
        self.assertEqual(len(data), 9)

    def test_productclientsalesmatrix(self):
        report = report_generators.ProductClientSalesMatrix(crosstab_ids=[self.client1.pk, self.client2.pk])
        data = report.get_report_data()
        self.assertEqual(data[0]['__total__CT%s' % self.client1.pk], 300)
        self.assertEqual(data[0]['__total__CT%s' % self.client2.pk], 600)
        self.assertEqual(data[0]['__total__CT----'], 900)

    def _test_default_order_by(self):
        self.client.login(username='super', password='secret')
        response = self.client.get(reverse('ra_admin:report', args=('client', 'clienttotalbalancesordered')),
                                   HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        previous_balance = 0
        self.assertTrue(len(data['data']) > 1)
        for i, line in enumerate(data['data']):
            if i == 0:
                previous_balance = line['__balance__']
            else:
                self.assertTrue(line['__balance__'] > previous_balance)

    def _test_default_order_by_reversed(self):
        self.client.login(username='super', password='secret')
        response = self.client.get(reverse('ra_admin:report', args=('client', 'ClientTotalBalancesOrderedDESC')),
                                   HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        previous_balance = 0
        self.assertTrue(len(data['data']) > 1)
        for i, line in enumerate(data['data']):
            if i == 0:
                previous_balance = line['__balance__']
            else:
                self.assertTrue(line['__balance__'] < previous_balance)

    def test_show_empty_records(self):
        report = report_generators.ClientTotalBalance()
        data = report.get_report_data()
        with_show_empty_len = len(data)
        wo_show_empty = report_generators.ClientTotalBalance(show_empty_records=False)
        self.assertNotEqual(with_show_empty_len, wo_show_empty)
        # self.assertEqual(data[0].get('__balance__'), 300, data[0])

    def test_filters(self):
        report = ClientTotalBalance(kwargs_filters={'client': self.client1.pk}, show_empty_records=True)
        data = report.get_report_data()
        self.assertEqual(len(data), 1, data)

        report = ClientTotalBalance(kwargs_filters={'client': self.client1.pk}, show_empty_records=False)
        data = report.get_report_data()
        self.assertEqual(len(data), 1, data)

    def test_filter_as_int_n_list(self):
        report = ClientTotalBalance(kwargs_filters={'client': self.client1.pk}, show_empty_records=True)
        data = report.get_report_data()
        self.assertEqual(len(data), 1, data)

        report = ClientTotalBalance(kwargs_filters={'client_id__in': [self.client1.pk]}, show_empty_records=True)
        data = report.get_report_data()
        self.assertEqual(len(data), 1, data)


class TestView(BaseTestData, TestCase):
    def test_view(self):
        reponse = self.client.get(reverse('report1'))
        self.assertEqual(reponse.status_code, 200)
        # import pdb; pdb.set_trace()
        view_report_data = reponse.context['report_data']['data']
        report_generator = ReportGenerator(report_model=OrderLine,
                                           date_field='date_placed',  # or 'order__date_placed',
                                           group_by='product',
                                           columns=['name', 'sku'],
                                           time_series_pattern='monthly',
                                           time_series_columns=['__total_quantity__'],
                                           )
        self.assertEqual(view_report_data, report_generator.get_report_data())


class TestReportFieldRegistry(TestCase):
    def test_unregister(self):
        # unregister a field that we know exists
        field_registry.unregister('__balance__')
        self.assertNotIn('__balance__', field_registry.get_all_report_fields_names())

    def test_registering_new(self):
        def register():
            class ReportFieldWDuplicatedName(BaseReportField):
                name = '__total_field__'
                calculation_field = 'field'

            field_registry.register(ReportFieldWDuplicatedName)

        register()
        self.assertIn('__total_field__', field_registry.get_all_report_fields_names())

    def test_already_registered(self):
        def register():
            class ReportFieldWDuplicatedName(BaseReportField):
                name = '__total__'

            field_registry.register(ReportFieldWDuplicatedName)

        with self.assertRaises(Exception):
            register()

    def test_unregister_a_non_existent(self):
        def register():
            field_registry.unregister('__a_weird_name__')

        with self.assertRaises(Exception):
            register()

    def test_get_non_existent_field(self):
        def register():
            field = field_registry.get_field_by_name('__a_weird_name__')
            return field

        with self.assertRaises(Exception):
            field = register()
            self.assertIsNone(field)

    def test_creating_a_report_field_on_the_fly(self):
        from django.db.models import Sum
        name = BaseReportField.create(Sum, 'value', '__sum_of_value__')
        self.assertIn(name, field_registry.get_all_report_fields_names())

    def test_creating_a_report_field_on_the_fly_wo_name(self):
        from django.db.models import Sum
        name = BaseReportField.create(Sum, 'value')
        self.assertIn(name, field_registry.get_all_report_fields_names())

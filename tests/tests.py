import datetime
from unittest import skip
from urllib.parse import urljoin

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from django.utils.timezone import now

from .models import Client, Product, SimpleSales

User = get_user_model()
SUPER_LOGIN = dict(username='superlogin', password='password')
year = now().year

from . import report_generators


class ReportRegistryTest(SimpleTestCase):
    pass


class BaseTestData:
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

    def _test_client_balance(self):
        self.client.login(username='super', password='secret')
        response = self.client.get(reverse('ra_admin:report', args=('client', 'balances')),
                                   HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['data'][0].get('__balance__'), 300, data['data'][0])

    def _test_product_total_sales(self):
        self.client.login(username='super', password='secret')
        response = self.client.get(reverse('ra_admin:report', args=('product', 'total_sales')),
                                   HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['data'][0]['__balance__'], 1800)

    def test_client_client_sales_monthly(self):
        report = report_generators.ClientSalesMonthlySeries()

        # self.client.login(username='super', password='secret')
        # response = self.client.get(reverse('ra_admin:report', args=('client', 'clientsalesmonthlyseries')), data={
        #     'client_id': self.client1.pk
        # }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        # self.assertEqual(response.status_code, 200)
        data = report.get_report_data()
        # import pdb; pdb.set_trace()
        # print(data['data'][0])

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
        report = report_generators.ProductClientSalesMatrix()

        data = report.get_report_data()
        # product1_row = get_obj_from_list(data['data'], 'client_id', str(self.product1.pk))
        # print(product1_row)
        # # self.assertEqual(product1_row['__total_MXclient-%s' % self.client1.pk], 300)
        # self.assertEqual(product1_row['__total_MXclient-%s' % self.client2.pk], 600)
        # self.assertEqual(product1_row['__total_MXclient-----'], 900)

        # response = self.client.get(reverse('ra_admin:report', args=('product', 'productclientsalesmatrix')),
        #                            data={'matrix_entities': [self.client1.pk, self.client2.pk],
        #                                  'matrix_show_other': False},
        #                            HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        # self.assertEqual(response.status_code, 200)

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

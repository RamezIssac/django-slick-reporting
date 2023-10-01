import datetime
from unittest import skip

from django.contrib.auth import get_user_model
from django.db.models import Count
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils.timezone import now

from slick_reporting.fields import ComputationField, BalanceReportField
from slick_reporting.generator import ReportGenerator
from slick_reporting.views import ReportView
from slick_reporting.registry import field_registry
from tests.report_generators import (
    ClientTotalBalance,
    ProductClientSalesMatrix2,
    GroupByCharField,
    GroupByCharFieldPlusTimeSeries,
    TimeSeriesWithOutGroupBy,
    ProductClientSalesMatrixwSimpleSales2,
)
from . import report_generators
from .models import (
    Client,
    Contact,
    Product,
    SimpleSales,
    UserJoined,
    SalesWithFlag,
    ComplexSales,
    TaxCode,
    ProductCustomID,
    SalesProductWithCustomID,
    Agent,
    SimpleSales2,
)

User = get_user_model()
SUPER_LOGIN = dict(username="superlogin", password="password")
year = now().year


class BaseTestData:
    databases = "__all__"

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        User.objects.create_superuser("super", None, "secret")

        user = User.objects.create(is_superuser=True, is_staff=True, **SUPER_LOGIN)
        limited_user = User.objects.create_user(
            is_superuser=False, is_staff=True, username="limited", password="password"
        )
        cls.user = user
        cls.limited_user = limited_user
        agent = Agent.objects.create(name="John")
        agent2 = Agent.objects.create(name="Frank")
        cls.client1 = Client.objects.create(name="Client 1", sex="MALE")
        cls.client1.contact = Contact.objects.create(address="Street 1", agent=agent)
        cls.client1.save()
        cls.client2 = Client.objects.create(name="Client 2", sex="FEMALE")
        cls.client2.contact = Contact.objects.create(address="Street 2", agent=agent)
        cls.client2.save()
        cls.client3 = Client.objects.create(name="Client 3", sex="OTHER")
        cls.client3.contact = Contact.objects.create(address="Street 3", agent=agent2)
        cls.client3.save()
        cls.clientIdle = Client.objects.create(name="Client Idle")

        cls.product1 = Product.objects.create(name="Product 1", category="small", sku="a1b1")
        cls.product2 = Product.objects.create(name="Product 2", category="medium", sku="a2b2")
        cls.product3 = Product.objects.create(name="Product 3", category="big", sku="3333")

        cls.product_w_custom_id1 = ProductCustomID.objects.create(name="Product 1", category="small")
        cls.product_w_custom_id2 = ProductCustomID.objects.create(name="Product 2", category="medium")

        SimpleSales.objects.create(
            doc_date=datetime.datetime(year, 1, 2),
            client=cls.client1,
            product=cls.product1,
            quantity=10,
            price=10,
            created_at=datetime.datetime(year, 1, 5),
        )
        SimpleSales.objects.create(
            doc_date=datetime.datetime(year, 2, 2),
            client=cls.client1,
            product=cls.product1,
            quantity=10,
            price=10,
            created_at=datetime.datetime(year, 2, 3),
        )

        SimpleSales.objects.create(
            doc_date=datetime.datetime(year, 3, 2),
            client=cls.client1,
            product=cls.product1,
            quantity=10,
            price=10,
            created_at=datetime.datetime(year, 3, 3),
        )

        # client 2
        SimpleSales.objects.create(
            doc_date=datetime.datetime(year, 1, 2),
            client=cls.client2,
            product=cls.product1,
            quantity=20,
            price=10,
        )
        SimpleSales.objects.create(
            doc_date=datetime.datetime(year, 2, 2),
            client=cls.client2,
            product=cls.product1,
            quantity=20,
            price=10,
        )

        SimpleSales.objects.create(
            doc_date=datetime.datetime(year, 3, 2),
            client=cls.client2,
            product=cls.product1,
            quantity=20,
            price=10,
        )

        # client 3
        SimpleSales.objects.create(
            doc_date=datetime.datetime(year, 1, 2),
            client=cls.client3,
            product=cls.product1,
            quantity=30,
            price=10,
        )
        SimpleSales.objects.create(
            doc_date=datetime.datetime(year, 2, 2),
            client=cls.client3,
            product=cls.product1,
            quantity=30,
            price=10,
        )

        SimpleSales.objects.create(
            doc_date=datetime.datetime(year, 3, 2),
            client=cls.client3,
            product=cls.product1,
            quantity=30,
            price=10,
        )

        SimpleSales2.objects.create(
            doc_date=datetime.datetime(year, 1, 2),
            client=cls.client1,
            product=cls.product1,
            quantity=10,
            price=10,
            created_at=datetime.datetime(year, 1, 5),
        )
        SimpleSales2.objects.create(
            doc_date=datetime.datetime(year, 2, 2),
            client=cls.client1,
            product=cls.product1,
            quantity=10,
            price=10,
            created_at=datetime.datetime(year, 2, 3),
        )

        SimpleSales2.objects.create(
            doc_date=datetime.datetime(year, 3, 2),
            client=cls.client1,
            product=cls.product1,
            quantity=10,
            price=10,
            created_at=datetime.datetime(year, 3, 3),
        )

        # client 2
        SimpleSales2.objects.create(
            doc_date=datetime.datetime(year, 1, 2),
            client=cls.client2,
            product=cls.product1,
            quantity=20,
            price=10,
        )
        SimpleSales2.objects.create(
            doc_date=datetime.datetime(year, 2, 2),
            client=cls.client2,
            product=cls.product1,
            quantity=20,
            price=10,
        )

        SimpleSales2.objects.create(
            doc_date=datetime.datetime(year, 3, 2),
            client=cls.client2,
            product=cls.product1,
            quantity=20,
            price=10,
        )

        # client 3
        SimpleSales2.objects.create(
            doc_date=datetime.datetime(year, 1, 2),
            client=cls.client3,
            product=cls.product1,
            quantity=30,
            price=10,
        )
        SimpleSales2.objects.create(
            doc_date=datetime.datetime(year, 2, 2),
            client=cls.client3,
            product=cls.product1,
            quantity=30,
            price=10,
        )

        SimpleSales2.objects.create(
            doc_date=datetime.datetime(year, 3, 2),
            client=cls.client3,
            product=cls.product1,
            quantity=30,
            price=10,
        )

        cls.tax1 = TaxCode.objects.create(name="State", tax=8)  # Added three times
        cls.tax2 = TaxCode.objects.create(name="Vat reduced", tax=5)  # Added two times
        cls.tax3 = TaxCode.objects.create(name="Vat full", tax=20)  # Added one time

        sale1 = ComplexSales.objects.create(
            doc_date=datetime.datetime(year, 3, 2),
            client=cls.client3,
            product=cls.product1,
            quantity=30,
            price=10,
            flag="sales",
        )
        sale2 = ComplexSales.objects.create(
            doc_date=datetime.datetime(year, 3, 2),
            client=cls.client3,
            product=cls.product1,
            quantity=30,
            price=10,
            flag="sales",
        )
        sale3 = ComplexSales.objects.create(
            doc_date=datetime.datetime(year, 3, 2),
            client=cls.client3,
            product=cls.product1,
            quantity=30,
            price=10,
            flag="sales",
        )
        sale4 = ComplexSales.objects.create(
            doc_date=datetime.datetime(year, 3, 2),
            client=cls.client3,
            product=cls.product1,
            quantity=30,
            price=10,
            flag="sales-return",
        )
        sale4 = ComplexSales.objects.create(
            doc_date=datetime.datetime(year, 3, 2),
            client=cls.client3,
            product=cls.product2,
            quantity=34,
            price=10,
            flag="sales-return",
        )
        ComplexSales.objects.create(
            doc_date=datetime.datetime(year, 3, 2),
            client=cls.client2,
            product=cls.product1,
            quantity=77,
            price=10,
            flag="",
        )
        sale1.tax.add(cls.tax1)
        sale1.tax.add(cls.tax2)
        sale2.tax.add(cls.tax1)
        sale2.tax.add(cls.tax3)
        sale3.tax.add(cls.tax1)
        sale4.tax.add(cls.tax2)

        SalesProductWithCustomID.objects.create(
            doc_date=datetime.datetime(year, 1, 2),
            client=cls.client1,
            product=cls.product_w_custom_id1,
            quantity=10,
            price=10,
            created_at=datetime.datetime(year, 1, 5),
        )
        SalesProductWithCustomID.objects.create(
            doc_date=datetime.datetime(year, 2, 2),
            client=cls.client1,
            product=cls.product_w_custom_id1,
            quantity=10,
            price=10,
            created_at=datetime.datetime(year, 2, 3),
        )

        SalesProductWithCustomID.objects.create(
            doc_date=datetime.datetime(year, 3, 2),
            client=cls.client1,
            product=cls.product_w_custom_id2,
            quantity=10,
            price=10,
            created_at=datetime.datetime(year, 3, 3),
        )


# @override_settings(ROOT_URLCONF='reporting_tests.urls', RA_CACHE_REPORTS=False, USE_TZ=False)
class ReportTest(BaseTestData, TestCase):
    def test_client_balance(self):
        report = report_generators.ClientTotalBalance()
        data = report.get_report_data()

        self.assertEqual(data[0].get("__balance__"), 300, data[0])

    def test_compute_from_queryset(self):
        report = report_generators.TotalBalanceWithQueryset()
        data = report.get_report_data()
        self.assertEqual(data, [])

    def test_product_total_sales(self):
        report = report_generators.ProductTotalSalesProductWithCustomID()
        data = report.get_report_data()
        self.assertEqual(data[0]["__balance__"], 200)
        self.assertEqual(data[1]["__balance__"], 100)

    def test_product_total_sales_product_custom_id(self):
        report = report_generators.ProductTotalSales()
        data = report.get_report_data()
        self.assertEqual(data[0]["__balance__"], 1800)
        self.assertEqual(data[0]["get_object_sku"], "A1B1")
        self.assertEqual(
            data[0]["average_value"],
            data[0]["__balance__"] / data[0]["__balance_quantity__"],
        )

    def test_product_total_sales_with_percentage(self):
        report = report_generators.ProductTotalSalesWithPercentage()
        data = report.get_report_data()
        self.assertEqual(data[2]["__percent_to_total_balance__"], 50)

    @override_settings(
        SLICK_REPORTING_DEFAULT_START_DATE=datetime.datetime(2020, 1, 1),
        SLICK_REPORTING_DEFAULT_END_DATE=datetime.datetime(2021, 1, 1),
    )
    def test_product_total_sales_with_changed_dated(self):
        report = report_generators.ProductTotalSales()
        data = report.get_report_data()
        self.assertEqual(len(data), 0)

    def test_client_client_sales_monthly(self):
        report = report_generators.ClientSalesMonthlySeries()

        data = report.get_report_data()

        self.assertEqual(data[0].get("__balance__TS%s0301" % year), 200, data[0])
        self.assertEqual(data[0]["__balance__TS%s0201" % year], 100)

        self.assertEqual(data[0]["__total__TS%s0401" % year], 100)
        self.assertEqual(data[0]["__total__TS%s0301" % year], 100)
        self.assertEqual(data[0]["__total__TS%s0201" % year], 100)

        self.assertEqual(data[0]["__debit__TS%s0401" % year], 100)
        self.assertEqual(data[0]["__debit__TS%s0301" % year], 100)
        self.assertEqual(data[0]["__debit__TS%s0201" % year], 100)

        self.assertEqual(data[2]["__debit__TS%s0401" % year], 300)
        self.assertEqual(data[2]["__debit__TS%s0301" % year], 300)
        self.assertEqual(data[2]["__debit__TS%s0201" % year], 300)

        # todo add __fb__ to time series and check the balance

    def test_productclientsalesmatrix(self):
        report = report_generators.ProductClientSalesMatrix(crosstab_ids=[self.client1.pk, self.client2.pk])
        data = report.get_report_data()
        self.assertEqual(data[0]["__total__CT%s" % self.client1.pk], 300)
        self.assertEqual(data[0]["__total__CT%s" % self.client2.pk], 600)
        self.assertEqual(data[0]["__total__CT----"], 900)

    def test_productclientsalesmatrix_no_remainder(self):
        report = report_generators.ProductClientSalesMatrix(
            crosstab_ids=[self.client1.pk, self.client2.pk],
            crosstab_compute_remainder=False,
        )
        data = report.get_report_data()
        self.assertEqual(data[0]["__total__CT%s" % self.client1.pk], 300)
        self.assertEqual(data[0]["__total__CT%s" % self.client2.pk], 600)

    def test_show_empty_records(self):
        report = report_generators.ClientTotalBalance()
        data = report.get_report_data()
        with_show_empty_len = len(data)
        wo_show_empty = report_generators.ClientTotalBalance(show_empty_records=False)
        self.assertNotEqual(with_show_empty_len, wo_show_empty)
        # self.assertEqual(data[0].get('__balance__'), 300, data[0])

    def test_filters(self):
        report = ClientTotalBalance(kwargs_filters={"client": self.client1.pk}, show_empty_records=True)
        data = report.get_report_data()
        self.assertEqual(len(data), 1, data)

        report = ClientTotalBalance(kwargs_filters={"client": self.client1.pk}, show_empty_records=False)
        data = report.get_report_data()
        self.assertEqual(len(data), 1, data)

    def test_view_filter_to_field_set(self):
        report_generator = ReportGenerator(
            report_model=SimpleSales2,
            date_field="doc_date",
            group_by="client",
            columns=["slug", "name"],
            time_series_pattern="monthly",
            time_series_columns=["__total__", "__balance__"],
        )
        data = report_generator.get_report_data()
        response = self.client.get(
            reverse("report-to-field-set"),
            data={
                "client_id": [self.client2.name, self.client1.name],
            },
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 200)

        response.json()
        self.assertTrue(len(data), 2)
        # self.assertEqual(view_report_data['data'], data)

    def test_filter_as_int_n_list(self):
        report = ClientTotalBalance(kwargs_filters={"client": self.client1.pk}, show_empty_records=True)
        data = report.get_report_data()
        self.assertEqual(len(data), 1, data)

        report = ClientTotalBalance(kwargs_filters={"client_id__in": [self.client1.pk]}, show_empty_records=True)
        data = report.get_report_data()
        self.assertEqual(len(data), 1, data)

    def test_timeseries_without_group(self):
        report = TimeSeriesWithOutGroupBy()
        data = report.get_report_data()
        self.assertEqual(data[0][f"__total__TS{year}0201"], 600)

    def test_many_to_many_group_by(self):
        field_registry.register(ComputationField.create(Count, "tax__name", "tax__count"))

        report_generator = ReportGenerator(
            report_model=ComplexSales,
            date_field="doc_date",
            group_by="tax__name",
            columns=["tax__name", "tax__count"],
        )
        data = report_generator.get_report_data()

        self.assertEqual(len(data), 4)  # 3 taxes + 1 empty
        self.assertEqual(data[0]["tax__name"], "State")
        self.assertEqual(data[0]["tax__count"], 3)
        self.assertEqual(data[1]["tax__name"], "Vat reduced")
        self.assertEqual(data[1]["tax__count"], 2)
        self.assertEqual(data[2]["tax__name"], "Vat full")
        self.assertEqual(data[2]["tax__count"], 1)


class TestView(BaseTestData, TestCase):
    def test_view(self):
        response = self.client.get(
            reverse("report1"),
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 200)
        view_report_data = response.json()["data"]
        report_generator = ReportGenerator(
            report_model=SimpleSales,
            date_field="doc_date",
            group_by="client",
            columns=["slug", "name"],
            time_series_pattern="monthly",
            time_series_columns=["__total__", "__balance__"],
        )
        self.assertTrue(view_report_data)
        self.assertEqual(view_report_data, report_generator.get_report_data())

    def test_qs_only(self):
        response = self.client.get(
            reverse("queryset-only"),
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 200)
        view_report_data = response.json()["data"]
        report_generator = ReportGenerator(
            report_model=SimpleSales,
            date_field="doc_date",
            group_by="client",
            columns=["slug", "name"],
            time_series_pattern="monthly",
            time_series_columns=["__total__", "__balance__"],
        )
        self.assertTrue(view_report_data)
        self.assertEqual(view_report_data, report_generator.get_report_data())

    def test_view_filter(self):
        report_generator = ReportGenerator(
            report_model=SimpleSales,
            date_field="doc_date",
            group_by="client",
            columns=["slug", "name"],
            time_series_pattern="monthly",
            time_series_columns=["__total__", "__balance__"],
            kwargs_filters={"client_id__in": [self.client1.pk, self.client2.pk]},
        )
        data = report_generator.get_report_data()
        response = self.client.get(
            reverse("report1"),
            data={
                "client_id": [self.client2.pk, self.client1.pk],
            },
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(len(data), 2)
        view_report_data = response.json()
        self.assertEqual(view_report_data["data"], data)

    def test_view_filter_to_field_set(self):
        report_generator = ReportGenerator(
            report_model=SimpleSales2,
            date_field="doc_date",
            group_by="client",
            columns=["slug", "name"],
            time_series_pattern="monthly",
            time_series_columns=["__total__", "__balance__"],
        )
        data = report_generator.get_report_data()
        response = self.client.get(
            reverse("report-to-field-set"),
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 200)

        self.assertTrue(len(data), 2)

        view_report_data = response.json()

        self.assertEqual(view_report_data["data"], data)

    def test_ajax(self):
        report_generator = ReportGenerator(
            report_model=SimpleSales,
            date_field="doc_date",
            group_by="client",
            columns=["slug", "name"],
            time_series_pattern="monthly",
            time_series_columns=["__total__", "__balance__"],
        )
        data = report_generator.get_report_data()
        response = self.client.get(reverse("report1"), HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(response.status_code, 200)
        view_report_data = response.json()
        self.assertEqual(view_report_data["data"], data)

    def test_crosstab_report_view(self):
        from .report_generators import ProductClientSalesMatrix

        data = ProductClientSalesMatrix(
            crosstab_compute_remainder=True,
            crosstab_ids=[self.client1.pk, self.client2.pk],
        ).get_report_data()

        response = self.client.get(reverse("product_crosstab_client"))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(
            reverse("product_crosstab_client"),
            data={
                "client_id": [self.client1.pk, self.client2.pk],
                "crosstab_compute_remainder": True,
            },
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 200)
        view_report_data = response.json()
        self.assertEqual(view_report_data["data"], data)

    def test_crosstab_report_view_clumns_on_fly(self):
        data = ProductClientSalesMatrix2(
            crosstab_compute_remainder=True,
            crosstab_ids=[self.client1.pk, self.client2.pk],
        ).get_report_data()

        response = self.client.get(
            reverse("crosstab-columns-on-fly"),
            data={
                "client_id": [self.client1.pk, self.client2.pk],
                "crosstab_compute_remainder": True,
            },
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 200)
        view_report_data = response.json()
        self.assertEqual(view_report_data["data"], data, view_report_data)

    def test_crosstab_report_view_to_field_set(self):
        from .report_generators import ProductClientSalesMatrixToFieldSet

        data = ProductClientSalesMatrixToFieldSet(
            crosstab_compute_remainder=True,
            crosstab_ids=[self.client1.name, self.client2.name],
        ).get_report_data()

        response = self.client.get(reverse("product_crosstab_client_to_field_set"))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(
            reverse("product_crosstab_client_to_field_set"),
            data={
                "client_id": [self.client1.name, self.client2.name],
                "crosstab_compute_remainder": True,
            },
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 200)
        view_report_data = response.json()
        self.assertEqual(view_report_data["data"], data)

    def test_crosstab_report_view_clumns_on_fly_to_field_set(self):
        data = ProductClientSalesMatrixwSimpleSales2(
            crosstab_compute_remainder=True,
            crosstab_ids=[self.client1.name, self.client2.name],
        ).get_report_data()

        response = self.client.get(
            reverse("crosstab-columns-on-fly-to-field-set"),
            data={
                "client_id": [self.client1.name, self.client2.name],
                "crosstab_compute_remainder": True,
            },
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 200)
        view_report_data = response.json()
        self.assertEqual(view_report_data["data"], data, view_report_data["data"])

    def test_chart_settings(self):
        response = self.client.get(
            reverse("product_crosstab_client"),
            data={
                "client_id": [self.client1.pk, self.client2.pk],
                "crosstab_compute_remainder": True,
            },
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["chart_settings"][0]["id"] != "")
        self.assertTrue(data["chart_settings"][0]["title"], "awesome report title")

    @skip
    def test_error_on_missing_date_field(self):
        def test_function():
            class TotalClientSales(ReportView):
                report_model = SimpleSales

        self.assertRaises(TypeError, test_function)


class TestReportFieldRegistry(TestCase):
    def test_unregister(self):
        # unregister a field that we know exists
        field_registry.unregister("__balance__")
        self.assertNotIn("__balance__", field_registry.get_all_report_fields_names())
        # bring it back again as later tests using it would fail
        field_registry.register(BalanceReportField)

    def test_registering_new(self):
        def register():
            class ReportFieldWDuplicatedName(ComputationField):
                name = "__total_field__"
                calculation_field = "field"

            field_registry.register(ReportFieldWDuplicatedName)

        register()
        self.assertIn("__total_field__", field_registry.get_all_report_fields_names())

    def test_already_registered(self):
        def register():
            class ReportFieldWDuplicatedName(ComputationField):
                name = "__total__"

            field_registry.register(ReportFieldWDuplicatedName)

        with self.assertRaises(Exception):
            register()

    def test_unregister_a_non_existent(self):
        def register():
            field_registry.unregister("__a_weird_name__")

        with self.assertRaises(Exception):
            register()

    def test_get_non_existent_field(self):
        def register():
            return field_registry.get_field_by_name("__a_weird_name__")

        with self.assertRaises(Exception):
            register()

    def test_creating_a_report_field_on_the_fly(self):
        from django.db.models import Sum

        name = ComputationField.create(Sum, "value", "__sum_of_value__")
        self.assertNotIn(name, field_registry.get_all_report_fields_names())

    def test_creating_a_report_field_on_the_fly_wo_name(self):
        from django.db.models import Sum

        name = ComputationField.create(Sum, "value")
        self.assertNotIn(name, field_registry.get_all_report_fields_names())


class TestGroupByDate(TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        UserJoined.objects.create(username="adam", date_joined=datetime.date(2020, 1, 2))
        UserJoined.objects.create(username="eve", date_joined=datetime.date(2020, 1, 3))
        UserJoined.objects.create(username="steve", date_joined=datetime.date(2020, 1, 5))
        UserJoined.objects.create(username="smiv", date_joined=datetime.date(2020, 1, 5))

    def test_joined_per_day(self):
        field_registry.register(ComputationField.create(Count, "id", "count__id"))
        report_generator = ReportGenerator(
            report_model=UserJoined,
            date_field="date_joined",
            group_by="date_joined",
            start_date=datetime.date(2020, 1, 1),
            end_date=datetime.date(2020, 1, 10),
            columns=["date_joined", "count__id"],
        )

        data = report_generator.get_report_data()
        self.assertEqual(len(data), 3)
        self.assertEqual(data[0]["count__id"], 1)
        self.assertEqual(data[1]["count__id"], 1)
        self.assertEqual(data[2]["count__id"], 2)


class TestGroupByFlag(TestCase):
    databases = "__all__"

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        User.objects.create_superuser("super", None, "secret")

        user = User.objects.create(is_superuser=True, is_staff=True, **SUPER_LOGIN)
        limited_user = User.objects.create_user(
            is_superuser=False, is_staff=True, username="limited", password="password"
        )
        cls.user = user
        cls.limited_user = limited_user
        cls.client1 = Client.objects.create(name="Client 1")
        cls.client2 = Client.objects.create(name="Client 2")
        cls.client3 = Client.objects.create(name="Client 3")
        cls.clientIdle = Client.objects.create(name="Client Idle")

        cls.product1 = Product.objects.create(name="Product 1")
        cls.product2 = Product.objects.create(name="Product 2")
        cls.product3 = Product.objects.create(name="Product 3")

        SalesWithFlag.objects.create(
            doc_date=datetime.datetime(year, 1, 1),
            client=cls.client1,
            product=cls.product1,
            quantity=10,
            price=10,
            created_at=datetime.datetime(year, 1, 5),
        )
        SalesWithFlag.objects.create(
            doc_date=datetime.datetime(year, 2, 1),
            client=cls.client1,
            product=cls.product1,
            quantity=10,
            price=10,
            created_at=datetime.datetime(year, 2, 3),
        )

        SalesWithFlag.objects.create(
            doc_date=datetime.datetime(year, 3, 1),
            client=cls.client1,
            product=cls.product1,
            quantity=10,
            price=10,
            created_at=datetime.datetime(year, 3, 3),
        )

        # client 2
        SalesWithFlag.objects.create(
            doc_date=datetime.datetime(year, 1, 1),
            client=cls.client2,
            product=cls.product1,
            quantity=20,
            price=10,
        )
        SalesWithFlag.objects.create(
            doc_date=datetime.datetime(year, 2, 1),
            client=cls.client2,
            product=cls.product1,
            quantity=20,
            price=10,
        )

        SalesWithFlag.objects.create(
            doc_date=datetime.datetime(year, 3, 1),
            client=cls.client2,
            product=cls.product1,
            quantity=20,
            price=10,
        )

        # client 3
        SalesWithFlag.objects.create(
            doc_date=datetime.datetime(year, 1, 1),
            client=cls.client3,
            product=cls.product1,
            quantity=30,
            price=10,
        )
        SalesWithFlag.objects.create(
            doc_date=datetime.datetime(year, 2, 1),
            client=cls.client3,
            product=cls.product1,
            quantity=30,
            price=10,
        )

        SalesWithFlag.objects.create(
            doc_date=datetime.datetime(year, 3, 1),
            client=cls.client3,
            product=cls.product1,
            quantity=30,
            price=10,
        )
        SalesWithFlag.objects.create(
            doc_date=datetime.datetime(year, 3, 1),
            client=cls.client3,
            product=cls.product1,
            quantity=25,
            price=10,
            flag="sales-return",
        )

    def test_group_by_flag(self):
        report = GroupByCharField()
        data = report.get_report_data()
        self.assertEqual(data[0]["sum__quantity"], 180)
        self.assertEqual(data[1]["sum__quantity"], 25)

    def test_group_by_flag_time_series(self):
        report = GroupByCharFieldPlusTimeSeries()
        data = report.get_report_data()
        self.assertEqual(len(data), 2)
        self.assertEqual(data[1]["sum__quantity"], 25)
        self.assertEqual(data[1][f"sum__quantityTS{year}0401"], 25)

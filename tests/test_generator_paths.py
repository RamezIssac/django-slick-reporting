import datetime

from django.db.models import Q
from django.test import RequestFactory, TestCase

from slick_reporting.generator import ListViewReportGenerator, ReportGenerator

from .models import Client, Product, SimpleSales
from .views import SimpleSalesListReport

START = datetime.datetime(2020, 1, 1, tzinfo=datetime.timezone.utc)
END = datetime.datetime(2020, 12, 31, tzinfo=datetime.timezone.utc)
MID = datetime.datetime(2020, 6, 15, tzinfo=datetime.timezone.utc)


class DateBoundaryTestBase(TestCase):
    """One sale dated exactly on the start date, one mid window and one exactly on the end date."""

    @classmethod
    def setUpTestData(cls):
        cls.clients = {}
        cls.products = {}
        for key, doc_date, price in (("start", START, 100), ("mid", MID, 50), ("end", END, 200)):
            client = Client.objects.create(name=f"Client {key}")
            product = Product.objects.create(name=f"Product {key}")
            SimpleSales.objects.create(
                slug=f"sale-{key}", doc_date=doc_date, client=client, product=product, quantity=1, price=price
            )
            cls.clients[key] = client
            cls.products[key] = product

    def key_of(self, pk, objects):
        return next(key for key, obj in objects.items() if obj.pk == pk)


class TestGroupByDateBoundaries(DateBoundaryTestBase):
    def test_group_by_report(self):
        report = ReportGenerator(
            report_model=SimpleSales,
            date_field="doc_date",
            group_by="client",
            columns=["id", "__total__"],
            start_date=START,
            end_date=END,
        )
        totals = {self.key_of(row["id"], self.clients): row["__total__"] for row in report.get_report_data()}
        self.assertEqual(totals, {"start": 100, "mid": 50})


class TestPrecomputedCrosstabDateBoundaries(DateBoundaryTestBase):
    def test_precomputed_crosstab_report(self):
        report = ReportGenerator(
            report_model=SimpleSales,
            date_field="doc_date",
            group_by="product",
            crosstab_field="client",
            crosstab_columns=["value"],
            crosstab_precomputed=True,
            columns=["id", "__crosstab__"],
            start_date=START,
            end_date=END,
        )
        data = report.get_report_data()
        values = {}
        for row in data:
            product_key = self.key_of(row["id"], self.products)
            values[product_key] = row[f"valueCT{self.clients[product_key].pk}"]
        self.assertEqual(values, {"start": 100, "mid": 50})


class TestListReportDateBoundaries(DateBoundaryTestBase):
    def get_slugs(self, **kwargs):
        report = ListViewReportGenerator(
            report_model=SimpleSales,
            date_field="doc_date",
            columns=["slug", "value"],
            start_date=START,
            end_date=END,
            **kwargs,
        )
        return sorted(row["slug"] for row in report.get_report_data())

    def test_list_report(self):
        self.assertEqual(self.get_slugs(), ["sale-mid", "sale-start"])

    def test_list_report_q_filters(self):
        self.assertEqual(self.get_slugs(q_filters=[Q(slug="sale-mid")]), ["sale-mid"])


class ListContainer:
    def slug_upper(self, obj):
        return obj["slug"].upper()

    def instance_slug(self, obj):
        return obj.slug


class ListGeneratorWithAttribute(ListViewReportGenerator):
    def slug_title(self, obj, row):
        return obj["slug"].title()


class GroupByContainer:
    def name_and_total(self, obj, row):
        return f"{obj['name']}: {row['__total__']}"


class TestRecordDataColumns(DateBoundaryTestBase):
    def test_list_report_container_method(self):
        report = ListViewReportGenerator(
            report_model=SimpleSales,
            date_field="doc_date",
            columns=["slug", "slug_upper"],
            start_date=START,
            end_date=END,
            container_class=ListContainer(),
        )
        self.assertEqual(sorted(row["slug_upper"] for row in report.get_report_data()), ["SALE-MID", "SALE-START"])

    def test_list_report_of_method_columns_only_gets_instances(self):
        report = ListViewReportGenerator(
            report_model=SimpleSales,
            date_field="doc_date",
            columns=["instance_slug"],
            start_date=START,
            end_date=END,
            container_class=ListContainer(),
        )
        self.assertEqual(sorted(row["instance_slug"] for row in report.get_report_data()), ["sale-mid", "sale-start"])

    def test_list_report_generator_method(self):
        report = ListGeneratorWithAttribute(
            report_model=SimpleSales,
            date_field="doc_date",
            columns=["slug", "slug_title"],
            start_date=START,
            end_date=END,
        )
        self.assertEqual(sorted(row["slug_title"] for row in report.get_report_data()), ["Sale-Mid", "Sale-Start"])

    def test_group_by_report_container_method(self):
        report = ReportGenerator(
            report_model=SimpleSales,
            date_field="doc_date",
            group_by="client",
            columns=["name", "__total__", "name_and_total"],
            start_date=START,
            end_date=END,
            container_class=GroupByContainer(),
        )
        self.assertEqual(
            sorted(row["name_and_total"] for row in report.get_report_data()), ["Client mid: 50", "Client start: 100"]
        )


class TestListViewFormClass(TestCase):
    def get_form_fields(self, **attrs):
        view_class = type("ListView", (SimpleSalesListReport,), attrs)
        view = view_class()
        view.request = RequestFactory().get("/")
        return sorted(view.get_form_class().base_fields)

    def test_default_form_matches_report_view_form(self):
        self.assertEqual(
            self.get_form_fields(), ["client_id", "content_type_id", "end_date", "product_id", "start_date"]
        )

    def test_filters_build_a_model_form(self):
        self.assertEqual(self.get_form_fields(filters=["client", "doc_date"]), ["client", "doc_date"])

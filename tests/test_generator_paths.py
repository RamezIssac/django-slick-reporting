import datetime
from unittest.mock import patch

from django.db.models import Q
from django.test import RequestFactory, TestCase

from slick_reporting import app_settings
from slick_reporting.forms import report_form_factory
from slick_reporting.generator import ListViewReportGenerator, ReportGenerator

from .models import Client, Product, SimpleSales, UserJoined
from .views import SimpleSalesListReport

START = datetime.datetime(2020, 1, 1, tzinfo=datetime.timezone.utc)
END = datetime.datetime(2020, 12, 31, tzinfo=datetime.timezone.utc)
MID = datetime.datetime(2020, 6, 15, tzinfo=datetime.timezone.utc)


class DateBoundaryTestBase(TestCase):
    """One sale at midnight of the start date, one mid window and one at midnight of the end date."""

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
        self.assertEqual(totals, {"start": 100, "mid": 50, "end": 200})


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
        self.assertEqual(values, {"start": 100, "mid": 50, "end": 200})


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
        self.assertEqual(self.get_slugs(), ["sale-end", "sale-mid", "sale-start"])

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
        self.assertEqual(
            sorted(row["slug_upper"] for row in report.get_report_data()), ["SALE-END", "SALE-MID", "SALE-START"]
        )

    def test_list_report_of_method_columns_only_gets_instances(self):
        report = ListViewReportGenerator(
            report_model=SimpleSales,
            date_field="doc_date",
            columns=["instance_slug"],
            start_date=START,
            end_date=END,
            container_class=ListContainer(),
        )
        self.assertEqual(
            sorted(row["instance_slug"] for row in report.get_report_data()), ["sale-end", "sale-mid", "sale-start"]
        )

    def test_list_report_generator_method(self):
        report = ListGeneratorWithAttribute(
            report_model=SimpleSales,
            date_field="doc_date",
            columns=["slug", "slug_title"],
            start_date=START,
            end_date=END,
        )
        self.assertEqual(
            sorted(row["slug_title"] for row in report.get_report_data()), ["Sale-End", "Sale-Mid", "Sale-Start"]
        )

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
            sorted(row["name_and_total"] for row in report.get_report_data()),
            ["Client end: 200", "Client mid: 50", "Client start: 100"],
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


def utc(*args):
    return datetime.datetime(*args, tzinfo=datetime.timezone.utc)


class TestInclusiveEndDate(TestCase):
    @classmethod
    def setUpTestData(cls):
        client = Client.objects.create(name="Client")
        product = Product.objects.create(name="Product")
        for slug, doc_date, price in (
            ("jan-31", utc(2020, 1, 31, 23, 0), 1),
            ("feb-01", utc(2020, 2, 1), 10),
            ("mar-10", utc(2020, 3, 10), 100),
            ("mar-20", utc(2020, 3, 20), 1000),
            ("dec-31-15:00:00.5", utc(2020, 12, 31, 15, 0, 0, 500000), 10000),
            ("dec-31-15:00:01", utc(2020, 12, 31, 15, 0, 1), 100000),
            ("dec-31-23:59:59.4", utc(2020, 12, 31, 23, 59, 59, 400000), 1000000),
        ):
            SimpleSales.objects.create(
                slug=slug, doc_date=doc_date, client=client, product=product, quantity=1, price=price
            )
        UserJoined.objects.create(username="last-day", date_joined=datetime.date(2020, 12, 31))

    def get_report(self, end_date, **kwargs):
        return ReportGenerator(
            report_model=SimpleSales,
            date_field="doc_date",
            group_by="client",
            columns=["name", "__total__", "__time_series__"],
            time_series_pattern="monthly",
            time_series_columns=["__total__"],
            start_date=utc(2020, 1, 1),
            end_date=end_date,
            **kwargs,
        )

    def get_total(self, end_date):
        return self.get_report(end_date).get_report_data()[0]["__total__"]

    def get_buckets(self, report):
        row = report.get_report_data()[0]
        return {col["start_date"].month: row[col["name"]] for col in report.get_time_series_parsed_columns()}, row

    def test_end_of_day_includes_its_last_second(self):
        self.assertEqual(self.get_total(utc(2020, 12, 31, 23, 59, 59)), 1111111)

    def test_typed_time_includes_that_second_only(self):
        self.assertEqual(self.get_total(utc(2020, 12, 31, 15, 0)), 11111)

    def test_midnight_stays_midnight(self):
        self.assertEqual(self.get_total(utc(2020, 12, 31)), 1111)

    def test_date_end_date_means_the_whole_day(self):
        report = ListViewReportGenerator(
            report_model=UserJoined,
            date_field="date_joined",
            columns=["username"],
            start_date=datetime.date(2020, 1, 1),
            end_date=datetime.date(2020, 12, 31),
        )
        self.assertEqual([row["username"] for row in report.get_report_data()], ["last-day"])

    def test_default_end_date_is_kept(self):
        default_end = utc(2020, 6, 1, 9, 30)
        with patch("slick_reporting.app_settings.SLICK_REPORTING_DEFAULT_END_DATE", default_end):
            report = ReportGenerator(report_model=SimpleSales, date_field="doc_date", columns=["__total__"])
        self.assertEqual(report.end_date, default_end.replace(tzinfo=None))

    def test_midnight_row_counts_only_in_its_own_month(self):
        buckets, _ = self.get_buckets(self.get_report(utc(2020, 2, 29, 23, 59, 59)))
        self.assertEqual(buckets, {1: 1, 2: 10})

    def test_month_buckets_sum_to_total_for_a_window_ending_mid_month(self):
        report = self.get_report(utc(2020, 3, 15, 23, 59, 59))
        buckets, row = self.get_buckets(report)
        self.assertEqual(report.get_time_series_parsed_columns()[-1]["end_date"], utc(2020, 3, 16))
        self.assertEqual(buckets, {1: 1, 2: 10, 3: 100})
        self.assertEqual(sum(buckets.values()), row["__total__"])


class TestEndDateFormField(TestCase):
    def get_form(self, end_date):
        form = report_form_factory(SimpleSales)(data={"end_date": end_date})
        self.assertTrue(form.is_valid(), form.errors)
        return form

    def test_default_initial_is_end_of_today(self):
        initial = report_form_factory(SimpleSales)().fields["end_date"].initial
        self.assertEqual(initial.time(), datetime.time(23, 59, 59))
        self.assertEqual(app_settings.get_end_date().time(), datetime.time(23, 59, 59))

    def test_date_only_input_becomes_end_of_that_day(self):
        form = self.get_form("2020-12-31")
        self.assertEqual(form.get_end_date().strftime("%Y-%m-%d %H:%M:%S"), "2020-12-31 23:59:59")
        self.assertIn('value="2020-12-31 23:59:59"', str(form["end_date"]))

    def test_typed_time_is_kept(self):
        form = self.get_form("2020-12-31 15:00")
        self.assertEqual(form.get_end_date().strftime("%Y-%m-%d %H:%M:%S"), "2020-12-31 15:00:00")
        self.assertIn('value="2020-12-31 15:00"', str(form["end_date"]))

    def test_typed_midnight_stays_midnight(self):
        form = self.get_form("2020-12-31 00:00")
        self.assertEqual(form.get_end_date().strftime("%Y-%m-%d %H:%M:%S"), "2020-12-31 00:00:00")

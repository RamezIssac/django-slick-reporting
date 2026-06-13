from datetime import datetime

from django.db.models import Sum
from django.test import TestCase, override_settings
from django.utils.translation import gettext_lazy as _

from slick_reporting.fields import ComputationField
from slick_reporting.generator import ReportGenerator, ListViewReportGenerator
from slick_reporting.helpers import get_foreign_keys
from .models import OrderLine, ComplexSales
from .models import SimpleSales, Client
from .report_generators import (
    GeneratorWithAttrAsColumn,
    CrosstabOnClient,
    GenericGenerator,
    GroupByCharField,
    TimeSeriesCustomDates,
    CrosstabOnField,
    CrosstabOnTraversingField,
    CrosstabCustomQueryset,
    TestCountField,
)
from .tests import BaseTestData, year


class CrosstabTests(BaseTestData, TestCase):
    def test_matrix_column_included(self):
        report = CrosstabOnClient(crosstab_ids=[self.client1.pk], crosstab_compute_remainder=False)
        columns = report.get_list_display_columns()
        self.assertEqual(len(columns), 3, columns)

        report = CrosstabOnClient(crosstab_ids=[self.client1.pk], crosstab_compute_remainder=True)
        columns = report.get_list_display_columns()
        self.assertEqual(len(columns), 4, columns)

    def test_matrix_column_position(self):
        report = CrosstabOnClient(
            columns=["__crosstab__", "name", "__total_quantity__"],
            crosstab_ids=[self.client1.pk],
            crosstab_compute_remainder=False,
        )
        columns = report.get_list_display_columns()
        self.assertEqual(len(columns), 3, columns)
        self.assertEqual(columns[0]["name"], "value__sumCT1")

        report = CrosstabOnClient(crosstab_ids=[self.client1.pk], crosstab_compute_remainder=True)
        columns = report.get_list_display_columns()
        self.assertEqual(len(columns), 4, columns)

    def test_get_crosstab_columns(self):
        report = CrosstabOnClient(crosstab_ids=[self.client1.pk])
        columns = report.get_list_display_columns()
        self.assertEqual(len(columns), 4)

        report = CrosstabOnClient(
            crosstab_ids=[self.client1.pk, self.client2.pk],
            crosstab_columns=["__total_quantity__", "__balance_quantity__"],
        )
        columns = report.get_list_display_columns()
        self.assertEqual(len(columns), 8, [x["name"] for x in columns])

    def test_get_crosstab_parsed_columns(self):
        """
        Test important attributes are passed .
        :return:
        """
        report = CrosstabOnClient(crosstab_ids=[self.client1.pk], crosstab_compute_remainder=False)
        columns = report.get_crosstab_parsed_columns()
        for col in columns:
            self.assertTrue("is_summable" in col.keys(), col)

    def test_crosstab_on_field(self):
        report = CrosstabOnField()
        data = report.get_report_data()
        self.assertEqual(len(data), 2, data)
        self.assertEqual(data[0]["value__sumCTsales"], 90, data)
        self.assertEqual(data[0]["value__sumCTsales-return"], 30, data)
        self.assertEqual(data[0]["value__sumCT----"], 77, data)
        self.assertEqual(data[1]["value__sumCTsales-return"], 34, data)

    def test_crosstab_ids_queryset(self):
        # same test values as above, tests that crosstab_ids_custom_filters
        report = CrosstabCustomQueryset()
        data = report.get_report_data()
        self.assertEqual(len(data), 2, data)
        self.assertEqual(data[0]["value__sumCT0"], 90, data)
        self.assertEqual(data[0]["value__sumCT1"], 30, data)
        self.assertEqual(data[1]["value__sumCT1"], 34, data)

    def test_crosstab_on_traversing_field(self):
        report = CrosstabOnTraversingField()
        data = report.get_report_data()
        self.assertEqual(len(data), 2, data)
        self.assertEqual(data[0]["value__sumCTOTHER"], 120, data)
        self.assertEqual(data[0]["value__sumCTFEMALE"], 77, data)
        self.assertEqual(data[0]["value__sumCT----"], 0, data)
        self.assertEqual(data[1]["value__sumCTOTHER"], 34, data)

    def test_crosstab_time_series(self):
        report = ReportGenerator(
            report_model=ComplexSales,
            date_field="doc_date",
            group_by="product",
            columns=["name", "__total_quantity__"],
            time_series_pattern="monthly",
            crosstab_field="client",
            crosstab_columns=[ComputationField.create(Sum, "quantity", name="value__sum", verbose_name=_("Sales"))],
            crosstab_ids=[self.client2.pk, self.client3.pk],
            crosstab_compute_remainder=False,
        )
        columns = report.get_list_display_columns()
        time_series_columns = report.get_time_series_parsed_columns()
        expected_num_of_columns = 2 * datetime.today().month  # 2 client + 1 remainder * months since start of year

        self.assertEqual(len(time_series_columns), expected_num_of_columns, columns)
        data = report.get_report_data()
        self.assertEqual(data[0]["__total_quantity__"], 197, data)
        sum_o_product_1 = 0
        for col in data[0]:
            if col.startswith("value__") and "TS" in col:
                sum_o_product_1 += data[0][col]

        self.assertEqual(sum_o_product_1, 197, data)


class GeneratorReportStructureTest(BaseTestData, TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        SimpleSales.objects.create(
            doc_date=datetime(year, 3, 2),
            client=cls.client3,
            product=cls.product3,
            quantity=30,
            price=10,
        )

    def test_time_series_columns_inclusion(self):
        x = ReportGenerator(
            OrderLine,
            date_field="order__date_placed",
            group_by="client",
            columns=["name", "__time_series__"],
            time_series_columns=["__total_quantity__"],
            time_series_pattern="monthly",
            start_date=datetime(2020, 1, 1),
            end_date=datetime(2020, 12, 31),
        )
        self.assertEqual(len(x.get_list_display_columns()), 13)

    def test_time_series_patterns(self):
        from slick_reporting.fields import TotalReportField

        report = ReportGenerator(
            OrderLine,
            date_field="order__date_placed",
            group_by="client",
            columns=["name", "__time_series__"],
            time_series_columns=["__total_quantity__"],
            time_series_pattern="monthly",
            start_date=datetime(2020, 1, 1),
            end_date=datetime(2020, 12, 31),
        )

        dates = report._get_time_series_dates()
        self.assertEqual(len(dates), 12)
        self.assertIsNotNone(report.get_time_series_field_verbose_name(TotalReportField, dates[0], 0, dates))

        dates = report._get_time_series_dates("daily")
        self.assertEqual(len(dates), 365, len(dates))
        self.assertIsNotNone(report.get_time_series_field_verbose_name(TotalReportField, dates[0], 0, dates, "daily"))

        dates = report._get_time_series_dates("weekly")
        self.assertEqual(len(dates), 53, len(dates))
        self.assertIsNotNone(report.get_time_series_field_verbose_name(TotalReportField, dates[0], 0, dates, "weekly"))

        dates = report._get_time_series_dates("bi-weekly")
        self.assertEqual(len(dates), 27, len(dates))
        self.assertIsNotNone(
            report.get_time_series_field_verbose_name(TotalReportField, dates[0], 0, dates, "semimonthly")
        )

        dates = report._get_time_series_dates("quarterly")
        self.assertEqual(len(dates), 4, len(dates))

        dates = report._get_time_series_dates("semiannually")
        self.assertEqual(len(dates), 2, len(dates))
        dates = report._get_time_series_dates("annually")
        self.assertEqual(len(dates), 1, len(dates))
        self.assertIsNotNone(report.get_time_series_field_verbose_name(TotalReportField, dates[0], 0, dates))

        def not_known_pattern():
            report._get_time_series_dates("each_spring")

        self.assertRaises(Exception, not_known_pattern)

    def test_time_series_custom_pattern(self):
        # report = ReportGenerator(OrderLine, date_field='order__date_placed', group_by='client',
        #                          columns=['name', '__time_series__'],
        #                          time_series_columns=['__total_quantity__'], time_series_pattern='monthly',
        #                          start_date=datetime(2020, 1, 1, tzinfo=pytz.timezone('utc')),
        #                          end_date=datetime(2020, 12, 31, tzinfo=pytz.timezone('utc')))
        report = TimeSeriesCustomDates()
        dates = report._get_time_series_dates()
        self.assertEqual(len(dates), 3, dates)

    def test_time_series_columns_placeholder(self):
        x = ReportGenerator(
            OrderLine,
            date_field="order__date_placed",
            group_by="client",
            columns=["name"],
            time_series_columns=["__total_quantity__"],
            time_series_pattern="monthly",
            start_date=datetime(2020, 1, 1),
            end_date=datetime(2020, 12, 31),
        )
        self.assertEqual(len(x.get_list_display_columns()), 13)

    def test_time_series_and_cros_tab(self):
        pass

    def test_attr_as_column(self):
        report = GeneratorWithAttrAsColumn()
        columns_data = report.get_list_display_columns()
        self.assertEqual(len(columns_data), 3)
        self.assertEqual(columns_data[0]["verbose_name"], "My Verbose Name")

    def test_improper_group_by(self):
        def load():
            ReportGenerator(OrderLine, group_by="no_field", date_field="order__date_placed")

        self.assertRaises(Exception, load)

    def test_missing_report_model(self):
        def load():
            ReportGenerator(report_model=None, group_by="product", date_field="order__date_placed")

        self.assertRaises(Exception, load)

    def test_missing_date_field(self):
        def load():
            ReportGenerator(report_model=OrderLine, group_by="product", date_field="", time_series_pattern="monthly")

        self.assertRaises(Exception, load)

    def test_wrong_date_field(self):
        def load():
            ReportGenerator(report_model=OrderLine, group_by="product", date_field="not_here")

        self.assertRaises(Exception, load)

    def test_unknown_column(self):
        def load():
            ReportGenerator(
                report_model=OrderLine,
                group_by="product",
                date_field="order__date_placed",
                columns=["product", "not_here"],
            )

        self.assertRaises(Exception, load)

    def test_gather_dependencies_for_time_series(self):
        report = ReportGenerator(
            report_model=SimpleSales,
            group_by="client",
            columns=["slug", "name"],
            time_series_pattern="monthly",
            date_field="doc_date",
            time_series_columns=["__debit__", "__credit__", "__balance__", "__total__"],
        )

        self.assertTrue(report._report_fields_dependencies)

    def test_group_by_traverse(self):
        report = ReportGenerator(
            report_model=SimpleSales,
            group_by="product__category",
            columns=[
                "product__category",
                ComputationField.create(Sum, "value"),
                "__total__",
            ],
            # time_series_pattern='monthly',
            date_field="doc_date",
            # time_series_columns=['__debit__', '__credit__', '__balance__', '__total__']
        )

        self.assertTrue(report._report_fields_dependencies)
        data = report.get_report_data()
        self.assertNotEqual(data, [])
        self.assertEqual(data[0]["product__category"], "small")
        self.assertEqual(data[1]["product__category"], "big")

    def test_group_by_and_foreign_key_field(self):
        report = ReportGenerator(
            report_model=SimpleSales,
            group_by="client",
            columns=[
                "name",
                "contact_id",
                "contact__address",
                ComputationField.create(Sum, "value"),
                "__total__",
            ],
            # time_series_pattern='monthly',
            date_field="doc_date",
            # time_series_columns=['__debit__', '__credit__', '__balance__', '__total__']
        )

        self.assertTrue(report._report_fields_dependencies)
        data = report.get_report_data()
        # import pdb;
        # pdb.set_trace()
        self.assertNotEqual(data, [])
        self.assertEqual(data[0]["name"], "Client 1")
        self.assertEqual(data[1]["name"], "Client 2")
        self.assertEqual(data[2]["name"], "Client 3")

        self.assertEqual(data[0]["contact_id"], 1)
        self.assertEqual(data[1]["contact_id"], 2)
        self.assertEqual(data[2]["contact_id"], 3)

        self.assertEqual(data[0]["sum__value"], 300)

        self.assertEqual(Client.objects.get(pk=1).contact.address, "Street 1")
        self.assertEqual(data[0]["contact__address"], "Street 1")
        self.assertEqual(data[1]["contact__address"], "Street 2")
        self.assertEqual(data[2]["contact__address"], "Street 3")

    def test_custom_group_by(self):
        report = ReportGenerator(
            report_model=SimpleSales,
            group_by_custom_querysets=[
                SimpleSales.objects.filter(client_id__in=[self.client1.pk, self.client2.pk]),
                SimpleSales.objects.filter(client_id__in=[self.client3.pk]),
            ],
            group_by_custom_querysets_column_verbose_name="Custom Title",
            columns=[
                # "__index__", is added automatically
                ComputationField.create(Sum, "value"),
                "__total__",
            ],
            date_field="doc_date",
        )
        data = report.get_report_data()
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]["sum__value"], 900)
        self.assertEqual(data[1]["sum__value"], 1200)
        self.assertIn("__index__", data[0].keys())
        columns_data = report.get_columns_data()
        self.assertEqual(columns_data[0]["verbose_name"], "Custom Title")

    def test_custom_group_by_with_index(self):
        report = ReportGenerator(
            report_model=SimpleSales,
            group_by_custom_querysets=[
                SimpleSales.objects.filter(client_id__in=[self.client1.pk, self.client2.pk]),
                SimpleSales.objects.filter(client_id__in=[self.client3.pk]),
            ],
            columns=[
                "__index__",  # assert that no issue if added manually , issue 68
                ComputationField.create(Sum, "value"),
                "__total__",
            ],
            date_field="doc_date",
        )

        data = report.get_report_data()
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]["sum__value"], 900)
        self.assertEqual(data[1]["sum__value"], 1200)
        self.assertIn("__index__", data[0].keys())

    def test_traversing_group_by_and_foreign_key_field(self):
        report = ReportGenerator(
            report_model=SimpleSales,
            group_by="client__contact",
            columns=[
                "po_box",
                "address",
                "agent__name",
                ComputationField.create(Sum, "value"),
                "__total__",
            ],
            date_field="doc_date",
        )

        self.assertTrue(report._report_fields_dependencies)
        data = report.get_report_data()
        self.assertNotEqual(data, [])
        # self.assertTrue(False)
        self.assertEqual(data[0]["address"], "Street 1")
        self.assertEqual(data[1]["address"], "Street 2")
        self.assertEqual(data[1]["agent__name"], "John")
        self.assertEqual(data[2]["agent__name"], "Frank")

    def test_traversing_group_by_sanity(self):
        report = ReportGenerator(
            report_model=SimpleSales,
            group_by="client__contact__agent",
            columns=["name", ComputationField.create(Sum, "value"), "__total__"],
            date_field="doc_date",
        )

        self.assertTrue(report._report_fields_dependencies)
        data = report.get_report_data()
        self.assertNotEqual(data, [])
        self.assertEqual(len(data), 2)

    def test_db_field_column_verbose_name(self):
        report = GenericGenerator()
        field_list = report.get_list_display_columns()
        self.assertEqual(field_list[0]["verbose_name"], "Client Slug")

    def test_group_by_char_field(self):
        report = GroupByCharField()
        self.assertEqual(len(report.get_list_display_columns()), 3)


# test that columns are a straight forward list
class TestReportFields(BaseTestData, TestCase):
    def test_get_full_dependency_list(self):
        from slick_reporting.fields import BalanceReportField

        deps = BalanceReportField.get_full_dependency_list()
        self.assertEqual(len(deps), 1)

    def test_computation_field_count(self):
        # test case for issue #77
        report = TestCountField()
        data = report.get_report_data()
        self.assertEqual(data[0]["count__id"], 5)
        self.assertEqual(data[1]["count__id"], 1)


class TestHelpers(TestCase):
    def test_get_model_for_keys(self):
        keys = get_foreign_keys(OrderLine)
        self.assertEqual(len(keys), 3)


class TestListViewGenerator(BaseTestData, TestCase):
    def test_traversing_field_in_column(self):
        report = ListViewReportGenerator(
            report_model=SimpleSales,
            columns=["id", "product__name", "client__name", "value"],
            date_field="doc_date",
        )
        data = report.get_report_data()
        self.assertEqual(len(data), SimpleSales.objects.count())
        self.assertEqual(data[0]["product__name"], "Product 1")
        self.assertEqual(data[0]["client__name"], "Client 1")


class NumberFormatTests(BaseTestData, TestCase):
    """
    Tests for the number_format feature.

    The feature adds display-only number formatting to datatable columns.
    Raw numeric values are kept in the JSON response so DataTables sorting
    and footer summation continue to work; formatting is applied by a JS
    render callback driven by a ``number_format`` dict that ``get_columns_data()``
    attaches to every ``type="number"`` column.

    Global default lives in ``SLICK_REPORTING_SETTINGS["NUMBER_FORMAT"]``.
    Per-field overrides are set via ``ComputationField.create(..., number_format={})``;
    they are merged with (not replace) the global, so only the specified keys change.
    """

    # Both fields are created at class level so each test re-uses the same objects.
    # ``field_plain`` has no override → resolved format equals the global default.
    # ``field_overridden`` sets decimal_places=0 → that key overrides the global,
    #   all other keys (use_locale, thousands_separator) are still inherited.
    field_plain = ComputationField.create(Sum, "value", name="nf_plain")
    field_overridden = ComputationField.create(Sum, "value", name="nf_overridden", number_format={"decimal_places": 0})

    def _make_report(self, columns, **kwargs):
        return ReportGenerator(
            report_model=SimpleSales,
            date_field="doc_date",
            group_by="client",
            columns=columns,
            **kwargs,
        )

    def _assert_fully_resolved_format(self, cols_data):
        """
        Assert that every type='number' column in cols_data carries a fully-resolved
        number_format dict — i.e. all three keys are present after global/field merge.

        Expected shape: {"decimal_places": int, "use_locale": bool, "thousands_separator": str}
        """
        numeric = [c for c in cols_data if c.get("type") == "number"]
        self.assertTrue(numeric, "No numeric columns found in columns_data")
        for col in numeric:
            with self.subTest(col=col["name"]):
                fmt = col.get("number_format", {})
                self.assertIn("decimal_places", fmt)
                self.assertIn("use_locale", fmt)
                self.assertIn("thousands_separator", fmt)

    # --- ComputationField ---

    def test_create_number_format(self):
        """
        ComputationField.create() stores number_format on the generated class.

        - When number_format is passed, it is stored verbatim on the class attribute.
        - When omitted, the attribute is None (signals "use global default").
        - The default type is "number", which is what the JS render gate checks.
        """
        with self.subTest("stored when given"):
            # field_overridden was created with number_format={"decimal_places": 0}
            self.assertEqual(self.field_overridden.number_format, {"decimal_places": 0})
        with self.subTest("None when omitted"):
            # field_plain was created without number_format → None means "use global"
            self.assertIsNone(self.field_plain.number_format)
        with self.subTest("default type is number"):
            # JS render callback fires only when column type == "number"
            self.assertEqual(ComputationField.type, "number")

    # --- regular group-by ---

    def test_group_by_columns_data(self):
        """
        get_columns_data() emits number_format on numeric columns only, with correct merge.

        Expected for field_plain (no override):
            {"decimal_places": 2, "use_locale": True, "thousands_separator": ","}  ← global default

        Expected for field_overridden (decimal_places=0):
            {"decimal_places": 0, "use_locale": True, "thousands_separator": ","}  ← merged

        The "name" text column must NOT receive a number_format key.
        """
        report = self._make_report(["name", self.field_plain, self.field_overridden])
        cols = {c["name"]: c for c in report.get_columns_data()}

        with self.subTest("numeric gets number_format, text does not"):
            self.assertIn("number_format", cols[self.field_plain.name])
            self.assertNotIn("number_format", cols["name"])  # "name" is a text column

        with self.subTest("global default has all keys"):
            # field_plain has no override → all three keys come from the global default
            self._assert_fully_resolved_format(list(cols.values()))

        with self.subTest("per-field decimal_places overrides global"):
            # field_overridden sets decimal_places=0; use_locale and thousands_separator
            # are inherited from the global and must still be present
            self.assertEqual(cols[self.field_overridden.name]["number_format"]["decimal_places"], 0)

    # --- settings override ---

    def test_global_settings_override(self):
        """
        SLICK_REPORTING_SETTINGS["NUMBER_FORMAT"] is deep-merged with the built-in default.

        User only has to specify the keys they want to change; omitted keys keep their
        default values.  E.g. setting just decimal_places=4 leaves use_locale untouched.

        Expected resolved format with {"decimal_places": 4}:
            {"decimal_places": 4, "use_locale": True, "thousands_separator": ","}
        """
        with override_settings(SLICK_REPORTING_SETTINGS={"NUMBER_FORMAT": {"decimal_places": 4}}):
            from slick_reporting.app_settings import get_slick_reporting_settings
            resolved = get_slick_reporting_settings()
            with self.subTest("override applied"):
                self.assertEqual(resolved["NUMBER_FORMAT"]["decimal_places"], 4)
            with self.subTest("other keys fall back to defaults"):
                # use_locale was not overridden → must still be present from the built-in default
                self.assertIn("use_locale", resolved["NUMBER_FORMAT"])

    # --- time-series ---

    def test_time_series_columns_data(self):
        """
        Time-series columns carry both ``type`` and ``number_format`` in get_columns_data().

        Time-series columns are named  "<field_name>TS<YYYYMMDD>" (e.g. "nf_plainTS20200131").
        They were previously missing the ``type`` key, which would silently skip formatting.

        Expected: each TS column has type="number" and a fully-resolved number_format dict.
        """
        report = ReportGenerator(
            report_model=SimpleSales,
            date_field="doc_date",
            group_by="client",
            columns=["name", "__time_series__"],
            time_series_columns=[self.field_plain],
            time_series_pattern="monthly",
            start_date=datetime(2020, 1, 1),
            end_date=datetime(2020, 3, 31),  # 3 monthly columns
        )
        with self.subTest("parsed columns have type key"):
            # get_time_series_parsed_columns() is the internal source; type must be present
            # before get_columns_data() can forward it to the frontend
            for col in report.get_time_series_parsed_columns():
                self.assertIn("type", col)
        with self.subTest("columns_data has number_format for TS columns"):
            ts_cols = [c for c in report.get_columns_data() if "TS" in c["name"]]
            self._assert_fully_resolved_format(ts_cols)

    # --- crosstab ---

    def test_crosstab_columns_data(self):
        """
        Crosstab columns carry both ``type`` and ``number_format`` in get_columns_data().

        Crosstab columns are named "<field_name>CT<id>" (e.g. "value__sumCT1").
        Like time-series, they were previously missing the ``type`` key.

        Expected: each CT column has type="number" and a fully-resolved number_format dict.
        """
        report = CrosstabOnClient(crosstab_ids=[self.client1.pk], crosstab_compute_remainder=False)
        with self.subTest("parsed columns have type key"):
            # get_crosstab_parsed_columns() is the internal source for crosstab column metadata
            for col in report.get_crosstab_parsed_columns():
                self.assertIn("type", col)
        with self.subTest("columns_data has number_format for CT columns"):
            ct_cols = [c for c in report.get_columns_data() if "CT" in c["name"]]
            self._assert_fully_resolved_format(ct_cols)

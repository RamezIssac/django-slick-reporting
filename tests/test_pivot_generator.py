import datetime

from django.db import connection
from django.test import TestCase

from slick_reporting.dynamic_model import get_dynamic_model, _model_cache
from slick_reporting.generator import ReportGenerator
from tests.models import Agent, Client, Contact, Product, SimpleSales

TABLE_NAME = "test_pivot_monthly_sales"

CREATE_TABLE_SQL = f"""
    CREATE TABLE {TABLE_NAME} (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER NOT NULL,
        product_name VARCHAR(100) NOT NULL,
        region VARCHAR(100) NOT NULL,
        month DATE NOT NULL,
        total_sales DECIMAL(10, 2) NOT NULL DEFAULT 0,
        total_quantity INTEGER NOT NULL DEFAULT 0
    )
"""

INSERT_SQL = f"""
    INSERT INTO {TABLE_NAME} (product_id, product_name, region, month, total_sales, total_quantity)
    VALUES (?, ?, ?, ?, ?, ?)
"""


class PrecomputedCrosstabTestBase(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        with connection.cursor() as cursor:
            cursor.execute(CREATE_TABLE_SQL)
            rows = [
                (1, "Product A", "North", "2024-01-01", 500, 10),
                (1, "Product A", "North", "2024-02-01", 600, 12),
                (1, "Product A", "North", "2024-03-01", 550, 11),
                (2, "Product B", "South", "2024-01-01", 300, 5),
                (2, "Product B", "South", "2024-02-01", 400, 8),
                # Product B has no March data — tests missing period
            ]
            cursor.executemany(INSERT_SQL, rows)

    @classmethod
    def tearDownClass(cls):
        with connection.cursor() as cursor:
            cursor.execute(f"DROP TABLE IF EXISTS {TABLE_NAME}")
        keys_to_remove = [k for k in _model_cache if k.endswith(f":{TABLE_NAME}")]
        for k in keys_to_remove:
            del _model_cache[k]
        from django.apps import apps

        model_key = TABLE_NAME.replace("_", "").lower()
        try:
            del apps.all_models["slick_reporting"][model_key]
        except KeyError:
            pass
        super().tearDownClass()


class TestPrecomputedCrosstabBasic(PrecomputedCrosstabTestBase):
    def test_date_crosstab(self):
        model = get_dynamic_model(TABLE_NAME)
        report = ReportGenerator(
            report_model=model,
            group_by="product_id",
            date_field="month",
            crosstab_field="month",
            crosstab_columns=["total_sales", "total_quantity"],
            crosstab_precomputed=True,
            columns=["product_id", "__crosstab__"],
            start_date=datetime.datetime(2024, 1, 1),
            end_date=datetime.datetime(2024, 12, 31),
        )
        data = report.get_report_data()
        self.assertEqual(len(data), 2)

        # Find Product A (id=1)
        prod_a = next(row for row in data if row["product_id"] == 1)
        # Should have sales for all 3 months
        self.assertEqual(prod_a["total_salesCT2024_01_01"], 500)
        self.assertEqual(prod_a["total_salesCT2024_02_01"], 600)
        self.assertEqual(prod_a["total_salesCT2024_03_01"], 550)
        self.assertEqual(prod_a["total_quantityCT2024_01_01"], 10)

    def test_missing_period_defaults_to_zero(self):
        model = get_dynamic_model(TABLE_NAME)
        report = ReportGenerator(
            report_model=model,
            group_by="product_id",
            date_field="month",
            crosstab_field="month",
            crosstab_columns=["total_sales"],
            crosstab_precomputed=True,
            columns=["product_id", "__crosstab__"],
            start_date=datetime.datetime(2024, 1, 1),
            end_date=datetime.datetime(2024, 12, 31),
        )
        data = report.get_report_data()
        prod_b = next(row for row in data if row["product_id"] == 2)
        # Product B has no March data
        self.assertEqual(prod_b["total_salesCT2024_03_01"], 0)

    def test_entity_crosstab(self):
        """Crosstab on a non-date field (region).
        Note: precomputed crosstab reads pre-computed data, it does NOT aggregate.
        When multiple rows exist for the same (group, crosstab_value),
        the last row encountered wins.
        """
        model = get_dynamic_model(TABLE_NAME)
        report = ReportGenerator(
            report_model=model,
            group_by="product_id",
            crosstab_field="region",
            crosstab_columns=["total_sales"],
            crosstab_precomputed=True,
            columns=["product_id", "__crosstab__"],
            start_date=datetime.datetime(2024, 1, 1),
            end_date=datetime.datetime(2024, 12, 31),
        )
        data = report.get_report_data()
        self.assertEqual(len(data), 2)

        prod_a = next(row for row in data if row["product_id"] == 1)
        # Product A has multiple rows in "North" — last one wins
        self.assertIn("total_salesCTNorth", prod_a)
        self.assertGreater(prod_a["total_salesCTNorth"], 0)

    def test_multiple_crosstab_columns(self):
        model = get_dynamic_model(TABLE_NAME)
        report = ReportGenerator(
            report_model=model,
            group_by="product_id",
            date_field="month",
            crosstab_field="month",
            crosstab_columns=["total_sales", "total_quantity"],
            crosstab_precomputed=True,
            columns=["product_id", "__crosstab__"],
            start_date=datetime.datetime(2024, 1, 1),
            end_date=datetime.datetime(2024, 12, 31),
        )
        columns_data = report.get_columns_data()
        col_names = [c["name"] for c in columns_data]
        # Should have both total_sales and total_quantity for each month
        self.assertIn("total_salesCT2024_01_01", col_names)
        self.assertIn("total_quantityCT2024_01_01", col_names)
        self.assertIn("total_salesCT2024_02_01", col_names)
        self.assertIn("total_quantityCT2024_02_01", col_names)


class TestPrecomputedCrosstabMetadata(PrecomputedCrosstabTestBase):
    def test_crosstab_metadata_populated(self):
        model = get_dynamic_model(TABLE_NAME)
        report = ReportGenerator(
            report_model=model,
            group_by="product_id",
            date_field="month",
            crosstab_field="month",
            crosstab_columns=["total_sales"],
            crosstab_precomputed=True,
            columns=["product_id", "__crosstab__"],
            start_date=datetime.datetime(2024, 1, 1),
            end_date=datetime.datetime(2024, 12, 31),
        )
        metadata = report.get_metadata()
        self.assertEqual(metadata["crosstab_model"], "month")
        self.assertTrue(len(metadata["crosstab_column_names"]) > 0)
        self.assertTrue(len(metadata["crosstab_column_verbose_names"]) > 0)
        # Time series should be empty
        self.assertFalse(metadata["time_series_pattern"])
        self.assertEqual(metadata["time_series_column_names"], [])

    def test_column_computation_field_attribute(self):
        """Chart JS uses computation_field to match data_source."""
        model = get_dynamic_model(TABLE_NAME)
        report = ReportGenerator(
            report_model=model,
            group_by="product_id",
            date_field="month",
            crosstab_field="month",
            crosstab_columns=["total_sales"],
            crosstab_precomputed=True,
            columns=["product_id", "__crosstab__"],
            start_date=datetime.datetime(2024, 1, 1),
            end_date=datetime.datetime(2024, 12, 31),
        )
        columns_data = report.get_columns_data()
        ct_cols = [c for c in columns_data if "CT" in c["name"]]
        for col in ct_cols:
            self.assertEqual(col["computation_field"], "total_sales")


class TestPrecomputedCrosstabWithTableName(PrecomputedCrosstabTestBase):
    def test_table_name_convenience(self):
        report = ReportGenerator(
            table_name=TABLE_NAME,
            group_by="product_id",
            date_field="month",
            crosstab_field="month",
            crosstab_columns=["total_sales"],
            crosstab_precomputed=True,
            columns=["product_id", "__crosstab__"],
            start_date=datetime.datetime(2024, 1, 1),
            end_date=datetime.datetime(2024, 12, 31),
        )
        data = report.get_report_data()
        self.assertEqual(len(data), 2)


class TestPrecomputedCrosstabDateFiltering(PrecomputedCrosstabTestBase):
    def test_date_filter_limits_crosstab_values(self):
        model = get_dynamic_model(TABLE_NAME)
        report = ReportGenerator(
            report_model=model,
            group_by="product_id",
            date_field="month",
            crosstab_field="month",
            crosstab_columns=["total_sales"],
            crosstab_precomputed=True,
            columns=["product_id", "__crosstab__"],
            start_date=datetime.datetime(2024, 1, 1),
            end_date=datetime.datetime(2024, 2, 1),
        )
        report.get_report_data()
        columns_data = report.get_columns_data()
        ct_col_names = [c["name"] for c in columns_data if "CT" in c["name"]]
        # Should only have January (end_date filter is __lte so Feb 1 is included)
        self.assertTrue(all("2024_03_01" not in n for n in ct_col_names))


SPACES_TABLE = "test_pivot_spaces"

CREATE_SPACES_TABLE_SQL = f"""
    CREATE TABLE {SPACES_TABLE} (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER NOT NULL,
        city VARCHAR(100) NOT NULL,
        total_sales DECIMAL(10, 2) NOT NULL DEFAULT 0
    )
"""

INSERT_SPACES_SQL = f"""
    INSERT INTO {SPACES_TABLE} (product_id, city, total_sales) VALUES (?, ?, ?)
"""


class TestPrecomputedCrosstabWithSpaces(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        with connection.cursor() as cursor:
            cursor.execute(CREATE_SPACES_TABLE_SQL)
            rows = [
                (1, "New York", 500),
                (1, "Los Angeles", 300),
                (2, "New York", 200),
                (2, "Los Angeles", 400),
                (1, "Q1/2024", 100),
            ]
            cursor.executemany(INSERT_SPACES_SQL, rows)

    @classmethod
    def tearDownClass(cls):
        with connection.cursor() as cursor:
            cursor.execute(f"DROP TABLE IF EXISTS {SPACES_TABLE}")
        keys_to_remove = [k for k in _model_cache if k.endswith(f":{SPACES_TABLE}")]
        for k in keys_to_remove:
            del _model_cache[k]
        from django.apps import apps

        model_key = SPACES_TABLE.replace("_", "").lower()
        try:
            del apps.all_models["slick_reporting"][model_key]
        except KeyError:
            pass
        super().tearDownClass()

    def test_crosstab_values_with_spaces(self):
        model = get_dynamic_model(SPACES_TABLE)
        report = ReportGenerator(
            report_model=model,
            group_by="product_id",
            crosstab_field="city",
            crosstab_columns=["total_sales"],
            crosstab_precomputed=True,
            columns=["product_id", "__crosstab__"],
        )
        data = report.get_report_data()
        prod_1 = next(row for row in data if row["product_id"] == 1)

        # Spaces sanitized to underscores in column names
        self.assertEqual(prod_1["total_salesCTNew_York"], 500)
        self.assertEqual(prod_1["total_salesCTLos_Angeles"], 300)

    def test_crosstab_values_with_special_chars(self):
        model = get_dynamic_model(SPACES_TABLE)
        report = ReportGenerator(
            report_model=model,
            group_by="product_id",
            crosstab_field="city",
            crosstab_columns=["total_sales"],
            crosstab_precomputed=True,
            columns=["product_id", "__crosstab__"],
        )
        data = report.get_report_data()
        prod_1 = next(row for row in data if row["product_id"] == 1)

        # Slash sanitized to underscore
        self.assertEqual(prod_1["total_salesCTQ1_2024"], 100)

    def test_verbose_name_preserves_original(self):
        model = get_dynamic_model(SPACES_TABLE)
        report = ReportGenerator(
            report_model=model,
            group_by="product_id",
            crosstab_field="city",
            crosstab_columns=["total_sales"],
            crosstab_precomputed=True,
            columns=["product_id", "__crosstab__"],
        )
        columns_data = report.get_columns_data()
        ny_col = next(c for c in columns_data if "New_York" in c["name"])
        self.assertIn("New York", ny_col["verbose_name"])


class TestPrecomputedCrosstabWithFKGroupBy(TestCase):
    """Regression: precomputed crosstab with a ForeignKey group_by returned empty rows.

    prepare_queryset returned .values("product_id") so each obj was {"product_id": N}.
    _get_record_data then looked up obj["id"] (the related model PK) which was missing,
    causing group_by_val="None" and every precomputed lookup to return 0.

    Fix: mirror the non-precomputed FK path and fetch related-model objects so obj["id"]
    and obj["name"] are available.
    """

    @classmethod
    def setUpTestData(cls):
        agent = Agent.objects.create(name="Agent FK")
        contact = Contact.objects.create(address="Addr", agent=agent)
        cls.product1 = Product.objects.create(name="Prod FK 1", category="small", sku="fk1", notes="", slug="fk1")
        cls.product2 = Product.objects.create(name="Prod FK 2", category="medium", sku="fk2", notes="", slug="fk2")
        cls.client1 = Client.objects.create(name="Cli FK 1", notes="", slug="cfk1")
        cls.client1.contact = contact
        cls.client1.save()
        cls.client2 = Client.objects.create(name="Cli FK 2", notes="", slug="cfk2")
        cls.client2.contact = contact
        cls.client2.save()
        SimpleSales.objects.create(
            slug="s1", doc_date=datetime.datetime(2024, 1, 15), client=cls.client1,
            product=cls.product1, quantity=5, price=100, created_at=datetime.datetime(2024, 1, 15),
        )
        SimpleSales.objects.create(
            slug="s2", doc_date=datetime.datetime(2024, 2, 15), client=cls.client2,
            product=cls.product2, quantity=3, price=200, created_at=datetime.datetime(2024, 2, 15),
        )

    def test_rows_populated_with_fk_group_by(self):
        report = ReportGenerator(
            report_model=SimpleSales,
            group_by="product",
            date_field="doc_date",
            crosstab_field="client",
            crosstab_columns=["value"],
            crosstab_precomputed=True,
            columns=["name", "__crosstab__"],
            start_date=datetime.datetime(2024, 1, 1),
            end_date=datetime.datetime(2024, 12, 31),
        )
        data = report.get_report_data()

        self.assertEqual(len(data), 2, "Expected one row per product")

        names = {row["name"] for row in data}
        self.assertEqual(names, {"Prod FK 1", "Prod FK 2"}, "Product names must be populated (not empty strings)")

        prod1_row = next(row for row in data if row["name"] == "Prod FK 1")
        client1_col = f"valueCT{self.client1.pk}"
        self.assertEqual(
            prod1_row[client1_col], 500,
            "Prod FK 1 / Client 1 value should be 500 (5 * 100); was 0 before the fix",
        )

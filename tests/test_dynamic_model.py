import datetime

from django.db import connection, models
from django.db.models import Sum, Count
from django.test import TestCase

from slick_reporting.dynamic_model import get_dynamic_model, _model_cache
from slick_reporting.fields import ComputationField
from slick_reporting.generator import ReportGenerator


TABLE_NAME = "test_dynamic_sales"

CREATE_TABLE_SQL = f"""
    CREATE TABLE {TABLE_NAME} (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_name VARCHAR(100) NOT NULL,
        client_name VARCHAR(100),
        doc_date DATE NOT NULL,
        quantity INTEGER NOT NULL DEFAULT 0,
        price DECIMAL(10, 2) NOT NULL DEFAULT 0,
        value DECIMAL(10, 2) NOT NULL DEFAULT 0
    )
"""

INSERT_SQL = f"""
    INSERT INTO {TABLE_NAME} (product_name, client_name, doc_date, quantity, price, value)
    VALUES (?, ?, ?, ?, ?, ?)
"""


class DynamicModelTestBase(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        with connection.cursor() as cursor:
            cursor.execute(CREATE_TABLE_SQL)
            rows = [
                ("Product A", "Client 1", "2024-01-15", 10, 5.00, 50.00),
                ("Product A", "Client 1", "2024-02-15", 5, 5.00, 25.00),
                ("Product A", "Client 2", "2024-01-20", 3, 5.00, 15.00),
                ("Product B", "Client 1", "2024-01-10", 7, 10.00, 70.00),
                ("Product B", "Client 2", "2024-02-10", 2, 10.00, 20.00),
                ("Product C", "Client 2", "2024-03-01", 1, 20.00, 20.00),
            ]
            cursor.executemany(INSERT_SQL, rows)

    @classmethod
    def tearDownClass(cls):
        with connection.cursor() as cursor:
            cursor.execute(f"DROP TABLE IF EXISTS {TABLE_NAME}")
        # Clean up model cache and app registry
        keys_to_remove = [k for k in _model_cache if k.endswith(f":{TABLE_NAME}")]
        for k in keys_to_remove:
            del _model_cache[k]
        from django.apps import apps

        try:
            del apps.all_models["slick_reporting"]["testdynamicsales"]
        except KeyError:
            pass
        super().tearDownClass()


class TestGetDynamicModel(DynamicModelTestBase):
    def test_returns_model_class(self):
        model = get_dynamic_model(TABLE_NAME)
        self.assertTrue(issubclass(model, models.Model))

    def test_model_meta(self):
        model = get_dynamic_model(TABLE_NAME)
        self.assertEqual(model._meta.db_table, TABLE_NAME)
        self.assertFalse(model._meta.managed)

    def test_model_fields(self):
        model = get_dynamic_model(TABLE_NAME)
        field_names = {f.name for f in model._meta.get_fields()}
        self.assertIn("id", field_names)
        self.assertIn("product_name", field_names)
        self.assertIn("client_name", field_names)
        self.assertIn("doc_date", field_names)
        self.assertIn("quantity", field_names)
        self.assertIn("price", field_names)
        self.assertIn("value", field_names)

    def test_pk_field(self):
        model = get_dynamic_model(TABLE_NAME)
        pk_field = model._meta.pk
        self.assertIsNotNone(pk_field)
        self.assertEqual(pk_field.name, "id")

    def test_cache_returns_same_model(self):
        model1 = get_dynamic_model(TABLE_NAME)
        model2 = get_dynamic_model(TABLE_NAME)
        self.assertIs(model1, model2)

    def test_nonexistent_table_raises(self):
        with self.assertRaises(ValueError) as cm:
            get_dynamic_model("nonexistent_table_xyz")
        self.assertIn("nonexistent_table_xyz", str(cm.exception))


class TestDynamicModelQuerySet(DynamicModelTestBase):
    def test_objects_all(self):
        model = get_dynamic_model(TABLE_NAME)
        qs = model.objects.all()
        self.assertEqual(qs.count(), 6)

    def test_filter(self):
        model = get_dynamic_model(TABLE_NAME)
        qs = model.objects.filter(product_name="Product A")
        self.assertEqual(qs.count(), 3)

    def test_values(self):
        model = get_dynamic_model(TABLE_NAME)
        products = list(
            model.objects.values("product_name").distinct().order_by("product_name")
        )
        self.assertEqual(len(products), 3)
        self.assertEqual(products[0]["product_name"], "Product A")

    def test_aggregate(self):
        model = get_dynamic_model(TABLE_NAME)
        result = model.objects.aggregate(total=Sum("value"))
        self.assertEqual(result["total"], 200.00)

    def test_annotate(self):
        model = get_dynamic_model(TABLE_NAME)
        result = list(
            model.objects.values("product_name")
            .annotate(total_value=Sum("value"))
            .order_by("product_name")
        )
        self.assertEqual(result[0]["product_name"], "Product A")
        self.assertEqual(result[0]["total_value"], 90.00)


class TestReportGeneratorWithDynamicModel(DynamicModelTestBase):
    def test_group_by_report(self):
        model = get_dynamic_model(TABLE_NAME)
        report = ReportGenerator(
            report_model=model,
            group_by="product_name",
            date_field="doc_date",
            columns=[
                "product_name",
                ComputationField.create(Sum, "value", name="value__sum", verbose_name="Total Value"),
            ],
            start_date=datetime.datetime(2024, 1, 1),
            end_date=datetime.datetime(2024, 12, 31),
        )
        data = report.get_report_data()
        self.assertEqual(len(data), 3)
        values_by_product = {row["product_name"]: row["value__sum"] for row in data}
        self.assertEqual(values_by_product["Product A"], 90.00)
        self.assertEqual(values_by_product["Product B"], 90.00)
        self.assertEqual(values_by_product["Product C"], 20.00)

    def test_time_series_report(self):
        model = get_dynamic_model(TABLE_NAME)
        report = ReportGenerator(
            report_model=model,
            group_by="product_name",
            date_field="doc_date",
            columns=["product_name", "__time_series__"],
            time_series_pattern="monthly",
            time_series_columns=[
                ComputationField.create(Sum, "value", name="ts_value", verbose_name="Value"),
            ],
            start_date=datetime.datetime(2024, 1, 1),
            end_date=datetime.datetime(2024, 3, 31),
        )
        data = report.get_report_data()
        self.assertEqual(len(data), 3)

    def test_table_name_convenience_param(self):
        report = ReportGenerator(
            table_name=TABLE_NAME,
            group_by="product_name",
            date_field="doc_date",
            columns=[
                "product_name",
                ComputationField.create(Sum, "value", name="value__sum2", verbose_name="Total"),
            ],
            start_date=datetime.datetime(2024, 1, 1),
            end_date=datetime.datetime(2024, 12, 31),
        )
        data = report.get_report_data()
        self.assertEqual(len(data), 3)

    def test_no_group_by_report(self):
        model = get_dynamic_model(TABLE_NAME)
        report = ReportGenerator(
            report_model=model,
            group_by="",
            date_field="doc_date",
            columns=[
                ComputationField.create(Sum, "value", name="total_val", verbose_name="Total"),
            ],
            start_date=datetime.datetime(2024, 1, 1),
            end_date=datetime.datetime(2024, 12, 31),
        )
        data = report.get_report_data()
        self.assertEqual(data[0]["total_val"], 200.00)


class TestReportViewTableNameImportSafety(TestCase):
    """Defining a ReportView with table_name must not touch the DB at class-definition time."""

    def test_class_definition_does_not_hit_db(self):
        from slick_reporting.views import ReportView

        try:

            class _GhostTableReport(ReportView):
                table_name = "nonexistent_table_xyz"
                date_field = "doc_date"
                group_by = "product_name"
                columns = [
                    "product_name",
                    ComputationField.create(Sum, "value", name="v__sum", verbose_name="V"),
                ]

        except Exception as exc:
            self.fail(
                f"Defining a ReportView with table_name must not hit the DB at "
                f"class-definition time, but got: {type(exc).__name__}: {exc}"
            )

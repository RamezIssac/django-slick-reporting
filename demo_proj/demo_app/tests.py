import datetime

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase
from django.utils import timezone

from . import helpers
from .models import Client, MonthlySalesSummary, Product, ProductCategory, SalesTransaction

ALL_REPORTS = helpers.TUTORIAL + helpers.GROUP_BY + helpers.TIME_SERIES + helpers.CROSSTAB + helpers.PIVOT + helpers.OTHER


class DemoSanityTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = get_user_model().objects.create_superuser("admin", "admin@example.com", "password")
        category = ProductCategory.objects.create(name="Electronics")

        cls.p1 = Product.objects.create(name="Widget A", product_category=category, size="medium")
        cls.p2 = Product.objects.create(name="Widget B", product_category=category, size="big")
        cls.p3 = Product.objects.create(name="Widget C", product_category=category, size="small")

        cls.c1 = Client.objects.create(name="Client US", country="US")
        cls.c2 = Client.objects.create(name="Client DE", country="DE")
        cls.c3 = Client.objects.create(name="Client KW", country="KW")

        pairs = [
            (cls.p1, cls.c1), (cls.p2, cls.c2), (cls.p1, cls.c3),
            (cls.p3, cls.c1), (cls.p2, cls.c2), (cls.p3, cls.c3),
        ]
        for i, (product, client) in enumerate(pairs):
            SalesTransaction.objects.create(
                number=f"INV-{i + 1:04d}",
                date=timezone.make_aware(datetime.datetime(2024, (i % 12) + 1, 15)),
                client=client,
                product=product,
                quantity=10,
                price=100,
            )

        for product in [cls.p1, cls.p2, cls.p3]:
            for month in range(1, 4):
                MonthlySalesSummary.objects.create(
                    product=product,
                    month=datetime.date(2024, month, 1),
                    total_sales=1000,
                    total_quantity=10,
                )

        with connection.cursor() as cursor:
            for row in [
                ("Widget A", "US", 5000, 50),
                ("Widget B", "DE", 3000, 30),
                ("Widget C", "KW", 2000, 20),
            ]:
                cursor.execute(
                    "INSERT INTO regional_sales_summary (product_name, country, total_sales, total_quantity)"
                    " VALUES (%s, %s, %s, %s)",
                    row,
                )

    def setUp(self):
        self.client.force_login(self.superuser)

    def test_all_pages_load(self):
        for url in ["/", "/dashboard/"]:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

        for name, _ in ALL_REPORTS:
            with self.subTest(name=name):
                response = self.client.get(f"/{name}/")
                self.assertEqual(response.status_code, 200)

    def test_all_report_data_endpoints(self):
        for name, _ in ALL_REPORTS:
            with self.subTest(name=name):
                response = self.client.get(
                    f"/{name}/",
                    data={"start_date": "2024-01-01", "end_date": "2024-12-31"},
                    HTTP_X_REQUESTED_WITH="XMLHttpRequest",
                )
                self.assertEqual(response.status_code, 200)
                self.assertIn("data", response.json())

    def test_precomputed_crosstab_fk_group_by_returns_data(self):
        """Regression: precomputed crosstab with FK group_by was returning empty rows.

        The generator was building main_queryset as .values("product_id") so each obj
        only had {"product_id": N}. _get_record_data then looked up obj["id"] which was
        None, causing every group key to resolve to "None" and miss the precomputed dict.
        Fix: fetch the related model objects (same as non-precomputed FK path).
        """
        response = self.client.get(
            "/precomputed-monthly-sales/",
            data={"start_date": "2024-01-01", "end_date": "2024-12-31"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]

        self.assertEqual(len(data), 3, "Expected one row per product")
        product_names = {row["name"] for row in data}
        self.assertEqual(product_names, {"Widget A", "Widget B", "Widget C"})

        for row in data:
            crosstab_values = [v for k, v in row.items() if k not in ("name",) and v != ""]
            self.assertTrue(
                any(v not in (0, "0", None) for v in crosstab_values),
                f"All crosstab values are zero/empty for {row['name']} — group key lookup is broken",
            )

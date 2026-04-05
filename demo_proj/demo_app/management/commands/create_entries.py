import datetime
import random
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

# from expense.models import Expense, ExpenseTransaction
from ...models import Client, Product, SalesTransaction, ProductCategory, MonthlySalesSummary

User = get_user_model()


def date_range(start_date, end_date):
    for i in range((end_date - start_date).days + 1):
        yield start_date + timedelta(i)


class Command(BaseCommand):
    help = "Create Sample entries for the demo app"

    def handle(self, *args, **options):
        # create clients
        client_countries = [
            "US",
            "DE",
            "EG",
            "IN",
            "KW",
            "RA"
        ]
        product_category = [
            "extra_big",
            "big",
            "medium",
            "small",
            "extra-small"
        ]
        SalesTransaction.objects.all().delete()
        Client.objects.all().delete()
        Product.objects.all().delete()
        ProductCategory.objects.all().delete()
        User.objects.filter(is_superuser=False).delete()
        for i in range(10):
            User.objects.create_user(username=f"user {i}", password="password")

        list(User.objects.values_list("id", flat=True))
        for i in range(1, 4):
            ProductCategory.objects.create(name=f"Product Category {i}")

        product_category_ids = list(ProductCategory.objects.values_list("id", flat=True))
        for i in range(1, 10):
            Client.objects.create(name=f"Client {i}",
                                  country=random.choice(client_countries),
                                  # owner_id=random.choice(users_id)
                                  )
        clients_ids = list(Client.objects.values_list("pk", flat=True))
        # create products
        for i in range(1, 10):
            Product.objects.create(name=f"Product {i}",
                                   product_category_id=random.choice(product_category_ids),
                                   size=random.choice(product_category))
        products_ids = list(Product.objects.values_list("pk", flat=True))

        current_year = datetime.datetime.today().year
        start_date = datetime.datetime(current_year, 1, 1)
        end_date = datetime.datetime(current_year + 1, 1, 1)

        for date in date_range(start_date, end_date):
            for i in range(1, 10):
                SalesTransaction.objects.create(
                    client_id=random.choice(clients_ids),
                    product_id=random.choice(products_ids),
                    quantity=random.randint(1, 10),
                    price=random.randint(1, 100),
                    date=date,
                    number=f"Sale {date.strftime('%Y-%m-%d')} #{i}",
                )
                # ExpenseTransaction.objects.create(
                #     expense_id=random.choice(expense_ids),
                #     value=random.randint(1, 100),
                #     date=date,
                #     number=f"Expense {date.strftime('%Y-%m-%d')} #{i}",
                # )

        # Populate MonthlySalesSummary from the generated SalesTransaction data
        MonthlySalesSummary.objects.all().delete()
        from django.db.models.functions import TruncMonth
        from django.db.models import Sum

        monthly_data = (
            SalesTransaction.objects.annotate(month=TruncMonth("date"))
            .values("product_id", "month")
            .annotate(total_sales=Sum("value"), total_quantity=Sum("quantity"))
        )
        for row in monthly_data:
            MonthlySalesSummary.objects.create(
                product_id=row["product_id"],
                month=row["month"],
                total_sales=row["total_sales"],
                total_quantity=row["total_quantity"],
            )

        # Create a raw SQL table for the dynamic model demo
        from django.db import connection

        with connection.cursor() as cursor:
            cursor.execute("DROP TABLE IF EXISTS regional_sales_summary")
            cursor.execute("""
                CREATE TABLE regional_sales_summary (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_name VARCHAR(100) NOT NULL,
                    country VARCHAR(100) NOT NULL,
                    total_sales DECIMAL(12, 2) NOT NULL DEFAULT 0,
                    total_quantity DECIMAL(12, 2) NOT NULL DEFAULT 0
                )
            """)
            country_data = (
                SalesTransaction.objects
                .values("product__name", "client__country")
                .annotate(total_sales=Sum("value"), total_quantity=Sum("quantity"))
            )
            for row in country_data:
                cursor.execute(
                    "INSERT INTO regional_sales_summary (product_name, country, total_sales, total_quantity) "
                    "VALUES (%s, %s, %s, %s)",
                    [row["product__name"], row["client__country"], row["total_sales"], row["total_quantity"]],
                )

        self.stdout.write(self.style.SUCCESS("Entries Created Successfully"))

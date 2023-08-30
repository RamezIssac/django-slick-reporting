import datetime
import random
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

# from expense.models import Expense, ExpenseTransaction
from ...models import Client, Product, SalesTransaction, ProductCategory

User = get_user_model()


def date_range(start_date, end_date):
    for i in range((end_date - start_date).days + 1):
        yield start_date + timedelta(i)


class Command(BaseCommand):
    help = "Create Sample entries for the demo app"

    def handle(self, *args, **options):
        # create clients
        models_list = [
            Client,
            Product,
        ]
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

        users_id = list(User.objects.values_list("id", flat=True))
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

        self.stdout.write(self.style.SUCCESS("Entries Created Successfully"))

import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _


# Create your models here.
class Client(models.Model):
    name = models.CharField(max_length=100, verbose_name="Client Name")
    country = models.CharField(_("Country"), max_length=255, default="US")

    class Meta:
        verbose_name = _("Client")
        verbose_name_plural = _("Clients")

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=100, verbose_name="Product Name")
    category = models.CharField(max_length=100, verbose_name="Product Category", default="Medium")
    sku = models.CharField(_("SKU"), max_length=255, default=uuid.uuid4)


    class Meta:
        verbose_name = _("Product")
        verbose_name_plural = _("Products")

    def __str__(self):
        return self.name


class SalesTransaction(models.Model):
    number = models.CharField(max_length=100, verbose_name="Sales Transaction #")
    date = models.DateTimeField()
    notes = models.TextField(blank=True, null=True)
    client = models.ForeignKey(
        Client, on_delete=models.PROTECT, verbose_name=_("Client")
    )
    product = models.ForeignKey(
        Product, on_delete=models.PROTECT, verbose_name=_("Product")
    )
    value = models.DecimalField(max_digits=9, decimal_places=2)
    quantity = models.DecimalField(max_digits=9, decimal_places=2)
    price = models.DecimalField(max_digits=9, decimal_places=2)

    class Meta:
        verbose_name = _("Sales Transaction")
        verbose_name_plural = _("Sales Transactions")

    def __str__(self):
        return f"{self.number} - {self.date}"

    def save(
        self, force_insert=False, force_update=False, using=None, update_fields=None
    ):
        self.value = self.price * self.quantity
        super().save(force_insert, force_update, using, update_fields)


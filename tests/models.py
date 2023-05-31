from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models

from django.utils.translation import gettext_lazy as _


class Product(models.Model):
    CATEGORY_CHOICES = (
        ("tiny", "tiny"),
        ("small", "small"),
        ("medium", "medium"),
        ("big", "big"),
    )
    slug = models.CharField(max_length=200, verbose_name=_("Slug"))
    name = models.CharField(max_length=200, verbose_name=_("Name"))
    sku = models.CharField(max_length=200, default="", blank=True)
    category = models.CharField(max_length=10, choices=CATEGORY_CHOICES)
    notes = models.TextField()

    class Meta:
        verbose_name = _("Product")
        verbose_name_plural = _("Products")


class ProductCustomID(models.Model):
    CATEGORY_CHOICES = (
        ("tiny", "tiny"),
        ("small", "small"),
        ("medium", "medium"),
        ("big", "big"),
    )
    hash = models.AutoField(primary_key=True)
    slug = models.CharField(max_length=200, verbose_name=_("Slug"))
    name = models.CharField(max_length=200, verbose_name=_("Name"))
    sku = models.CharField(max_length=200, default="", blank=True)
    category = models.CharField(max_length=10, choices=CATEGORY_CHOICES)
    notes = models.TextField()

    class Meta:
        verbose_name = _("Product")
        verbose_name_plural = _("Products")


class Agent(models.Model):
    name = models.CharField(max_length=200, verbose_name=_("Name"))


class Contact(models.Model):
    address = models.CharField(max_length=200, verbose_name=_("Name"))
    po_box = models.CharField(
        max_length=200, verbose_name=_("po_box"), null=True, blank=True
    )
    agent = models.ForeignKey(Agent, on_delete=models.CASCADE)


class Client(models.Model):
    class SexChoices(models.TextChoices):
        FEMALE = "FEMALE", _("Female")
        MALE = "MALE", _("Male")
        OTHER = "OTHER", _("Other")

    slug = models.CharField(max_length=200, verbose_name=_("Client Slug"))

    name = models.CharField(max_length=200, verbose_name=_("Name"), unique=True)
    email = models.EmailField(blank=True)
    notes = models.TextField()
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, null=True)
    sex = models.CharField(max_length=10, choices=SexChoices.choices, default="OTHER")

    class Meta:
        verbose_name = _("Client")
        verbose_name_plural = _("Clients")


class SimpleSales(models.Model):
    slug = models.SlugField()
    doc_date = models.DateTimeField(_("date"), db_index=True)
    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.DecimalField(
        _("quantity"), max_digits=19, decimal_places=2, default=0
    )
    price = models.DecimalField(_("price"), max_digits=19, decimal_places=2, default=0)
    value = models.DecimalField(_("value"), max_digits=19, decimal_places=2, default=0)
    created_at = models.DateTimeField(null=True, verbose_name=_("Created at"))
    flag = models.CharField(max_length=50, default="sales")

    content_type = models.ForeignKey(
        ContentType, on_delete=models.DO_NOTHING, null=True
    )
    object_id = models.PositiveIntegerField(null=True)
    content_object = GenericForeignKey("content_type", "object_id")

    def save(
        self, force_insert=False, force_update=False, using=None, update_fields=None
    ):
        self.value = self.quantity * self.price
        super().save(force_insert, force_update, using, update_fields)

    class Meta:
        verbose_name = _("Sale")
        verbose_name_plural = _("Sales")
        ordering = ["-created_at"]


class SimpleSales2(models.Model):
    slug = models.SlugField()
    doc_date = models.DateTimeField(_("date"), db_index=True)
    client = models.ForeignKey(Client, on_delete=models.CASCADE, to_field="name")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.DecimalField(
        _("quantity"), max_digits=19, decimal_places=2, default=0
    )
    price = models.DecimalField(_("price"), max_digits=19, decimal_places=2, default=0)
    value = models.DecimalField(_("value"), max_digits=19, decimal_places=2, default=0)
    created_at = models.DateTimeField(null=True, verbose_name=_("Created at"))
    flag = models.CharField(max_length=50, default="sales")

    content_type = models.ForeignKey(
        ContentType, on_delete=models.DO_NOTHING, null=True
    )
    object_id = models.PositiveIntegerField(null=True)
    content_object = GenericForeignKey("content_type", "object_id")

    def save(
        self, force_insert=False, force_update=False, using=None, update_fields=None
    ):
        self.value = self.quantity * self.price
        super().save(force_insert, force_update, using, update_fields)

    class Meta:
        verbose_name = _("Sale")
        verbose_name_plural = _("Sales")
        ordering = ["-created_at"]


class SalesProductWithCustomID(models.Model):
    slug = models.SlugField()
    doc_date = models.DateTimeField(_("date"), db_index=True)
    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    product = models.ForeignKey(ProductCustomID, on_delete=models.CASCADE)
    quantity = models.DecimalField(
        _("quantity"), max_digits=19, decimal_places=2, default=0
    )
    price = models.DecimalField(_("price"), max_digits=19, decimal_places=2, default=0)
    value = models.DecimalField(_("value"), max_digits=19, decimal_places=2, default=0)
    created_at = models.DateTimeField(null=True, verbose_name=_("Created at"))
    flag = models.CharField(max_length=50, default="sales")

    content_type = models.ForeignKey(
        ContentType, on_delete=models.DO_NOTHING, null=True
    )
    object_id = models.PositiveIntegerField(null=True)
    content_object = GenericForeignKey("content_type", "object_id")

    def save(
        self, force_insert=False, force_update=False, using=None, update_fields=None
    ):
        self.value = self.quantity * self.price
        super().save(force_insert, force_update, using, update_fields)

    class Meta:
        verbose_name = _("Sale")
        verbose_name_plural = _("Sales")
        ordering = ["-created_at"]


class SalesWithFlag(models.Model):
    slug = models.SlugField()
    doc_date = models.DateTimeField(_("date"), db_index=True)
    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.DecimalField(
        _("quantity"), max_digits=19, decimal_places=2, default=0
    )
    price = models.DecimalField(_("price"), max_digits=19, decimal_places=2, default=0)
    value = models.DecimalField(_("value"), max_digits=19, decimal_places=2, default=0)
    created_at = models.DateTimeField(null=True, verbose_name=_("Created at"))
    flag = models.CharField(max_length=50, default="sales")

    def save(
        self, force_insert=False, force_update=False, using=None, update_fields=None
    ):
        self.value = self.quantity * self.price
        super().save(force_insert, force_update, using, update_fields)

    class Meta:
        verbose_name = _("Sale")
        verbose_name_plural = _("Sales")
        ordering = ["-created_at"]


class UserJoined(models.Model):
    username = models.CharField(max_length=255)
    date_joined = models.DateField()


class TaxCode(models.Model):
    name = models.CharField(max_length=255)
    tax = models.DecimalField(_("tax"), max_digits=19, decimal_places=2, default=0)


class ComplexSales(models.Model):
    tax = models.ManyToManyField(TaxCode)
    slug = models.SlugField()
    doc_date = models.DateTimeField(_("date"), db_index=True)
    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.DecimalField(
        _("quantity"), max_digits=19, decimal_places=2, default=0
    )
    price = models.DecimalField(_("price"), max_digits=19, decimal_places=2, default=0)
    value = models.DecimalField(_("value"), max_digits=19, decimal_places=2, default=0)
    created_at = models.DateTimeField(null=True, verbose_name=_("Created at"))
    flag = models.CharField(max_length=50, default="sales")

    content_type = models.ForeignKey(
        ContentType, on_delete=models.DO_NOTHING, null=True
    )
    object_id = models.PositiveIntegerField(null=True)
    content_object = GenericForeignKey("content_type", "object_id")

    def save(
        self, force_insert=False, force_update=False, using=None, update_fields=None
    ):
        self.value = self.quantity * self.price
        super().save(force_insert, force_update, using, update_fields)

    class Meta:
        verbose_name = _("VAT Sale")
        verbose_name_plural = _("VAT Sales")
        ordering = ["-created_at"]


#
# class Invoice(BaseMovementInfo):
#     client = models.ForeignKey(Client, on_delete=models.CASCADE)
#
#     @classmethod
#     def get_doc_type(cls):
#         return 'sales'
#
#
# class InvoiceLine(QuanValueMovementItem):
#     invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE)
#
#     product = models.ForeignKey(Product, on_delete=models.CASCADE)
#     client = models.ForeignKey(Client, on_delete=models.CASCADE)
#
#     @classmethod
#     def get_doc_type(cls):
#         return 'sales'
#
#
# class Journal(BaseMovementInfo):
#     data = models.CharField(max_length=100, null=True, blank=True)
#
#     @classmethod
#     def get_doc_type(cls):
#         return 'journal-sales'
#
#
# class JournalItem(BaseMovementItemInfo):
#     journal = models.ForeignKey(Journal, on_delete=models.CASCADE)
#     client = models.ForeignKey(Client, on_delete=models.CASCADE)
#     data = models.CharField(max_length=100, null=True, blank=True)
#
#     @classmethod
#     def get_doc_type(cls):
#         return 'journal-sales'
#
#
# class JournalWithCriteria(Journal):
#     class Meta:
#         proxy = True
#

# Vanilla models


class Order(models.Model):
    date_placed = models.DateTimeField(auto_created=True)
    client = models.ForeignKey(Client, null=True, on_delete=models.CASCADE)


class OrderLine(models.Model):
    date_placed = models.DateTimeField(auto_created=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=0)
    client = models.ForeignKey(Client, null=True, on_delete=models.CASCADE)


class Architect(models.Model):
    """A lookup table for CX Enterprise Architects, used mostly for reporting purposes. Associated with Initiatives and Features."""

    id = models.AutoField(primary_key=True)
    name = models.CharField(
        max_length=60,
        verbose_name="Lead Architect",
        null=False,
        unique=True,
        blank=False,
        db_index=True,
    )


class Initiative(models.Model):
    id = models.AutoField(primary_key=True)
    # cx_pem = models.ForeignKey(ProjectEngineeringManager, on_delete=models.DO_NOTHING,
    #                            verbose_name="CX PEM:", null=True,
    #                            blank=True)
    architect = models.ForeignKey(
        Architect,
        on_delete=models.DO_NOTHING,
        verbose_name="CX Architect:",
        null=True,
        blank=True,
        to_field="name",
    )


"""
form 
-----

get_filters
self.form.cleaned_data["start_date"],
self.form.cleaned_data["end_date"],


get_crosstab_ids
get_crosstab_compute_remainder

form.cleaned_data["time_series_pattern"]

crispy_helper (already done)

"""

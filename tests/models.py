from django.db import models
from django.urls import reverse_lazy

from django.utils.translation import ugettext_lazy as _


class Product(models.Model):
    slug = models.CharField(max_length=200, verbose_name=_('Slug'))
    name = models.CharField(max_length=200, verbose_name=_('Name'))
    sku = models.CharField(max_length=200, default='', blank=True)
    notes = models.TextField()

    class Meta:
        verbose_name = _('Product')
        verbose_name_plural = _('Products')


class Client(models.Model):
    slug = models.CharField(max_length=200, verbose_name=_('Slug'))

    name = models.CharField(max_length=200, verbose_name=_('Name'))
    email = models.EmailField(blank=True)
    notes = models.TextField()

    class Meta:
        verbose_name = _('Client')
        verbose_name_plural = _('Clients')


class SimpleSales(models.Model):
    slug = models.SlugField()
    doc_date = models.DateTimeField(_('date'), db_index=True)
    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.DecimalField(_('quantity'), max_digits=19, decimal_places=2, default=0)
    price = models.DecimalField(_('price'), max_digits=19, decimal_places=2, default=0)
    value = models.DecimalField(_('value'), max_digits=19, decimal_places=2, default=0)

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        self.value  = self.quantity * self.price
        super().save(force_insert, force_update, using, update_fields)

    class Meta:
        verbose_name = _('Sale')
        verbose_name_plural = _('Sales')

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
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=0)
    client = models.ForeignKey(Client, null=True, on_delete=models.CASCADE)

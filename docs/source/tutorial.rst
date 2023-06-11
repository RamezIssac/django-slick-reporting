=========
Tutorial
=========


Let' say we have a Sale Transaction model in your project and you want to create some reports about it.

.. code-block:: python

    from django.db import models


    class Client(models.Model):
        name = models.CharField(_("Name"), max_length=255)
        country = models.CharField(_("Country"), max_length=255)


    class Product(models.Model):
        name = models.CharField(_("Name"), max_length=255)
        sku = models.CharField(_("SKU"), max_length=255)


    class Sales(models.Model):
        doc_date = models.DateTimeField(_("date"), db_index=True)
        client = models.ForeignKey(Client, on_delete=models.CASCADE)
        product = models.ForeignKey(Product, on_delete=models.CASCADE)
        quantity = models.DecimalField(
            _("Quantity"), max_digits=19, decimal_places=2, default=0
        )
        price = models.DecimalField(_("Price"), max_digits=19, decimal_places=2, default=0)
        value = models.DecimalField(_("Value"), max_digits=19, decimal_places=2, default=0)



Like:

#. Total sales value per each project during a certain period.
#. Total sales value per each product each month during a certain period.
#. How much was sold per each product each month per each client country
#. Display last 10 sales transactions



You can create a report for each of these questions using the following code:

.. code-block:: python
            # in views.py
            from django.db.models import Sum
            from slick_reporting.views import ReportView, Chart
            from slick_reporting.fields import SlickReportField
            from .models import Sales


            class TotalProductSales(ReportView):

                report_model = Sales
                date_field = "doc_date"
                group_by = "product"
                columns = [
                    "title",
                    (
                        SlickReportField.create(Sum, "quantity"),
                        {"verbose_name": "Total Quantity sold", "is_summable": False},
                    ),
                    SlickReportField.create(Sum, "value", name="sum__value"),
                ]

                chart_settings = [
                    Chart(
                        "Total sold $",
                        Chart.BAR,
                        data_source="value__sum",
                        title_source="title",
                    ),
                ]
Then in your urls.py add the following:

.. code-block:: python

    from django.urls import path
    from .views import TotalProductSales

    urlpatterns = [
        path(
            "total-product-sales/", TotalProductSales.as_view(), name="total-product-sales"
        ),
    ]

Now visit the url ``/total-product-sales/`` and you will see the report. Containing a Filter Form, the report table and a chart.


You can change the dates in the filter form , add some filters and the report will be updated.
You can also export the report to CSV.

Let's continue with the second question:

.. code-block:: python

    from slick_reporting.fields import SlickReportField


    class SumValueComputationField(SlickReportField):
        computation_method = Sum
        computation_field = "value"
        verbose_name = _("Sales Value")


    class MonthlyProductSales(ReportView):
        report_model = Sales
        date_field = "doc_date"
        group_by = "product"
        columns = ["name", "sku"]

        time_series_pattern = "monthly"
        time_series_columns = [
            SumValueComputationField,
        ]

        chart_settings = [
            Chart(
                _("Total Sales Monthly"),
                Chart.PIE,
                data_source=["value"],
                title_source=["name"],
                plot_total=True,
            ),
        ]

then again in your urls.py add the following:

.. code-block:: python

    from django.urls import path
    from .views import MonthlyProductSales

    urlpatterns = [
        path(
            "monthly-product-sales/",
            MonthlyProductSales.as_view(),
            name="monthly-product-sales",
        ),
    ]

Pretty Cool yes ?

Now let's continue with the third question:

.. code-block:: python


    class ProductSalesPerCountry(ReportView):
        report_model = Sales
        date_field = "doc_date"
        group_by = "product"
        crosstab_field = "client__country"

        crosstab_columns = [
            SumValueComputationField,
        ]

        crosstab_ids = ["US", "KW", "EG", "DE"]
        crosstab_compute_remainder = True

        columns = [
            "name",
            "sku",
            "__crosstab__",
            SumValueComputationField,
        ]

Then again in your urls.py add the following:

.. code-block:: python

    from django.urls import path
    from .views import MyCrosstabReport

    urlpatterns = [
        path(
            "product-sales-per-country/",
            ProductSalesPerCountry.as_view(),
            name="product-sales-per-country",
        ),
    ]


Now let's continue with the fourth question:

.. code-block:: python

    from slick_reporting.view import ListReportView


    class LastTenSales(ListReportView):
        report_model = Sales
        date_field = "doc_date"
        group_by = "product"
        columns = [
            "product__name",
            "product__sku",
            "doc_date",
            "quantity",
            "price",
            "value",
        ]
        default_order_by = "-doc_date"
        limit_records = 10


Then again in your urls.py add the following:

.. code-block:: python

    from django.urls import path
    from .views import LastTenSales

    urlpatterns = [
        path(
            "last-ten-sales/",
            LastTenSales.as_view(),
            name="last-ten-sales",
        ),
    ]

Recap
=====
You can create a report by inheriting from ``ReportView`` or ``ListReportView`` and setting the following attributes:

* ``report_model``: The model to be used in the report
* ``date_field``: The date field to be used in the report
* ``group_by``: The field to be used to group the report by
* ``columns``: The columns to be displayed in the report
* ``default_order_by``: The default order by for the report
* ``limit_records``: The limit of records to be displayed in the report
* ``crosstab_field``: The field to be used to create a crosstab report
* ``crosstab_columns``: The columns to be displayed in the crosstab report
* ``crosstab_ids``: The ids to be used in the crosstab report
* ``crosstab_compute_remainder``: Whether to compute the remainder in the crosstab report
* ``time_series_pattern``: The time series pattern to be used in the report
* ``time_series_columns``: The columns to be displayed in the time series report
* ``chart_settings``: The chart settings to be used in the report


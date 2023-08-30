.. _tutorial:

=========
Tutorial
=========

In this tutorial we will go over how to create different reports using Slick Reporting and integrating them into your projects.

Let' say you have a Sales Transaction model in your project. Schema looking like this:

.. code-block:: python

    from django.db import models
    from django.utils.translation import gettext_lazy as _


    class Client(models.Model):
        name = models.CharField(_("Name"), max_length=255)
        country = models.CharField(_("Country"), max_length=255, default="US")


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



Now, you want to extract the following information from that sales model, present to your users in a nice table and chart:

#. Total sales per product.
#. Total Sales per client country.
#. Total sales per product each month.
#. Total Sales per product and country.
#. Total Sales per product and country, per month.
#. Display last 10 sales transactions.

Group By Reports
================

1. Total sales per product
--------------------------

This can be done via an SQL statement looking like this:

.. code-block:: sql

    SELECT product_id, SUM(value) FROM sales GROUP BY product_id;

In Slick Reporting, you can do the same thing by creating a report view looking like this:

.. code-block:: python

            # in views.py

            from django.db.models import Sum
            from slick_reporting.views import ReportView, Chart
            from slick_reporting.fields import SlickReportField
            from .models import Sales


            class TotalProductSales(ReportView):
                report_model = SalesTransaction
                date_field = "date"
                group_by = "product"
                columns = [
                    "name",
                    SlickReportField.create(Sum, "quantity", verbose_name="Total quantity sold", is_summable=False),
                    SlickReportField.create(Sum, "value", name="sum__value", verbose_name="Total Value sold $"),
                ]

                chart_settings = [
                    Chart(
                        "Total sold $",
                        Chart.BAR,
                        data_source=["sum__value"],
                        title_source=["name"],
                    ),
                    Chart(
                        "Total sold $ [PIE]",
                        Chart.PIE,
                        data_source=["sum__value"],
                        title_source=["name"],
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

Now visit the url ``/total-product-sales/`` and you will see the page report. Containing a Filter Form, the report table and a chart.


You can change the dates in the filter form , add some filters and the report will be updated.
You can also export the report to CSV.

2. Total Sales per each client country
--------------------------------------

.. code-block:: python

            # in views.py

            from django.db.models import Sum
            from slick_reporting.views import ReportView, Chart
            from slick_reporting.fields import SlickReportField
            from .models import SalesTransaction


            class TotalProductSalesByCountry(ReportView):
                report_model = SalesTransaction
                date_field = "date"
                group_by = "client__country"  # notice the double underscore
                columns = [
                    "client__country",
                    SlickReportField.create(Sum, "value", name="sum__value", verbose_name="Total Value sold by country $"),
                ]

                chart_settings = [
                    Chart(
                        "Total sold by country $",
                        Chart.PIE,  # A Pie Chart
                        data_source=["sum__value"],
                        title_source=["client__country"],
                    ),
                ]


Time Series Reports
====================
A time series report is a report that computes the data for each period of time. For example, if you want to see the total sales per each month, then you need to create a time series report.



.. code-block:: python

    from django.utils.translation import gettext_lazy as _
    from slick_reporting.fields import SlickReportField


    class SumValueComputationField(SlickReportField):
        computation_method = Sum
        computation_field = "value"
        verbose_name = _("Sales Value")
        name = "my_value_sum"



    class MonthlyProductSales(ReportView):
        report_model = SalesTransaction
        date_field = "date"
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
                data_source=["my_value_sum"],
                title_source=["name"],
                plot_total=True,
            ),
            Chart(
                _("Sales Monthly [Bar]"),
                Chart.COLUMN,
                data_source=["my_value_sum"],
                title_source=["name"],
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

Note: We created SumValueComputationField to avoid repeating the same code in each report. You can create your own ``ComputationFields`` and use them in your reports.

Pretty Cool yes ?

CrossTab Reports
================
A crosstab report shows the relation between two or more variables. For example, if you want to see the total sales per each product and country, then you need to create a crosstab report.

.. code-block:: python


    class ProductSalesPerCountryCrosstab(ReportView):
        report_model = SalesTransaction
        date_field = "date"
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
            ProductSalesPerCountryCrosstab.as_view(),
            name="product-sales-per-country",
        ),
    ]


List Reports
============
A list report is a report that shows a list of records. For example, if you want to see the last 10 sales transactions, then you need to create a list report.

.. code-block:: python

    from slick_reporting.views import ListReportView


    class LastTenSales(ListReportView):
        report_model = SalesTransaction
        report_title = "Last 10 sales"
        date_field = "date"
        filters = ["client"]
        columns = [
            "product",
            "date",
            "quantity",
            "price",
            "value",
        ]
        default_order_by = "-date"
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

Integrate the view in your project
===================================

You can use the template in your own project by following these steps:

#. Override ``slick_reporting/base.html`` in your own project and make it extends you own base template.
#. Make sure your base template has a ``{% block content %}`` block and a  ``{% block extrajs %}`` block.
#. Add the slick reporting js resources to the page by adding `{% include "slick_reporting/js_resources.html" %}` to an appropriate block.


Overriding the Form
===================

The system expect that the form used with the ``ReportView`` to implement the ``slick_reporting.forms.BaseReportForm`` interface.

The interface is simple, only 3 mandatory methods to implement, The rest are mandatory only if you are working with a crosstab report or a time series report.


* ``get_filters``: Mandatory, return a tuple (Q_filers , kwargs filter) to be used in filtering.
  q_filter: can be none or a series of Django's Q queries
  kwargs_filter: None or a dictionary of filters

* ``get_start_date``: Mandatory, return the start date of the report.

* ``get_end_date``: Mandatory, return the end date of the report.

* ``get_crispy_helper`` : return a crispy form helper to be used in rendering the form. (optional)

For detailed information about the form, please check :ref:`filter_form`

Example
-------

.. code-block:: python

    # forms.py
    from slick_reporting.forms import BaseReportForm
    from crispy_forms.helper import FormHelper

    # A Normal form , Inheriting from BaseReportForm
    class RequestLogForm(BaseReportForm, forms.Form):

        SECURE_CHOICES = (
            ("all", "All"),
            ("secure", "Secure"),
            ("non-secure", "Not Secure"),
        )

        start_date = forms.DateField(
            required=False,
            label="Start Date",
            widget=forms.DateInput(attrs={"type": "date"}),
        )
        end_date = forms.DateField(
            required=False, label="End Date", widget=forms.DateInput(attrs={"type": "date"})
        )
        secure = forms.ChoiceField(
            choices=SECURE_CHOICES, required=False, label="Secure", initial="all"
        )
        other_people_only = forms.BooleanField(
            required=False, label="Show requests from other users only"
        )


        def get_filters(self):
            # return the filters to be used in the report
            # Note: the use of Q filters and kwargs filters
            kw_filters = {}
            q_filters = []
            if self.cleaned_data["secure"] == "secure":
                kw_filters["is_secure"] = True
            elif self.cleaned_data["secure"] == "non-secure":
                kw_filters["is_secure"] = False
            if self.cleaned_data["other_people_only"]:
                q_filters.append(~Q(user=self.request.user))
            return q_filters, kw_filters

        def get_start_date(self):
            return self.cleaned_data["start_date"]

        def get_end_date(self):
            return self.cleaned_data["end_date"]

        def get_crispy_helper(self):
            return FormHelper()


Recap
=====
In the tutorial we went over how to create a report using the ``ReportView`` and ``ListReportView`` classes.
The different types of reports we created are:

1. Grouped By Reports
2. Time Series Reports
3. Crosstab Reports
4. List Reports

You can create a report by inheriting from ``ReportView`` or ``ListReportView`` and setting the following attributes:

* ``report_model``: The model to be used in the report
* ``date_field``: The date field to be used in the report
* ``columns``: The columns to be displayed in the report
* ``default_order_by``: The default order by for the report
* ``limit_records``: The limit of records to be displayed in the report
* ``group_by``: The field to be used to group the report by
* ``time_series_pattern``: The time series pattern to be used in the report
* ``time_series_columns``: The columns to be displayed in the time series report
* ``crosstab_field``: The field to be used to create a crosstab report
* ``crosstab_columns``: The columns to be displayed in the crosstab report
* ``crosstab_ids``: The ids to be used in the crosstab report
* ``crosstab_compute_remainder``: Whether to compute the remainder in the crosstab report
* ``chart_settings``: The chart settings to be used in the report

We also saw how you can customize the form used in the report by inheriting from ``BaseReportForm``, and integrating the view in your project.

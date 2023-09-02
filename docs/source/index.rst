Django Slick Reporting
======================

**Django Slick Reporting** a reporting engine allowing you to create & display diverse analytics. Batteries like a ready to use View and Highcharts & Charts.js integration are included.

* Create group by , crosstab , timeseries, crosstab in timeseries and list reports in handful line with intuitive syntax
* Highcharts & Charts.js integration ready to use with the shipped in View, easily extendable to use with your own charts.
* Export to CSV
* Easily extendable to add your own computation fields,
* Create Dashboard(s) with multiple charts and reports

Installation
------------

To install django-slick-reporting with pip

.. code-block:: bash

        pip install django-slick-reporting


Usage
-----

#. Add ``"slick_reporting", "crispy_forms", "crispy_bootstrap4",`` to ``INSTALLED_APPS``.
#. Add ``CRISPY_TEMPLATE_PACK = "bootstrap4"`` to your ``settings.py``
#. Execute `python manage.py collectstatic` so the JS helpers are collected and served.



Quickstart
----------

You can start by using ``ReportView`` which is a subclass of ``django.views.generic.FormView``

.. code-block:: python

    # in views.py
    from slick_reporting.views import ReportView, Chart
    from slick_reporting.fields import SlickReportField
    from .models import MySalesItems
    from django.db.models import Sum


    class ProductSales(ReportView):

        report_model = MySalesItems
        date_field = "date_placed"
        group_by = "product"

        columns = [
            "title",
            SlickReportField.create(
                method=Sum, field="value", name="value__sum", verbose_name="Total sold $"
            ),
        ]

        # Charts
        chart_settings = [
            Chart(
                "Total sold $",
                Chart.BAR,
                data_source=["value__sum"],
                title_source=["title"],
            ),
        ]


    # in urls.py
    from django.urls import path
    from .views import ProductSales

    urlpatterns = [
        path("product-sales/", ProductSales.as_view(), name="product-sales"),
    ]

Demo site
----------

https://django-slick-reporting.com is a quick walk-though with live code examples



Next step :ref:`tutorial`

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   concept
   tutorial
   topics/index
   howto/index
   charts
   ref/index



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`


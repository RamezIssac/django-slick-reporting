.. image:: https://img.shields.io/pypi/v/django-slick-reporting.svg
    :target: https://pypi.org/project/django-slick-reporting

.. image:: https://img.shields.io/pypi/pyversions/django-slick-reporting.svg
    :target: https://pypi.org/project/django-slick-reporting

.. image:: https://img.shields.io/readthedocs/django-slick-reporting
    :target: https://django-slick-reporting.readthedocs.io/

.. image:: https://api.travis-ci.com/ra-systems/django-slick-reporting.svg?branch=master
    :target: https://app.travis-ci.com/github/ra-systems/django-slick-reporting

.. image:: https://img.shields.io/codecov/c/github/ra-systems/django-slick-reporting
    :target: https://codecov.io/gh/ra-systems/django-slick-reporting




Django Slick Reporting
======================

A one stop reports engine with batteries included.

Features
--------

- Effortlessly create Simple, Grouped, Time series and Crosstab reports in a handful of code lines.
- Create Chart(s) for your reports with a single line of code.
- Create Custom complex Calculation.
- Optimized for speed.
- Easily extendable.

Installation
------------

Use the package manager `pip <https://pip.pypa.io/en/stable/>`_ to install django-slick-reporting.

.. code-block:: console

        pip install django-slick-reporting


Usage
-----

So you have a model that contains data, let's call it `MySalesItems`

You can simply use a code like this

.. code-block:: python

    # in your urls.py
    path("path-to-report", TotalProductSales.as_view())


    # in views.py
    from django.db.models import Sum
    from slick_reporting.views import ReportView, Chart
    from slick_reporting.fields import SlickReportField
    from .models import MySalesItems


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

To get something this

.. image:: https://i.ibb.co/SvxTM23/Selection-294.png
    :target: https://i.ibb.co/SvxTM23/Selection-294.png
    :alt: Shipped in View Page


Time Series
-----------


.. code-block:: python

    # in views.py
    from slick_reporting.views import ReportView
    from slick_reporting.fields import SlickReportField
    from .models import MySalesItems


    class MonthlyProductSales(ReportView):
        report_model = MySalesItems
        date_field = "date_placed"
        group_by = "product"
        columns = ["name", "sku"]

        # Settings for creating time series report
        time_series_pattern = (
            "monthly"  # or "yearly" , "weekly" , "daily" , others and custom patterns
        )
        time_series_columns = [
            SlickReportField.create(
                Sum, "value", verbose_name=_("Sales Value"), name="value"
            )
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


.. image:: https://github.com/ra-systems/django-slick-reporting/blob/develop/docs/source/report_view/_static/timeseries.png?raw=true
    :alt: Time Series Report
    :align: center

Cross Tab
---------

.. code-block:: python

        # in views.py
        from slick_reporting.views import ReportView
        from slick_reporting.fields import SlickReportField
        from .models import MySalesItems


        class MyCrosstabReport(ReportView):

            crosstab_field = "client"
            crosstab_ids = [1, 2, 3]
            crosstab_columns = [
                SlickReportField.create(Sum, "value", verbose_name=_("Value for")),
            ]
            crosstab_compute_remainder = True

            columns = [
                "some_optional_field",
                # You can customize where the crosstab columns are displayed in relation to the other columns
                "__crosstab__",
                # This is the same as the Same as the calculation in the crosstab, but this one will be on the whole set. IE total value
                SlickReportField.create(Sum, "value", verbose_name=_("Total Value")),
            ]


.. image:: https://github.com/ra-systems/django-slick-reporting/blob/develop/docs/source/report_view/_static/crosstab.png?raw=true
   :alt: Homepage
   :align: center


Low level
---------

The view is a wrapper over the `ReportGenerator` class, which is the core of the reporting engine.
You can interact with the `ReportGenerator` using same syntax as used with the `ReportView` .

.. code-block:: python

    from slick_reporting.generator import ReportGenerator
    from .models import MySalesModel


    class MyReport(ReportGenerator):
        report_model = MySalesModel
        group_by = "product"
        columns = ["title", "__total__"]


    # OR
    my_report = ReportGenerator(
        report_model=MySalesModel, group_by="product", columns=["title", "__total__"]
    )
    my_report.get_report_data()  # -> [{'title':'Product 1', '__total__: 56}, {'title':'Product 2', '__total__: 43}, ]


This is just a scratch of what you can do and customize.

Demo site
---------

Available on `Django Slick Reporting <https://django-slick-reporting.com/>`_


You can also use locally

.. code-block:: console

        # clone the repo
        # create a virtual environment, activate it, then
        cd django-slick-reporting/demo_proj
        pip install requirements.txt
        python manage.py migrate
        python manage.py create_entries
        python manage.py runserver

the ``create_entries`` command will generate data for the demo app


Batteries Included
------------------

Slick Reporting comes with

* An auto-generated, bootstrap-ready Filter Form
* Carts.js Charting support `Chart.js <https://www.chartjs.org/>`_
* Highcharts.js Charting support `Highcharts.js <https://www.highcharts.com//>`_
* Datatables `datatables.net <https://datatables.net/>`_

A Preview:

.. image:: https://i.ibb.co/SvxTM23/Selection-294.png
    :target: https://i.ibb.co/SvxTM23/Selection-294.png
    :alt: Shipped in View Page


Documentation
-------------

Available on `Read The Docs <https://django-slick-reporting.readthedocs.io/en/latest/>`_

Road Ahead
----------

* Continue on enriching the demo project
* Add the dashboard capabilities


Running tests
-----------------
Create a virtual environment (maybe with `virtual slick_reports_test`), activate it; Then ,
 
.. code-block:: console
    
    $ git clone git+git@github.com:ra-systems/django-slick-reporting.git
    $ cd tests
    $ python -m pip install -e ..

    $ python runtests.py
    #     Or for Coverage report
    $ coverage run --include=../* runtests.py [-k]
    $ coverage html


Support & Contributing
----------------------

Please consider star the project to keep an eye on it. Your PRs, reviews are most welcome and needed.

We honor the well formulated `Django's guidelines <https://docs.djangoproject.com/en/dev/internals/contributing/writing-code/unit-tests/>`_ to serve as contribution guide here too.


Authors
--------

* **Ramez Ashraf** - *Initial work* - `RamezIssac <https://github.com/RamezIssac>`_

Cross Reference
---------------

If you like this package, chances are you may like those packages too!

`Django Tabular Permissions <https://github.com/RamezIssac/django-tabular-permissions>`_ Display Django permissions in a HTML table that is translatable and easy customized.

`Django ERP Framework <https://github.com/ra-systems/RA>`_ A framework to build business solutions with ease.

If you find this project useful or promising , You can support us by a github ⭐

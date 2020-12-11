.. image:: https://img.shields.io/pypi/v/django-slick-reporting.svg
    :target: https://pypi.org/project/django-slick-reproting

.. image:: https://img.shields.io/pypi/pyversions/django-slick-reporting.svg
    :target: https://pypi.org/project/django-slick-reporting

.. image:: https://img.shields.io/readthedocs/django-slick-reporting
    :target: https://django-slick-reporting.readthedocs.io/

.. image:: https://api.travis-ci.org/ra-systems/django-slick-reporting.svg?branch=master
    :target: https://travis-ci.org/ra-systems/django-slick-reporting

.. image:: https://img.shields.io/codecov/c/github/ra-systems/django-slick-reporting
    :target: https://codecov.io/gh/ra-systems/django-slick-reporting




Django Slick Reporting
======================

A one stop reports engine with batteries included.


Features
--------

- Effortlessly create Simple, Grouped, Time series and Crosstab reports in a handful of code lines.
- Create your Custom Calculation easily, which will be integrated with the above reports types
- Optimized for speed.
- Batteries included! Charts.js , DataTable.net & a Bootstrap form.

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
    path('path-to-report', TotalProductSales.as_view())


    # in views.py
    from django.db.models import Sum
    from slick_reporting.views import SlickReportView
    from .models import MySalesItems

    class TotalProductSales(SlickReportView):

        report_model = MySalesItems
        date_field = 'date_placed'
        group_by = 'product'
        columns = ['title',
                    SlickReportField.create(Sum, 'quantity') ,
                    SlickReportField.create(Sum, 'value', name='sum__value') ]

        chart_settings = [{
            'type': 'column',
            'data_source': ['sum__value'],
            'plot_total': False,
            'title_source': 'title',
            'title': _('Detailed Columns'),

        }, ]


To get something like this

.. image:: https://i.ibb.co/SvxTM23/Selection-294.png
    :target: https://i.ibb.co/SvxTM23/Selection-294.png
    :alt: Shipped in View Page


You can do a monthly time series :


.. code-block:: python

    # in views.py
    from slick_reporting.views import SlickReportView
    from .models import MySalesItems

    class MonthlyProductSales(SlickReportView):
        report_model = MySalesItems
        date_field = 'date_placed'
        group_by = 'product'
        columns = ['name', 'sku']

        # Analogy for time series
        time_series_pattern = 'monthly'
        time_series_columns = [SlickReportField.create(Sum, 'quantity', name='sum__quantity') ]


This would return a table looking something like this:

+--------------+----------------------+-----------------+----------------+-----------------------+-------------------------------+
| Product Name | SKU                  | Total Quantity  | Total Quantity | Total Quantity in ... | Total Quantity in December 20 |
|              |                      | in Jan 20       | in Feb 20      |                       |                               |
+--------------+----------------------+-----------------+----------------+-----------------------+-------------------------------+
| Product 1    | <from product model> | 10              | 15             | ...                   | 14                            |
+--------------+----------------------+-----------------+----------------+-----------------------+-------------------------------+
| Product 2    | <from product model> | 11              | 12             | ...                   | 12                            |
+--------------+----------------------+-----------------+----------------+-----------------------+-------------------------------+
| Product 3    | <from product model> | 17              | 12             | ...                   | 17                            |
+--------------+----------------------+-----------------+----------------+-----------------------+-------------------------------+

*This example code assumes your "MySalesItems" model contains the fields `product` as foreign key,  `quantity` as number , and `date_placed` as a date field. It also assumes your `Product` model has an SKU field.. Change those to better suit your structure.*


--

**On a low level**

You can interact with the `ReportGenerator` using same syntax as used with the `SlickReportView` .

.. code-block:: python

    from slick_reporting.generator import ReportGenerator
    from . models import MySalesModel

    report = ReportGenerator(report_model=MySalesModel,
                            group_by='product',
                            columns=['title', '__total__']
    )
    report.get_report_data() #-> [{'title':'Product 1', '__total__: 56}, {'title':'Product 2', '__total__: 43}, ]


This is just a scratch, for more please visit the documentation 

Batteries Included
------------------

Slick Reporting comes with

* A Bootstrap Filter Form
* Charting support `Charts.js <https://www.chartjs.org/>`_
* Powerful tables `datatables.net <https://datatables.net/>`_

A Preview:

.. image:: https://i.ibb.co/SvxTM23/Selection-294.png
    :target: https://i.ibb.co/SvxTM23/Selection-294.png
    :alt: Shipped in View Page


Documentation
-------------

Available on `Read The Docs <https://django-slick-reporting.readthedocs.io/en/latest/>`_

Road Ahead
----------

This project is young and can use your support.

Some of the ideas / features that ought be added

* Support Other backends like SQL Alchemy & Pandas
* Support Grouping by non foreign key fields
* Support Time Series and Crosstab at the same time


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

`Django Ra ERP Framework <https://github.com/ra-systems/RA>`_ A framework to build business solutions with ease.

If you find this project useful or promising , You can support us by a github ⭐

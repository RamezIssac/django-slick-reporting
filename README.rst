.. image:: https://img.shields.io/pypi/v/django-slick-reporting.svg
    :target: https://pypi.org/project/django-ra

.. image:: https://img.shields.io/pypi/pyversions/django-slick-reporting.svg
    :target: https://pypi.org/project/django-ra

.. image:: https://img.shields.io/readthedocs/django-slick-reporting
    :target: https://django-slick-reporting.readthedocs.io/

.. image:: https://api.travis-ci.org/ra-systems/django-slick-reporting.svg?branch=master
    :target: https://travis-ci.org/ra-systems/django-slick-reporting

.. image:: https://img.shields.io/codecov/c/github/ra-systems/django-slick-reporting
    :target: https://codecov.io/gh/ra-systems/django-slick-reporting




Django Slick Reporting
======================

A one stop reports engine with batteries included.

What it does:
-------------

Given a model that contains some data *(ex: an OrderLine Model)*; Slick Reporting allows you to compute any kind of stats
(Sum, AVG, etc.. ) over any field using simple and intuitive analogy.
It also allow you to use those computation units in a time series and cross tab.

Features
--------

- Preform Different computation grouping over the foreign keys.
- Those computation can also be calculated on Time Series report *like monthly*, with custom dates ability.
- Computation can be used on Cross tab reports
- Create your Custom Calculation
- Optimized for speed !
- ... and much more

Installation
------------

Use the package manager `pip <https://pip.pypa.io/en/stable/>`_ to install django-slick-reporting.

.. code-block:: console

        pip install django-slick-reporting


Usage
-----

**From high Level**,

You can use ``SampleReportView`` which is a subclass of ``django.views.generic.FormView`` like this

.. code-block:: python

    # in views.py
    from slick_reporting.views import SampleReportView
    from .models import MySalesItems

    class TotalProductSales(SampleReportView):

        # The model where you have the data
        report_model = MySalesItems

        # the main date to use if date filter is needed
        date_field = 'date_placed' # or 'order__date_placed'
        # date_field support traversing,
        # date_field = 'order__date_placed'

        # A foreign key to group calculation on
        group_by = 'product'

        # The columns you want to display
        columns = ['title', '__total_quantity__', '__total__']

    # in your urls.py
    path('url-to-report', TotalProductSales.as_view())

This will return a page, with a table looking like

+-----------+----------------+-------------+
| Product   | Total Quantity | Total Value |
+-----------+----------------+-------------+
| Product 1 | 8              | 120         |
+-----------+----------------+-------------+
| Product 2 | 13             | 240         |
+-----------+----------------+-------------+

You can also do a monthly time series :


.. code-block:: python

    # in views.py
    from slick_reporting.views import SampleReportView
    from .models import MySalesItems

    class MonthlyProductSales(SampleReportView):
        report_model = MySalesItems
        date_field = 'date_placed'
        group_by = 'product'
        columns = ['name', 'sku']

        # Analogy for time series
        time_series_pattern = 'monthly'
        time_series_columns = ['__total_quantity__']


hook it into your ``urls.py`` , and it would return a page with a table looking something like this:

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

*This example code assumes your "MySalesItems" contains the fields `product` as foreign key,  `quantity` as number and `date_placed` as a date field. It also assumes your `Product` model has an SKU field..*
--

**On a low level**

You can interact with the `ReportGenerator` using same syntax as used with the `SampleReportView` .

.. code-block:: python

    from slick_reporting.generator import ReportGenerator
    from . models import MySalesModel

    report = ReportGenerator(report_model=MySalesModel,
                            group_by='product',
                            columns=['title', '__total__']
    )
    report.get_report_data() #-> [{'title':'Product 1', '__total__: 56}, {'title':'Product 2', '__total__: 43}, ]


This is just a scratch, for more please visit the documentation 


Documentation
-------------

Available on `Read The Docs <https://django-slick-reporting.readthedocs.io/en/latest/>`_



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


Contributing
------------

We follow `Django's guidelines <https://docs.djangoproject.com/en/dev/internals/contributing/writing-code/unit-tests/>`_ guidelines.

Authors
--------

* **Ramez Ashraf** - *Initial work* - `RamezIssac <https://github.com/RamezIssac>`_


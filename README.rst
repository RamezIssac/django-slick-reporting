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

A one stop reports and analytics tool for Django

# Features
1- Simple Reporting over the content of a model
2- Preform Different computation grouping over the content of model
3- Those computation can also be computed on Time Series report (like montly)_, with custom dates ability
4- Also can be used on Crosstab reports
5- Custom computation with smart dependency management to optimize calculations
6- ... and much more 

Installation
------------

Use the package manager `pip <https://pip.pypa.io/en/stable/>_` to install django-slick-reporting.

.. code-block:: console

        pip install django-slick-reporting


Usage
-----

**From high Level**, you can use `SampleReportView` which is a subclass of `django.views.generic.FormView` like this

.. code-block:: python

    # in views.py
    from slick_reporting.views import SampleReportView
    from .models import MySalesItems

    class MonthlyProductSales(SampleReportView):
        report_model = MySalesItems
        date_field = 'order__date_placed'
        group_by = 'product'
        columns = ['title', 'SKU']
        time_series_pattern = 'monthly'
        time_series_columns = ['__total_quantity__']


And the above view would return a page with a table looking something like this:

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

--

**On a low level**

You can interact with the `ReportGenerator` using same syntax as used with the `SampleReportView` .

.. code-block:: python

    from slick_reporting import ReportGenerator
    from . models import MySalesModel

    report = ReportGenerator(report_model=MySalesModel,
                            group_by='product',
    )
    report.get_report_data()


This is just a scratch, for more please visit the documentation 

Documentation
-------------

Available on `Read The Docs <https://django-slick-reporting.readthedocs.io/en/latest/>`_



Running the tests
-----------------
First create a virtual environment (maybe with `virtual slick_reports_test`), activate it then ,
 
.. code-block:: console
    
    $ git clone git+git@github.com:ra-systems/django-slick-reporting.git
    $ cd tests
    $ python -m pip install -e ..
    $ python runtests.py

        # And for Coverage report
    $ coverage run --include=../* runtests.py [-k]
    $ coverage html



Tests tests the proper computation and structure generation ,

Contributing
------------

We follow `Django's guidelines <https://docs.djangoproject.com/en/dev/internals/contributing/writing-code/unit-tests/>`_ guidelines.

Authors
--------

* **Ramez Ashraf** - *Initial work* - [RamezIssac](https://github.com/RamezIssac)


License
-------

This project is licensed under the BSD License - see the [LICENSE.md](LICENSE.md) file for details

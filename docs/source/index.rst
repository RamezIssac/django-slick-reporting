.. Django Slick Reporting documentation master file, created by
sphinx-quickstart on Fri Apr 24 17:39:17 2020.
You can adapt this file completely to your liking, but it should at least
contain the root `toctree` directive.

Django Slick Reporting
======================

**Django Slick Reporting** is a report engine that allows you to compute and create diverse report form with custom calculations


Installation
------------

To install django-slick-reporting:

1.  Install with pip: ``pip install django-slick-reporting``.
2.  Add ``'slick_reporting'`` to ``INSTALLED_APPS``.


Quickstart
----------

You can start by using ``SampleReportView`` which is a subclass of ``django.views.generic.FormView``

.. code-block:: python

    # in views.py
    from slick_reporting.views import SampleReportView
    from .models import MySalesItems

    class MonthlyProductSales(SampleReportView):
        # The model where you have the data
        report_model = MySalesItems

        # the main date field used for the model.
        date_field = 'date_placed' # or 'order__date_placed'
        # this support traversing, like so
        # date_field = 'order__date_placed'

        # A foreign key to group calculation on
        group_by = 'product'

        # The columns you want to display
        columns = ['title', '__total_quantity__']

        # Charts
        charts_settings = [
         {
            'type': 'bar',
            'data_source': '__total_quantity__',
            'title_source': 'title',
         },
        ]


.. toctree::
   :maxdepth: 2
   :caption: Contents:

   tour
   customization
   report_generator
   computation_field




Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`



Django Slick Reporting
======================

**Django Slick Reporting** is a report engine that where you can create & display diverse analytics. Batteries like a ready to use View and Charts.js integration are included.


Installation
------------

To install django-slick-reporting:

1.  Install with pip: ``pip install django-slick-reporting``.
2.  Add ``'slick_reporting'`` to ``INSTALLED_APPS``.
3. For the shipped in View, add ``'crispy_forms'`` to ``INSTALLED_APPS``and add `CRISPY_TEMPLATE_PACK = 'bootstrap4'`
   to your `settings.py`


Quickstart
----------

You can start by using ``SlickReportView`` which is a subclass of ``django.views.generic.FormView``

.. code-block:: python

    # in views.py
    from slick_reporting.views import SlickReportView
    from .models import MySalesItems

    class MonthlyProductSales(SlickReportView):
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

The above simple code will result in a page similar to this

.. image:: https://i.ibb.co/SvxTM23/Selection-294.png
    :target: https://i.ibb.co/SvxTM23/Selection-294.png
    :alt: Shipped in View Page

Neat huh ? Next step :ref:`usage`

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


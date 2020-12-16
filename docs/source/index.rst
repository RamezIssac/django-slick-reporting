Django Slick Reporting
======================

**Django Slick Reporting** a report engine allowing you to create & display diverse analytics. Batteries like a ready to use View and Highcharts & Charts.js integration are included.


Installation
------------

To install django-slick-reporting:

1.  Install with pip: `pip install django-slick-reporting`.
2.  Add ``slick_reporting'`` to ``INSTALLED_APPS``.
3. For the shipped in View, add ``'crispy_forms'`` to ``INSTALLED_APPS`` and add ``CRISPY_TEMPLATE_PACK = 'bootstrap4'``
   to your ``settings.py``
4. Execute `python manage.py collectstatic` so the JS helpers are collected and served.

Demo site
----------

https://django-slick-reporting.com is a quick walk-though with live code examples


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
        columns = ['title',
                    SlickReportField.create(method=Sum, field='value', name='value__sum', verbose_name=_('Total sold $'))
                    ]

        # Charts
        charts_settings = [
         {
            'type': 'bar',
            'data_source': 'value__sum',
            'title_source': 'title',
         },
        ]


Next step :ref:`structure`

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   concept
   the_view
   report_generator
   computation_field




Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`


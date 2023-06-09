.. _structure:

Structure
==========

If you haven't yet, please check https://django-slick-reporting.com for a quick walk-though with live code examples..

And now, Let's explore the main components of Django Slick Reporting and what setting you can set on project level.

Components
----------
These are the main components of Django Slick Reporting, ordered from low level to high level:

1. :ref:`Computation Field <computation_field>`: a calculation unit,like a Sum or a Count of a certain field.
   Computation field class set how the calculation should be done. ComputationFields can also depend on each other.

2. :ref:`Generator <report_generator>`: Responsible for generating report and orchestrating and calculating the computation fields values and mapping them to the results.
   It has an intuitive API that allows you to define the report structure and the computation fields to be calculated.

3. :ref:`Report View : A wrapper around the generator exposing the generator API in a ``FormView`` subclass that you can hook straight to your urls.
   It provide a :ref:`Filter Form <filter_form>` to filter the report on.
   It mimics the Generator API interface, so knowing one is enough to work with the other.

4. Charting JS helpers: Django slick Reporting comes with highcharts and Charts js helpers libraries to plot the data generated.



Settings
--------

1. ``SLICK_REPORTING_DEFAULT_START_DATE``: Default: the beginning of the current year
2. ``SLICK_REPORTING_DEFAULT_END_DATE``: Default: the end of the current  year.
3. ``SLICK_REPORTING_FORM_MEDIA``: Controls the media files required by the search form.
   Defaults is:

.. code-block:: python

    SLICK_REPORTING_FORM_MEDIA = {
        "css": {
            "all": (
                "https://cdn.datatables.net/v/bs4/dt-1.10.20/datatables.min.css",
                "https://cdnjs.cloudflare.com/ajax/libs/Chart.js/2.9.3/Chart.min.css",
            )
        },
        "js": (
            "https://code.jquery.com/jquery-3.3.1.slim.min.js",
            "https://cdn.datatables.net/v/bs4/dt-1.10.20/datatables.min.js",
            "https://cdnjs.cloudflare.com/ajax/libs/Chart.js/2.9.3/Chart.bundle.min.js",
            "https://cdnjs.cloudflare.com/ajax/libs/Chart.js/2.9.3/Chart.min.js",
            "https://code.highcharts.com/highcharts.js",
        ),
    }

4. ``SLICK_REPORTING_DEFAULT_CHARTS_ENGINE``: Controls the default chart engine used.

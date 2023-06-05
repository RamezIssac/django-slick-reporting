.. _structure:

Structure
==========

If you haven't yet, please check https://django-slick-reporting.com for a quick walk-though with live code examples..

And now, Let's explore the main components of Django Slick Reporting and what setting you can set on project level.

Components
----------
These are the main components of Django Slick Reporting, ordered from low level to high level:

1. Report Field: represent a calculation unit, for example: a Sum or a Count of a certain field.
   The report field identifies how the calculation should be done. ReportFields can depend on each other.

2. Generator: The heart of the reporting engine , It's responsible for computing and generating the data and provides low level access.

3. View: A wrapper around the generator exposing the generator options in a FormView that you can hook straight to your urls.
   It also provide a Search Form to filter the report on.
   It mimics the Generator API interface, so knowing one is enough to work with the other.

4. Charting JS helpers: Django slick Reporting comes with highcharts and Charts js helpers libraries to plot the data generated.


Types of Reports
----------------

1. Time Series: A report that is grouped by a date field, and the report fields are calculated on each group.
   For example: Sum of sales per month, Count of sales per day, etc..

2. Cross Tab: shows data in rows and columns with information summarized at the intersection points.
    For example: Sum of product sales per month, crosstab by client would show Products as rows, clients included in the crosstab_ids as columns.

3. Grouped: A report that is grouped by a field, and the report fields are calculated on each group.
   For example: Sum of sales per product, Count of sales per product, etc..

4. Flat: A report that is not grouped, similar to what an admin list view would show.
   For example: Sales Transactions log



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

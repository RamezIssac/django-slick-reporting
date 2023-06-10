.. _structure:

Structure
==========

If you haven't yet, please check https://django-slick-reporting.com for a quick walk-though with live code examples..

And now, Let's explore the main components of Django Slick Reporting and what setting you can set on project level.

Components
----------
These are the main components of Django Slick Reporting

#. :ref:`Report View <report_view>`: A ``FormView`` CBV subclass with reporting capabilities allowing you to create different types of reports in the view.
   It provide a default :ref:`Filter Form <filter_form>` to filter the report on.
   It mimics the Generator API interface, so knowing one is enough to work with the other.

#. :ref:`Generator <report_generator>`: Responsible for generating report and orchestrating and calculating the computation fields values and mapping them to the results.
   It has an intuitive API that allows you to define the report structure and the computation fields to be calculated.

#. :ref:`Computation Field <computation_field>`: a calculation unit,like a Sum or a Count of a certain field.
   Computation field class set how the calculation should be done. ComputationFields can also depend on each other.

#. Charting JS helpers: Highcharts and Charts js helpers libraries to plot the data generated. so you can create the chart in 1 line in the view


Types of reports
----------------
We can categorize the output of the reports in this package into 4 sections:

#. Grouped report: similar to what we'd do with a GROUP BY sql statement. We group by a field and do some kind of calculations over the grouped records.
#. Time series report: a step up from the grouped report, where the calculations are computed for each time period (day, week, month, etc).
#. Crosstab report: a report where the results shows the relationship between two or more variables. Example: Rows are the clients, columns are the products, and the intersection values are the sum of sales for each client and product combination. This report can be created in time series as well. Example: Rows are the clients, columns are the products, and the intersection values are the sum of sales for each client and product combination, for each month.
#. List report: Similar to a django changelist, it's a direct view of the report model records with some extra features like sorting, filtering, pagination, etc.




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

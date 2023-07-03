.. _structure:

How the documentation is organized
==================================

:ref:`Tutorial <tutorial>`
--------------------------

If you are new to Django Slick Reporting, start here. It's a step-by-step guide to building a simple report(s).


:ref:`How-to guides <how_to>`
-----------------------------

Practical, hands-on guides that show you how to achieve a specific goal with Django Slick Reporting. Like customizing the form, creating a computation field, etc.


:ref:`Topic Guides <topics>`
----------------------------

Discuss each type of reports you can create with Django Slick Reporting and their options.

    * :ref:`Grouped report <group_by_topic>`: Similar to what we'd do with a GROUP BY sql statement. We group by a field and do some kind of calculations over the grouped records.
    * :ref:`time_series`: A step up from the grouped report, where the calculations are computed for each time period (day, week, month, etc).
    * :ref:`crosstab_reports`: Where the results shows the relationship between two or more variables. Example: Rows are the clients, columns are the products, and the intersection values are the sum of sales for each client and product combination. This report can be created in time series as well. Example: Rows are the clients, columns are the products, and the intersection values are the sum of sales for each client and product combination, for each month.
    * :ref:`list_reports`: Similar to a django changelist, it's a direct view of the report model records with some extra features like sorting, filtering, pagination, etc.
    * And other topics like how to customize the form, and extend the exporting options.


:ref:`Reference <reference>`
----------------------------

Detailed information about main on Django Slick Reporting's main components, such as the :ref:`Report View <report_view_options>`, :ref:`Generator <report_generator>`, :ref:`Computation Field <computation_field>`, etc.

    #. :ref:`Report View <report_view_options>`: A ``FormView`` CBV subclass with reporting capabilities allowing you to create different types of reports in the view.
       It provide a default :ref:`Filter Form <filter_form>` to filter the report on.
       It mimics the Generator API interface, so knowing one is enough to work with the other.

    #. :ref:`Generator <report_generator>`: Responsible for generating report and orchestrating and calculating the computation fields values and mapping them to the results.
       It has an intuitive API that allows you to define the report structure and the computation fields to be calculated.

    #. :ref:`Computation Field <computation_field>`: a calculation unit,like a Sum or a Count of a certain field.
       Computation field class set how the calculation should be done. ComputationFields can also depend on each other.

    #. Charting JS helpers: Highcharts and Charts js helpers libraries to plot the data generated. so you can create the chart in 1 line in the view




Demo site
---------

If you haven't yet, please check https://django-slick-reporting.com for a quick walk-though with live code examples..

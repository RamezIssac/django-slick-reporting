.. _structure:

Welcome to Django Slick Reporting documentation!
==================================================

Django Slick Reporting a reporting engine allowing you to create and chart different kind of analytics from your model in a breeze.

Demo site
---------

If you haven't yet, please check https://django-slick-reporting.com for a quick walk-though with live code examples..



:ref:`Tutorial <tutorial>`
--------------------------

The tutorial will guide you to what is slick reporting, what kind of reports it can do for you and how to use it in your project.



:ref:`Topic Guides <topics>`
----------------------------

Discuss each type of report main structures you can create with Django Slick Reporting and their options.

    * :ref:`Group By report <group_by_topic>`: Similar to what we'd do with a GROUP BY sql statement. We group by a field and do some kind of calculations over the grouped records.
    * :ref:`time_series`: A step further, where the calculations are computed for time periods (day, week, month, custom etc).
    * :ref:`crosstab_reports`: Where the results shows the relationship between two or more variables. It's a table that shows the distribution of one variable in rows and another in columns.
    * :ref:`list_reports`: Similar to a django admin's changelist, it's a direct view of the report model records
    * And other topics like how to customize the form, and extend the exporting options.


:ref:`Reference <reference>`
----------------------------

Detailed information about main on Django Slick Reporting's main components

    #. :ref:`Settings <settings>`: The settings you can use to customize the behavior of Django Slick Reporting.
    #. :ref:`Report View <report_view_options>`: A ``FormView`` CBV subclass with reporting capabilities allowing you to create different types of reports in the view.
       It provide a default :ref:`Filter Form <filter_form>` to filter the report on.
       It mimics the Generator API interface, so knowing one is enough to work with the other.

    #. :ref:`Generator <report_generator>`: Responsible for generating report and orchestrating and calculating the computation fields values and mapping them to the results.
       It has an intuitive API that allows you to define the report structure and the computation fields to be calculated.

    #. :ref:`Computation Field <computation_field>`: a calculation unit,like a Sum or a Count of a certain field.
       Computation field class set how the calculation should be done. ComputationFields can also depend on each other.

    #. Charting JS helpers: Highcharts and Charts js helpers libraries to plot the data generated. so you can create the chart in 1 line in the view




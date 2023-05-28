
Report View Options
===================

We can categorize the output of a report into 4 sections:

* List report: Similar to a django changelist, it's a direct view of the report model records with some extra features like sorting, filtering, pagination, etc.
* Grouped report: similar to what you'd expect from a SQL group by query, it's a list of records grouped by a certain field
* Time series report: a step up from the grouped report, where the results are computed for each time period (day, week, month, year, etc) or you can specify a custom periods.
* Crosstab report: It's a report where a table showing the relationship between two or more variables. (like Client sales of each product comparison)



General Options
---------------

* columns

Columns can be a list of column names , or a tuple of (column name, options dictionary) pairs.

example:

.. code-block:: python

    class MyReport()
        columns = [
            'id',
            ('name', {'verbose_name': "My verbose name", is_summable=False}),
            'description',
        ]



* date_field: the date field to be used in filtering and computing (ie: the time series report).

* report_model: the model where the relevant data is stored, in more complex reports, it's usually a database view / materialized view.

* report_title: the title of the report to be displayed in the report page.

* group_by : the group by field, if not specified, the report will be a list report.

* excluded_fields

* chart_settings : a list of dictionary (or Chart object) of charts you want to attach to the report.






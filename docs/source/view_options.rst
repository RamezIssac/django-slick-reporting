
Report View Options
===================

We can categorize the output of a report into 4 sections:

* List report: Similar to a django changelist, it's a direct view of the report model records with some extra features like sorting, filtering, pagination, etc.
* Grouped report: similar to what you'd expect from a SQL group by query, it's a list of records grouped by a certain field
* Time series report: a step up from the grouped report, where the results are computed for each time period (day, week, month, year, etc) or you can specify a custom periods.
* Crosstab report: It's a report where a table showing the relationship between two or more variables. (like Client sales of each product comparison)



``ReportView`` Options
----------------------

.. attribute:: ReportView.report_model

    the model where the relevant data is stored, in more complex reports, it's usually a database view / materialized view.

.. attribute:: ReportView.queryset

        the queryset to be used in the report, if not specified, it will default to ``report_model._default_manager.all()``


.. attribute:: ReportView.columns

    Columns can be a list of column names , or a tuple of (column name, options dictionary) pairs.

    Example:

    .. code-block:: python

        class MyReport()
            columns = [
                'id',
                ('name', {'verbose_name': "My verbose name", is_summable=False}),
                'description',
            ]


    Columns names can be

    *. A Computation Field

    *. If group_by is set and it's a foreign key, then any field on the group_by model

    *. If group_by is not set, then any field name on the report_model / queryset

    *. A callable on the view /or the generator, that takes the record as a parameter and returns a value.

    *. A Special ``__time_series__``, and ``__crosstab__``
       Those are used to control the position of the time series inside the columns, defaults it's appended at the end


.. attribute:: ReportView.date_field

    the date field to be used in filtering and computing

.. attribute:: ReportView.start_date_field_name

        the name of the start date field, if not specified, it will default to ``date_field``

.. attribute:: ReportView.end_date_field_name

        the name of the end date field, if not specified, it will default to ``date_field``


.. attribute:: ReportView.report_title

        the title of the report to be displayed in the report page.

.. attribute:: ReportView.report_title_context_key

        the context key to be used to pass the report title to the template, default to ``title``.

* group_by : the group by field, if not specified, the report will be a list report.

* excluded_fields

* chart_settings : a list of dictionary (or Chart object) of charts you want to attach to the report.






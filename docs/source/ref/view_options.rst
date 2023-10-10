.. _report_view_options:

General Options
================



Below is the list of general options that is used across all types of reports.


.. attribute:: ReportView.report_model

    The model where the relevant data is stored, in more complex reports, it's usually a database view / materialized view.

.. attribute:: ReportView.queryset

        The queryset to be used in the report, if not specified, it will default to ``report_model._default_manager.all()``


.. attribute:: ReportView.columns

    Columns can be a list of column names , or a tuple of (column name, options dictionary) pairs.

    Example:

    .. code-block:: python

        class MyReport(ReportView):
            columns = [
                "id",
                ("name", {"verbose_name": "My verbose name", "is_summable": False}),
                "description",
                # A callable on the view /or the generator, that takes the record as a parameter and returns a value.
                ("get_full_name", {"verbose_name": "Full Name", "is_summable": False}),
            ]

            def get_full_name(self, record):
                return record["first_name"] + " " + record["last_name"]


    Here is a list of all available column options available. A column can be

    * A Computation Field. Added as a class or by its name if its registered see :ref:`computation_field`

        Example:

            .. code-block:: python

                    class MyTotalReportField(ComputationField):
                        pass


                    class MyReport(ReportView):
                        columns = [
                            # a computation field created on the fly
                            ComputationField.create(Sum, "value", verbose_name=_("Value"), name="value"),
                            # A computation Field class
                            MyTotalReportField,
                            # a computation field registered in the computation field registry
                            "__total__",
                        ]




    * If group_by is set and it's a foreign key, then any field on the grouped by model.

        Example:

        .. code-block:: python

                class MyReport(ReportView):
                    report_model = MySales
                    group_by = "client"
                    columns = [
                        "name",  # field that exists on the Client Model
                        "date_of_birth",  # field that exists on the Client Model
                        "agent__name",  # field that exists on the Agent Model related to the Client Model
                        # calculation fields
                    ]




    * If group_by is not set, then
        1. Any field name on the report_model / queryset
        2. A calculation field, in this case the calculation will be made on the whole set of records, not on each group.
           Example:

                .. code-block:: python

                    class MyReport(ReportView):
                        report_model = MySales
                        group_by = None
                        columns = [
                            ComputationField.create(Sum, "value", verbose_name=_("Value"), name="value")
                        ]

            Above code will return the calculated sum of all values in the report_model / queryset

    * A callable on the view /or the generator, that takes the record as a parameter and returns a value.

    * A Special ``__time_series__``, and ``__crosstab__``

       Those are used to control the position of the time series inside the columns, defaults it's appended at the end


.. attribute:: ReportView.date_field

    the date field to be used in filtering and computing

.. attribute:: ReportView.start_date_field_name

        the name of the start date field, if not specified, it will default to ``date_field``

.. attribute:: ReportView.end_date_field_name

        the name of the end date field, if not specified, it will default to ``date_field``


.. attribute:: ReportView.group_by

        the group by field, it can be a foreign key, a text field, on the report model or traversing a foreign key.

        Example:

        .. code-block:: python

            class MyReport(ReportView):
                report_model = MySalesModel
                group_by = "client"
                # OR
                # group_by = 'client__agent__name'
                # OR
                # group_by = 'client__agent'


.. attribute:: ReportView.report_title

        the title of the report to be displayed in the report page.

.. attribute:: ReportView.report_title_context_key

        the context key to be used to pass the report title to the template, default to ``title``.


.. attribute:: ReportView.chart_settings

        A list of Chart objects representing the charts you want to attach to the report.

        Example:

        .. code-block:: python

            class MyReport(ReportView):
                report_model = Request
                # ..
                chart_settings = [
                    Chart(
                        "Browsers",
                        Chart.PIE,
                        title_source=["user_agent"],
                        data_source=["count__id"],
                        plot_total=True,
                    ),
                    Chart(
                        "Browsers Bar Chart",
                        Chart.BAR,
                        title_source=["user_agent"],
                        data_source=["count__id"],
                        plot_total=True,
                    ),
                ]


.. attribute:: ReportView.default_order_by

        Default order by for the results. Ordering can also be controlled on run time by passing order_by='field_name' as a parameter to the view.
        As you would expect, for DESC order: default_order_by (or order_by as a parameter) ='-field_name'

.. attribute:: ReportView.template_name

        The template to be used to render the report, default to ``slick_reporting/simple_report.html``
        You can override this to customize the report look and feel.

.. attribute:: ReportView.limit_records

        Limit the number of records to be displayed in the report, default to ``None`` (no limit)

.. attribute:: ReportView.swap_sign

            Swap the sign of the values in the report, default to ``False``


.. attribute:: ReportView.csv_export_class

        Set the csv export class to be used to export the report, default to ``ExportToStreamingCSV``

.. attribute:: ReportView.report_generator_class

        Set the generator class to be used to generate the report, default to ``ReportGenerator``

.. attribute:: ReportView.with_type

        Set if double sided calculations should be taken into account, default to ``False``
        Read more about double sided calculations here https://django-erp-framework.readthedocs.io/en/latest/topics/doc_types.html

.. attribute:: ReportView.doc_type_field_name

        Set the doc_type field name to be used in double sided calculations, default to ``doc_type``

.. attribute:: ReportView.doc_type_plus_list

        Set the doc_type plus list to be used in double sided calculations, default to ``None``

.. attribute:: ReportView.doc_type_minus_list

            Set the doc_type minus list to be used in double sided calculations, default to ``None``



Hooks and functions
====================

.. attribute:: ReportView.get_queryset()

        Override this function to return a custom queryset to be used in the report.

.. attribute:: ReportView.get_report_title()

        Override this function to return a custom report title.

.. attribute:: ReportView.ajax_render_to_response()

            Override this function to return a custom response for ajax requests.

.. attribute:: ReportView.format_row()

        Override this function to return a custom row format.

.. attribute:: ReportView.filter_results(data, for_print=False)

        Hook to Filter results, usable if you want to do actions on the data set based on computed data (like eliminate __balance__ = 0, etc)
        :param data: the data set , list of dictionaries
        :param for_print: if the data is being filtered for printing or not
        :return: the data set after filtering.

.. attribute:: ReportView.get_form_crispy_helper()

        Override this function to return a custom crispy form helper for the report form.


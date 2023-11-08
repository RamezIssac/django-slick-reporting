.. _report_view_options:

================
The Report View
================


Below is the list of options that can be used in the ReportView class.


Core Options
=============

report_model
------------

The model where the relevant data is stored, in more complex reports,
it's usually a database view / materialized view.
You can customize it at runtime via the ``get_report_model`` hook.

.. code-block:: python

    class MyReportView(ReportView):

        def get_report_model(self):
            from my_app.models import MyReportModel
            return MyReportModel.objects.filter(some_field__isnull=False)


queryset
--------

The queryset to be used in the report,
if not specified, it will default to ``report_model._default_manager.all()``

group_by
--------

If the data in the report_model needs to be grouped by a field.
It can be a foreign key, a text field / choice field on the report model or traversing.

Example:
Assuming we have the following SalesModel

.. code-block:: python

            class SalesModel(models.Model):
                date = models.DateTimeField()
                notes = models.TextField(blank=True, null=True)
                client = models.ForeignKey(
                    "client.Client", on_delete=models.PROTECT, verbose_name=_("Client")
                )
                product = models.ForeignKey(
                    "product.Product", on_delete=models.PROTECT, verbose_name=_("Product")
                )
                value = models.DecimalField(max_digits=9, decimal_places=2)
                quantity = models.DecimalField(max_digits=9, decimal_places=2)
                price = models.DecimalField(max_digits=9, decimal_places=2)

Our ReportView can have the following group_by options:

.. code-block:: python

            from slick_reporting.views import ReportView

            class MyReport(ReportView):
                report_model = SalesModel
                group_by = "product"  # a field on the model
                # OR
                # group_by = 'client__country' a traversing foreign key field
                # group_by = 'client__gender' a traversing  choice field




columns
-------
Columns are a list of column names and to make it more flexible,
you can pass a tuple of column name and options.
The options are only `verbose_name` and `is_summable`.

like this:

.. code-block:: python

        class MyReport(ReportView):
                    columns = [
                        "id",
                        ("name", {"verbose_name": "My verbose name", "is_summable": False}),
                        ]



A column name can be any of the following:

1. A computation field
2. A field on the grouped by model
3. A callable on the view /or the generator
4. A Special ``__time_series__``, ``__crosstab__``, ``__index__``

Let's take them one by one:

1. A Computation Field.
~~~~~~~~~~~~~~~~~~~~~~~~~~

Added as a class or by its name.
Example:

.. code-block:: python

                from slick_reporting.fields import ComputationField, Sum
                from slick_reporting.registry import field_registry
                from slick_reporting.views import ReportView

                @field_registry.register
                class MyTotalReportField(ComputationField):
                    name = "__some_special_name__"

                class MyReport(ReportView):
                    columns = [
                        ComputationField.create(Sum, "value", verbose_name=_("Value"), name="value"),
                        # a computation field created on the fly

                        MyTotalReportField, # Added a a class

                        "__some_special_name__", # added by name
                    ]

For more information: :ref:`computation_field`


2. Fields on the group by model
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Implying that the group_by is set to a field on the report_model.

.. code-block:: python

        class MyReport(ReportView):
            report_model = SalesModel
            group_by = "client"
            columns = [
                "name",  # field that exists on the Client Model
                "date_of_birth",  # field that exists on the Client Model
                "agent__name",  # a traversing field from client model
                # ...
            ]

         # If the group_by is traversing then the available columns would be of the model at the end of the traversing
        class MyOtherReport(ReportView):
            report_model = MySales
            group_by = "client__agent"
            columns = [
                "name",
                "country",  # fields that exists on the Agent Model
                "contact__email",  # A traversing field from the Agent model
            ]


.. note::

    If group_by is not set, columns can be only a calculation field. refer to the topic `no_group_by_topic`


3. A callable on the view
~~~~~~~~~~~~~~~~~~~~~~~~~~~

The callable should accept the following arguments

        :param obj: a dictionary of the current group_by row
        :param row: a the current row of the report.
        :return: the value to be displayed in the report


.. code-block:: python

    class Report(ReportView):
        columns = [ "field_on_group_by_model", "group_by_model__traversing_field",
                    "get_attribute", ComputationField.create(name="example")]

        def get_attribute(self, obj: dict, row: dict):
             # obj: a dictionary of the current group_by row
             # row: a the current row of the report.

            return f"{obj["field_on_group_by_model_2"]} - {row["group_by_model__traversing_field"]}"

        get_attribute.verbose_name = "My awesome title"


4. A Special ``__time_series__``, ``__crosstab__``, ``__index__``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``__time_series__``: is used to control the position of the time series columns inside the report.

``__crosstab__``: is used to control the position of the crosstab columns inside the report.

``__index__``: is used to display the index of the report, it's usually used with the ``group_by_custom_querysets`` option.



date_field
----------

The date field to be used in filtering and computing

start_date_field_name
---------------------
The name of the start date field, if not specified, it will default to what set in ``date_field``

end_date_field_name
-------------------
The name of the end date field, if not specified, it will default to ``date_field``



chart_settings
--------------
A list of Chart objects representing the charts you want to attach to the report.

        Example:

        .. code-block:: python

            class MyReport(ReportView):
                report_model = Request
                # ..
                chart_settings = [
                    Chart(
                        title="Browsers",
                        type=Chart.PIE, # or just string "bar"
                        title_source=["user_agent"],
                        data_source=["count__id"],
                        plot_total=False,
                    ),
                    Chart(
                        "Browsers Bar Chart",
                        Chart.BAR,
                        title_source=["user_agent"],
                        data_source=["count__id"],
                        plot_total=True,
                    ),
                ]


form_class
----------
The form you need to display to control the results.
Default to an automatically generated form containing the start date, end date and all foreign keys on the model.
For more information: `filter_form`

excluded_fields
-----------------
Fields to be excluded from the automatically generated form


auto_load
--------------
Control if the report should be loaded automatically on page load or not, default to ``True``


``report_title``
----------------
The title of the report to be displayed in the report page.

``report_title_context_key``
----------------------------
The context key to be used to pass the report title to the template, default to ``report_title``.



``template_name``
-----------------

The template to be used to render the report, default to ``slick_reporting/report.html``
You can override this to customize the report look and feel.


``csv_export_class``
--------------------
Set the csv export class to be used to export the report, default to ``ExportToStreamingCSV``


``report_generator_class``
--------------------------
Set the generator class to be used to generate the report, default to ``ReportGenerator``

``default_order_by``
--------------------
A Default order by for the results.
As you would expect, for DESC order: default_order_by (or order_by as a parameter) ='-field_name'

.. note::

    Ordering can also be controlled at run time by passing order_by='field_name' as a parameter to the view.


``limit_records``
-----------------

Limit the number of records to be displayed in the report, default to ``None`` (no limit)

``swap_sign``
--------------
Swap the sign of the values in the report, default to ``False``


Double Sided Calculations Options
==================================

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


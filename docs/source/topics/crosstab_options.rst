.. _crosstab_reports:

Crosstab Reports
=================
Use crosstab reports, also known as matrix reports, to show the relationships between three or more query items.
Crosstab reports show data in rows and columns with information summarized at the intersection points.


General use case
----------------
Here is a general use case:

.. code-block:: python

    from django.utils.translation import gettext_lazy as _
    from django.db.models import Sum
    from slick_reporting.views import ReportView


    class MyCrosstabReport(ReportView):
        group_by = "product"
        crosstab_field = "client"
        # the column you want to make a crosstab on, can be a foreign key or a choice field

        crosstab_columns = [
            SlickReportField.create(Sum, "value", verbose_name=_("Value")),
        ]

        crosstab_ids = [
            1,
            2,
        ]  # a list of ids of the crosstab field you want to use. This will be passed on by the filter form, or , if set here, values here will be used.
        # OR in case of a choice / text field
        # crosstab_ids = ["my-choice-1", "my-choice-2", "my-choice-3"]

        crosstab_compute_remainder = True
        # Compute reminder will add a column with the remainder of the crosstab computed
        # Example: if you choose to do a cross tab on clientIds 1 & 2 , cross tab remainder will add a column with the calculation of all clients except those set/passed in crosstab_ids

        columns = [
            "name",
            "sku",
            "__crosstab__",
            # You can customize where the crosstab columns are displayed in relation to the other columns
            SlickReportField.create(Sum, "value", verbose_name=_("Total Value")),
            # This is the same as the Same as the calculation in the crosstab, but this one will be on the whole set. IE total value
        ]


Customizing the crosstab ids
----------------------------

For more fine tuned report, You can customize the ids of the crosstab report by suppling a list of tuples to the ``crosstab_ids_custom_filters`` attribute.
the tuple should have 2 items, the first is a Q object(s) -if any- , and the second is a dict of kwargs filters that will be passed to the filter method of the ``report_model``.

Example:

.. code-block:: python

        from .models import MySales


        class MyCrosstabReport(ReportView):

            date_field = "date"
            group_by = "product"
            report_model = MySales

            crosstab_columns = [
                SlickReportField.create(Sum, "value", verbose_name=_("Value")),
            ]

            crosstab_ids_custom_filters = [
                (
                    ~Q(special_field="something"),
                    dict(flag="sales"),
                ),  # special_field and flag are fields on the report_model .
                (None, dict(flag="sales-return")),
            ]

            # These settings has NO EFFECT if crosstab_ids_custom_filters is set
            crosstab_field = "client"
            crosstab_ids = [1, 2]
            crosstab_compute_remainder = True



Having Time Series Crosstab Reports
-----------------------------------
You can have a crosstab report in a time series by setting the :ref:`time_series_options` in addition to the crosstab options.


Customizing the verbose name of the crosstab columns
----------------------------------------------------
You can customize the verbose name of the crosstab columns by Customizing the ``ReportField`` and setting the ``crosstab_field_verbose_name`` attribute to your custom class.
Default is that the verbose name will display the id of the crosstab field, and the remainder column will be called "The remainder".


.. code-block:: python

        class CustomCrossTabTotalField(SlickReportField):

            calculation_field = "value"
            calculation_method = Sum
            verbose_name = _("Total Value")

            @classmethod
            def get_crosstab_field_verbose_name(cls, model, id):
                from .models import Client

                if id == "----":  # the remainder column
                    return _("Rest of clients")
                name = Client.objects.get(pk=id).name
                # OR if you crosstab on a choice field
                # name = get_choice_name(model, "client", id)
                return f"{cls.verbose_name} {name}"


Example
-------

.. code-block:: python

    from .models import MySales


    class MyCrosstabReport(ReportView):

        date_field = "date"
        group_by = "product"
        report_model = MySales
        crosstab_field = "client"

        crosstab_columns = [
            SlickReportField.create(Sum, "value", verbose_name=_("Value")),
        ]

        crosstab_ids = [1, 2]  # either set here via the filter form
        crosstab_compute_remainder = True


The above code would return a result like this:

.. image:: _static/crosstab.png
  :width: 800
  :alt: crosstab
  :align: center


1. The Group By. In this example, it is the product field.
2. The Crosstab. In this example, it is the client field. crosstab_ids were set to client 1 and client 2
3. The remainder. In this example, it is the rest of the clients. crosstab_compute_remainder was set to True

.. _list_reports:

List Reports
============


It's a simple ListView / admin changelist like report to display data in a model.
It's quite similar to ReportView except there is no calculation by default.

Here is the options you can use to customize the report:

#. ``columns``: a list of report_model fields to be displayed in the report, which support traversing

.. code-block:: python

    class RequestLog(ListReportView):
        report_model = SalesTransaction
        columns = [
            "id",
            "date",
            "client__name",
            "product__name",
            "quantity",
            "price",
            "value",
        ]


#. ``filters``: a list of report_model fields to be used as filters.

.. code-block:: python

    class RequestLog(ListReportView):
        report_model = SalesTransaction
        columns = [
            "id",
            "date",
            "client__name",
            "product__name",
            "quantity",
            "price",
            "value",
        ]

        filters = ["product", "client"]




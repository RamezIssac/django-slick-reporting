================
Group By Reports
================

Group by reports are reports that group the data by a specific field. For example, a report that groups the expenses by the expense type.

Example:

.. code-block:: python

    class ExpenseTotal(ReportView):
        report_model = ExpenseTransaction
        report_title = _("Expenses Daily")
        group_by = "expense"

        columns = [
            "name", # name field on the expense model
            SlickReportField.create(Sum, "value", verbose_name=_("Total Expenditure"), name="value"),
        ]


Group by can also be a traversing field


.. note::
    If the group by field is a traversing field, the report will be grouped by the last field in the traversing path.
    and the columns available will be the fields on the last model in the traversing path.


Example:

.. code-block:: python

    class ExpenseTotal(ReportView):
        report_model = ExpenseTransaction
        report_title = _("Expenses Daily")
        group_by = "expense__expensecategory" # Note the traversing

        columns = [
            "name", # name field on the ExpenseCategory model
            SlickReportField.create(Sum, "value", verbose_name=_("Value"), name="value"),
        ]

A Sample group by report would look like this:

.. image:: _static/group_report.png
  :width: 800
  :alt: Group Report
  :align: center



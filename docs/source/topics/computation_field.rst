.. _computation_field:


Computation Field
=================

ComputationFields are the basic unit in a report.they represent a number that is being computed.

Computation Fields can be add to a report as a class, as you saw in other examples , or by name.


Reusing Computation Fields
---------------------------

You do not have to create the Computation Field each time you need one. You can create one and register it and reuse it.

Let's say you want to compute the total quantity of a product in a report.

.. code-block:: python

    from slick_reporting.fields import ComputationField
    from slick_reporting.decorators import report_field_register


    @report_field_register
    class TotalQTYReportField(ComputationField):
        name = '__total_quantity__' # The name to use when using this field in the generator
        calculation_field = 'quantity' # the field we want to compute on
        calculation_method = Sum  # What method we want, default to Sum
        verbose name = 'Total quantity' # A verbose name

    class ProductSales(ReportView):
        report_title = _("Product Sales")
        report_model = SalesTransaction
        date_field = "date"
        group_by = "product"

        columns = [
            "name",
            "__total_quantity__",
            ]

Above we created the Computation Field
1. Created a ComputationField subclass and gave it the needed attributes
2. Register it via ``report_field_register`` so it can be picked up by the framework
3. Used it by name inside the columns attribute (or in time_series_columns, or in crosstab_columns)

So another example, If you want AVG to the field `price` then it would look like this

.. code-block:: python

    from django.db.models import Avg
    from slick_reporting.decorators import report_field_register

    @report_field_register
    class TotalQTYReportField(ComputationField):
        name = '__avg_price__'
        calculation_field = 'price'
        calculation_method = Avg
        verbose name = 'Avg. Price'

    class ProductSales(ReportView):
        # ..
        columns = [
            "name",
            "__avg_price__",
            ]

Using Value of a Computation Field within a another
---------------------------------------------------

Sometime you want to stack values on top of each other. For example: Net revenue = Gross revenue - Discounts.

.. code-block:: python

    class PercentageToTotalBalance(ComputationField):
        requires = [BalanceReportField]
        name = "__percent_to_total_balance__"
        verbose_name = _("%")
        calculation_method = Sum
        calculation_field = "value"

        prevent_group_by = True

        def final_calculation(self, debit: float, credit: float, required_results: dict):
            obj_balance = required_results.get("__balance__")
            total = debit - credit
            return (obj_balance / total) * 100

We need to override ``final_calculation`` to do the needed calculation. The ``required_results`` is a dictionary of the results of the required fields, where the keys are the names.

How it works ?
--------------
When the `ReportGenerator` is initialized, it generates a list of the needed fields to be displayed and computed.
Each computation field in the report is given the filters needed and asked to get all the results prepared.
Then for each record, the ReportGenerator again asks each ComputationField to get the data it has for each record and map it back.


Customizing the Calculation Flow:
---------------------------------

The results are prepared in 2 main stages

1. Preparation: Where you can get the whole result set for the report. Example: Sum of all the values in a model group by the products.
2. resolve: Where you get the value for each record.




.. code-block:: python

    class MyCustomComputationField(ComputationField):
        name = "__custom_field__"

        def prepare(self, q_filters: list | object = None, kwargs_filters: dict = None, queryset=None, **kwargs):
            # do all you calculation here for the whole set if any and return the prepared results
            pass

        def resolve(self, prepared_results, required_computation_results: dict, current_pk, current_row=None) -> float:
            # does the calculation for each record, return a value
            pass

Bundled Report Fields
---------------------
As this project came form an ERP background, there are some bundled report fields that you can use out of the box.

* __total__ : `Sum` of the field named `value`
* __total_quantity__ : `Sum` of the field named `quantity`
* __fb__ : First Balance, Sum of the field `value` on the start date (or period in case of time series)
* __balance__: Compound Sum of the field `value`. IE: the sum of the field `value` on end date.
* __credit__: Sum of field Value for the minus_list
* __debit__: Sum of the field value for the plus list
* __percent_to_total_balance__: Percent of the field value to the balance

Difference between total and balance is:

Total: Sum of the value for the period
Balance: Sum of the value for the period + all the previous periods.

Example:
Case: You have a client that buys 10 in Jan, 12 in Feb and 13 in March.
`__total__` will return 10 in Jan, 12 in Feb and 13 in March.
`__balance__` will return 10 in Jan, 22 in Feb and 35 in March




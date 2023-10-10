.. _computation_field:


Computation Field
=================

ComputationFields are the basic unit in a report.they represent a number that is being computed.

Computation Fields can be add to a report as a class, as you saw in other examples , or by name.


Creating Computation Fields
---------------------------

There are 3 ways you can create a Computation Field

1. Create a subclass of ComputationField and set the needed attributes and use it in the columns attribute of the ReportView
2. Use the `ComputationField.create()` method and pass the needed attributes and use it in the columns attribute of the ReportView
3. Use the `report_field_register` decorator to register a ComputationField subclass and use it by its name in the columns attribute of the ReportView



.. code-block:: python

    from slick_reporting.fields import ComputationField
    from slick_reporting.decorators import report_field_register


    @report_field_register
    class TotalQTYReportField(ComputationField):
        name = "__total_quantity__"
        calculation_field = "quantity"  # the field we want to compute on
        calculation_method = Sum  # What method we want, default to Sum
        verbose_name = _("Total quantity")


    class ProductSales(ReportView):
        report_model = SalesTransaction
        # ..
        columns = [
            # ...
            "__total_quantity__",  # Use the ComputationField by its registered name
            TotalQTYReportField,  # Use Computation Field as a class
            ComputationField.create(
                Sum, "quantity", name="__total_quantity__", verbose_name=_("Total quantity")
            )
            # Using the ComputationField.create() method
        ]

What happened here is that we:

1. Created a ComputationField subclass and gave it the needed attributes
2. Register it via ``report_field_register`` so it can be picked up by the framework.
3. Used it by name inside the columns attribute (or in time_series_columns, or in crosstab_columns)
4. Note that this is same as using the class directly in the columns , also the same as using `ComputationField.create()`

Another example, adding and AVG to the field `price`:

.. code-block:: python

    from django.db.models import Avg
    from slick_reporting.decorators import report_field_register


    @report_field_register
    class TotalQTYReportField(ComputationField):
        name = "__avg_price__"
        calculation_field = "price"
        calculation_method = Avg
        verbose_name = _("Avg. Price")


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

        def resolve(
            self,
            prepared_results,
            required_computation_results: dict,
            current_pk,
            current_row=None,
        ) -> float:
            result = super().resolve(
                prepared_results, required_computation_results, current_pk, current_row
            )
            return required_computation_results.get("__balance__") / result * 100


We need to override ``resolve`` to do the needed calculation. The ``required_computation_results`` is a dictionary of the results of the required fields, where the keys are the names.

Note:

1. The ``requires`` attribute is a list of the required fields to be computed before this field.
2. The values of the ``requires`` fields are available in the ``required_computation_results`` dictionary.
3. In the example we used the ``prevent_group_by`` attribute. It's as the name sounds, it prevents the rows from being grouped for teh ComputationField giving us the result over the whole set.


How it works ?
--------------
When the `ReportGenerator` is initialized, it generates a list of the needed fields to be displayed and computed.
Each computation field in the report is given the filters needed and asked to get all the results prepared.
Then for each record, the ReportGenerator again asks each ComputationField to get the data it has for each record and map it back.


Customizing the Calculation Flow
--------------------------------

The results are prepared in 2 main stages

1. Preparation: Where you can get the whole result set for the report. Example: Sum of all the values in a model group by the products.
2. resolve: Where you get the value for each record.




.. code-block:: python

    class MyCustomComputationField(ComputationField):
        name = "__custom_field__"

        def prepare(
            self,
            q_filters: list | object = None,
            kwargs_filters: dict = None,
            queryset=None,
            **kwargs
        ):
            # do all you calculation here for the whole set if any and return the prepared results
            pass

        def resolve(
            self,
            prepared_results,
            required_computation_results: dict,
            current_pk,
            current_row=None,
        ) -> float:
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

What is the difference between total and balance fields ?

Total: Sum of the value for the period
Balance: Sum of the value for the period + all the previous periods.

Example: You have a client who buys 10 in Jan., 12 in Feb. and 13 in March:

* `__total__` will return 10 in Jan, 12 in Feb and 13 in March.
* `__balance__` will return 10 in Jan, 22 in Feb and 35 in March




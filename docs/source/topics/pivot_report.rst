.. _pivot_report_topic:

=============
Pivot Reports
=============

General use case
----------------

Pivot reports are designed for **pre-computed or pre-aggregated data** stored as rows in the database.
Instead of aggregating raw transactions at report time (like group by or crosstab reports do),
the ``PivotReportGenerator`` reads existing values and spreads a field's distinct values into columns.

This is common with:

* Materialized views or summary tables
* Data warehouse fact tables
* ETL pipeline outputs
* Pre-aggregated reporting tables
* Legacy tables with denormalized data

Example source data:

+------------+------------+-------------+----------------+
| product_id | month      | total_sales | total_quantity |
+============+============+=============+================+
| 1          | 2024-01-01 | 500         | 10             |
+------------+------------+-------------+----------------+
| 1          | 2024-02-01 | 600         | 12             |
+------------+------------+-------------+----------------+
| 2          | 2024-01-01 | 300         | 5              |
+------------+------------+-------------+----------------+
| 2          | 2024-02-01 | 400         | 8              |
+------------+------------+-------------+----------------+

The pivot report transforms this into:

+------------+-------------------+-------------------+
| product_id | total_sales Jan   | total_sales Feb   |
+============+===================+===================+
| 1          | 500               | 600               |
+------------+-------------------+-------------------+
| 2          | 300               | 400               |
+------------+-------------------+-------------------+


How it relates to crosstab and time series
------------------------------------------

The pivot concept is closely related to crosstab reports — both spread a field's distinct values as columns.
The difference:

* **Crosstab** aggregates raw data per pivot value using ``ComputationField``
* **Pivot** reads pre-existing values from the database — no aggregation

Pivot reports use the same crosstab metadata path for the frontend, so all existing chart types
(bar, line, pie, area) work with pivot data.


Basic example
-------------

.. code-block:: python

    from slick_reporting.views import ReportView, Chart
    from slick_reporting.generator import PivotReportGenerator

    class MonthlyProductSales(ReportView):
        report_model = MonthlySummary
        report_generator_class = PivotReportGenerator
        date_field = "month"
        group_by = "product_id"
        pivot_field = "month"
        pivot_columns = ["total_sales", "total_quantity"]
        columns = ["product_id", "__pivot__"]

        chart_settings = [
            Chart(
                "Monthly Sales",
                Chart.LINE,
                data_source=["total_sales"],
                title_source=["product_id"],
            ),
        ]

Key attributes:

* ``report_generator_class = PivotReportGenerator`` — use the pivot generator
* ``pivot_field`` — the column whose distinct values become the dynamic columns
* ``pivot_columns`` — list of database column names to read values from
* ``columns`` — use ``"__pivot__"`` as a placeholder for where pivot columns appear


Pivoting by a non-date field
-----------------------------

The pivot field doesn't have to be a date — it can be any column:

.. code-block:: python

    class SalesByRegion(ReportView):
        report_model = RegionalSummary
        report_generator_class = PivotReportGenerator
        group_by = "product_id"
        pivot_field = "region"
        pivot_columns = ["total_sales"]
        columns = ["product_id", "__pivot__"]

This produces one row per product with a column for each region.

.. note::

    When multiple source rows exist for the same ``(group_by, pivot_field)`` combination,
    the last row encountered is used. The pivot generator does **not** aggregate — if you
    need aggregation, use a standard crosstab or time series report instead.


Using with dynamic models
--------------------------

Pivot reports pair naturally with ``table_name`` for tables without a Django model:

.. code-block:: python

    class WarehouseReport(ReportView):
        table_name = "warehouse_monthly_sales"
        report_generator_class = PivotReportGenerator
        date_field = "period_date"
        group_by = "sku"
        pivot_field = "period_date"
        pivot_columns = ["revenue", "units_sold"]
        columns = ["sku", "__pivot__"]

See :ref:`dynamic_model_topic` for more on reporting from arbitrary database tables.


Using with ReportGenerator directly
------------------------------------

.. code-block:: python

    from slick_reporting.generator import PivotReportGenerator

    report = PivotReportGenerator(
        report_model=MonthlySummary,
        group_by="product_id",
        date_field="month",
        pivot_field="month",
        pivot_columns=["total_sales"],
        columns=["product_id", "__pivot__"],
        start_date=datetime.datetime(2024, 1, 1),
        end_date=datetime.datetime(2024, 6, 30),
    )
    data = report.get_report_data()


Date filtering
--------------

When ``date_field`` is set, the pivot generator respects ``start_date`` and ``end_date`` filters.
Only rows within the date range are included, and only pivot values found in those rows
appear as columns.


Pivot values with spaces or special characters
-----------------------------------------------

Pivot values like ``"New York"`` or ``"Q1/2024"`` are sanitized for use in column names
(non-alphanumeric characters replaced with underscores). The ``verbose_name`` preserves the
original value for display in tables and charts.

For example, a pivot value of ``"New York"`` produces:

* Column name: ``total_salesCTNew_York`` (sanitized, used internally)
* Verbose name: ``total_sales New York`` (original, displayed to users)


Limitations
-----------

* **No aggregation.** Pivot reads pre-existing values. If you need computation (Sum, Count, etc.),
  use a standard ``ReportGenerator`` with crosstab or time series.

* **Last value wins.** If multiple rows share the same ``(group_by, pivot_field)`` value,
  the last row's values are used.

* **No FK traversal.** When using dynamic models, foreign key columns are plain integers.
  Group by the column directly (e.g. ``product_id``) rather than traversing (``product__name``).

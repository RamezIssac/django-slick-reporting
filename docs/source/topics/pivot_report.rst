.. _pivot_report_topic:

============================
Precomputed Crosstab Reports
============================

General use case
----------------

Precomputed crosstab reports are designed for **pre-computed or pre-aggregated data** stored as rows in the database.
Instead of aggregating raw transactions at report time (like regular crosstab reports do),
setting ``crosstab_precomputed = True`` reads existing values and spreads a field's distinct values into columns.

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

The precomputed crosstab report transforms this into:

+------------+-------------------+-------------------+
| product_id | total_sales Jan   | total_sales Feb   |
+============+===================+===================+
| 1          | 500               | 600               |
+------------+-------------------+-------------------+
| 2          | 300               | 400               |
+------------+-------------------+-------------------+


How it relates to regular crosstab
----------------------------------

Precomputed crosstab is a mode of the standard crosstab feature. Both spread a field's distinct values as columns.
The difference:

* **Regular crosstab** (``crosstab_precomputed = False``) aggregates raw data per crosstab value using ``ComputationField``
* **Precomputed crosstab** (``crosstab_precomputed = True``) reads pre-existing values from the database — no aggregation

Both modes use the same metadata and frontend integration, so all existing chart types
(bar, line, pie, area) work with precomputed crosstab data.


Basic example
-------------

.. code-block:: python

    from slick_reporting.views import ReportView, Chart

    class MonthlyProductSales(ReportView):
        report_model = MonthlySummary
        date_field = "month"
        group_by = "product_id"
        crosstab_field = "month"
        crosstab_columns = ["total_sales", "total_quantity"]
        crosstab_precomputed = True
        columns = ["product_id", "__crosstab__"]

        chart_settings = [
            Chart(
                "Monthly Sales",
                Chart.LINE,
                data_source=["total_sales"],
                title_source=["product_id"],
            ),
        ]

Key attributes:

* ``crosstab_precomputed = True`` — read pre-computed values instead of aggregating
* ``crosstab_field`` — the column whose distinct values become the dynamic columns
* ``crosstab_columns`` — list of database column name strings to read values from
* ``columns`` — use ``"__crosstab__"`` as a placeholder for where crosstab columns appear


Crosstab by a non-date field
-----------------------------

The crosstab field doesn't have to be a date — it can be any column:

.. code-block:: python

    class SalesByRegion(ReportView):
        report_model = RegionalSummary
        group_by = "product_id"
        crosstab_field = "region"
        crosstab_columns = ["total_sales"]
        crosstab_precomputed = True
        columns = ["product_id", "__crosstab__"]

This produces one row per product with a column for each region.

.. note::

    When multiple source rows exist for the same ``(group_by, crosstab_field)`` combination,
    the last row encountered is used. Precomputed crosstab does **not** aggregate — if you
    need aggregation, use a standard crosstab (without ``crosstab_precomputed``) or time series report instead.


Using with dynamic models
--------------------------

Precomputed crosstab reports pair naturally with ``table_name`` for tables without a Django model:

.. code-block:: python

    class WarehouseReport(ReportView):
        table_name = "warehouse_monthly_sales"
        date_field = "period_date"
        group_by = "sku"
        crosstab_field = "period_date"
        crosstab_columns = ["revenue", "units_sold"]
        crosstab_precomputed = True
        columns = ["sku", "__crosstab__"]

See :ref:`dynamic_model_topic` for more on reporting from arbitrary database tables.


Using with ReportGenerator directly
------------------------------------

.. code-block:: python

    from slick_reporting.generator import ReportGenerator

    report = ReportGenerator(
        report_model=MonthlySummary,
        group_by="product_id",
        date_field="month",
        crosstab_field="month",
        crosstab_columns=["total_sales"],
        crosstab_precomputed=True,
        columns=["product_id", "__crosstab__"],
        start_date=datetime.datetime(2024, 1, 1),
        end_date=datetime.datetime(2024, 6, 30),
    )
    data = report.get_report_data()


Date filtering
--------------

When ``date_field`` is set, the precomputed crosstab respects ``start_date`` and ``end_date`` filters.
Only rows within the date range are included, and only crosstab values found in those rows
appear as columns.


Crosstab values with spaces or special characters
--------------------------------------------------

Crosstab values like ``"New York"`` or ``"Q1/2024"`` are sanitized for use in column names
(non-alphanumeric characters replaced with underscores). The ``verbose_name`` preserves the
original value for display in tables and charts.

For example, a crosstab value of ``"New York"`` produces:

* Column name: ``total_salesCTNew_York`` (sanitized, used internally)
* Verbose name: ``total_sales New York`` (original, displayed to users)


Limitations
-----------

* **No aggregation.** Precomputed crosstab reads pre-existing values. If you need computation (Sum, Count, etc.),
  use a standard crosstab without ``crosstab_precomputed``.

* **Last value wins.** If multiple rows share the same ``(group_by, crosstab_field)`` value,
  the last row's values are used.

* **No FK traversal.** When using dynamic models, foreign key columns are plain integers.
  Group by the column directly (e.g. ``product_id``) rather than traversing (``product__name``).

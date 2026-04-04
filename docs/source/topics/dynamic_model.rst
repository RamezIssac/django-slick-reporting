.. _dynamic_model_topic:

==============
Dynamic Models
==============

General use case
----------------

Sometimes you need to generate reports from database tables that don't have a corresponding Django model.
This is common with:

* Legacy database tables
* Data warehouse / analytics tables
* Tables managed by other systems or ETL pipelines
* Temporary or staging tables

Django Slick Reporting provides ``get_dynamic_model`` which introspects any database table and creates
a real Django model at runtime. Since the result is a genuine Django model, all report features work
natively: group by, time series, crosstab, aggregation, filtering, and charts.


Basic usage
-----------

Use the ``get_dynamic_model`` utility to create a model from an existing table:

.. code-block:: python

    from slick_reporting.dynamic_model import get_dynamic_model

    # Introspect the table and get a Django model class
    SalesData = get_dynamic_model("legacy_sales")

    # Use it like any Django model
    SalesData.objects.all()
    SalesData.objects.filter(region="US").count()

Then use it with ``ReportGenerator`` or ``ReportView`` as usual:

.. code-block:: python

    from slick_reporting.views import ReportView, Chart
    from slick_reporting.fields import ComputationField
    from slick_reporting.dynamic_model import get_dynamic_model
    from django.db.models import Sum

    SalesData = get_dynamic_model("legacy_sales")

    class LegacySalesReport(ReportView):
        report_model = SalesData
        date_field = "sale_date"
        group_by = "product_id"

        columns = [
            "product_id",
            ComputationField.create(
                method=Sum,
                field="amount",
                name="amount__sum",
                verbose_name="Total Sales",
            ),
        ]

        chart_settings = [
            Chart(
                "Total Sales",
                Chart.BAR,
                data_source=["amount__sum"],
                title_source=["product_id"],
            ),
        ]


Using ``table_name`` shortcut
-----------------------------

Instead of calling ``get_dynamic_model`` yourself, you can set ``table_name`` directly on
``ReportView`` or pass it to ``ReportGenerator``:

.. code-block:: python

    # On a view
    class LegacySalesReport(ReportView):
        table_name = "legacy_sales"
        date_field = "sale_date"
        group_by = "product_id"

        columns = [
            "product_id",
            ComputationField.create(
                method=Sum,
                field="amount",
                name="amount__sum",
                verbose_name="Total Sales",
            ),
        ]


.. code-block:: python

    # With ReportGenerator directly
    from slick_reporting.generator import ReportGenerator

    report = ReportGenerator(
        table_name="legacy_sales",
        date_field="sale_date",
        group_by="product_id",
        columns=[
            "product_id",
            ComputationField.create(Sum, "amount", name="amount__sum", verbose_name="Total Sales"),
        ],
        start_date=start,
        end_date=end,
    )
    data = report.get_report_data()

When ``table_name`` is set and ``report_model`` is not, the dynamic model is created automatically.


Using a different database
--------------------------

If the table is in a non-default database, pass the ``database`` parameter:

.. code-block:: python

    WarehouseData = get_dynamic_model("fact_sales", database="warehouse")

This uses the database alias defined in your Django ``DATABASES`` setting.


Working with database schemas
-----------------------------

On PostgreSQL, tables can live in different schemas (e.g. ``analytics``, ``staging``).

**Prerequisites:** The schema must be accessible via the connection's ``search_path`` so Django's
introspection can find the table. You can configure this in your database settings:

.. code-block:: python

    # settings.py
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": "mydb",
            "OPTIONS": {
                "options": "-c search_path=analytics,public",
            },
        }
    }

Then pass the ``schema`` parameter so ORM queries reference the correct schema:

.. code-block:: python

    SalesData = get_dynamic_model("sales", schema="analytics")

This sets the model's ``db_table`` to ``"analytics"."sales"`` so all generated SQL uses the
schema-qualified table name.

**Schema support by database backend:**

+----------------+-------------------------------------------------------------------+
| Backend        | How schemas work                                                  |
+================+===================================================================+
| PostgreSQL     | Use ``schema`` parameter + ensure schema is in ``search_path``    |
+----------------+-------------------------------------------------------------------+
| MySQL          | Schemas are databases. Use the ``database`` parameter instead     |
+----------------+-------------------------------------------------------------------+
| SQLite         | No schema concept. Just use ``table_name``                        |
+----------------+-------------------------------------------------------------------+


How it works
------------

``get_dynamic_model`` performs the following steps:

1. Connects to the database and verifies the table exists.
2. Uses Django's ``connection.introspection`` to read column names, types, and constraints.
3. Maps each database column to the appropriate Django field (``IntegerField``, ``CharField``, ``DateField``, etc.).
4. Creates a Django model class at runtime with ``managed = False`` (no migrations needed).
5. Registers the model in Django's app registry so the ORM works fully.
6. Caches the result so subsequent calls for the same table return the same model class.

Since the result is a standard Django model, all ``ReportGenerator`` features work without
any special handling: ``group_by``, ``time_series_pattern``, ``crosstab_field``, ``ComputationField``,
form generation, and chart rendering.


Caching
-------

Dynamic models are cached in memory. Calling ``get_dynamic_model("my_table")`` multiple times
returns the same model class. The cache key includes the database alias and schema, so models
for different databases or schemas are cached separately.


Limitations
-----------

* **No foreign key relationships.** Foreign key columns are introspected as plain integer or
  varchar fields. This means ``group_by`` traversal across relationships (e.g. ``product__category``)
  is not available. You can group by the FK column directly (e.g. ``product_id``).

* **No automatic form filters for FK fields.** Since there are no FK relations, the auto-generated
  filter form will only contain date range fields. Supply a custom ``form_class`` if you need
  additional filters.

* **Schema must be in search_path.** On PostgreSQL, Django's introspection only finds tables
  visible in the current ``search_path``. The schema must be configured at the connection level.

* **Table structure changes require restart.** Because models are cached, if the table structure
  changes (columns added/removed), you need to restart the application or clear the cache.

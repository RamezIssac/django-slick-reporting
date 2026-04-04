.. _dynamic_model_ref:

=============
Dynamic Model
=============

.. module:: slick_reporting.dynamic_model

``get_dynamic_model``
---------------------

.. function:: get_dynamic_model(table_name, database="default", schema=None)

    Introspect a database table and return a Django model class for it.

    The returned model has ``managed = False`` and is fully compatible with the Django ORM.
    Results are cached so repeated calls return the same class.

    :param table_name: The database table name to introspect.
    :type table_name: str
    :param database: The database alias from ``DATABASES`` setting.
    :type database: str
    :param schema: Optional schema name (PostgreSQL). The schema must be in the
        connection's ``search_path``. When provided, ``db_table`` is set to
        ``"schema"."table_name"``.
    :type schema: str or None
    :returns: A Django model class mapped to the table.
    :rtype: type (subclass of ``django.db.models.Model``)
    :raises ValueError: If the table does not exist.


``table_name`` attribute
------------------------

Both ``ReportGenerator`` and ``ReportView`` accept a ``table_name`` parameter.
When set (and ``report_model`` is not), ``get_dynamic_model`` is called automatically.

.. code-block:: python

    class MyReport(ReportView):
        table_name = "legacy_sales"
        date_field = "sale_date"
        group_by = "region"
        columns = [...]

    # Or via ReportGenerator init
    report = ReportGenerator(table_name="legacy_sales", ...)

See :ref:`dynamic_model_topic` for full usage guide and examples.

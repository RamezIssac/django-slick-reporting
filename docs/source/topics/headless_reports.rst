.. _headless_reports:

Running Reports Without a Page
==============================

Reports can run outside an HTML page, for example from an API endpoint or a tool an AI assistant calls.
Three entry points cover this:

* ``ReportViewBase.run()`` runs a report view from JSON parameters.
* ``slick_reporting.helpers.compact_response()`` turns a report response into compact rows and totals.
* ``slick_reporting.dynamic_report.run_dynamic_report()`` builds and runs an ad-hoc report from a JSON spec.


Running a report view
---------------------

.. code-block:: python

    from slick_reporting.helpers import compact_response

    full_response = MonthlySales.run(request, {"client_id": [1, 2], "start_date": "2026-01-01"})
    result = compact_response(full_response, max_rows=200)

``run(request, params=None, check_access=True, **initkwargs)`` is a classmethod. It:

#. copies ``request`` as a GET request whose ``request.GET`` holds the params,
#. fills every form field missing from ``params`` with its initial value, computed at call time
   (``start_date`` and ``end_date`` default to the start of the year and the end of today),
#. binds and validates the report form,
#. returns ``get_report_results()``, so overrides of ``get_report_generator``, ``filter_results`` and
   ``get_report_results`` still apply.

``params`` keys are the form field names (``start_date``, ``end_date``, ``<foreign key>_id`` filters,
``time_series_pattern``, ``crosstab_compute_remainder`` ...). Lists become repeated GET values;
``true`` / ``false`` become checkbox values. A date-only ``end_date`` such as ``"2026-03-31"`` covers the
whole day (``2026-03-31T23:59:59``).

* An unknown key raises ``ValidationError`` with code ``unknown_parameter``.
* An invalid value raises ``ValidationError``; its ``error_dict`` is the form errors, keyed by field name.
* When ``check_access`` is set and ``test_func()`` fails, it raises ``PermissionDenied``.

A view that reads GET parameters outside its form declares them in ``extra_params``, a dict of JSON Schema
properties. ``run()`` accepts those names and passes them through ``request.GET``:

.. code-block:: python

    class CategorySales(ReportView):
        extra_params = {"category_id": {"type": "integer", "description": "Limit to one category."}}

Note: declare such parameters in ``extra_params`` and not only in your API layer, because ``run()`` rejects
every key that is neither a form field nor declared there.


Compact output
--------------

``compact_response(full_response, max_rows=None)`` returns:

.. code-block:: python

    {
        "columns": [{"name": "name", "label": "Name", "type": "text"},
                    {"name": "__total__", "label": "Total", "type": "number"}],
        "rows": [["Client 1", "300"], ["Client 2", "600"]],
        "totals": {"__total__": "900"},
        "row_count": 2,
        "truncated": False,
        "date_window": {"start": "2026-01-01", "end": "2026-11-20", "label": "From 2026-01-01 to 2026-11-20"},
    }

* Only visible columns are included. ``type`` is one of ``number``, ``text``, ``date``, ``datetime``, ``boolean``.
* ``rows`` are positional, in the order of ``columns``. At most ``max_rows`` rows are returned;
  ``row_count`` is the number of rows before truncation and ``truncated`` tells whether rows were cut.
* ``totals`` covers every ``number`` column whose ``is_summable`` is ``True``, over all rows, before truncation.
  Computation fields are summable by default; a list report column becomes summable through its options,
  e.g. ``("value", {"is_summable": True})``.
* Numbers are strings (Decimal safe), dates and datetimes are ISO strings, empty cells are ``null``.


Dynamic reports from a JSON spec
--------------------------------

``run_dynamic_report(spec, request, allowed_models=None)`` validates ``spec`` and returns the report full
response, ready for ``compact_response()``. ``DYNAMIC_REPORT_SPEC_SCHEMA`` is the JSON Schema of the spec,
and ``describe_dynamic_report_models(request, allowed_models)`` lists the usable models and fields in the
shape of the LLM assistant catalog.

.. code-block:: python

    from slick_reporting.dynamic_report import run_dynamic_report

    spec = {
        "report_model": "sales.SalesTransaction",
        "group_by": "client",
        "columns": ["name", {"method": "Sum", "field": "value", "name": "value_sum", "verbose_name": "Sales"}],
        "date_field": "date",
        "start_date": "2026-03-01",
        "end_date": "2026-03-31T23:59:59",
        "filters": {"product__category": "small"},
    }
    full_response = run_dynamic_report(spec, request, allowed_models=["sales.SalesTransaction", "sales.Client"])

The keys follow the configuration of the LLM assistant (``run_llm_report_config``):

``report_model`` (required)
    The model holding the rows, as ``app_label.ModelName``.
``kind``
    ``aggregate`` (default) computes the columns per ``group_by`` value, or one total row without ``group_by``.
    ``list`` returns the matching ``report_model`` rows; it takes ``columns`` (field paths), dates and filters only.
``title``
    Used as the report title.
``group_by``
    Field path on ``report_model``.
``columns``
    Field paths and computation columns. Field paths resolve on the ``group_by`` related model when
    ``group_by`` is a relation (``name``, ``email``), else on ``report_model``. A computation column is
    ``{"method": "Sum|Avg|Count|Min|Max", "field": "<path on report_model>", "name": ..., "verbose_name": ...}``
    or a registered computation field name such as ``__total__``. ``Sum`` and ``Avg`` need a numeric field;
    ``Sum`` and ``Count`` columns are summable.
``date_field``, ``start_date``, ``end_date``
    ``date_field`` is a date or datetime field path; the dates are ISO strings and a date-only ``end_date``
    covers the whole day. Missing dates take the report defaults.
``time_series_pattern``, ``time_series_columns``
    ``daily``, ``weekly``, ``bi-weekly``, ``monthly``, ``quarterly``, ``semiannually`` or ``annually``,
    with the computation columns to repeat per period. Needs ``date_field``. At most 120 periods
    (``max_time_series_periods``).
``crosstab_field``, ``crosstab_ids``, ``crosstab_columns``, ``crosstab_compute_remainder``
    The field path to pivot on, up to 50 of its values, the computation columns per value, and whether to
    add a column for all other values (default ``false``).
``filters``
    ``{"<field path>[__<lookup>]": value}``. Lookups: ``exact``, ``iexact``, ``in``, ``gt``, ``gte``, ``lt``,
    ``lte``, ``range``, ``isnull``, ``contains``, ``icontains``, ``startswith``, ``istartswith``, ``endswith``,
    ``iendswith``, ``year``, ``month``, ``day``. ``in`` and ``range`` take a list. Values of a primary key
    lookup (``client``, ``client_id__in``) may be labels such as ``"Client 1"``; they are resolved to ids.

Validation runs before any query:

* Every model the spec names or traverses (``client__contact__agent`` traverses three), and every model a
  registered computation field reads, must be in ``allowed_models``, else ``ValidationError`` with code
  ``model_not_allowed``. ``allowed_models=None`` allows every installed model.
* Filter values are checked against their field (``value__gte: "abc"`` is rejected).
* A report computes at most 500 computation columns (columns, plus time series and crosstab columns
  repeated per period and value), else code ``too_large``.
* With a ``request``, ``request.user`` needs the view or change permission on each of those models, else
  ``PermissionDenied``. ``request=None`` skips this check.
* Unknown keys, unknown fields, unsupported lookups and malformed values raise ``ValidationError``; its
  ``error_dict`` is keyed by spec key, with the codes ``unknown_key``, ``unknown_field``, ``required``,
  ``too_many_periods``, ``too_large``, ``invalid`` or ``invalid_spec``.

Note: pass an explicit ``allowed_models`` list when the spec comes from a user or an LLM and not
``None``, because ``None`` lets a spec traverse into any installed model the user can view.

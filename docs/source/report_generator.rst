.. _report_generator:

Report Generator API
====================

The main class responsible generating the report and managing the flow


ReportGenerator
---------------

.. autoclass:: slick_reporting.generator.ReportGenerator

    .. rubric:: Below are the basic needed attrs
    .. autoattribute:: report_model
    .. autoattribute:: date_field
    .. autoattribute:: columns
    .. autoattribute:: group_by

    .. rubric:: Below are the needed attrs and methods for time series manipulation
    .. autoattribute:: time_series_pattern
    .. autoattribute:: time_series_columns
    .. automethod:: get_custom_time_series_dates
    .. automethod:: get_time_series_field_verbose_name

    .. rubric:: Below are the needed attrs and methods for crosstab manipulation
    .. autoattribute:: crosstab_model
    .. autoattribute:: crosstab_columns
    .. autoattribute:: crosstab_ids
    .. autoattribute:: crosstab_compute_reminder
    .. automethod:: get_crosstab_field_verbose_name

    .. rubric:: Below are the magical attrs
    .. autoattribute:: limit_records
    .. autoattribute:: swap_sign
    .. autoattribute:: field_registry_class







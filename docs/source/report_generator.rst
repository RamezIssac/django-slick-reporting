.. _report_generator:

Report Generator
=================

The main class responsible generating the report and managing the flow


ReportGenerator
---------------

.. autoclass:: slick_reporting.generator.ReportGenerator

    .. autoattribute:: report_model
    .. autoattribute:: date_field
    .. autoattribute:: group_by
    .. autoattribute:: columns

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




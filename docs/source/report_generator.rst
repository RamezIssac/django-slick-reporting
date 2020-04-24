.. _report_generator:

Report Generator
=================

Let's explore creating a ReportGenerator and teh analogy involved


Attributes :
------------

.. autoclass:: slick_reporting.generator.ReportGenerator

    .. autoattribute:: report_model
    .. autoattribute:: date_field
    .. autoattribute:: group_by
    .. autoattribute:: columns

    .. rubric:: Below are the needed attrs and methods for time series manipulation
    .. autoattribute:: time_series_pattern
    .. autoattribute:: time_series_columns
    .. autoattribute:: get_custom_time_series_dates
    .. autoattribute:: get_time_series_field_verbose_name

    .. rubric:: Below are the needed attrs and methods for crosstab manipulation
    .. autoattribute:: crosstab_model
    .. autoattribute:: crosstab_columns
    .. autoattribute:: crosstab_ids
    .. autoattribute:: crosstab_compute_reminder
    .. autoattribute:: get_crosstab_field_verbose_name




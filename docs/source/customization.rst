.. _customization:

Customization
==============

How it works ?
--------------
The ReportGenerator is initialized with the needed configuration,
it generates a list of the needed fields to be displayed and computed.
For each computation field, it's given the filters needed and
asked to get all the results prepared. **The preparation is a duty of the ReportField anyway**,
then for each report_model record, the ReportGenerator again asks each ComputationField to get the data it has for each record and map it where it belongs.



1. View Customization
---------------------
The SampleReportView is a wrapper around FormView. It

1. Passes the needed reporting attributes to the ReportGenerator and get the results into the context.
2. Work on GET as well as on POST.
3. If the request is ajax, the view return the results as a json response.
4. Auto generate the search form

2. Form Customization
---------------------
Behind the scene, Sample report calls ``slick_reporting.form_factory.report_form_factory``
a helper method which generates a form containing startdate and end date, as well as all foreign keys on the report_model.

The Form has exactly 2 purposes

1. Provide the start_date and end_date
2. provide a ``get_filters`` method which return a tuple (Q_filers , kwargs filter) to be used in filtering.
   q_filter: can be none or a series of Django's Q queries
   kwargs_filter: None or a dict of filters

Following those 2 simple recommendation, your awesome custom form will work as you'd expect.


3. Calculation Field Customization
----------------------------------

:ref:`computation_field`

4. Settings
-----------

Slick Reporting comes with only 2 settings that can manipulated from `settings.py`

1. ``SLICK_REPORTING_DEFAULT_START_DATE``: Default to the beginning of this year
2. ``SLICK_REPORTING_DEFAULT_END_DATE``: Defaults to the end of the current  year.

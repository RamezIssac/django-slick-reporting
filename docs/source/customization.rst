.. _customization:

Customization
==============

How it works ?
--------------
The ReportGenerator is initialized with the needed configuration,
it generates a list of the needed fields to be displayed and computed.
For each computation field, it's given teh filter needed and
asked to get all the results prepared. **The preparation is a duty of the ReportField anyway**.

Then for each report


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
a helper method which generates a form containing start_date and end date, as well and all foreign keys on the model.

The Form has exactly 2 purposes

1. Provide the start_date and end_date
2. provide a ``get_filters`` method which return a tuple (Q filer , kwargs filter to be used in filtering.

Following those 2 simple recommendation, your awesome custom form will work as you'd expect


3. Calculation Field Customization
----------------------------------

:ref:`computation_field`


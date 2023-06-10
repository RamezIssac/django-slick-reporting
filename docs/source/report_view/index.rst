.. _report_view:

The Report View
===============

What is ReportView?
--------------------

ReportView is a ``FromView`` subclass that exposes the report generator API allowing you to create a report in view.
It also

* Auto generate the filter form based on the report model
* return the results as a json response if it's ajax request.
* Export to CSV (extendable to apply other exporting method)
* Print the report in a dedicated format



.. toctree::
   :maxdepth: 2
   :caption: Contents:
   :titlesonly:

   view_options
   group_by_report
   time_series_options
   crosstab_options
   list_report_options
   filter_form



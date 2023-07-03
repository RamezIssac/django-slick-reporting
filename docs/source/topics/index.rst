.. _topics:

Topics
======

ReportView is a ``django.views.generic.FromView`` subclass that exposes the **Report Generator API** allowing you to create a report seamlessly in a view.

* Exposes the report generation options in the view class.
* Auto generate the filter form based on the report model, or uses your custom form to generate and filter the report.
* Return an html page prepared to display the results in a table and charts.
* Export to CSV, which is extendable to apply other exporting methods. (like yaml or other)
* Print the report in a dedicated page design.


You saw how to use the ReportView class in the tutorial and you identified the types of reports available, in the next section we will go in depth about:

#. Each type of the reports and its options.
#. The general options available for all report types
#. How to customize the Form
#. How to customize exports and print.


.. toctree::
   :maxdepth: 2
   :caption: Topics:
   :titlesonly:


   group_by_report
   time_series_options
   crosstab_options
   list_report_options
   filter_form
   exporting



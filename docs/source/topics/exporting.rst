Exporting
=========

Exporting to CSV
-----------------
To trigger an export to CSV, just add ``?_export=csv`` to the url. This is performed by by the Export to CSV button in the default form.

This will call the export_csv on the view class, engaging a `ExportToStreamingCSV`

You can extend the functionality, say you want to export to pdf.
Add a ``export_pdf`` method to the view class, accepting the report_data json response and return the response you want.
This ``export_pdf` will be called automatically when url parameter contain ``?_export=pdf``

Having an `_export` parameter not implemented, ie the view class do not implement ``export_{parameter_name}``,  will be ignored.


Adding an export option
-----------------------

To add an export option you need to add the function to the view class.

For example, to add a pdf export option, add the following to the view class:

.. code-block:: python

    class CustomExportReport(GroupByReport):
        report_title = _("Custom Export Report")
        export_actions = ["export_pdf"]

        def export_pdf(self, report_data):
            return HttpResponse(f"Dummy PDF Exported {report_data}")

        export_pdf.title = _("Export PDF")
        export_pdf.icon = "fa fa-file-pdf-o"
        export_pdf.css_class = "btn btn-primary"

The export function should accept the report_data json response and return the response you want.

Configuring the CSV export option
---------------------------------

You can disable the CSV export option by setting the ``csv_export_class`` attribute to ``False`` on the view class.
and you can override the function and its attributes to customize the button text

.. code-block:: python

    class CustomExportReport(GroupByReport):
        report_title = _("Custom Export Report")

        def export_csv(self, report_data):
            return super().export_csv(report_data)

        export_csv.title = _("My Custom CSV export Title")
        export_csv.css_class = "btn btn-success"


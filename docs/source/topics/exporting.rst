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



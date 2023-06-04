.. _customization:

The Slick Report View
=====================

What is SlickReportView?
-----------------------

SlickReportView is a CBV that inherits form ``FromView`` and expose the report generator needed attributes.
It:

* Auto generate the search form based on the report model (Or you can create you own)
* return the results as a json response if it's ajax request.
* Export to CSV (extendable to apply other exporting method)
* Print the report in a dedicated format


Export to CSV
--------------
To trigger an export to CSV, just add ``?_export=csv`` to the url.
This will call the export_csv on the view class, engaging a `ExportToStreamingCSV`

You can extend the functionality, say you want to export to pdf.
Add a ``export_pdf`` method to the view class, accepting the report_data json response and return the response you want.
This ``export_pdf` will be called automatically when url parameter contain ``?_export=pdf``

Having an `_export` parameter not implemented, to say the view class do not implement ``export_{parameter_name}``,  will be ignored.



The ajax response structure
---------------------------

Understanding how the response is structured is imperative in order to customize how the report is displayed on the front end.

Let's have a look

.. code-block:: python


    # Ajax response or `report_results` template context variable.
    response = {
        # the report slug, defaults to the class name all lower
        "report_slug": "",

        # a list of objects representing the actual results of the report
        "data": [
            {"name": "Product 0", "quantity__sum": "1774", "value__sum": "8758", "field_n" : "value_n"},
            # .....
        ],

        # A list explaining the columns/keys in the data results.
        # ie: len(response.columns) == len(response.data[i].keys())
        # Contains needed information about the verbose name , if summable , hints about the data type.
        "columns": [
            {"name": "name",
             "computation_field": "",
             "verbose_name": "Name",
             "visible": True,
             "type": "CharField",
             "is_summable": False
             },
            {"name": "quantity__sum",
             "computation_field": "",
             "verbose_name": "Quantities Sold",
             "visible": True,
             "type": "number",
             "is_summable": True},
            {"name": "value__sum",
             "computation_field": "",
             "verbose_name": "Value $",
             "visible": True,
             "type": "number",
             "is_summable": True}
        ],

        # Contains information about the report as whole if it's time series or a a crosstab
        # And what's the actual and verbose names of the time series or crosstab specific columns.
        "metadata": {"time_series_pattern": "",
                     "time_series_column_names": [],
                     "time_series_column_verbose_names": [],
                     "crosstab_model": '',
                     "crosstab_column_names": [],
                     "crosstab_column_verbose_names": []
                     },


        # a mirror of the set charts_settings on the SlickReportView
        # SlickReportView populates the id if missing and fill the `engine_name' if not set
        "chart_settings": [
            {"type": "pie",
            'engine_name': 'highcharts',
             "data_source": ["quantity__sum"],
             "title_source": ["name"],
             "title": "Pie Chart (Quantities)",
             "id": "pie-0"},

            {"type": "bar",
            "engine_name": "chartsjs",
            "data_source": ["value__sum"],
            "title_source": ["name"],
            "title": "Column Chart (Values)",
             "id": "bar-1"}
        ]
    }



.. _customization:

The Slick Report View
=====================

Types of reports
----------------
We can categorize the output of a report into 4 sections:

#. Grouped report: similar to what you'd so with a GROUP BY sql statement. We group by a field and do some kind of calculations over the grouped records.
#. Time series report: a step up from the previous grouped report, where the calculations are done for each time period set in the time series options.
#. Crosstab report: It's a report where the results shows the relationship between two or more variables. Example: Rows are the clients, columns are the products, and the intersection values are the sum of sales for each client and product combination. This report can be created in time series as well. Example: Rows are the clients, columns are the products, and the intersection values are the sum of sales for each client and product combination, for each month.
#. List report: Similar to a django changelist, it's a direct view of the report model records with some extra features like sorting, filtering, pagination, etc.


What is ReportView?
--------------------

ReportView is a ``FromView`` subclass that exposes the report generator API allowing you to create a report in view.
It also
* Auto generate the filter form based on the report model
* return the results as a json response if it's ajax request.
* Export to CSV (extendable to apply other exporting method)
* Print the report in a dedicated format

How to use it?
--------------
You can import it from ``django_slick_reporting.views``
``from django_slick_reporting.views import ReportView``

In the next section we will go over the options and methods available on the ReportView class in regard to each of the types of reports listed above.


Exporting to CSV
-----------------
To trigger an export to CSV, just add ``?_export=csv`` to the url.
This will call the export_csv on the view class, engaging a `ExportToStreamingCSV`

You can extend the functionality, say you want to export to pdf.
Add a ``export_pdf`` method to the view class, accepting the report_data json response and return the response you want.
This ``export_pdf` will be called automatically when url parameter contain ``?_export=pdf``

Having an `_export` parameter not implemented, ie the view class do not implement ``export_{parameter_name}``,  will be ignored.



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
            {
                "name": "Product 1",
                "quantity__sum": "1774",
                "value__sum": "8758",
                "field_x": "value_x",
            },
            {
                "name": "Product 2",
                "quantity__sum": "1878",
                "value__sum": "3000",
                "field_x": "value_x",
            },
            # etc .....
        ],

        # A list explaining the columns/keys in the data results.
        # ie: len(response.columns) == len(response.data[i].keys())
        # It contains needed information about verbose name , if summable and hints about the data type.
        "columns": [
            {
                "name": "name",
                "computation_field": "",
                "verbose_name": "Name",
                "visible": True,
                "type": "CharField",
                "is_summable": False,
            },
            {
                "name": "quantity__sum",
                "computation_field": "",
                "verbose_name": "Quantities Sold",
                "visible": True,
                "type": "number",
                "is_summable": True,
            },
            {
                "name": "value__sum",
                "computation_field": "",
                "verbose_name": "Value $",
                "visible": True,
                "type": "number",
                "is_summable": True,
            },
        ],
        # Contains information about the report as whole if it's time series or a a crosstab
        # And what's the actual and verbose names of the time series or crosstab specific columns.
        "metadata": {
            "time_series_pattern": "",
            "time_series_column_names": [],
            "time_series_column_verbose_names": [],
            "crosstab_model": "",
            "crosstab_column_names": [],
            "crosstab_column_verbose_names": [],
        },

        # A mirror of the set charts_settings on the ReportView
        # ``ReportView`` populates the id and the `engine_name' if not set
        "chart_settings": [
            {
                "type": "pie",
                "engine_name": "highcharts",
                "data_source": ["quantity__sum"],
                "title_source": ["name"],
                "title": "Pie Chart (Quantities)",
                "id": "pie-0",
            },
            {
                "type": "bar",
                "engine_name": "chartsjs",
                "data_source": ["value__sum"],
                "title_source": ["name"],
                "title": "Column Chart (Values)",
                "id": "bar-1",
            },
        ],
    }



Charting and Front End Customization
=====================================

Charts Configuration
---------------------

Charts settings is a list of objects which each object represent a chart configurations.

* type: what kind of chart it is: Possible options are bar, pie, line and others subject of the underlying charting engine.
  Hats off to : `Charts.js <https://www.chartjs.org/>`_.
* engine_name: String, default to ``SLICK_REPORTING_DEFAULT_CHARTS_ENGINE``. Passed to front end in order to use the appropriate chart engine.
  By default supports `highcharts` & `chartsjs`.
* data_source: Field name containing the numbers we want to plot.
* title_source: Field name containing labels of the data_source
* title: the Chart title. Defaults to the `report_title`.
* plot_total if True the chart will plot the total of the columns. Useful with time series and crosstab reports.

On front end, for each chart needed we pass the whole response to the relevant chart helper function and it handles the rest.




The ajax response structure
---------------------------

Understanding how the response is structured is imperative in order to customize how the report is displayed on the front end

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



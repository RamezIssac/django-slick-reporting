Charting
---------

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



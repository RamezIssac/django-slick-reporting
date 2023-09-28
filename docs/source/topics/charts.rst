Charts Customization
====================

Charts Configuration
---------------------

ReportView ``charts_settings`` is a list of objects which each object represent a chart configurations.
The chart configurations are:

* title: the Chart title. Defaults to the `report_title`.
* type: A string. Examples are pie, bar, line, etc ...
* engine_name: A string, default to the ReportView ``chart_engine`` attribute, then to the ``SLICK_REPORTING_SETTINGS.DEFAULT_CHARTS_ENGINE``.
* data_source: string, the field name containing the numbers we want to plot.
* title_source: string, the field name containing labels of the data_source
* plot_total: if True the chart will plot the total of the columns. Useful with time series and crosstab reports.
* entryPoint: the javascript entry point to display the chart, the entryPoint function accepts the data, $elem and the chartSettings parameters.

On front end, for each chart needed we pass the whole response to the relevant chart helper function and it handles the rest.



Customizing the entryPoint for a chart
--------------------------------------

Sometimes you want to display the chart differently, in this case, you can just change the entryPoint function.

Example:

.. code-block:: python

    class ProductSalesApexChart(ReportView):
        # ..
        template_name = "product_sales_report.html"
        chart_settings = [
            # ..
            Chart(
                "Total sold $",
                type="bar",
                data_source=["value__sum"],
                title_source=["name"],
                entryPoint="displayChartCustomEntryPoint",  # this is the new entryPoint
            ),
        ]


Then in your template `product_sales_report.html` add the javascript function specified as the new entryPoint.

.. code-block:: html+django

            {% extends "slick_reporting/report.html" %}
            {% load  slick_reporting_tags %}
            {% block extra_js %}
                {{ block.super }}
                <script>
                    function displayChartCustomEntryPoint(data, $elem, chartSettings) {
                        // data: is the ajax response coming from server
                        // $elem: is the jquery element where the chart should be rendered
                        // chartSettings: is the relevant chart dictionary/object in your ReportView chart_settings
                        // do your custom logic here
                    }
                </script>

            {% endblock %}

Adding a new charting engine
----------------------------

In the following part we will add some Apex charts to the demo app to demonstrate how you can add your own charting engine to slick reporting.

#. We need to add the new chart Engine to the settings. Note that the css and js are specified and handled like Django's ``Form.Media``

.. code-block:: python

    SLICK_REPORTING_SETTINGS = {
        "CHARTS": {
            "apexcharts": {
                "entryPoint": "DisplayApexPieChart",
                "js": (
                    "https://cdn.jsdelivr.net/npm/apexcharts",
                    "js_file_for_apex_chart.js",  # this file contains the entryPoint function and is responsible
                    # for compiling the data and rendering the chart
                ),
                "css": {
                    "all": "https://cdn.jsdelivr.net/npm/apexcharts/dist/apexcharts.min.css"
                },
            }
        },
    }

#. Add the entry point function to the javascript file `js_file_for_apex_chart.js` in this example.

It can look something like this:

.. code-block:: javascript

    let chart = null;
    function DisplayApexPieChart(data, $elem, chartOptions) {
        // Where:
        // data: is the ajax response coming from server
        // $elem: is the jquery element where the chart should be rendered
       // chartOptions: is the relevant chart dictionary/object in your ReportView chart_settings

            let legendAndSeries = $.slick_reporting.chartsjs.getGroupByLabelAndSeries(data, chartOptions);
            // `getGroupByLabelAndSeries` is a helper function that will return an object with two keys: labels and series

            let options = {}
            if (chartOptions.type === "pie") {
                options = {
                    series: legendAndSeries.series,
                    chart: {
                        type: "pie",
                        height: 350
                    },
                    labels: legendAndSeries.labels,
                };
            } else {
                options = {
                    chart: {
                        type: 'bar'
                    },
                    series: [{
                        name: 'Sales',
                        data: legendAndSeries.series
                    }],
                    xaxis: {
                        categories: legendAndSeries.labels,
                    }
                }
            }

            try {
                // destroy old chart, if any
                chart.destroy();
            } catch (e) {
                // do nothing
            }

            chart = new ApexCharts($elem[0], options);
            chart.render();
    }


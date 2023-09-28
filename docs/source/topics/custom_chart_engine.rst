Custom Charting Engine
======================

In this guide we will add some Apex charts to the demo app.
to demonstrate how you can add your own charting engine to slick reporting.

#. We need to add the new chart Engine to the settings

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

#. and then you add the entry point function to the javascript file `js_file_for_apex_chart.js` in this example.

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


Customizing the entryPoint for a chart
--------------------------------------

Sometimes you want just to display the chart differently, in this case, you can just change the entryPoint function

Example:

.. code-block:: python

    class ProductSalesApexChart(ReportView):
        # ..
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




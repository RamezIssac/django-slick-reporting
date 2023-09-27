Custom Charting Engine
======================


To add a new chart engine you add it to the settings and provide an entry point function for the front end

.. code-block:: python

    SLICK_REPORTING_SETTINGS_DEFAULT = {
        "CHARTS": {
            "apexcharts": {
                "entryPoint": "DisplayChart",
                "js": ("https://cdn.jsdelivr.net/npm/apexcharts",),
                "css": "https://cdn.jsdelivr.net/npm/apexcharts/dist/apexcharts.min.css",
            }
        },
    }

and then you add the entry point function to the front end

.. code-block:: javascript

    function displayChart(data, $elem, chart_id) {
        // data is the ajax response coming from server
        // $elem is the jquery element where the chart should be rendered
       // chart_id is the id of the chart, which is teh index of teh needed chart in the [data.chart_settings] array

    }


The data is a json object with the following structure
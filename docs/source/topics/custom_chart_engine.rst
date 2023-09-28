Custom Charting Engine
======================

In this guide we will add some Apex charts to the demo app.
to demonstrate how you can add your own charting engine to slick reporting.

#. We need to add the new chart Engine to the settings

.. code-block:: python

    SLICK_REPORTING_SETTINGS = {
        "CHARTS": {
            "apexcharts": {
                "entryPoint": "DisplayChart",
                "js": ("https://cdn.jsdelivr.net/npm/apexcharts",),
                "css": {
                    "all": "https://cdn.jsdelivr.net/npm/apexcharts/dist/apexcharts.min.css"
                },
            }
        },
    }

#. and then you add the entry point function to the front end javascript

.. code-block:: javascript

    function displayChart(data, $elem, chartOptions) {
        // data is the ajax response coming from server
        // $elem is the jquery element where the chart should be rendered
       // chartOptions is the relevant chart dictionary/object in your ReportView chart_settings

    }


Complete example:
-----------------

.. code-block:: python

    class ProductSalesApexChart(ReportView):
        report_title = _("Product Sales Apex Charts")
        report_model = SalesTransaction
        date_field = "date"
        group_by = "product"

        chart_engine = "apexcharts"  #
        template_name = "demo/apex_report.html"

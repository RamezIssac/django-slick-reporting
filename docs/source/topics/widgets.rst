.. _widgets:

Widgets
=======
You can use the report data on any other page, for example to create a dashboard.
A dashboard page is a collection of report results  / charts / tables.

Adding a widget to a page is as easy as this code

.. code-block:: html+django

        {% load static slick_reporting_tags %}

        {#  make sure to have the js_resources added to your page  #}
        {% block extrajs %}
            {% include "slick_reporting/js_resources.html" %}
        {% endblock %}

        {% block content %}
            {% get_widget_from_url url_name="product-sales" %}
        {% endblock %}

Arguments
---------
You can pass arguments to the ``get_widget`` function to control aspects of its behavior


* title: string, a title for the widget, default to the report title.
* chart_id: the id of the chart that will be rendered as default.
  chart_id is, by default, its index in the ``chart_settings`` list.
* display_table: bool, If the widget should show the results table.
* display_chart: bool, If the widget should show the chart.
* display_chart_selector: bool, If the widget should show the chart selector links or just display the default,or the set chart_id, chart.
* success_callback: string, the name of a javascript function that will be called after the report data is retrieved.
* failure_callback: string, the name of a javascript function that will be called if the report data retrieval fails.
* template_name: string, the template name used to render the widget. Default to `slick_reporting/widget_template.html`
* extra_params: string, extra parameters to pass to the report.
* report_form_selector: string, a jquery selector that will be used to find the form that will be used to pass extra parameters to the report.


This code above will be actually rendered as this in the html page:

.. code-block:: html+django

            <div class="card" id="">
                    <div class="card-body">
                        <div data-report-widget
                             data-report-url="/reports/expense/expensestotalstatement/"
                             data-extra-params=""
                             data-success-callback=""
                             data-fail-callback=""
                            report-form-selector=""
                            data-chart-id=""
                            data-display-chart-selector=""
                            >

                            <!-- container for the chart -->
                            <div id="container" data-report-chart>
                            </div>

                            <!-- container for the table -->
                            <div data-report-table>
                            </div>
                        </div>
                    </div>
                </div>

The ``data-report-widget`` attribute is used by the javascript to find the
widget and render the report.
you can add [data-no-auto-load] to the widget to prevent report loader to get the widget data automatically.

Customization Example
---------------------

You You can customize how the widget is loading by defining your own success call-back
and fail call-back functions.

The success call-back function will receive the report data as a parameter


.. code-block:: html+django

        {% load i18n static slick_reporting_tags %}

        {% get_widget_from_url url_name="product-sales" success_callback=my_success_callback %}

        <script>
            function my_success_callback(data, $element) {
                $element.html(data);
                console.log(data);
            }
        </script>

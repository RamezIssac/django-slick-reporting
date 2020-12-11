.. _usage:

Concept
=======


Given that you have a model where there are data stored which you want to generate reports on.
Consider below SalesOrder model example.

+------------+------------+-----------+----------+-------+-------+
| order_date | product_id | client_id | quantity | price | value |
+------------+------------+-----------+----------+-------+-------+
| 2019-01-01 | 1          | 1         | 5        | 15    | 75    |
+------------+------------+-----------+----------+-------+-------+
| 2019-02-15 | 2          | 2         | 7        | 20    | 140   |
+------------+------------+-----------+----------+-------+-------+
| 2019-02-20 | 2          | 1         | 5        | 20    | 100   |
+------------+------------+-----------+----------+-------+-------+
| 2019-03-14 | 1          | 2         | 3        | 15    | 45    |
+------------+------------+-----------+----------+-------+-------+

Slick Reporting help us answer some questions, like:

* To start: Wouldn't it be nice if we have a view page where we can filter the data based on date , client(s) and or product(s)
* How much each product was sold or How much each Client bought? Filter by date range / client(s) / product(s)
* How well each product sales is doing, monthly?
* How client 1 compared with client 2,  compared with the rest of clients, on each product sales ?
* How many orders were created a day ?

To answer those question, We can identify basic kind of alteration / calculation on the data


1. Basic filtering
------------------

Start small,
A ReportView like the below

.. code-block:: python

    # in your urls.py
    path('path-to-report', TransactionsReport.as_view())

    # in your views.py
    from slick_reporting.views import SlickReportView

    class TransactionsReport(SlickReportView):
        report_model = MySalesItem
        columns = ['order_date', 'product__name' , 'client__name', 'quantity', 'price', 'value' ]


will yield a Page with a nice filter form with
A report where it displays the data as is but with filters however we can apply date and other filters

+------------+---------------+-------------+----------+-------+-------+
| order_date | Product Name  | Client Name | quantity | price | value |
+------------+---------------+-------------+----------+-------+-------+
| 2019-01-01 | Product 1     | Client 1    | 5        | 15    | 75    |
+------------+---------------+-------------+----------+-------+-------+
| 2019-02-15 | Product 2     | Client 2    | 7        | 20    | 140   |
+------------+---------------+-------------+----------+-------+-------+
| 2019-02-20 | Product 2     | Client 1    | 5        | 20    | 100   |
+------------+---------------+-------------+----------+-------+-------+
| 2019-03-14 | Product 1     | Client 2    | 3        | 15    | 45    |
+------------+---------------+-------------+----------+-------+-------+

2. Group By report
-------------------

Where we can group by product -for example- and sum the quantity, or value sold.

+-----------+----------------+-------------+
| Product   | Total Quantity | Total Value |
+-----------+----------------+-------------+
| Product 1 | 8              | 120         |
+-----------+----------------+-------------+
| Product 2 | 13             | 240         |
+-----------+----------------+-------------+

which can be written like this:

.. code-block:: python

        class TotalQuanAndValueReport(SlickReportView):
            report_model = MySalesItem
            group_by = 'product'
            columns = ['name', '__total_quantity__', '__total__' ]



3. Time Series report
------------------------

where we can say how much sum of the quantity sold over a chunks of time periods (like weekly, monthly, ... )

+--------------+----------------------+-----------------+----------------+-----------------------+-------------------------------+
| Product Name | SKU                  | Total Quantity  | Total Quantity | Total Quantity in ... | Total Quantity in December 20 |
|              |                      | in Jan 20       | in Feb 20      |                       |                               |
+--------------+----------------------+-----------------+----------------+-----------------------+-------------------------------+
| Product 1    | <from product model> | 5               | 0              | ...                   | 14                            |
+--------------+----------------------+-----------------+----------------+-----------------------+-------------------------------+
| Product 2    | <from product model> | 0               | 13             | ...                   | 12                            |
+--------------+----------------------+-----------------+----------------+-----------------------+-------------------------------+
| Product 3    | <from product model> | 17              | 12             | ...                   | 17                            |
+--------------+----------------------+-----------------+----------------+-----------------------+-------------------------------+

can be written like this

.. code-block:: python

        class TotalQuantityMonthly(SlickReportView):
            report_model = MySalesItem
            group_by = 'product'
            columns = ['name', 'sku']

            time_series_pattern = 'monthly'
            time_series_columns = ['__total_quantity__']


4. Cross tab report
--------------------

Where we can cross product sold over client for example

+--------------+----------------------+-----------------+----------------+-----------------------+-------------------------------+
| Product Name | SKU                  | Client 1        | Client 2       | Client (n)            | The Reminder                  |
|              |                      | Total value     | Total Value    |                       |                               |
+--------------+----------------------+-----------------+----------------+-----------------------+-------------------------------+
| Product 1    | <from product model> | 10              | 15             | ...                   | 14                            |
+--------------+----------------------+-----------------+----------------+-----------------------+-------------------------------+
| Product 2    | <from product model> | 11              | 12             | ...                   | 12                            |
+--------------+----------------------+-----------------+----------------+-----------------------+-------------------------------+
| Product 3    | <from product model> | 17              | 12             | ...                   | 17                            |
+--------------+----------------------+-----------------+----------------+-----------------------+-------------------------------+

Which can be written like this

.. code-block:: python

    class CrosstabProductClientValue(SlickReportView):
            report_model = MySalesItem
            group_by = 'product'
            columns = ['name', 'sku']

            crosstab_model = 'client'
            crosstab_columns = ['__total_value__']
            crosstab_ids = [client1.pk, client2.pk, client3.pk]
            crosstab_compute_reminder = True



5. Time series - Cross tab
--------------------------
 (#2 & #3 together) Not support at the time.. but soon we hope.




Charts
-------

To create a report we need to a dictionary to a ``chart_settings`` to the SlickReportView.

.. code-block:: python

    class MonthlySalesReport(SlickReportView):
        # ....

        charts_settings = [{
                'type': 'bar',
                'title_source': 'title',
                'data_source': '__total_quantity__',
                'title': _('Total Monthly Sales'),
                'plot_total': True,
            },
            # ... another chart goes here
        ]


* type: what kind of chart it is: Possible options are bar, pie, line and others subject of the underlying charting engine.
  Hats off to : `Charts.js <https://www.chartjs.org/>`_.
* engine_name: String, default to ``SLICK_REPORTING_DEFAULT_CHARTS_ENGINE``. Passed to front end in order to use the appropriate chart engine.
  By default supports `highcharts` & `chartsjs`.
* data_source: Field name containing the numbers we want to plot.
* title_source: Field name containing labels of the data_source
* title: the Chart title. Defaults to the `report_title`.
* plot_total if True the chart will plot the total of the columns. Useful with time series and crosstab reports


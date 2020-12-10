.. _view_response_structure:

SlickReportView Response Structure
==================================

Understanding how the response is structured is imperative in order to customize how the report is displayed on the front end.

Let's have a look

.. code-block:: python

    # Given a class like this
    class GroupByViewWith2Charts(SlickReportView):

        report_model = SalesLineTransaction
        date_field = 'transaction_date'
        group_by = 'product'
        columns = ['name',
                   SlickReportField.create(Sum, 'quantity', name='quantity__sum', verbose_name=_('Quantities Sold')),
                   SlickReportField.create(Sum, 'value', name='value__sum', verbose_name=_('Value $')),
                   ]

        chart_settings = [
            {'type': 'pie',
             'data_source': ['quantity__sum'],
             'title_source': ['name'],
             'title': 'Pie Chart (Quantities)'
             },
            {'type': 'bar',
             'data_source': ['value__sum'],
             'title_source': ['name'],
             'title': 'Column Chart (Values)'
             },
        ]

    # Ajax response or `report_results` template context variable.
    response = {
        # the report slug, defaults to all lower class name.
        "report_slug": "myreportviewclassname",

        # a list of objects representing the actual results of the report
        "data": [
            {"name": "Product 0", "quantity__sum": "1774", "value__sum": "8758"},
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
        # SlickReportView only populate the id if missing.
        "chart_settings": [
            {"type": "pie",
             "data_source": ["quantity__sum"],
             "title_source": ["name"],
             "title": "Pie Chart (Quantities)",
             "id": "pie-0"},

            {"type": "bar",
            "data_source": ["value__sum"],
            "title_source": ["name"],
            "title": "Column Chart (Values)",
             "id": "bar-1"}
        ]
    }



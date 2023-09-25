.. _ settings:

Settings
========

.. note::

        Settings are changed in version 1.1.1 to being a dictionary instead of individual variables.
        Variables will continue to work till next major release.


Below are the default settings for django-slick-reporting. You can override them in your settings file.

.. code-block:: python

    SLICK_REPORTING_SETTINGS = {
        "JQUERY_URL": "https://code.jquery.com/jquery-3.7.0.min.js",
        "DEFAULT_START_DATE_TIME": datetime(
            datetime.now().year, 1, 1, 0, 0, 0, tzinfo=timezone.utc
        ),  # Default: 1st Jan of current year
        "DEFAULT_END_DATE_TIME": datetime.datetime.today(),  # Default to today
        "FONT_AWESOME": {
            "CSS_URL": "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.3/css/all.min.css",
            "ICONS": {
                "pie": "fas fa-chart-pie",
                "bar": "fas fa-chart-bar",
                "line": "fas fa-chart-line",
                "area": "fas fa-chart-area",
                "column": "fas fa-chart-column",
            },
        },
        "CHARTS": {
            "highcharts": "$.slick_reporting.highcharts.displayChart",
            "chartjs": "$.slick_reporting.chartjs.displayChart",
        },
        "MESSAGES": {
            "total": _("Total"),
        },
    }

* JQUERY_URL:

    Link to the jquery file, You can use set it to False and manage the jQuery addition to your liking

* DEFAULT_START_DATE_TIME

    Default date time that would appear on the filter form in the start date

* DEFAULT_END_DATE_TIME

    Default date time that would appear on the filter form in the end date

* FONT_AWESOME:

    Font awesome is used to display the icon next to the chart title. You can override the following settings:

    1. ``CSS_URL``: URL to the font-awesome css file
    2. ``ICONS``: Icons used for different chart types.

* CHARTS:

    The entry points for displaying charts on the front end.
    You can add your own chart engine by adding an entry to this dictionary.

* MESSAGES:

   The strings used in the front end. You can override them here, it also gives a chance to set and translate them per your requirements.


Old versions settings:

1. ``SLICK_REPORTING_DEFAULT_START_DATE``: Default: the beginning of the current year
2. ``SLICK_REPORTING_DEFAULT_END_DATE``: Default: the end of the current  year.
3. ``SLICK_REPORTING_FORM_MEDIA``: Controls the media files required by the search form.
   Defaults is:

.. code-block:: python

    SLICK_REPORTING_FORM_MEDIA = {
        "css": {
            "all": (
                "https://cdn.datatables.net/v/bs4/dt-1.10.20/datatables.min.css",
                "https://cdnjs.cloudflare.com/ajax/libs/Chart.js/2.9.3/Chart.min.css",
            )
        },
        "js": (
            "https://code.jquery.com/jquery-3.3.1.slim.min.js",
            "https://cdn.datatables.net/v/bs4/dt-1.10.20/datatables.min.js",
            "https://cdnjs.cloudflare.com/ajax/libs/Chart.js/2.9.3/Chart.bundle.min.js",
            "https://cdnjs.cloudflare.com/ajax/libs/Chart.js/2.9.3/Chart.min.js",
            "https://code.highcharts.com/highcharts.js",
        ),
    }

4. ``SLICK_REPORTING_DEFAULT_CHARTS_ENGINE``: Controls the default chart engine used.


Settings
========


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

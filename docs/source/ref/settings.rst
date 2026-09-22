.. _settings:


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
        "DEFAULT_CHARTS_ENGINE": SLICK_REPORTING_DEFAULT_CHARTS_ENGINE,
        "MEDIA": {
            "override": False,  # set it to True to override the media files,
            # False will append the media files to the existing ones.
            "js": (
                "https://cdn.jsdelivr.net/momentjs/latest/moment.min.js",
                "https://cdn.datatables.net/1.13.4/js/jquery.dataTables.min.js",
                "https://cdn.datatables.net/1.13.4/js/dataTables.bootstrap5.min.js",
                "slick_reporting/slick_reporting.js",
                "slick_reporting/slick_reporting.report_loader.js",
                "slick_reporting/slick_reporting.datatable.js",
            ),
            "css": {
                "all": (
                    "https://cdn.datatables.net/1.13.4/css/dataTables.bootstrap5.min.css",
                )
            },
        },
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
            "export_to_csv": _("Export to CSV"),
            "print_report": _("Print"),
        },
        # LLM assistant settings
        "LLM_BACKEND": None,
        "LLM_BACKEND_OPTIONS": None,
        "LLM_CATALOG_MODELS": None,
        "LLM_ASK_URL": None,
        "LLM_PLAIN_TEXT_RESPONSE": False,
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

* LLM_BACKEND:

    Dotted path to an LLM backend class. Built-in options are
    ``slick_reporting.llm.backends.OpenRouterBackend`` (preconfigured for
    `OpenRouter <https://openrouter.ai>`_, key read from the
    ``OPENROUTER_API_KEY`` environment variable, defaults to a free-tier
    model), ``slick_reporting.llm.backends.OpenAICompatibleBackend`` (any
    OpenAI-compatible endpoint, including a local llama.cpp server) and
    ``slick_reporting.llm.backends.EchoBackend``. If unset, the backend is
    auto-detected from the environment (``OPENROUTER_API_KEY``, then
    ``OPENAI_API_KEY``), defaulting to ``EchoBackend``.

* LLM_BACKEND_OPTIONS:

    Dictionary passed as keyword arguments when instantiating the
    ``LLM_BACKEND`` class. For ``OpenAICompatibleBackend`` (and
    ``OpenRouterBackend``) supply:

    * ``api_url``: the full chat-completions URL, or ``base_url``: an
      OpenAI-style base URL (``/chat/completions`` is appended).
    * ``api_key``: the literal API key, or ``api_key_env``: the name of an
      environment variable to read it from (``OpenRouterBackend`` defaults
      to ``OPENROUTER_API_KEY``).
    * ``model``: the model identifier (``OpenRouterBackend`` defaults to
      ``slick_reporting.llm.backends.OPENROUTER_DEFAULT_MODEL``).
    * optionally ``temperature``, ``max_tokens``, ``timeout``,
      ``extra_headers`` (dict merged into request headers),
      ``extra_payload`` (dict merged into every request payload, e.g.
      OpenRouter reasoning controls ``{"reasoning": {"effort": "low"}}``),
      and the llama.cpp reasoning switches ``enable_thinking`` /
      ``reasoning_budget``.

* LLM_CATALOG_MODELS:

    Optional list of ``app_label.ModelName`` strings restricting which
    models are visible to the LLM assistant. If omitted, the catalog
    includes all installed models.

* LLM_ASK_URL:

    Optional URL suffix for the assistant endpoint. Defaults to ``ask/``
    under the dashboard path.

* LLM_PLAIN_TEXT_RESPONSE:

    If ``True``, the assistant exchanges reports and answers as structured
    plain text instead of JSON. Useful for smaller/local LLMs. Defaults to
    ``False``.


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

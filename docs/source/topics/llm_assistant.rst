.. _llm_assistant:

Natural-Language / LLM Assistant
================================

django-slick-reporting ships with an optional "Ask the data" assistant.
It lets users post a plain-English business question and returns a natural-language
answer together with the report data that supports it.

How it works
------------

The assistant runs in two stages:

1. **Planning**: the LLM is given a catalog of available report models,
   fields, aggregations, and time-series patterns. It returns a report
   configuration (model, dates, ``group_by``, columns, filters, etc.).

2. **Answer**: the report is executed by slick_reporting, and the LLM is
   called a second time with the report data to produce a concise answer,
   reasoning, and one or more "proofs".

Both the planning and answer stages can exchange data as **JSON** or
**plain text**. JSON is the default; plain text is useful for smaller/local
models that struggle with strict JSON formatting.

Configuration
-------------

Add an ``LLM_BACKEND`` and ``LLM_BACKEND_OPTIONS`` to your
``SLICK_REPORTING_SETTINGS`` dictionary.

OpenRouter (hosted, free-tier models)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

`OpenRouter <https://openrouter.ai>`_ exposes many models through one
OpenAI-compatible API, including free-tier models (ids ending in ``:free``).
The ``OpenRouterBackend`` defaults to the OpenRouter API URL, reads the API
key from the ``OPENROUTER_API_KEY`` environment variable, and uses a free
model unless told otherwise:

.. code-block:: python

    SLICK_REPORTING_SETTINGS = {
        # ... your other settings ...
        "LLM_BACKEND": "slick_reporting.llm.backends.OpenRouterBackend",
        "LLM_BACKEND_OPTIONS": {
            # Any OpenRouter model id; browse free ones at
            # https://openrouter.ai/models?q=free
            # (nex-agi/nex-n2.5-mini:free verified best on the demo
            # evaluation set as of 2026-09)
            "model": "nex-agi/nex-n2.5-mini:free",
            "temperature": 0.2,
            # Optional OpenRouter reasoning controls (or any extra payload keys):
            # "extra_payload": {"reasoning": {"effort": "low"}},
            # Optional OpenRouter attribution headers:
            # "site_url": "https://your-site.example",
            # "app_name": "Your App",
        },
    }

    # and in your shell environment (never in code):
    # export OPENROUTER_API_KEY=sk-or-...

Free-tier models share an upstream pool that is frequently rate-limited
(popular ones such as ``google/gemma-4-*:free`` may answer with HTTP 429 for
stretches of time); pick a verified model with the ``evaluate_llm`` command
shown below, and choose a paid model for production workloads.

A local llama.cpp server
^^^^^^^^^^^^^^^^^^^^^^^^

A locally hosted `llama.cpp <https://github.com/ggml-org/llama.cpp>`_ server
speaks the same OpenAI-compatible protocol and needs no real API key:

.. code-block:: python

    SLICK_REPORTING_SETTINGS = {
        # ... your other settings ...
        "LLM_BACKEND": "slick_reporting.llm.backends.OpenAICompatibleBackend",
        "LLM_BACKEND_OPTIONS": {
            "base_url": "http://localhost:8080/v1",
            "api_key": "not-needed",
            "model": "local",
            "temperature": 0.2,
            # llama.cpp reasoning controls:
            # "enable_thinking": False,
            # "reasoning_budget": 0,
        },
    }

Any other OpenAI-compatible provider
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

    SLICK_REPORTING_SETTINGS = {
        # ... your other settings ...
        "LLM_BACKEND": "slick_reporting.llm.backends.OpenAICompatibleBackend",
        "LLM_BACKEND_OPTIONS": {
            # Either the full chat-completions URL:
            "api_url": "https://api.openai.com/v1/chat/completions",
            # ... or an OpenAI-style base URL ("/chat/completions" is appended):
            # "base_url": "https://api.openai.com/v1",
            # A literal key, or the name of an env var to read it from:
            "api_key": os.environ.get("OPENAI_API_KEY"),
            # "api_key_env": "OPENAI_API_KEY",
            "model": "gpt-4o-mini",
            "temperature": 0.2,
        },
        "LLM_CATALOG_MODELS": [
            # Optional. Restrict which models the assistant can see.
            # "myapp.Client",
            # "myapp.SalesTransaction",
        ],
    }

If ``LLM_BACKEND`` is not set at all, the backend is auto-detected from the
environment: ``OPENROUTER_API_KEY`` selects the OpenRouter backend with its
default free model, ``OPENAI_API_KEY`` selects the OpenAI backend, and
otherwise the no-op ``EchoBackend`` is used (the ask endpoint then answers
with a "no backend configured" error).

Then include the assistant URLs wherever you mount the reporting dashboard:

.. code-block:: python

    from django.urls import path, include

    urlpatterns = [
        path("dashboard/", include("slick_reporting.llm.urls")),
    ]

The ask endpoint is exposed at ``/dashboard/ask/`` by default and accepts a
POST body of ``{"question": "..."}``.

You can also build the endpoint behind your own access check; the assistant
reuses ``SLICK_REPORTING_SETTINGS["REPORT_VIEW_ACCESS_FUNCTION"]``.

Plain-text mode
---------------

Some LLMs produce cleaner output when they do not have to emit valid JSON.
Set ``LLM_PLAIN_TEXT_RESPONSE`` to ``True`` to switch both planning and
answering to structured plain text.

.. code-block:: python

    SLICK_REPORTING_SETTINGS = {
        # ... other settings ...
        "LLM_PLAIN_TEXT_RESPONSE": True,
    }

In plain-text mode the LLM is asked to return blocks like::

    THINKING: short reasoning
    REPORT_MODEL: app_label.ModelName
    DATE_FIELD: date
    START_DATE: 2026-01-01
    END_DATE: 2026-12-31
    GROUP_BY: product
    COLUMNS: name, Sum(value)
    TIME_SERIES_PATTERN: monthly
    TIME_SERIES_COLUMNS: Sum(value)
    CROSSTAB_FIELD:
    CROSSTAB_COLUMNS:
    FILTERS: product_id__in=Product 1

The backend parses this into the same internal report configuration that the
JSON path uses, so execution and validation behave identically.

For the answer stage, the LLM returns blocks like::

    ANSWER: concise business-friendly answer
    REASONING: how the data was interpreted
    PROOF_TITLE: Product totals
    PROOF_REPORT_MODEL: app_label.ModelName
    PROOF_SUMMARY: what this report shows
    PROOF_KEY_NUMBERS: Total: 12345; Average: 678

Evaluating the assistant
------------------------

A management command is included to benchmark the assistant end-to-end. It
runs a set of questions, checks the resulting report configuration, and
captures timing information.

.. code-block:: bash

    # JSON mode (default)
    python manage.py evaluate_llm \
        --questions-file demo_app/fixtures/llm_eval_questions.json

    # Plain-text mode
    python manage.py evaluate_llm \
        --questions-file demo_app/fixtures/llm_eval_questions.json \
        --plain-text

    # Compare several backend configs
    python manage.py evaluate_llm \
        --configs-file demo_app/fixtures/llm_eval_configs.json \
        --questions-file demo_app/fixtures/llm_eval_questions.json \
        --output eval_report.json

    # One-off overrides, e.g. try an OpenRouter model:
    python manage.py evaluate_llm \
        --api-url https://openrouter.ai/api/v1/chat/completions \
        --api-key "$OPENROUTER_API_KEY" \
        --model nex-agi/nex-n2.5-mini:free

Writing a custom backend
------------------------

A backend is any class implementing ``complete(self, prompt: str) -> str``.
The ``prompt`` contains the full system + user text; the method returns the
raw assistant content.

.. code-block:: python

    from slick_reporting.llm.backends import LLMBackend

    class MyBackend(LLMBackend):
        def complete(self, prompt: str) -> str:
            ...
            return response_text

Point to it with::

    SLICK_REPORTING_SETTINGS = {
        "LLM_BACKEND": "myapp.backends.MyBackend",
        "LLM_BACKEND_OPTIONS": {},
    }

The included ``OpenAICompatibleBackend`` works with any provider exposing the
OpenAI chat-completions JSON schema; ``OpenRouterBackend`` is a preconfigured
subclass for OpenRouter.

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Django Slick Reporting is a Django library for generating analytical reports: simple aggregations, group-by, time-series, and crosstab (matrix) reports with built-in chart support (Highcharts, Chart.js).

## Commands

### Run all tests
```bash
python runtests.py
```

### Run a specific test
```bash
python runtests.py tests.tests.TestClassName.test_method_name
```

### Run tests with coverage
```bash
coverage run --include=../* runtests.py && coverage html
```

### Format & lint
```bash
black --line-length 120 .
ruff check --line-length 120 .
```

## Architecture

The library is layered as: **ReportView** (Django CBV) → **ReportGenerator** (computation engine) → **ComputationField** (calculation definitions) → **ReportFieldRegistry** (field lookup).

### Key modules in `slick_reporting/`

- **generator.py** — Core engine. `ReportGenerator` handles group-by, time-series, and crosstab logic. `ListViewReportGenerator` handles ungrouped row-level reports. Entry point is `get_report_data()`.
- **fields.py** — `ComputationField` base class and built-ins (`TotalReportField`, `BalanceReportField`, etc.). Fields declare `calculation_method` (e.g. `Sum`), `calculation_field`, and `requires` for dependency chaining. Use `ComputationField.create()` factory or subclass + `@report_field_register` decorator.
- **views.py** — `ReportView` extends `FormView` with report generation, chart context, CSV export, and AJAX support. Access control via `test_func()`.
- **forms.py** — `ReportForm` auto-generates filter forms from model ForeignKeys with crispy-forms/Bootstrap layout. `report_form_factory` builds forms dynamically.
- **registry.py** — `field_registry` singleton. ComputationFields self-register to avoid naming collisions with factory-created fields.
- **app_settings.py** — Defaults and settings loaded from Django's `SLICK_REPORTING_SETTINGS` dict.

### Charts

Charts are configurable per report via `Chart` dataclass. Supported engines: Highcharts, Chart.js, and Apex Charts. New chart engines can be added by providing a JS integration file and registering it in settings.

### Report types

Controlled by `ReportGenerator` configuration:
- **Group-by**: set `group_by` field, get one row per distinct value
- **Time-series**: set `time_series_pattern` (daily/weekly/monthly/yearly/custom), columns repeat per period
- **Crosstab**: set `crosstab_field` + `crosstab_ids`, produces matrix layout
- **Crosstab + Time-series**: can be combined for a matrix over time periods
- **List view**: use `ListViewReportGenerator` for ungrouped row-level output

### Column duck typing

Columns in `columns` list can be: model field names (str), traversing field names on the group-by model (e.g. `"client__contact__name"`), `ComputationField` subclasses, or special markers (`__total__`, `__balance__`, `__time_series__`, `__crosstab__`).

## Test structure

Tests live in `tests/` with settings in `tests/settings.py` (SQLite, no migrations). Test models (`Product`, `Client`, `SimpleSales`, etc.) are defined in `tests/models.py`. `BaseTestData` in `tests/tests.py` creates fixture data across multiple dates for time-series testing.

- LLM assistant tests live in `tests/llm_tests.py`; `tests/test_llm.py` re-exports them because the default `test*.py` discovery pattern does not match `llm_tests.py` — extend `llm_tests.py`, keep the shim.
- `demo_proj/` is a separate runnable demo app with its own tests: `cd demo_proj && python manage.py test demo_app`. Its settings load `<demo_proj>/.env` via python-dotenv (`override=False`, so exported env vars win; `DJANGO_DOTENV_PATH` overrides the location).
- View tests (e.g. `tests.tests.TestView`) can 302-redirect when run standalone because `DEBUG=False` makes the default `REPORT_VIEW_ACCESS_FUNCTION` demand a superuser; validate with the full `python runtests.py`, not single-test runs.

## LLM assistant

- Code lives in `slick_reporting/llm/` (backends, executor, prompts, views); docs in `docs/source/topics/llm_assistant.rst`.
- Configure via `SLICK_REPORTING_SETTINGS["LLM_BACKEND"]` + `["LLM_BACKEND_OPTIONS"]`; `OpenRouterBackend` (key from `OPENROUTER_API_KEY` env, free-tier default model) and `OpenAICompatibleBackend` (covers local llama.cpp via `base_url`) are built in; auto-detected from the environment when unset.
- Benchmark end-to-end with `demo_proj/manage.py evaluate_llm --questions-file demo_proj/demo_app/fixtures/llm_eval_questions.json [--model <id>] [--plain-text]`.

## Branches / release

- `develop` is the default/integration branch (`origin/HEAD -> origin/develop`); `master` is release-only.
- Releases are tag-triggered (`v*`) via `.github/workflows/release.yml`: tests, build, PyPI publish, changelog extraction via `scripts/extract_changelog.py`, GitHub release, then merge `master` back into `develop`.

## Code style

- Black + Ruff, line length 120
- CI runs on Python 3.9, 3.10, 3.11

## Gotchas

- CI lints only `slick_reporting/` (not `tests/` or `demo_proj/`), with ruff **pinned** (`pip install "ruff==0.16.9"` in `.github/workflows/django.yml`). Keep the pin in sync when bumping ruff locally; the drift history (51 pre-existing errors from an unpinned ruff) was cleared in #122.
- The JSON/AJAX report response is **columnar**: `data` maps each column name to a list of values (one per row),
  not a list of row objects. `ReportGenerator.rows_to_columns()` / `columns_to_rows()` convert between shapes;
  docs: `docs/source/howto/customize_frontend.rst`.
- Browser verification of the front end: run `demo_proj` (`manage.py migrate && manage.py create_entries &&
  manage.py runserver`), then exercise report pages (`demo_app/helpers.py` lists all report URLs).

## Maintaining this file

Keep this file for knowledge useful to almost every future agent session in this project.
Do not repeat what the codebase already shows; point to the authoritative file or command instead.
Prefer rewriting or pruning existing entries over appending new ones.
When updating this file, preserve this bar for all agents and keep entries concise.

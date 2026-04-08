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

## Code style

- Black + Ruff, line length 120
- CI runs on Python 3.9, 3.10, 3.11

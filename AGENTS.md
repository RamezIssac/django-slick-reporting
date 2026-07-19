# AGENTS.md

Guidance for OpenCode sessions in this repo. See `CLAUDE.md` for deeper architecture notes.

## Commands

- Run all tests: `python runtests.py`
- Run a single test: `python runtests.py tests.tests.TestClassName.test_method_name` (also works for modules in `tests/test_*.py`)
- Lint: `ruff check --line-length 120 slick_reporting/` (CI only lints `slick_reporting/`, not `tests/` or `demo_proj/`)
- Format: `black --line-length 120 .`
- CI order: lint (ruff) then tests — matches `.github/workflows/django.yml`, tested on Python 3.9–3.12
- No package manager lockfile; deps come from `requirements.txt` (runtime) and `tests/requirements.txt` (adds `crispy-bootstrap4` for the test suite)

## Test suite quirks

- `runtests.py` sets `DJANGO_SETTINGS_MODULE=tests.settings` itself — don't need to export it manually
- Test DB is SQLite with `MIGRATE: False` (see `tests/settings.py`) — the app has no migrations; test tables are created directly from models
- Test models live in `tests/models.py`; shared fixture data (multiple dates, for time-series tests) comes from `BaseTestData` in `tests/tests.py`
- `demo_proj/` is a separate runnable Django demo app (own `manage.py`, `db.sqlite3`, `requirements.txt`) used for manual/visual verification — it is not part of the automated test suite

## Architecture (see CLAUDE.md for details)

`ReportView` (Django CBV, `slick_reporting/views.py`) → `ReportGenerator` (`slick_reporting/generator.py`) → `ComputationField` (`slick_reporting/fields.py`) → `ReportFieldRegistry` (`slick_reporting/registry.py`, singleton `field_registry`).

- `ListViewReportGenerator` (subclass of `ReportGenerator`) handles ungrouped row-level reports
- Forms live in `slick_reporting/forms.py` (`SlickReportForm`, `report_form_factory`) — not "ReportForm"
- Report types are controlled by `ReportGenerator` config: `group_by`, `time_series_pattern`, `crosstab_field`/`crosstab_ids`, or combinations thereof
- `columns` list entries are duck-typed: model field name (str), related-field path (e.g. `"client__contact__name"`), a `ComputationField` subclass, or markers `__total__`/`__balance__`/`__time_series__`/`__crosstab__`
- Chart support is configured via the `Chart` dataclass in `generator.py`; built-in engines are `highcharts` (default) and `chartsjs`, registered in `app_settings.py` under `SLICK_REPORTING_SETTINGS["CHARTS"]`
- Any JS charting library can be plugged in as a custom engine (Apex Charts is the worked example) by registering it in `SLICK_REPORTING_SETTINGS["CHARTS"]` and providing an `entryPoint` JS function — see `docs/source/topics/charts.rst`

## Branches / release

- `develop` is the default/integration branch (`origin/HEAD -> origin/develop`); `master` is release-only
- Releases are tag-triggered (`v*`) via `.github/workflows/release.yml`: runs tests, builds, publishes to PyPI, extracts changelog notes via `scripts/extract_changelog.py`, and auto-merges `master` back into `develop`
- Per global user preference: never commit, push, branch, or open a PR unless explicitly asked

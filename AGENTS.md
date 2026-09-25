# AGENTS.md

Guidance for OpenCode sessions in this repo. See `CLAUDE.md` for deeper architecture notes.

## Commands

- Run all tests: `python runtests.py`
- Run a single test: `python runtests.py tests.tests.TestClassName.test_method_name` (also works for modules in `tests/test_*.py`)
- Coverage: `coverage run --include=../* runtests.py && coverage html`
- Lint: `ruff check --line-length 120 slick_reporting/` (CI only lints `slick_reporting/`, not `tests/` or `demo_proj/`)
- Format: `black --line-length 120 .`
- CI order: lint (ruff) then tests — matches `.github/workflows/django.yml`, tested on Python 3.9–3.12
- No package manager lockfile; deps come from `requirements.txt` (runtime) and `tests/requirements.txt` (adds `crispy-bootstrap4` for the test suite)

## Test suite quirks

- `runtests.py` sets `DJANGO_SETTINGS_MODULE=tests.settings` itself — don't need to export it manually
- Test DB is SQLite with `MIGRATE: False` (see `tests/settings.py`) — the app has no migrations; test tables are created directly from models
- Test models live in `tests/models.py`; shared fixture data (multiple dates, for time-series tests) comes from `BaseTestData` in `tests/tests.py`
- `demo_proj/` is a separate runnable Django demo app (own `manage.py`, `db.sqlite3`, `requirements.txt`) used for manual/visual verification — it is not part of the automated test suite
- `demo_proj` has its own tests, run separately: `cd demo_proj && python manage.py test demo_app`
- View tests (e.g. `tests.tests.TestView`) get 302 redirects when run standalone because `tests/settings.py` leaves `DEBUG=False`, so the default `REPORT_VIEW_ACCESS_FUNCTION` demands a superuser; they pass in a full-suite run — validate with the whole `python runtests.py`, not single-test runs
- `demo_proj/demo_proj/settings.py` loads `<demo_proj>/.env` (next to `manage.py`) via python-dotenv before reading any env var; `override=False` so an explicitly exported var wins over the deployed `.env`. `DJANGO_DOTENV_PATH` overrides the location (the tests use it with a tmp dir)
- `tests/llm_tests.py` holds the LLM assistant tests; `tests/test_llm.py` re-exports them because the default `test*.py` discovery pattern does not match `llm_tests.py` — extend `llm_tests.py`, keep the shim

## LLM assistant

- Code lives in `slick_reporting/llm/` (backends, executor, prompts, views); docs in `docs/source/topics/llm_assistant.rst`
- Configure via `SLICK_REPORTING_SETTINGS["LLM_BACKEND"]` + `["LLM_BACKEND_OPTIONS"]`; `OpenRouterBackend` (key from `OPENROUTER_API_KEY` env, free-tier default model) and `OpenAICompatibleBackend` (covers local llama.cpp via `base_url`) are built in
- Benchmark end-to-end with `demo_proj/manage.py evaluate_llm --questions-file demo_proj/demo_app/fixtures/llm_eval_questions.json [--model <id>] [--plain-text]`
- The data-format evaluation (JSON vs plain vs TOON prompt serialization) lives in `slick_reporting/llm/evaluator.py` + `slick_reporting/llm/toon_data.py`; run it with `python run_benchmark.py` (needs `toon-format==0.9.0b1` for the TOON arm, a local OpenAI-compatible endpoint at `192.168.178.100:8080`, writes evidence JSON to `eval_evidence/`). Its tests are `tests/test_llm_eval.py`; the fixture seeds `tests` app models (`Client` has a real `country` field for the US-vs-EG question).
- Executor label-to-id resolution (`prepare_filters`) only applies to pk-targeting lookups (`product`, `product_id`, `product__id__in`); a lookup on a relation's concrete field (`product__name`) keeps its string value — resolving it to a pk silently empties the report.

## Architecture

`ReportView` (Django CBV, `slick_reporting/views.py`) → `ReportGenerator` (`slick_reporting/generator.py`) → `ComputationField` (`slick_reporting/fields.py`) → `ReportFieldRegistry` (`slick_reporting/registry.py`, singleton `field_registry`).

- `generator.py` — core engine; `ReportGenerator` handles group-by/time-series/crosstab, entry point `get_report_data()`; `ListViewReportGenerator` handles ungrouped row-level reports
- `fields.py` — `ComputationField` base + built-ins (`TotalReportField`, `BalanceReportField`, ...); fields declare `calculation_method`/`calculation_field`/`requires` for dependency chaining; create via `ComputationField.create()` or subclass + `@report_field_register`
- `views.py` — `ReportView` extends `FormView` with report generation, chart context, CSV export, AJAX; access control via `test_func()`
- `forms.py` — `SlickReportForm` / `report_form_factory` auto-generate filter forms from model ForeignKeys with crispy-forms layout
- `app_settings.py` — defaults loaded from the Django `SLICK_REPORTING_SETTINGS` dict
- Forms live in `slick_reporting/forms.py` (`SlickReportForm`, `report_form_factory`) — not "ReportForm"
- Report types are controlled by `ReportGenerator` config: `group_by`, `time_series_pattern`, `crosstab_field`/`crosstab_ids`, or combinations thereof
- `columns` list entries are duck-typed: model field name (str), related-field path (e.g. `"client__contact__name"`), a `ComputationField` subclass, or markers `__total__`/`__balance__`/`__time_series__`/`__crosstab__`
- Chart support is configured via the `Chart` dataclass in `generator.py`; built-in engines are `highcharts` (default) and `chartsjs`, registered in `app_settings.py` under `SLICK_REPORTING_SETTINGS["CHARTS"]`
- Any JS charting library can be plugged in as a custom engine (Apex Charts is the worked example) by registering it in `SLICK_REPORTING_SETTINGS["CHARTS"]` and providing an `entryPoint` JS function — see `docs/source/topics/charts.rst`

## Branches / release

- `develop` is the default/integration branch (`origin/HEAD -> origin/develop`); `master` is release-only
- Releases are tag-triggered (`v*`) via `.github/workflows/release.yml`: runs tests, builds, publishes to PyPI, extracts changelog notes via `scripts/extract_changelog.py`, and auto-merges `master` back into `develop`
- Per global user preference: never commit, push, branch, or open a PR unless explicitly asked
- Per global user preference: always ask the user before running any `no-mistakes axi` command (starting runs, responding to gates) — never start or drive a validation pipeline unprompted

## Maintaining this file

Keep this file for knowledge useful to almost every future agent session in this project.
Do not repeat what the codebase already shows; point to the authoritative file or command instead.
Prefer rewriting or pruning existing entries over appending new ones.
When updating this file, preserve this bar for all agents and keep entries concise.

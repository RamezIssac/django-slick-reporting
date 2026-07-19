<div align="center">

# Django Slick Reporting

### The one-stop reporting engine for Django — analytics, charts & dashboards in a few lines of code.

[![PyPI version](https://img.shields.io/pypi/v/django-slick-reporting.svg)](https://pypi.org/project/django-slick-reporting)
[![Python versions](https://img.shields.io/pypi/pyversions/django-slick-reporting.svg)](https://pypi.org/project/django-slick-reporting)
[![Docs](https://img.shields.io/readthedocs/django-slick-reporting)](https://django-slick-reporting.readthedocs.io/)
[![Coverage](https://img.shields.io/codecov/c/github/ra-systems/django-slick-reporting)](https://codecov.io/gh/ra-systems/django-slick-reporting)
[![License](https://img.shields.io/pypi/l/django-slick-reporting.svg)](https://github.com/ra-systems/django-slick-reporting/blob/develop/LICENSE.md)

Grouped totals, time-series, crosstabs and pivots — each one a small Python class, each one chartable with a single line, in **Highcharts, Chart.js or ApexCharts**.

[**Live Demo**](https://django-slick-reporting.com/) · [**Documentation**](https://django-slick-reporting.readthedocs.io/) · [**Quickstart**](#quickstart)

<img src="https://raw.githubusercontent.com/ra-systems/django-slick-reporting/develop/docs/source/topics/_static/srr-hero.png" alt="Django Slick Reporting dashboard" width="900">

</div>

---

## One report class, every chart

Declare the calculation **once**. Switch the visualization by changing a single argument — no new query, no new template.

<div align="center">
<img src="https://raw.githubusercontent.com/ra-systems/django-slick-reporting/develop/docs/source/topics/_static/srr-chart-types.gif" alt="Switching chart types by changing one argument" width="640">
</div>

---

## Why Django Slick Reporting?

- **Every report shape** — simple aggregates, group-by, time-series, crosstab/pivot, and combinations of them.
- **Charts included** — Highcharts, Chart.js and ApexCharts wrappers. Bar, column, line, area, pie — stacked or totalled — from one `Chart(...)` line.
- **Custom calculations** — build reusable computation fields, chain dependencies, compute percentages and balances.
- **Dashboards** — drop any report onto a page as a self-contained widget with a template tag.
- **Model-optional** — report against a Django model, a traversed relation, a raw SQL table, or precomputed/aggregated data.
- **Fast & extendable** — optimized queries, CSV export out of the box, and hooks for everything.

## Installation

```console
pip install django-slick-reporting
```

Add it to `INSTALLED_APPS` and you're ready:

```python
INSTALLED_APPS = [
    ...,
    "crispy_forms",
    "crispy_bootstrap5",
    "slick_reporting",
]
```

## Quickstart

Given a typical `SalesTransaction` model, here is a **group-by** report — total value sold per product — with a bar chart:

<table>
<tr>
<td width="52%" valign="top">

```python
# views.py
from django.db.models import Sum
from slick_reporting.views import ReportView, Chart
from slick_reporting.fields import ComputationField
from .models import SalesTransaction


class ProductSales(ReportView):
    report_model = SalesTransaction
    date_field = "date"
    group_by = "product"

    columns = [
        "name",
        ComputationField.create(
            Sum, "value", name="value__sum",
            verbose_name="Total sold $",
        ),
    ]

    chart_settings = [
        Chart(
            "Total sold $",
            Chart.BAR,
            data_source=["value__sum"],
            title_source=["name"],
        ),
    ]
```

```python
# urls.py
path("product-sales/", ProductSales.as_view()),
```

</td>
<td width="48%" valign="top">

<img src="https://raw.githubusercontent.com/ra-systems/django-slick-reporting/develop/docs/source/topics/_static/srr-groupby.png" alt="Group-by bar chart result" width="100%">

</td>
</tr>
</table>

That's the whole report — filter form, chart, sortable data table and CSV export are generated for you.

## Same data, any visualization

The chart is just configuration. Keep the report, change the `Chart(...)` line:

<table>
<tr>
<td width="50%" valign="top">

```python
Chart(
    "Sales",
    Chart.BAR,
    data_source=["value__sum"],
    title_source=["name"],
)
```
<img src="https://raw.githubusercontent.com/ra-systems/django-slick-reporting/develop/docs/source/topics/_static/srr-bar.png" alt="Bar chart" width="100%">

</td>
<td width="50%" valign="top">

```python
Chart(
    "Sales",
    Chart.PIE,
    data_source=["value__sum"],
    title_source=["name"],
    plot_total=True,
)
```
<img src="https://raw.githubusercontent.com/ra-systems/django-slick-reporting/develop/docs/source/topics/_static/srr-pie.png" alt="Pie chart" width="100%">

</td>
</tr>
</table>

### …and any chart engine

Set `chart_engine` on the report (or per `Chart`). The same data renders through your engine of choice:

<table>
<tr>
<td width="33%" align="center"><b>Highcharts</b><br><code>chart_engine="highcharts"</code></td>
<td width="33%" align="center"><b>Chart.js</b><br><code>chart_engine="chartsjs"</code></td>
<td width="33%" align="center"><b>ApexCharts</b><br><code>chart_engine="apexcharts"</code></td>
</tr>
<tr>
<td width="33%"><img src="https://raw.githubusercontent.com/ra-systems/django-slick-reporting/develop/docs/source/topics/_static/srr-engine-highcharts.png" alt="Highcharts" width="100%"></td>
<td width="33%"><img src="https://raw.githubusercontent.com/ra-systems/django-slick-reporting/develop/docs/source/topics/_static/srr-engine-chartjs.png" alt="Chart.js" width="100%"></td>
<td width="33%"><img src="https://raw.githubusercontent.com/ra-systems/django-slick-reporting/develop/docs/source/topics/_static/srr-engine-apex.png" alt="ApexCharts" width="100%"></td>
</tr>
</table>

## Report types

<details>
<summary><b>Time series</b> — one column per period (daily / weekly / monthly / yearly / custom)</summary>

<br>

```python
class MonthlyProductSales(ReportView):
    report_model = SalesTransaction
    date_field = "date"
    group_by = "product"
    columns = ["name", "sku"]

    time_series_pattern = "monthly"          # daily / weekly / yearly / custom
    time_series_columns = [
        ComputationField.create(Sum, "value", name="value", verbose_name="Sales"),
    ]

    chart_settings = [
        Chart("Sales Monthly", Chart.COLUMN, data_source=["value"], title_source=["name"]),
    ]
```

Calculations are performed for each period and laid out as repeating columns, with an optional grand-total column.

</details>

<details>
<summary><b>Crosstab / Pivot</b> — matrix reports with rows, columns and intersecting totals</summary>

<br>

```python
class ClientProductMatrix(ReportView):
    report_model = SalesTransaction
    group_by = "client"
    crosstab_field = "product"
    crosstab_columns = [
        ComputationField.create(Sum, "value", verbose_name="Value"),
    ]
    crosstab_compute_remainder = True         # a column capturing "everything else"

    columns = [
        "name",
        "__crosstab__",                       # where the matrix columns land
        ComputationField.create(Sum, "value", verbose_name="Total Value"),
    ]
```

<div align="center">
<img src="https://raw.githubusercontent.com/ra-systems/django-slick-reporting/develop/docs/source/topics/_static/srr-crosstab.png" alt="Crosstab matrix report" width="820">
</div>

Crosstab and time-series can even be combined for a matrix over periods. Already-aggregated data? Set `crosstab_precomputed=True`.

</details>

<details>
<summary><b>List view</b> — ungrouped, row-level data</summary>

<br>

```python
from slick_reporting.views import ListReportView

class LastTenSales(ListReportView):
    report_model = SalesTransaction
    date_field = "date"
    columns = ["product__name", "client__name", "date", "quantity", "value"]
    default_order_by = "-date"
    limit_records = 10
```

</details>

<details>
<summary><b>Low-level engine</b> — get raw data without a view</summary>

<br>

```python
from slick_reporting.generator import ReportGenerator

report = ReportGenerator(
    report_model=SalesTransaction,
    group_by="product",
    columns=["title", "__total__"],
)
report.get_report_data()
# -> [{'title': 'Product 1', '__total__': 56}, {'title': 'Product 2', '__total__': 43}, ...]
```

`ReportView` is a thin wrapper over `ReportGenerator` — the same configuration syntax works in both.

</details>

## Dashboards

Compose any report into a page as a self-contained widget — chart, table, or both — with one template tag:

```django
{% load slick_reporting_tags %}

{% get_widget_from_url url_name="product-sales" %}
{% get_widget_from_url url_name="monthly-product-sales" chart_id=1 display_table=False title="Chart only" %}
```

See the [live dashboard example](https://django-slick-reporting.com/dashboard/).

## Demo site

Live at **[django-slick-reporting.com](https://django-slick-reporting.com/)**, or run it locally:

```console
git clone https://github.com/ra-systems/django-slick-reporting.git
python -m venv .venv && source .venv/bin/activate

cd django-slick-reporting/demo_proj
pip install -r requirements.txt
python manage.py migrate
python manage.py create_entries   # generates demo data
python manage.py runserver
```

## Documentation

Full documentation lives on [Read the Docs](https://django-slick-reporting.readthedocs.io/en/latest/). Build it locally with:

```console
cd docs
pip install -r requirements.txt
sphinx-build -b html source build
```

## Running the tests

```console
git clone git@github.com:ra-systems/django-slick-reporting.git
cd django-slick-reporting/tests
python -m pip install -e ..
python runtests.py
# coverage:
coverage run --include=../* runtests.py && coverage html
```

## Contributing

PRs and reviews are most welcome. We follow
[Django's contributing guidelines](https://docs.djangoproject.com/en/dev/internals/contributing/writing-code/unit-tests/).
If the project is useful to you, please consider giving it a star — it keeps the project visible and motivated.

## Authors

- **Ramez Ashraf** — *Initial work* — [@RamezIssac](https://github.com/RamezIssac)

## You might also like

- [**Django ERP Framework**](https://github.com/ra-systems/RA) — build business solutions with ease.
- [**Django Tabular Permissions**](https://github.com/RamezIssac/django-tabular-permissions) — Django permissions in a translatable, filterable HTML table.

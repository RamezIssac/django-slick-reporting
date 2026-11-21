import datetime
import json
from decimal import Decimal
from unittest.mock import patch

from django import forms
from django.core.exceptions import ImproperlyConfigured, PermissionDenied, ValidationError
from django.db.models import Max
from django.test import RequestFactory, TestCase, override_settings

from slick_reporting.fields import ComputationField
from slick_reporting.forms import BaseReportForm
from slick_reporting.generator import ListViewReportGenerator, ReportGenerator
from slick_reporting.helpers import compact_response
from slick_reporting.views import ListReportView, ReportView

from .models import SimpleSales
from .tests import BaseTestData, year
from .views import MonthlyProductSales, ProductClientSalesMatrix


def superuser_only(report_view):
    return report_view.request.user.is_superuser


# get_callable() caches the default access function path, so these tests use their own path.
HEADLESS_SETTINGS = {"REPORT_VIEW_ACCESS_FUNCTION": "tests.test_headless.superuser_only"}


class SalesListReport(ListReportView):
    report_model = SimpleSales
    date_field = "doc_date"
    columns = ["id", "doc_date", "client__name", "value"]


class SalesListReportWithFilters(SalesListReport):
    filters = ["client"]


class SalesStatement(SalesListReport):
    columns = ["id", "doc_date", "client__name", "value", "value_as_text"]
    total_columns = ["value", "value_as_text"]

    def value_as_text(self, obj):
        return str(obj["value"])

    value_as_text.verbose_name = "Value as text"


@override_settings(SLICK_REPORTING_SETTINGS=HEADLESS_SETTINGS)
class ListReportDateRangeTest(BaseTestData, TestCase):
    def get_ajax_data(self, view_class, data):
        request = RequestFactory().get("/", data=data, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        request.user = self.user
        response = view_class.as_view()(request)
        self.assertEqual(response.status_code, 200)
        return ReportGenerator.columns_to_rows(json.loads(response.content)["data"])

    def test_list_report_honors_requested_date_range(self):
        data = self.get_ajax_data(
            SalesListReport,
            {"start_date": f"{year}-02-01 00:00:00", "end_date": f"{year}-02-28 23:59:59"},
        )
        self.assertEqual(len(data), 3)
        self.assertEqual({row["doc_date"][:7] for row in data}, {f"{year}-02"})

    def test_list_report_with_model_form_filters_keeps_default_window(self):
        data = self.get_ajax_data(SalesListReportWithFilters, {"client": self.client1.pk})
        self.assertEqual(len(data), 3)

    def test_list_generator_includes_rows_on_the_start_date(self):
        report = ListViewReportGenerator(
            report_model=SimpleSales,
            columns=["id", "doc_date"],
            date_field="doc_date",
            start_date=datetime.datetime(year, 2, 2),
            end_date=datetime.datetime(year, 2, 28),
        )
        self.assertEqual(len(report.get_report_data()), 3)


class DefaultDatesAreDynamicTest(TestCase):
    def test_settings_default_dates_are_computed_on_each_read(self):
        from slick_reporting import app_settings

        first, later = datetime.datetime(year, 3, 1), datetime.datetime(year, 3, 2)
        with patch.object(app_settings, "get_start_date", return_value=first), patch.object(
            app_settings, "get_end_date", return_value=first
        ):
            self.assertEqual(app_settings.SLICK_REPORTING_SETTINGS["DEFAULT_START_DATE_TIME"], first)
            self.assertEqual(app_settings.SLICK_REPORTING_SETTINGS["DEFAULT_END_DATE_TIME"], first)
        with patch.object(app_settings, "get_end_date", return_value=later):
            self.assertEqual(app_settings.SLICK_REPORTING_SETTINGS["DEFAULT_END_DATE_TIME"], later)

    @override_settings(SLICK_REPORTING_SETTINGS={"DEFAULT_END_DATE_TIME": datetime.datetime(2020, 1, 1)})
    def test_user_setting_overrides_the_computed_default(self):
        from slick_reporting import app_settings

        self.assertEqual(app_settings.SLICK_REPORTING_SETTINGS["DEFAULT_END_DATE_TIME"], datetime.datetime(2020, 1, 1))


class ClientTotals(ReportView):
    report_model = SimpleSales
    date_field = "doc_date"
    group_by = "client"
    columns = ["name", "__total__"]


class ClientTotalsScopedByGetParam(ClientTotals):
    extra_params = {"min_total": {"type": "number"}}

    def filter_results(self, data, for_print=False):
        minimum = Decimal(self.request.GET.get("min_total", "0"))
        return [row for row in data if row["__total__"] >= minimum]


class DateOnlyFilterForm(BaseReportForm, forms.Form):
    start_date = forms.DateField(required=False)
    end_date = forms.DateField(required=False)

    def get_filters(self):
        return [], {}

    def get_start_date(self):
        return datetime.datetime.combine(self.cleaned_data["start_date"], datetime.time.min)

    def get_end_date(self):
        return datetime.datetime.combine(self.cleaned_data["end_date"], datetime.time.max)


class ClientTotalsWithDateOnlyForm(ClientTotals):
    form_class = DateOnlyFilterForm


@override_settings(SLICK_REPORTING_SETTINGS=HEADLESS_SETTINGS)
class HeadlessRunTest(BaseTestData, TestCase):
    def setUp(self):
        self.request = RequestFactory().post("/mcp/")
        self.request.user = self.user

    def rows(self, response):
        return ReportGenerator.columns_to_rows(response["data"])

    def test_group_by_with_defaults(self):
        rows = self.rows(ClientTotals.run(self.request))
        self.assertEqual(
            {row["name"]: row["__total__"] for row in rows}, {"Client 1": 300, "Client 2": 600, "Client 3": 900}
        )

    def test_group_by_with_fk_filter_and_dates(self):
        params = {"client_id": [self.client1.pk], "start_date": f"{year}-02-01T00:00:00", "end_date": f"{year}-02-28"}
        rows = self.rows(ClientTotals.run(self.request, params))
        self.assertEqual([(row["name"], row["__total__"]) for row in rows], [("Client 1", 100)])

    def test_time_series(self):
        params = {"start_date": f"{year}-01-01", "end_date": f"{year}-03-31"}
        response = MonthlyProductSales.run(self.request, params)
        self.assertEqual(len(response["metadata"]["time_series_column_names"]), 6)
        self.assertEqual(response["metadata"]["date_window"]["start"].isoformat(), f"{year}-01-01")

    def test_crosstab(self):
        response = ProductClientSalesMatrix.run(self.request, {"client_id": [self.client1.pk]})
        crosstab_columns = response["metadata"]["crosstab_column_names"]
        self.assertEqual(crosstab_columns, [f"__total__CT{self.client1.pk}", "__total__CT----"])
        row = self.rows(response)[0]
        self.assertEqual((row[crosstab_columns[0]], row[crosstab_columns[1]]), (300, 1500))

    def test_list_report(self):
        params = {"start_date": f"{year}-02-01", "end_date": f"{year}-02-28"}
        self.assertEqual(len(self.rows(SalesListReport.run(self.request, params))), 3)

    def test_extra_params_reach_request_get(self):
        rows = self.rows(ClientTotalsScopedByGetParam.run(self.request, {"min_total": 500}))
        self.assertEqual([row["name"] for row in rows], ["Client 2", "Client 3"])

    def test_unknown_param_is_rejected(self):
        with self.assertRaises(ValidationError) as caught:
            ClientTotals.run(self.request, {"client": [self.client1.pk]})
        self.assertEqual(caught.exception.error_dict["client"][0].code, "unknown_parameter")

    def test_invalid_value_carries_form_errors(self):
        with self.assertRaises(ValidationError) as caught:
            ClientTotals.run(self.request, {"client_id": ["x"]})
        self.assertEqual(caught.exception.error_dict["client_id"][0].code, "invalid_pk_value")

    def test_access_is_checked(self):
        self.request.user = self.limited_user
        with self.assertRaises(PermissionDenied):
            ClientTotals.run(self.request)
        self.assertTrue(self.rows(ClientTotals.run(self.request, check_access=False)))

    def test_date_field_form(self):
        rows = self.rows(ClientTotalsWithDateOnlyForm.run(self.request))
        self.assertEqual([row["__total__"] for row in rows], [300, 600, 900])
        params = {"start_date": f"{year}-02-01", "end_date": f"{year}-02-28"}
        rows = self.rows(ClientTotalsWithDateOnlyForm.run(self.request, params))
        self.assertEqual([row["__total__"] for row in rows], [100, 200, 300])

    def test_default_dates_are_computed_at_call_time(self):
        later = datetime.datetime(year, 2, 28, 23, 59, 59)
        with patch("slick_reporting.forms.app_settings.get_end_date", return_value=later), patch(
            "slick_reporting.views.get_end_date", return_value=later
        ):
            rows = self.rows(ClientTotals.run(self.request))
        self.assertEqual(rows[0]["__total__"], 200)


class LatestValue(ComputationField):
    calculation_method = Max

    def resolve(self, prepared_results, required_computation_results, current_pk, current_row=None):
        return self.extract_data(prepared_results, current_pk)[0]


class ClientLastSale(ClientTotals):
    columns = [
        "name",
        "__total__",
        LatestValue.create(Max, "flag", name="last_flag", verbose_name="Last flag"),
        LatestValue.create(Max, "doc_date", name="last_sale", verbose_name="Last sale"),
    ]


@override_settings(SLICK_REPORTING_SETTINGS=HEADLESS_SETTINGS)
class CompactResponseTest(BaseTestData, TestCase):
    def setUp(self):
        self.request = RequestFactory().get("/")
        self.request.user = self.user

    def test_group_by(self):
        compact = compact_response(ClientTotals.run(self.request))
        self.assertEqual(
            compact["columns"],
            [
                {"name": "name", "label": "Name", "type": "text"},
                {"name": "__total__", "label": "Sum of value", "type": "number"},
            ],
        )
        self.assertEqual(compact["rows"], [["Client 1", "300"], ["Client 2", "600"], ["Client 3", "900"]])
        self.assertEqual(compact["totals"], {"__total__": "1800"})
        self.assertEqual((compact["row_count"], compact["truncated"]), (3, False))
        self.assertEqual(compact["date_window"]["end"], datetime.date.today().isoformat())
        json.dumps(compact)

    def test_totals_cover_all_rows_when_truncated(self):
        compact = compact_response(ClientTotals.run(self.request), max_rows=1)
        self.assertEqual(compact["rows"], [["Client 1", "300"]])
        self.assertEqual(
            (compact["row_count"], compact["truncated"], compact["totals"]), (3, True, {"__total__": "1800"})
        )

    def test_time_series_columns_are_numbers_and_summed(self):
        params = {"start_date": f"{year}-01-01", "end_date": f"{year}-03-31"}
        compact = compact_response(MonthlyProductSales.run(self.request, params))
        series = [col for col in compact["columns"] if "TS" in col["name"]]
        self.assertEqual({col["type"] for col in series}, {"number"})
        january_total = next(col["name"] for col in series if col["name"].startswith("__total__"))
        self.assertEqual(compact["totals"][january_total], "600")
        json.dumps(compact)

    def test_list_values_are_json_safe(self):
        params = {"start_date": f"{year}-02-01", "end_date": f"{year}-02-28"}
        compact = compact_response(SalesListReport.run(self.request, params))
        self.assertEqual([col["type"] for col in compact["columns"]], ["number", "datetime", "text", "number"])
        self.assertEqual(compact["totals"], {})
        self.assertTrue(compact["rows"][0][1].startswith(f"{year}-02-02"))
        self.assertIn(compact["rows"][0][3], {"100.00", "200.00", "300.00"})
        json.dumps(compact)

    def test_list_report_totals_declared_columns_over_all_rows(self):
        compact = compact_response(SalesStatement.run(self.request), max_rows=2)
        self.assertEqual(len(compact["rows"]), 2)
        self.assertEqual((compact["row_count"], compact["truncated"]), (9, True))
        self.assertEqual(compact["totals"], {"value": "1800.00", "value_as_text": "1800.00"})
        self.assertEqual(compact["columns"][4]["type"], "text")

    def test_declared_total_columns_are_summable_in_the_full_response(self):
        columns = {col["name"]: col["is_summable"] for col in SalesStatement.run(self.request)["columns"]}
        self.assertEqual((columns["value"], columns["value_as_text"], columns["client__name"]), (True, True, ""))

    def test_declared_total_column_with_text_values_has_no_total(self):
        class NamesTotalled(SalesListReport):
            total_columns = ["client__name"]

        self.assertEqual(compact_response(NamesTotalled.run(self.request))["totals"], {})

    def test_unknown_total_column_raises(self):
        class TypoTotal(SalesListReport):
            total_columns = ["valeu"]

        with self.assertRaisesMessage(ImproperlyConfigured, "['valeu']"):
            TypoTotal.run(self.request)

    def test_grouped_report_total_columns_add_to_computation_fields(self):
        class ClientTotalsWithIdTotal(ClientTotals):
            columns = ["id", "name", "__total__"]
            total_columns = ["id"]

        compact = compact_response(ClientTotalsWithIdTotal.run(self.request), max_rows=1)
        self.assertEqual(compact["totals"]["__total__"], "1800")
        self.assertIn("id", compact["totals"])

    def test_non_numeric_computation_column_has_no_total(self):
        compact = compact_response(ClientLastSale.run(self.request))
        self.assertEqual(compact["totals"], {"__total__": "1800"})
        self.assertEqual([row[2] for row in compact["rows"]], ["sales", "sales", "sales"])
        json.dumps(compact)

    def test_value_normalization(self):
        response = {
            "columns": [
                {"name": "amount", "verbose_name": "Amount", "type": "number", "is_summable": True},
                {"name": "ratio", "verbose_name": "Ratio", "type": "FloatField", "is_summable": ""},
                {"name": "active", "verbose_name": "Active", "type": "BooleanField"},
                {"name": "hidden", "verbose_name": "Hidden", "type": "text", "visible": False},
            ],
            "data": {
                "amount": [Decimal("100"), 0.1, None, ""],
                "ratio": [1.5, None, 2, Decimal("1E+2")],
                "active": [True, False, None, True],
                "hidden": ["a", "b", "c", "d"],
            },
            "metadata": {},
        }
        compact = compact_response(response)
        self.assertEqual([col["name"] for col in compact["columns"]], ["amount", "ratio", "active"])
        self.assertEqual(
            compact["rows"],
            [["100", "1.5", True], ["0.1", None, False], [None, "2", None], [None, "100", True]],
        )
        self.assertEqual(compact["totals"], {"amount": "100.1"})
        self.assertEqual(compact["date_window"], {"start": None, "end": None, "label": None})


@override_settings(SLICK_REPORTING_SETTINGS=HEADLESS_SETTINGS)
class HeadlessEdgeCasesTest(BaseTestData, TestCase):
    def setUp(self):
        self.request = RequestFactory().get("/")
        self.request.user = self.user

    def test_date_only_end_date_covers_the_whole_day(self):
        SimpleSales.objects.create(
            doc_date=datetime.datetime(year, 2, 28, 15, 0),
            client=self.client1,
            product=self.product1,
            quantity=1,
            price=7,
        )
        params = {"client_id": [self.client1.pk], "start_date": f"{year}-02-01", "end_date": f"{year}-02-28"}
        compact = compact_response(ClientTotals.run(self.request, params))
        self.assertEqual(compact["rows"], [["Client 1", "107"]])

    def test_empty_result(self):
        compact = compact_response(
            ClientTotals.run(self.request, {"start_date": "2030-01-01", "end_date": "2030-12-31"})
        )
        self.assertEqual((compact["rows"], compact["row_count"], compact["truncated"]), ([], 0, False))
        self.assertEqual(compact["totals"], {"__total__": "0"})

    def test_order_by_is_not_a_parameter(self):
        with self.assertRaises(ValidationError) as caught:
            ClientTotals.run(self.request, {"order_by": "name"})
        self.assertEqual(caught.exception.error_dict["order_by"][0].code, "unknown_parameter")

import json

import datetime

from django.contrib.auth.models import Permission
from django.db.models import Sum
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import RequestFactory, TestCase

from slick_reporting.fields import ComputationField
from slick_reporting.dynamic_report import (
    DYNAMIC_REPORT_SPEC_SCHEMA,
    describe_dynamic_report_models,
    run_dynamic_report,
)
from slick_reporting.generator import ReportGenerator
from slick_reporting.helpers import compact_response
from slick_reporting.registry import field_registry

from .models import Client, SalesWithFlag, SimpleSales
from .tests import BaseTestData, year

ALLOWED = ["tests.SimpleSales", "tests.Client", "tests.Product"]
VALUE_SUM = {"method": "Sum", "field": "value", "name": "value_sum", "verbose_name": "Sales"}


class DynamicReportTest(BaseTestData, TestCase):
    def setUp(self):
        self.request = RequestFactory().post("/mcp/")
        self.request.user = self.user

    def run_spec(self, spec, **kwargs):
        return run_dynamic_report(spec, self.request, allowed_models=kwargs.pop("allowed_models", ALLOWED), **kwargs)

    def assert_spec_error(self, spec, key, code, **kwargs):
        with self.assertRaises(ValidationError) as caught:
            self.run_spec(spec, **kwargs)
        self.assertIn(code, [error.code for error in caught.exception.error_dict[key]])

    def test_group_by_with_computation(self):
        spec = {"report_model": "tests.SimpleSales", "group_by": "client", "columns": ["name", VALUE_SUM]}
        response = self.run_spec(spec)
        rows = ReportGenerator.columns_to_rows(response["data"])
        self.assertEqual(
            {row["name"]: row["value_sum"] for row in rows}, {"Client 1": 300, "Client 2": 600, "Client 3": 900}
        )
        compact = compact_response(response)
        self.assertEqual(compact["totals"], {"value_sum": "1800"})
        self.assertEqual(compact["columns"][1], {"name": "value_sum", "label": "Sales", "type": "number"})
        json.dumps(compact)

    def test_totals_row_without_group_by_and_avg_is_not_summed(self):
        spec = {
            "report_model": "tests.SimpleSales",
            "columns": [VALUE_SUM, {"method": "Avg", "field": "value"}, {"method": "Count", "field": "id"}],
        }
        compact = compact_response(self.run_spec(spec))
        self.assertEqual(compact["rows"], [["1800", "200", "9"]])
        self.assertEqual(compact["totals"], {"value_sum": "1800", "count__id": "9"})

    def test_date_range_and_label_filter(self):
        spec = {
            "report_model": "tests.SimpleSales",
            "group_by": "client",
            "columns": ["name", VALUE_SUM],
            "date_field": "doc_date",
            "start_date": f"{year}-02-01",
            "end_date": f"{year}-02-28T23:59:59",
            "filters": {"client_id__in": ["Client 1", "Client 3"]},
        }
        compact = compact_response(self.run_spec(spec))
        self.assertEqual(compact["rows"], [["Client 1", "100"], ["Client 3", "300"]])
        self.assertEqual(compact["date_window"]["start"], f"{year}-02-01")

    def test_time_series(self):
        spec = {
            "report_model": "tests.SimpleSales",
            "group_by": "client",
            "columns": ["name"],
            "date_field": "doc_date",
            "start_date": f"{year}-01-01",
            "end_date": f"{year}-03-31",
            "time_series_pattern": "monthly",
            "time_series_columns": [VALUE_SUM],
        }
        compact = compact_response(self.run_spec(spec))
        self.assertEqual(len(compact["columns"]), 4)
        self.assertEqual(compact["rows"][0], ["Client 1", "100", "100", "100"])
        self.assertEqual(sorted(compact["totals"].values()), ["600", "600", "600"])

    def test_crosstab(self):
        spec = {
            "report_model": "tests.SimpleSales",
            "group_by": "product",
            "columns": ["name"],
            "crosstab_field": "client",
            "crosstab_ids": [self.client1.pk],
            "crosstab_compute_remainder": True,
            "crosstab_columns": ["__total__"],
        }
        compact = compact_response(self.run_spec(spec))
        self.assertEqual(
            [col["name"] for col in compact["columns"]], ["name", f"__total__CT{self.client1.pk}", "__total__CT----"]
        )
        self.assertEqual(compact["rows"], [["Product 1", "300", "1500"]])

    def test_list(self):
        spec = {
            "report_model": "tests.SimpleSales",
            "kind": "list",
            "columns": ["doc_date", "client__name", "value"],
            "date_field": "doc_date",
            "start_date": f"{year}-02-01",
            "end_date": f"{year}-02-28",
            "filters": {"value__gte": 200},
        }
        compact = compact_response(self.run_spec(spec))
        self.assertEqual(sorted(row[1] for row in compact["rows"]), ["Client 2", "Client 3"])

    def test_disallowed_models_and_traversals(self):
        spec = {"report_model": "tests.SimpleSales", "columns": [VALUE_SUM]}
        self.assert_spec_error(spec, "report_model", "model_not_allowed", allowed_models=["tests.Client"])
        spec = {"report_model": "tests.SimpleSales", "group_by": "client", "columns": ["name", VALUE_SUM]}
        with self.assertRaises(ValidationError) as caught:
            self.run_spec(spec, allowed_models=["tests.SimpleSales"])
        self.assertEqual(list(caught.exception.error_dict), ["group_by"])
        self.assertEqual(caught.exception.error_dict["group_by"][0].code, "model_not_allowed")
        spec = {"report_model": "tests.SimpleSales", "columns": [VALUE_SUM], "filters": {"client__contact__agent": 1}}
        self.assert_spec_error(spec, "filters", "model_not_allowed")

    def test_invalid_specs(self):
        base = {"report_model": "tests.SimpleSales", "group_by": "client"}
        self.assert_spec_error({**base, "columns": ["nope"]}, "columns", "unknown_field")
        self.assert_spec_error({**base, "columns": [{"method": "Sum", "field": "slug"}]}, "columns", "invalid")
        self.assert_spec_error({**base, "q_raw": 1}, "q_raw", "unknown_key")
        self.assert_spec_error({**base, "filters": {"value__regex": "."}}, "filters", "unknown_field")
        self.assert_spec_error({**base, "start_date": "2024-01-01"}, "date_field", "required")
        self.assert_spec_error({**base, "date_field": "doc_date", "start_date": "soon"}, "start_date", "invalid")
        self.assert_spec_error({"report_model": "tests.Nope"}, "report_model", "invalid")
        self.assert_spec_error({**base, "kind": "list", "columns": ["value"]}, "group_by", "invalid")

    def test_time_series_period_cap(self):
        spec = {
            "report_model": "tests.SimpleSales",
            "date_field": "doc_date",
            "start_date": "2020-01-01",
            "end_date": "2024-12-31",
            "time_series_pattern": "daily",
            "time_series_columns": [VALUE_SUM],
        }
        self.assert_spec_error(spec, "time_series_pattern", "too_many_periods")
        spec["time_series_pattern"] = "annually"
        self.assertEqual(len(compact_response(self.run_spec(spec))["columns"]), 5)

    def test_view_permission_is_required_on_every_model(self):
        self.request.user = self.limited_user
        spec = {"report_model": "tests.SimpleSales", "group_by": "client", "columns": ["name", VALUE_SUM]}
        with self.assertRaises(PermissionDenied):
            self.run_spec(spec)
        self.limited_user.user_permissions.add(Permission.objects.get(codename="view_simplesales"))
        self.limited_user = type(self.limited_user).objects.get(pk=self.limited_user.pk)
        self.request.user = self.limited_user
        with self.assertRaises(PermissionDenied):
            self.run_spec(spec)
        self.limited_user.user_permissions.add(Permission.objects.get(codename="change_client"))
        self.request.user = type(self.limited_user).objects.get(pk=self.limited_user.pk)
        self.assertEqual(len(self.run_spec(spec)["data"]["name"]), 3)

    def test_request_with_a_user_is_required(self):
        spec = {"report_model": "tests.SimpleSales", "columns": [VALUE_SUM]}
        for request in (None, RequestFactory().get("/")):
            with self.assertRaises(PermissionDenied):
                run_dynamic_report(spec, request)
            with self.assertRaises(PermissionDenied):
                describe_dynamic_report_models(request)

    def test_default_allowed_models_are_the_ones_the_user_may_view(self):
        self.limited_user.user_permissions.add(Permission.objects.get(codename="view_simplesales"))
        self.request.user = type(self.limited_user).objects.get(pk=self.limited_user.pk)
        catalog = describe_dynamic_report_models(self.request)
        self.assertEqual([entry["identifier"] for entry in catalog], ["tests.SimpleSales"])
        response = run_dynamic_report({"report_model": "tests.SimpleSales", "columns": [VALUE_SUM]}, self.request)
        self.assertEqual(response["data"]["value_sum"], [SimpleSales.objects.aggregate(total=Sum("value"))["total"]])
        with self.assertRaises(PermissionDenied):
            run_dynamic_report({"report_model": "tests.Client"}, self.request)

    def test_runs_leave_the_field_registry_unchanged(self):
        names = field_registry.get_all_report_fields_names()
        for _ in range(3):
            self.run_spec(
                {"report_model": "tests.SimpleSales", "columns": [VALUE_SUM, {"method": "Max", "field": "value"}]}
            )
        self.assertEqual(field_registry.get_all_report_fields_names(), names)

    def test_schema_and_catalog(self):
        self.assertEqual(DYNAMIC_REPORT_SPEC_SCHEMA["required"], ["report_model"])
        json.dumps(DYNAMIC_REPORT_SPEC_SCHEMA)
        catalog = describe_dynamic_report_models(self.request, allowed_models=[SimpleSales, Client])
        self.assertEqual([entry["identifier"] for entry in catalog], ["tests.Client", "tests.SimpleSales"])
        sales_fields = {field["name"] for field in catalog[1]["fields"]}
        self.assertIn("client", sales_fields)
        self.assertNotIn("product", sales_fields)
        json.dumps(catalog)


class FlaggedSalesTotal(ComputationField):
    name = "__flagged_sales_total__"
    report_model = SalesWithFlag
    calculation_field = "value"
    calculation_method = Sum


class DynamicReportEdgeCasesTest(BaseTestData, TestCase):
    def setUp(self):
        self.request = RequestFactory().get("/")
        self.request.user = self.user

    def run_spec(self, spec, allowed_models=ALLOWED):
        return run_dynamic_report(spec, self.request, allowed_models=allowed_models)

    def assert_spec_error(self, spec, key, code, allowed_models=ALLOWED):
        with self.assertRaises(ValidationError) as caught:
            self.run_spec(spec, allowed_models)
        self.assertIn(code, [error.code for error in caught.exception.error_dict[key]])

    def test_date_only_end_date_covers_the_whole_day(self):
        SimpleSales.objects.create(
            doc_date=datetime.datetime(year, 2, 28, 15, 0),
            client=self.client1,
            product=self.product1,
            quantity=1,
            price=7,
        )
        spec = {
            "report_model": "tests.SimpleSales",
            "columns": [VALUE_SUM],
            "date_field": "doc_date",
            "start_date": f"{year}-02-01",
            "end_date": f"{year}-02-28",
        }
        self.assertEqual(compact_response(self.run_spec(spec))["rows"], [["607"]])

    def test_filter_values_are_checked_against_the_field(self):
        base = {"report_model": "tests.SimpleSales", "columns": [VALUE_SUM]}
        self.assert_spec_error({**base, "filters": {"value__gte": "abc"}}, "filters", "invalid")
        self.assert_spec_error({**base, "filters": {"doc_date__gte": "soon"}}, "filters", "invalid")
        self.assert_spec_error({**base, "filters": {"doc_date__year": "2026"}}, "filters", "invalid")
        self.assert_spec_error({**base, "filters": {"client_id": "No such client"}}, "spec", "invalid_spec")

    def test_empty_result(self):
        spec = {
            "report_model": "tests.SimpleSales",
            "group_by": "client",
            "columns": ["name", VALUE_SUM],
            "filters": {"value__gt": 100000},
        }
        compact = compact_response(self.run_spec(spec))
        self.assertEqual((compact["rows"], compact["row_count"], compact["totals"]), ([], 0, {"value_sum": "0"}))

    def test_registered_field_reading_another_model_is_checked(self):
        field_registry.register(FlaggedSalesTotal)
        self.addCleanup(field_registry.unregister, FlaggedSalesTotal)
        spec = {"report_model": "tests.SimpleSales", "columns": ["__flagged_sales_total__"]}
        self.assert_spec_error(spec, "columns", "model_not_allowed")
        self.assertTrue(self.run_spec(spec, allowed_models=ALLOWED + ["tests.SalesWithFlag"])["data"])

    def test_computed_column_cap(self):
        spec = {
            "report_model": "tests.SimpleSales",
            "date_field": "doc_date",
            "start_date": f"{year}-01-01",
            "end_date": f"{year}-12-31",
            "time_series_pattern": "monthly",
            "time_series_columns": [VALUE_SUM],
            "crosstab_field": "client",
            "crosstab_ids": list(range(1, 51)),
            "crosstab_columns": [VALUE_SUM],
        }
        self.assert_spec_error(spec, "spec", "too_large")

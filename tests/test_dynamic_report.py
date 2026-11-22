import json

import datetime
from unittest import mock

from django.contrib.auth.models import Permission, User
from django.db.models import Sum
from django.core.exceptions import ImproperlyConfigured, PermissionDenied, ValidationError
from django.test import RequestFactory, TestCase, modify_settings

from slick_reporting.fields import ComputationField
from slick_reporting.dynamic_report import (
    DEFAULT_EXCLUDED_MODELS,
    DYNAMIC_REPORT_SPEC_SCHEMA,
    describe_dynamic_report_models,
    run_dynamic_report,
)
from slick_reporting.generator import ReportGenerator
from slick_reporting.helpers import compact_response
from slick_reporting.registry import field_registry

from .models import Client, Contact, Product, SalesWithFlag, SimpleSales
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

    def crosstab_spec(self, **extra):
        return {
            "report_model": "tests.SimpleSales",
            "group_by": "product",
            "columns": ["name"],
            "crosstab_field": "client",
            "crosstab_columns": [VALUE_SUM],
            **extra,
        }

    def crosstab_labels(self, spec, **kwargs):
        compact = compact_response(self.run_spec(spec, **kwargs))
        return [col["label"] for col in compact["columns"][1:]], compact["rows"]

    def test_crosstab_without_ids_pivots_on_the_ids_in_the_data(self):
        compact = compact_response(self.run_spec(self.crosstab_spec()))
        clients = (self.client1, self.client2, self.client3)
        self.assertEqual([col["name"] for col in compact["columns"][1:]], [f"value_sumCT{c.pk}" for c in clients])
        labels = [col["label"] for col in compact["columns"][1:]]
        self.assertEqual(labels, ["Sales Client 1", "Sales Client 2", "Sales Client 3"])
        self.assertEqual(compact["rows"], [["Product 1", "300", "600", "900"]])

    def test_crosstab_without_ids_follows_filters_dates_and_scope(self):
        SimpleSales.objects.create(
            doc_date=datetime.datetime(year - 1, 6, 1),
            client=self.clientIdle,
            product=self.product1,
            quantity=1,
            price=5,
        )
        labels = self.crosstab_labels(self.crosstab_spec())[0]
        self.assertEqual(labels, ["Sales Client 1", "Sales Client 2", "Sales Client 3", "Sales Client Idle"])
        dated = self.crosstab_spec(date_field="doc_date", start_date=f"{year}-01-01", end_date=f"{year}-12-31")
        self.assertEqual(self.crosstab_labels(dated), (labels[:3], [["Product 1", "300", "600", "900"]]))
        filtered = self.crosstab_spec(filters={"value__gte": 200})
        self.assertEqual(self.crosstab_labels(filtered), (labels[1:3], [["Product 1", "600", "900"]]))
        scoped = {Client: Client.objects.exclude(pk=self.client3.pk)}
        self.assertEqual(self.crosstab_labels(self.crosstab_spec(), base_querysets=scoped)[0], labels[:2] + labels[3:])

    def test_crosstab_labels_stay_ids_out_of_scope_and_on_plain_fields(self):
        scoped = {Client: Client.objects.exclude(pk=self.client3.pk)}
        spec = self.crosstab_spec(crosstab_ids=[str(self.client3.pk)], crosstab_compute_remainder=True)
        labels = self.crosstab_labels(spec, base_querysets=scoped)[0]
        self.assertEqual(labels, [f"Sales client {self.client3.pk}", "The remainder"])
        spec = self.crosstab_spec(crosstab_ids=[str(self.client1.pk)], crosstab_compute_remainder=True)
        self.assertEqual(self.crosstab_labels(spec)[0], ["Sales Client 1", "The remainder"])
        labels, rows = self.crosstab_labels(self.crosstab_spec(crosstab_field="client__sex"))
        self.assertEqual(labels, [f"Sales client__sex {sex}" for sex in ("FEMALE", "MALE", "OTHER")])
        self.assertEqual(rows, [["Product 1", "600", "300", "900"]])

    def test_crosstab_without_ids_caps_the_ids_found(self):
        with mock.patch("slick_reporting.dynamic_report.MAX_CROSSTAB_IDS", 3):
            self.assertEqual(len(self.crosstab_labels(self.crosstab_spec())[0]), 3)
        with mock.patch("slick_reporting.dynamic_report.MAX_CROSSTAB_IDS", 2):
            self.assert_spec_error(self.crosstab_spec(), "crosstab_ids", "too_many_ids")

    def test_crosstab_without_ids_counts_the_ids_found_in_the_column_cap(self):
        with mock.patch("slick_reporting.dynamic_report.MAX_COMPUTED_COLUMNS", 4):
            self.assertEqual(len(self.crosstab_labels(self.crosstab_spec())[0]), 3)
        with mock.patch("slick_reporting.dynamic_report.MAX_COMPUTED_COLUMNS", 3):
            self.assert_spec_error(self.crosstab_spec(), "spec", "too_large")

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

    def test_series_and_crosstab_keys_need_their_driving_key(self):
        base = {"report_model": "tests.SimpleSales", "group_by": "client", "columns": ["name", VALUE_SUM]}
        self.assert_spec_error({**base, "time_series_columns": [VALUE_SUM]}, "time_series_pattern", "required")
        for key, value in (("crosstab_ids", [self.client1.pk]), ("crosstab_columns", [VALUE_SUM])):
            self.assert_spec_error({**base, key: value}, "crosstab_field", "required")
        self.assert_spec_error({**base, "crosstab_compute_remainder": True}, "crosstab_field", "required")
        placeholder_columns = {"time_series_pattern": "__time_series__", "crosstab_field": "__crosstab__"}
        for key, placeholder in placeholder_columns.items():
            self.assert_spec_error({**base, "columns": ["name", placeholder, VALUE_SUM]}, key, "required")
        list_spec = {"report_model": "tests.SimpleSales", "kind": "list", "columns": ["value"]}
        self.assert_spec_error({**list_spec, "crosstab_ids": [self.client1.pk]}, "crosstab_ids", "invalid")

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
                run_dynamic_report(spec, request, ALLOWED)
            with self.assertRaises(PermissionDenied):
                describe_dynamic_report_models(request, ALLOWED)

    def test_default_allowed_models_are_the_ones_the_user_may_view(self):
        spec = {"report_model": "tests.SimpleSales", "columns": [VALUE_SUM]}
        self.limited_user.user_permissions.add(Permission.objects.get(codename="view_simplesales"))
        self.request.user = type(self.limited_user).objects.get(pk=self.limited_user.pk)
        catalog = describe_dynamic_report_models(self.request)
        self.assertEqual([entry["identifier"] for entry in catalog], ["tests.SimpleSales"])
        response = run_dynamic_report(spec, self.request)
        self.assertEqual(response["data"]["value_sum"], [SimpleSales.objects.aggregate(total=Sum("value"))["total"]])
        with self.assertRaises(PermissionDenied):
            run_dynamic_report({"report_model": "tests.Client"}, self.request)

    def test_auth_and_sessions_are_excluded_by_default(self):
        for spec in (
            {"report_model": "auth.User", "kind": "list", "columns": ["username", "password"]},
            {"report_model": "sessions.Session", "kind": "list", "columns": ["session_key"]},
        ):
            with self.assertRaises(ValidationError) as caught:
                run_dynamic_report(spec, self.request)
            self.assertEqual(caught.exception.error_dict["report_model"][0].code, "model_not_allowed")
        identifiers = {entry["identifier"] for entry in describe_dynamic_report_models(self.request)}
        self.assertIn("tests.SimpleSales", identifiers)
        self.assertFalse({"auth.User", "auth.Group", "auth.Permission", "sessions.Session"} & identifiers)

    def test_excluded_models_replace_the_default(self):
        spec = {"report_model": "tests.SimpleSales", "group_by": "product", "columns": ["name", VALUE_SUM]}
        with self.assertRaises(ValidationError) as caught:
            run_dynamic_report(spec, self.request, excluded_models=["tests.Product"])
        self.assertEqual(caught.exception.error_dict["group_by"][0].code, "model_not_allowed")
        users = {"report_model": "auth.User", "kind": "list", "columns": ["username"]}
        response = run_dynamic_report(users, self.request, excluded_models=[Product])
        self.assertEqual(len(response["data"]["username"]), User.objects.count())
        catalog = describe_dynamic_report_models(self.request, ALLOWED, excluded_models=["tests.Product"])
        self.assertEqual([entry["identifier"] for entry in catalog], ["tests.Client", "tests.SimpleSales"])
        self.assertNotIn("product", {field["name"] for field in catalog[1]["fields"]})

    def test_wrongly_typed_values_are_invalid_on_their_key(self):
        base = {"report_model": "tests.SimpleSales", "columns": [VALUE_SUM]}
        self.assert_spec_error({**base, "filters": {"doc_date__gte": 20260101}}, "filters", "invalid")
        self.assert_spec_error({**base, "filters": {"doc_date__range": [1, 2]}}, "filters", "invalid")
        self.assert_spec_error({**base, "date_field": "doc_date", "start_date": 2026}, "start_date", "invalid")
        self.assert_spec_error({"report_model": 5}, "report_model", "invalid")
        series = {**base, "date_field": "doc_date", "time_series_columns": [VALUE_SUM]}
        self.assert_spec_error({**series, "time_series_pattern": ["monthly"]}, "time_series_pattern", "invalid")
        self.assert_spec_error({**base, "columns": [{"method": ["Sum"], "field": "value"}]}, "columns", "invalid")
        self.assert_spec_error(
            {**base, "columns": [{"method": "Sum", "field": "value", "name": 5}]}, "columns", "invalid"
        )

    def test_column_names_must_be_unique(self):
        base = {"report_model": "tests.SimpleSales", "group_by": "client"}
        max_value = {"method": "Max", "field": "value", "name": "value_sum"}
        self.assert_spec_error({**base, "columns": ["name", VALUE_SUM, max_value]}, "columns", "invalid")
        name_sum = {**VALUE_SUM, "name": "name"}
        self.assert_spec_error({**base, "columns": ["name", name_sum]}, "columns", "invalid")
        series = {"date_field": "doc_date", "time_series_pattern": "monthly", "columns": ["name", VALUE_SUM]}
        spec = {**base, **series, "time_series_columns": [VALUE_SUM, max_value]}
        self.assert_spec_error(spec, "time_series_columns", "invalid")
        spec = {**base, "columns": ["name"], "crosstab_field": "product", "crosstab_columns": [VALUE_SUM, max_value]}
        self.assert_spec_error(spec, "crosstab_columns", "invalid")
        list_spec = {"report_model": "tests.SimpleSales", "kind": "list", "columns": ["value", "value"]}
        self.assert_spec_error(list_spec, "columns", "invalid")

    def test_base_queryset_of_the_report_model_scopes_rows_and_totals(self):
        scoped = {SimpleSales: SimpleSales.objects.filter(client=self.client1)}
        spec = {"report_model": "tests.SimpleSales", "group_by": "client", "columns": ["name", VALUE_SUM]}
        compact = compact_response(self.run_spec(spec, base_querysets=scoped))
        self.assertEqual(compact["rows"], [["Client 1", "300"]])
        self.assertEqual(compact["totals"], {"value_sum": "300"})
        list_spec = {"report_model": "tests.SimpleSales", "kind": "list", "columns": ["value"]}
        self.assertEqual(compact_response(self.run_spec(list_spec, base_querysets=scoped))["row_count"], 3)

    def test_base_queryset_of_a_traversed_relation_scopes_the_report(self):
        scoped = {"tests.Client": Client.objects.exclude(pk=self.client3.pk)}
        spec = {"report_model": "tests.SimpleSales", "group_by": "client", "columns": ["name", VALUE_SUM]}
        compact = compact_response(self.run_spec(spec, base_querysets=scoped))
        self.assertEqual(compact["rows"], [["Client 1", "300"], ["Client 2", "600"]])
        spec = {
            "report_model": "tests.SimpleSales",
            "columns": [VALUE_SUM],
            "filters": {"client__name__startswith": "C"},
        }
        self.assertEqual(compact_response(self.run_spec(spec))["totals"], {"value_sum": "1800"})
        self.assertEqual(compact_response(self.run_spec(spec, base_querysets=scoped))["totals"], {"value_sum": "900"})
        with self.assertRaises(ImproperlyConfigured):
            self.run_spec(spec, base_querysets={Client: SimpleSales.objects.all()})

    def test_partial_scope_sums_only_in_scope_rows(self):
        SimpleSales.objects.create(
            doc_date=datetime.datetime(year, 1, 3), client=self.client1, product=self.product2, quantity=5, price=10
        )
        scoped = {Product: Product.objects.filter(pk=self.product1.pk)}
        spec = {
            "report_model": "tests.SimpleSales",
            "group_by": "client",
            "columns": ["name", VALUE_SUM],
            "filters": {"product__name__startswith": "Product"},
        }
        compact = compact_response(self.run_spec(spec, base_querysets=scoped))
        # The fixture sales are all product1; the added product2 sale of 5 x 10 is out of scope.
        self.assertEqual(compact["rows"], [["Client 1", "300"], ["Client 2", "600"], ["Client 3", "900"]])
        self.assertEqual(compact["totals"], {"value_sum": "1800"})

    def test_reverse_path_into_a_scoped_model_is_rejected(self):
        scoped = {SimpleSales: SimpleSales.objects.filter(product=self.product1)}
        base = {"report_model": "tests.Client"}
        sales_sum = {"method": "Sum", "field": "simplesales__value", "name": "sales"}
        count = {"method": "Count", "field": "id", "name": "clients"}
        for spec, key in (
            ({**base, "columns": [sales_sum]}, "columns"),
            ({**base, "columns": [count], "filters": {"simplesales__product__name": "Product 2"}}, "filters"),
            ({**base, "columns": [count], "date_field": "simplesales__doc_date"}, "date_field"),
            ({**base, "group_by": "simplesales", "columns": [count]}, "group_by"),
        ):
            self.assert_spec_error(spec, key, "model_not_allowed", base_querysets=scoped)
        products = {Product: Product.objects.filter(pk=self.product1.pk)}
        spec = {**base, "columns": [count], "crosstab_field": "simplesales__product", "crosstab_columns": [count]}
        self.assert_spec_error(spec, "crosstab_field", "model_not_allowed", base_querysets=products)
        self.assertEqual(compact_response(self.run_spec({**base, "columns": [sales_sum]}))["totals"], {"sales": "1800"})

    def test_excluded_app_labels_must_exist(self):
        spec = {"report_model": "tests.SimpleSales", "columns": [VALUE_SUM]}
        for excluded in (["auht", "sessions"], None):
            with self.assertRaises(ImproperlyConfigured):
                run_dynamic_report(spec, self.request, excluded_models=excluded)
            with self.assertRaises(ImproperlyConfigured):
                describe_dynamic_report_models(self.request, excluded_models=excluded)

    @modify_settings(INSTALLED_APPS={"remove": ["django.contrib.sessions"]})
    def test_default_exclusion_skips_apps_that_are_not_installed(self):
        spec = {"report_model": "tests.SimpleSales", "columns": [VALUE_SUM]}
        self.assertEqual(compact_response(self.run_spec(spec))["totals"], {"value_sum": "1800"})
        identifiers = {entry["identifier"] for entry in describe_dynamic_report_models(self.request)}
        self.assertIn("tests.SimpleSales", identifiers)
        self.assertFalse({"auth.User", "auth.Group"} & identifiers)
        with self.assertRaises(ImproperlyConfigured):
            run_dynamic_report(spec, self.request, excluded_models=[*DEFAULT_EXCLUDED_MODELS, "payrol"])
        response = run_dynamic_report(spec, self.request, excluded_models=[*DEFAULT_EXCLUDED_MODELS, "tests.Product"])
        self.assertEqual(compact_response(response)["totals"], {"value_sum": "1800"})

    def test_rows_with_a_null_relation_stay_in_scope(self):
        no_contact = Client.objects.create(name="Client 4", sex="MALE")
        SimpleSales.objects.create(
            doc_date=datetime.datetime(year, 1, 3), client=no_contact, product=self.product1, quantity=5, price=10
        )
        scoped = {Contact: Contact.objects.exclude(pk=self.client3.contact_id)}
        spec = {"report_model": "tests.SimpleSales", "kind": "list", "columns": ["value", "client__contact__address"]}
        compact = compact_response(self.run_spec(spec, allowed_models=[*ALLOWED, Contact], base_querysets=scoped))
        self.assertEqual(sorted(row[0] for row in compact["rows"]), ["100.00"] * 3 + ["200.00"] * 3 + ["50.00"])

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

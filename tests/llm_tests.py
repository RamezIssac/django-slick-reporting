import json
import os
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import path, include

from slick_reporting.llm.backends import (
    OPENROUTER_DEFAULT_MODEL,
    EchoBackend,
    OpenAICompatibleBackend,
    OpenRouterBackend,
    get_llm_backend,
)
from slick_reporting.llm.executor import (
    _normalize_llm_columns,
    clean_json_output,
    parse_llm_json,
    parse_llm_plain_text_answer,
    parse_llm_plain_text_plan,
    prepare_filters,
    run_llm_report_config,
)
from slick_reporting.llm.introspection import build_reporting_catalog, resolve_aggregation_method
from tests.tests import BaseTestData, year
from tests.models import Client, Product, SimpleSales


class CatalogTests(TestCase):
    databases = "__all__"

    def test_catalog_contains_simplesales(self):
        catalog = build_reporting_catalog(extra_models=["tests.SimpleSales"])
        model_ids = [m["identifier"] for m in catalog["models"]]
        self.assertIn("tests.SimpleSales", model_ids)
        simplesales = next(m for m in catalog["models"] if m["identifier"] == "tests.SimpleSales")
        self.assertTrue(any(f["name"] == "value" and f["is_numeric"] for f in simplesales["fields"]))
        self.assertTrue(any(f["name"] == "doc_date" and f["is_date"] for f in simplesales["fields"]))


class ExecutorUnitTests(TestCase):
    databases = "__all__"

    def test_clean_json_output_strips_fences(self):
        text = '```json\n{"a": 1}\n```'
        self.assertEqual(clean_json_output(text), '{"a": 1}')

    def test_parse_llm_json(self):
        self.assertEqual(parse_llm_json('{"b": 2}'), {"b": 2})
        self.assertIsNone(parse_llm_json("not json"))

    def test_resolve_aggregation_method(self):
        from django.db.models import Sum

        self.assertEqual(resolve_aggregation_method("Sum"), Sum)
        self.assertEqual(resolve_aggregation_method(Sum), Sum)
        self.assertIsNone(resolve_aggregation_method("Unknown"))

    def test_prepare_filters_resolves_labels_to_ids(self):
        product = Product.objects.create(name="Widget Z", slug="widget-z", category="small", notes="n")
        kw_filters = prepare_filters(SimpleSales, {"product_id__in": [str(product.pk)]})[1]
        self.assertEqual(kw_filters["product_id__in"], [product.pk])

    def test_prepare_filters_resolves_name_labels_in__in(self):
        product = Product.objects.create(name="Widget Z", slug="widget-z", category="small", notes="n")
        kw_filters = prepare_filters(SimpleSales, {"product_id__in": ["Widget Z"]})[1]
        self.assertEqual(kw_filters["product_id__in"], [product.pk])

    def test_prepare_filters_resolves_relation_name_labels_in__in(self):
        product = Product.objects.create(name="Widget Z", slug="widget-z", category="small", notes="n")
        kw_filters = prepare_filters(SimpleSales, {"product__in": ["Widget Z"]})[1]
        self.assertEqual(kw_filters["product__in"], [product.pk])

    def test_prepare_filters_resolves_bare_id_string(self):
        product = Product.objects.create(name="Widget Z", slug="widget-z", category="small", notes="n")
        kw_filters = prepare_filters(SimpleSales, {"product_id": "Widget Z"})[1]
        self.assertEqual(kw_filters["product_id"], product.pk)

    def test_prepare_filters_resolves_through_relation_name(self):
        # A filter on a concrete field of a relation (client__name) compares
        # against the field value itself; the label must NOT be resolved to a
        # pk, or the ORM would match name against an integer id.
        Client.objects.create(name="Acme")
        kw_filters = prepare_filters(SimpleSales, {"client__name__in": ["Acme"]})[1]
        self.assertEqual(kw_filters["client__name__in"], ["Acme"])

    def test_prepare_filters_bare_relation_still_resolves(self):
        product = Product.objects.create(name="Widget Z", slug="widget-z", category="small", notes="n")
        kw_filters = prepare_filters(SimpleSales, {"product__name": "Widget Z", "product_id__in": ["Widget Z"]})[1]
        # Concrete-field filter keeps the string ...
        self.assertEqual(kw_filters["product__name"], "Widget Z")
        # ... while the relation-id filter resolves the label to the pk.
        self.assertEqual(kw_filters["product_id__in"], [product.pk])

    def test_normalize_columns_bare_fk_group_by(self):
        # Bare-FK group_by re-points at the related model, so echo the relation
        # name to its display field "name".
        self.assertEqual(
            _normalize_llm_columns(["product", "value"], "product"),
            ["name", "value"],
        )
        self.assertEqual(
            _normalize_llm_columns(["product__name", "value"], "product"),
            ["name", "value"],
        )

    def test_normalize_columns_fk_path_group_by_kept(self):
        # FK-path group_by (client__country) stays on the report model, so the
        # echo column must be left as the path, not rewritten to "name".
        self.assertEqual(
            _normalize_llm_columns(["client__country", "value"], "client__country"),
            ["client__country", "value"],
        )

    def test_parse_plain_text_plan_group_by(self):
        text = """
THINKING: sum value by product
REPORT_MODEL: demo_app.SalesTransaction
DATE_FIELD: date
START_DATE: 2026-01-01
END_DATE: 2026-12-31
GROUP_BY: product
COLUMNS: name, Sum(value)
TIME_SERIES_PATTERN:
TIME_SERIES_COLUMNS:
FILTERS:
"""
        plan = parse_llm_plain_text_plan(text)
        self.assertEqual(plan["report"]["report_model"], "demo_app.SalesTransaction")
        self.assertEqual(plan["report"]["group_by"], "product")
        self.assertEqual(plan["report"]["columns"], ["name", {"method": "Sum", "field": "value", "name": "value__sum"}])

    def test_parse_plain_text_plan_filter_and_time_series(self):
        text = """
REPORT_MODEL: demo_app.SalesTransaction
DATE_FIELD: date
START_DATE: 2026-01-01
END_DATE: 2026-12-31
GROUP_BY: product
COLUMNS: name
TIME_SERIES_PATTERN: monthly
TIME_SERIES_COLUMNS: Sum(value)
FILTERS: product_id__in=Product 1,Product 2
"""
        plan = parse_llm_plain_text_plan(text)
        self.assertEqual(plan["report"]["time_series_pattern"], "monthly")
        self.assertEqual(
            plan["report"]["time_series_columns"], [{"method": "Sum", "field": "value", "name": "value__sum"}]
        )
        self.assertEqual(plan["report"]["filters"], {"product_id__in": ["Product 1", "Product 2"]})

    def test_parse_plain_text_answer(self):
        text = """
ANSWER: Product 1 sold a lot.
REASONING: Summed value over the period.
PROOF_TITLE: Product totals
PROOF_REPORT_MODEL: demo_app.SalesTransaction
PROOF_SUMMARY: Totals
PROOF_KEY_NUMBERS: Total: 100; Count: 5
"""
        answer = parse_llm_plain_text_answer(text)
        self.assertEqual(answer["answer"], "Product 1 sold a lot.")
        self.assertEqual(answer["reasoning"], "Summed value over the period.")
        self.assertEqual(answer["proofs"][0]["key_numbers"], {"Total": 100, "Count": 5})


class ReportConfigExecutionTests(BaseTestData, TestCase):
    databases = "__all__"

    def test_run_llm_report_config_group_by(self):
        config = {
            "report_model": "tests.SimpleSales",
            "date_field": "doc_date",
            "start_date": "{year}-01-01".format(year=year),
            "end_date": "{year}-04-01".format(year=year),
            "group_by": "product",
            "columns": [
                "name",
                {"method": "Sum", "field": "value", "name": "value__sum"},
            ],
            "filters": {"product_id__in": [self.product1.pk]},
        }
        response = run_llm_report_config(config)
        self.assertEqual(response["report_slug"], "llm_report")
        names = [row["name"] for row in response["data"]]
        self.assertIn("Product 1", names)

    def test_run_llm_report_config_time_series(self):
        config = {
            "report_model": "tests.SimpleSales",
            "date_field": "doc_date",
            "start_date": "{year}-01-01".format(year=year),
            "end_date": "{year}-04-01".format(year=year),
            "group_by": "client",
            "columns": ["name"],
            "time_series_pattern": "monthly",
            "time_series_columns": [{"method": "Sum", "field": "value", "name": "value__sum"}],
        }
        response = run_llm_report_config(config)
        self.assertTrue(response["data"])
        self.assertTrue(response["metadata"]["time_series_column_names"])

    def test_run_llm_report_config_explicit_nulls(self):
        # LLMs emit explicit nulls for unused keys (observed on gemma-4-12b);
        # none of them may break the executor.
        config = {
            "report_model": "tests.SimpleSales",
            "date_field": None,
            "start_date": None,
            "end_date": None,
            "group_by": "client__name",
            "columns": ["client__name", {"method": "Sum", "field": "value", "name": "value__sum"}],
            "time_series_pattern": None,
            "time_series_columns": None,
            "crosstab_columns": None,
            "filters": {},
        }
        response = run_llm_report_config(config)
        self.assertTrue(response["data"])

    def test_run_llm_report_config_fk_path_group_by_and_column(self):
        # FK-path group_by with the path echoed as a column (the eval's
        # "country-total" scenario): data stays on the report model.
        config = {
            "report_model": "tests.SimpleSales",
            "date_field": "doc_date",
            "start_date": "{year}-01-01".format(year=year),
            "end_date": "{year}-04-01".format(year=year),
            "group_by": "client__name",
            "columns": [
                "client__name",
                {"method": "Sum", "field": "value", "name": "value__sum"},
            ],
        }
        response = run_llm_report_config(config)
        names = [row["client__name"] for row in response["data"]]
        self.assertIn(self.client1.name, names)


class _FakeHTTPResponse:
    """Minimal context-manager response for mocked urllib.request.urlopen calls."""

    def __init__(self, payload):
        self._payload = payload
        self.status = 200

    def read(self):
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def _chat_response(content):
    return _FakeHTTPResponse({"choices": [{"message": {"content": content}}]})


class BackendTests(TestCase):
    def test_echo_backend(self):
        backend = EchoBackend()
        self.assertEqual(backend.complete("hello"), "hello")

    def test_openai_backend_payload(self):
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = mock_urlopen.return_value.__enter__.return_value
            mock_response.read.return_value = json.dumps({"choices": [{"message": {"content": '{"a": 1}'}}]}).encode(
                "utf-8"
            )
            backend = OpenAICompatibleBackend(
                api_url="https://api.example.com/v1/chat/completions",
                api_key="test-key",
                model="gpt-4o-mini",
            )
            result = backend.complete('{"a": 1}')
            self.assertEqual(result, '{"a": 1}')

    def test_base_url_resolution(self):
        backend = OpenAICompatibleBackend(base_url="https://api.example.com/v1/", api_key="k", model="m")
        self.assertEqual(backend.api_url, "https://api.example.com/v1/chat/completions")
        # An explicit api_url always wins over base_url.
        backend = OpenAICompatibleBackend(
            base_url="https://api.example.com/v1",
            api_url="https://other.example.com/chat/completions",
            api_key="k",
            model="m",
        )
        self.assertEqual(backend.api_url, "https://other.example.com/chat/completions")

    def test_api_key_env_resolution(self):
        with patch.dict(os.environ, {"MY_LLM_KEY": "secret-from-env"}, clear=True):
            backend = OpenAICompatibleBackend(base_url="https://api.example.com/v1", api_key_env="MY_LLM_KEY", model="m")
        self.assertEqual(backend.api_key, "secret-from-env")
        # A literal api_key wins over the env var.
        with patch.dict(os.environ, {"MY_LLM_KEY": "secret-from-env"}, clear=True):
            backend = OpenAICompatibleBackend(
                base_url="https://api.example.com/v1", api_key_env="MY_LLM_KEY", api_key="literal", model="m"
            )
        self.assertEqual(backend.api_key, "literal")

    def test_missing_url_or_model_raise(self):
        with self.assertRaises(ValueError):
            OpenAICompatibleBackend(api_key="k", model="m")
        with self.assertRaises(ValueError):
            OpenAICompatibleBackend(base_url="https://api.example.com/v1", api_key="k")

    def test_openrouter_backend_defaults(self):
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "or-key"}, clear=True):
            backend = OpenRouterBackend()
        self.assertEqual(backend.api_url, "https://openrouter.ai/api/v1/chat/completions")
        self.assertEqual(backend.api_key, "or-key")
        self.assertEqual(backend.model, OPENROUTER_DEFAULT_MODEL)

    def test_openrouter_attribution_headers(self):
        backend = OpenRouterBackend(api_key="k", model="m", site_url="https://example.com", app_name="Demo")
        self.assertEqual(backend.extra_headers["HTTP-Referer"], "https://example.com")
        self.assertEqual(backend.extra_headers["X-Title"], "Demo")

    def test_openrouter_backend_payload(self):
        """Mocked OpenRouter round trip: URL, auth header, model and extra_payload."""
        captured = {}

        def fake_urlopen(req, timeout=None):
            captured["url"] = req.full_url
            captured["auth"] = req.get_header("Authorization")
            captured["payload"] = json.loads(req.data.decode("utf-8"))
            return _chat_response('{"ok": true}')

        backend = OpenRouterBackend(
            api_key="or-key",
            model="google/gemma-4-31b-it:free",
            extra_payload={"reasoning": {"effort": "low"}},
        )
        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            result = backend.complete("Return the JSON configuration.")

        self.assertEqual(result, '{"ok": true}')
        self.assertEqual(captured["url"], "https://openrouter.ai/api/v1/chat/completions")
        self.assertEqual(captured["auth"], "Bearer or-key")
        self.assertEqual(captured["payload"]["model"], "google/gemma-4-31b-it:free")
        self.assertEqual(captured["payload"]["reasoning"], {"effort": "low"})
        self.assertEqual(captured["payload"]["messages"], [{"role": "user", "content": "Return the JSON configuration."}])

    def test_openrouter_backend_null_content(self):
        # Some providers return explicit null content; treat it as empty text.
        def fake_urlopen(req, timeout=None):
            return _FakeHTTPResponse({"choices": [{"message": {"content": None}}]})

        backend = OpenRouterBackend(api_key="or-key", model="m")
        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            self.assertEqual(backend.complete("hi"), "")

    def test_get_llm_backend_autodetects_openrouter(self):
        with patch("slick_reporting.llm.backends.SLICK_REPORTING_SETTINGS", {}):
            with patch.dict(os.environ, {"OPENROUTER_API_KEY": "or-key"}, clear=True):
                backend = get_llm_backend()
        self.assertIsInstance(backend, OpenRouterBackend)
        self.assertEqual(backend.api_key, "or-key")
        self.assertEqual(backend.model, OPENROUTER_DEFAULT_MODEL)

    def test_get_llm_backend_autodetects_openai(self):
        with patch("slick_reporting.llm.backends.SLICK_REPORTING_SETTINGS", {}):
            with patch.dict(os.environ, {"OPENAI_API_KEY": "oa-key"}, clear=True):
                backend = get_llm_backend()
        self.assertIsInstance(backend, OpenAICompatibleBackend)
        self.assertNotIsInstance(backend, OpenRouterBackend)
        self.assertEqual(backend.api_url, "https://api.openai.com/v1/chat/completions")

    def test_get_llm_backend_falls_back_to_echo(self):
        with patch("slick_reporting.llm.backends.SLICK_REPORTING_SETTINGS", {}):
            with patch.dict(os.environ, {}, clear=True):
                backend = get_llm_backend()
        self.assertIsInstance(backend, EchoBackend)

    def test_get_llm_backend_respects_configured_backend(self):
        settings_dict = {
            "LLM_BACKEND": "slick_reporting.llm.backends.OpenRouterBackend",
            "LLM_BACKEND_OPTIONS": {"api_key": "or-key", "model": "some/model:free"},
        }
        with patch("slick_reporting.llm.backends.SLICK_REPORTING_SETTINGS", settings_dict):
            backend = get_llm_backend()
        self.assertIsInstance(backend, OpenRouterBackend)
        self.assertEqual(backend.model, "some/model:free")


@override_settings(ROOT_URLCONF="tests.llm_tests")
class AskLLMViewTests(BaseTestData, TestCase):
    databases = "__all__"

    def setUp(self):
        super().setUp()
        self.url = "/dashboard/ask/"
        self.user.is_superuser = True
        self.user.save()
        self.client.force_login(self.user)

    def _mock_backend_response(self, plan_json, answer_json):
        class FakeBackend:
            _calls = []

            def complete(self, prompt):
                self._calls.append(prompt)
                if "Available catalog" in prompt:
                    return json.dumps(plan_json)
                return json.dumps(answer_json)

        return FakeBackend()

    @override_settings(
        SLICK_REPORTING_SETTINGS={
            "LLM_BACKEND": "tests.llm_tests.FakeBackend",
            "LLM_BACKEND_OPTIONS": {},
            "JQUERY_URL": "https://code.jquery.com/jquery-3.7.0.min.js",
        }
    )
    def test_ask_endpoint_returns_answer(self):
        plan = {
            "thinking": "Group by product and sum value",
            "report": {
                "report_model": "tests.SimpleSales",
                "date_field": "doc_date",
                "start_date": "{year}-01-01".format(year=year),
                "end_date": "{year}-04-01".format(year=year),
                "group_by": "product",
                "columns": [
                    "name",
                    {"method": "Sum", "field": "value", "name": "value__sum"},
                ],
                "filters": {"product_id__in": [self.product1.pk]},
            },
        }
        answer = {
            "answer": "Product 1 sold a lot.",
            "reasoning": "Summed value over the period.",
            "proofs": [{"title": "Product totals", "summary": "Totals", "key_numbers": {"Total": 100}}],
        }

        fake_backend = self._mock_backend_response(plan, answer)
        # Patch the backend loader instead of relying on import_string for a test-only class.
        with patch("slick_reporting.llm.views.get_llm_backend", return_value=fake_backend):
            response = self.client.post(
                self.url,
                data=json.dumps({"question": "How much did Product 1 sell?"}),
                content_type="application/json",
            )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["answer"], "Product 1 sold a lot.")
        self.assertIn("report_data", data)
        self.assertEqual(data["report_config"]["report_model"], "tests.SimpleSales")

    def test_ask_endpoint_requires_question(self):
        response = self.client.post(self.url, data=json.dumps({}), content_type="application/json")
        self.assertEqual(response.status_code, 400)

    def test_ask_endpoint_forbidden_for_anon(self):
        self.client.logout()
        response = self.client.post(
            self.url,
            data=json.dumps({"question": "test"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)


urlpatterns = [
    path("dashboard/", include("slick_reporting.llm.urls")),
]


@override_settings(ROOT_URLCONF="tests.llm_tests")
class AskLLMViewOpenRouterTests(BaseTestData, TestCase):
    """End-to-end ask flow through the OpenRouter backend with HTTP mocked out."""

    databases = "__all__"

    def setUp(self):
        super().setUp()
        self.url = "/dashboard/ask/"
        self.user.is_superuser = True
        self.user.save()
        self.client.force_login(self.user)

    def test_ask_endpoint_with_openrouter_backend(self):
        plan = {
            "thinking": "Group by product and sum value",
            "report": {
                "report_model": "tests.SimpleSales",
                "date_field": "doc_date",
                "start_date": "{year}-01-01".format(year=year),
                "end_date": "{year}-04-01".format(year=year),
                "group_by": "product",
                "columns": [
                    "name",
                    {"method": "Sum", "field": "value", "name": "value__sum"},
                ],
            },
        }
        answer = {
            "answer": "Product 1 sold a lot.",
            "reasoning": "Summed value over the period.",
            "proofs": [{"title": "Product totals", "summary": "Totals", "key_numbers": {"Total": 100}}],
        }
        captured = []

        def fake_urlopen(req, timeout=None):
            payload = json.loads(req.data.decode("utf-8"))
            is_plan = any("Available catalog" in m.get("content", "") for m in payload["messages"])
            captured.append({"url": req.full_url, "auth": req.get_header("Authorization"), "payload": payload})
            return _chat_response(json.dumps(plan if is_plan else answer))

        backend = OpenRouterBackend(api_key="or-key", model="google/gemma-4-31b-it:free")
        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            with patch("slick_reporting.llm.views.get_llm_backend", return_value=backend):
                response = self.client.post(
                    self.url,
                    data=json.dumps({"question": "How much did Product 1 sell?"}),
                    content_type="application/json",
                )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["answer"], "Product 1 sold a lot.")
        self.assertIn("report_data", data)
        # Both stages (plan + answer) hit the OpenRouter endpoint with the
        # configured model and the bearer key.
        self.assertEqual(len(captured), 2)
        for call in captured:
            self.assertEqual(call["url"], "https://openrouter.ai/api/v1/chat/completions")
            self.assertEqual(call["auth"], "Bearer or-key")
            self.assertEqual(call["payload"]["model"], "google/gemma-4-31b-it:free")


class FakeBackend:
    def __init__(self, **options):
        pass

    def complete(self, prompt):
        if "Available catalog" in prompt:
            return json.dumps(
                {
                    "thinking": "simple",
                    "report": {
                        "report_model": "tests.SimpleSales",
                        "date_field": "doc_date",
                        "start_date": "2024-01-01",
                        "end_date": "2024-04-01",
                        "group_by": "product",
                        "columns": ["name", {"method": "Sum", "field": "value", "name": "value__sum"}],
                    },
                }
            )
        return json.dumps(
            {
                "answer": "Test answer",
                "reasoning": "Test reasoning",
                "proofs": [],
            }
        )

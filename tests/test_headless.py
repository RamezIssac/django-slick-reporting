import datetime
import json
from unittest.mock import patch

from django.test import RequestFactory, TestCase, override_settings

from slick_reporting.generator import ListViewReportGenerator
from slick_reporting.views import ListReportView

from .models import SimpleSales
from .tests import BaseTestData, year


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


@override_settings(SLICK_REPORTING_SETTINGS=HEADLESS_SETTINGS)
class ListReportDateRangeTest(BaseTestData, TestCase):
    def get_ajax_data(self, view_class, data):
        request = RequestFactory().get("/", data=data, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        request.user = self.user
        response = view_class.as_view()(request)
        self.assertEqual(response.status_code, 200)
        return json.loads(response.content)["data"]

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

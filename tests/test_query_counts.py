import datetime
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from . import report_generators
from .tests import BaseTestData, year


class ReportQueryCountTest(BaseTestData, TestCase):
    """Pins the number of queries each report type runs. A change in a count is a new or lost query per row,
    period or crosstab id."""

    start_date = datetime.datetime(year, 1, 1)
    end_date = datetime.datetime(year, 4, 1)

    def test_group_by(self):
        with self.assertNumQueries(4):
            data = report_generators.ClientTotalBalance().get_report_data()
        self.assertEqual(len(data), 3)

    def test_time_series(self):
        with self.assertNumQueries(16):
            report = report_generators.ClientSalesMonthlySeries(start_date=self.start_date, end_date=self.end_date)
            data = report.get_report_data()
        self.assertEqual(len(data), 3)

    def test_crosstab(self):
        with self.assertNumQueries(10):
            report = report_generators.ProductClientSalesMatrix(
                crosstab_ids=[self.client1.pk, self.client2.pk], start_date=self.start_date, end_date=self.end_date
            )
            data = report.get_report_data()
        self.assertEqual(len(data), 1)

    # Patched here: resolving the real access function caches it (get_callable) and changes later view tests.
    @patch("slick_reporting.views.get_access_function", return_value=lambda view: True)
    def test_view_json(self, _):
        with self.assertNumQueries(17):
            response = self.client.get(
                reverse("report1"),
                data={"start_date": self.start_date.date(), "end_date": self.end_date.date()},
                HTTP_X_REQUESTED_WITH="XMLHttpRequest",
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["data"]["name"]), 3)

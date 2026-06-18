from django.urls import path

from .views import AvailableReportsAPIView, DashboardConfiguratorView, DashboardSaveView, DashboardView

app_name = "slick_reporting_dashboard"

urlpatterns = [
    path("", DashboardView.as_view(), name="dashboard"),
    path("edit/", DashboardConfiguratorView.as_view(), name="configurator"),
    path("save/", DashboardSaveView.as_view(), name="save"),
    path("reports/", AvailableReportsAPIView.as_view(), name="available_reports"),
]

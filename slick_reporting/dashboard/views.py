import json

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.http import JsonResponse
from django.urls import reverse, NoReverseMatch
from django.views.generic import TemplateView, View

from .models import Dashboard, DashboardWidget
from .registry import report_registry


class DashboardMixin:
    def get_dashboard(self, request):
        """Return the user's personal Dashboard, or the shared default, or None."""
        try:
            return Dashboard.objects.get(user=request.user)
        except Dashboard.DoesNotExist:
            return Dashboard.objects.filter(user__isnull=True, is_default=True).first()

    def get_or_create_user_dashboard(self, request):
        dashboard, _ = Dashboard.objects.get_or_create(
            user=request.user,
            defaults={"name": f"{request.user}'s Dashboard"},
        )
        return dashboard


class DashboardView(LoginRequiredMixin, DashboardMixin, TemplateView):
    template_name = "slick_reporting/dashboard/dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        dashboard = self.get_dashboard(self.request)
        widgets = []
        if dashboard:
            for widget in dashboard.widgets.all():
                try:
                    reverse(widget.report_url_name)
                    widgets.append(widget)
                except NoReverseMatch:
                    pass
        ctx["dashboard"] = dashboard
        ctx["widgets"] = widgets
        return ctx


class DashboardConfiguratorView(LoginRequiredMixin, DashboardMixin, TemplateView):
    template_name = "slick_reporting/dashboard/configurator.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        dashboard = self.get_dashboard(self.request)
        current_widgets = []
        if dashboard:
            for widget in dashboard.widgets.all():
                try:
                    reverse(widget.report_url_name)
                    current_widgets.append(widget)
                except NoReverseMatch:
                    pass
        ctx["dashboard"] = dashboard
        ctx["current_widgets"] = current_widgets
        ctx["available_reports"] = report_registry.get_available_reports()
        ctx["save_url"] = reverse("slick_reporting_dashboard:save")
        ctx["dashboard_url"] = reverse("slick_reporting_dashboard:dashboard")
        return ctx


class DashboardSaveView(LoginRequiredMixin, DashboardMixin, View):
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            return JsonResponse({"status": "error", "message": "Invalid JSON"}, status=400)

        widgets_data = data.get("widgets", [])

        with transaction.atomic():
            dashboard = self.get_or_create_user_dashboard(request)
            dashboard.widgets.all().delete()
            for item in widgets_data:
                url_name = item.get("report_url_name", "").strip()
                if not url_name:
                    continue
                try:
                    reverse(url_name)
                except NoReverseMatch:
                    continue
                DashboardWidget.objects.create(
                    dashboard=dashboard,
                    report_url_name=url_name,
                    title=item.get("title", ""),
                    gs_x=int(item.get("gs_x", 0)),
                    gs_y=int(item.get("gs_y", 0)),
                    gs_w=int(item.get("gs_w", 6)),
                    gs_h=int(item.get("gs_h", 4)),
                    display_chart=bool(item.get("display_chart", True)),
                    display_table=bool(item.get("display_table", False)),
                    chart_id=int(item.get("chart_id", 0)),
                )

        return JsonResponse({"status": "ok"})


class AvailableReportsAPIView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        reports = report_registry.get_available_reports()
        return JsonResponse({"reports": reports})

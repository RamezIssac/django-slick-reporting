import json

from crispy_forms.utils import render_crispy_form
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseForbidden, JsonResponse, QueryDict
from django.shortcuts import redirect
from django.urls import NoReverseMatch, resolve, reverse
from django.views.generic import TemplateView, View

from .app_settings import dashboard_edit_allowed
from .models import Dashboard, DashboardWidget, SavedWidget
from .registry import report_registry

# Foreign keys that are noise in a user-facing filter builder.
INTERNAL_FKS = {"polymorphic_ctype_id", "owner_id", "lastmod_user_id", "created_by_id", "lastmod_by_id"}


def _url_ok(url_name):
    try:
        reverse(url_name)
        return True
    except NoReverseMatch:
        return False


def saved_widget_dict(widget):
    """Full client-side representation of a SavedWidget, incl. the resolved report URL
    so the configurator can render a live preview without server round-trips per render."""
    try:
        report_url = reverse(widget.report_url_name)
    except NoReverseMatch:
        report_url = "#"
    return {
        "id": widget.pk,
        "name": widget.name,
        "report_url_name": widget.report_url_name,
        "report_url": report_url,
        "chart_id": widget.chart_id,
        "display_chart": widget.display_chart,
        "display_table": widget.display_table,
        "column_span": widget.column_span,
        "extra_params": widget.extra_params,
        "shared": widget.owner_id is None,
    }


class RequireDashboardEditMixin:
    """Block the view when dashboard editing is disabled (read-only mode)."""

    def dispatch(self, request, *args, **kwargs):
        if not dashboard_edit_allowed():
            return self.edit_disabled_response(request)
        return super().dispatch(request, *args, **kwargs)

    def edit_disabled_response(self, request):
        return HttpResponseForbidden("Dashboard editing is disabled.")


class DashboardMixin:
    def get_dashboard(self, request):
        """
        Return the dashboard to display: the user's personal Dashboard, else the
        shared default. When editing is disabled, personal dashboards can't be
        created/curated by users, so any that linger are stale — always use the
        shared default instead (otherwise a stale personal dashboard would shadow
        the curated one and the page would look empty).
        """
        shared_default = Dashboard.objects.filter(user__isnull=True, is_default=True).first()
        if not dashboard_edit_allowed():
            return shared_default
        try:
            return Dashboard.objects.get(user=request.user)
        except Dashboard.DoesNotExist:
            return shared_default

    def get_or_create_user_dashboard(self, request):
        dashboard, _ = Dashboard.objects.get_or_create(
            user=request.user,
            defaults={"name": f"{request.user}'s Dashboard"},
        )
        return dashboard

    def get_placements(self, dashboard):
        """Ordered placements whose report still resolves."""
        if not dashboard:
            return []
        return [
            p
            for p in dashboard.widgets.select_related("saved_widget").all()
            if _url_ok(p.saved_widget.report_url_name)
        ]

    def get_saved_widget_palette(self, request):
        """SavedWidgets available to this user (own + shared), with resolvable reports."""
        qs = SavedWidget.objects.filter(Q(owner=request.user) | Q(owner__isnull=True))
        return [w for w in qs if _url_ok(w.report_url_name)]


class DashboardView(LoginRequiredMixin, DashboardMixin, TemplateView):
    template_name = "slick_reporting/dashboard/dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        dashboard = self.get_dashboard(self.request)
        ctx["dashboard"] = dashboard
        ctx["widgets"] = self.get_placements(dashboard)
        ctx["can_edit"] = dashboard_edit_allowed()
        return ctx


class DashboardConfiguratorView(LoginRequiredMixin, RequireDashboardEditMixin, DashboardMixin, TemplateView):
    template_name = "slick_reporting/dashboard/configurator.html"

    def edit_disabled_response(self, request):
        # Friendlier than a 403 for a page: send the user to the read-only dashboard.
        return redirect("slick_reporting_dashboard:dashboard")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        dashboard = self.get_dashboard(self.request)
        placements = self.get_placements(dashboard)
        ctx["dashboard"] = dashboard
        ctx["current_widgets"] = placements
        ctx["current_widgets_json"] = [saved_widget_dict(p.saved_widget) for p in placements]
        ctx["available_reports"] = report_registry.get_available_reports()
        ctx["saved_widgets"] = self.get_saved_widget_palette(self.request)
        ctx["builder_form_url"] = reverse("slick_reporting_dashboard:builder_form")
        ctx["saved_widget_url"] = reverse("slick_reporting_dashboard:saved_widget")
        ctx["save_url"] = reverse("slick_reporting_dashboard:save")
        ctx["dashboard_url"] = reverse("slick_reporting_dashboard:dashboard")
        return ctx


class WidgetBuilderFormView(LoginRequiredMixin, RequireDashboardEditMixin, View):
    """
    Returns the chosen report's filter form (rendered crispy HTML, internal FKs
    stripped) plus its available charts, so the builder can configure a widget.
    Pass ?report_url_name=... and optionally ?saved_widget_id=... to pre-fill from
    an existing widget for editing.
    """

    def get(self, request, *args, **kwargs):
        report_url_name = request.GET.get("report_url_name", "").strip()
        if not _url_ok(report_url_name):
            return JsonResponse({"status": "error", "message": "Unknown report"}, status=400)

        view_class = resolve(reverse(report_url_name)).func.view_class

        saved = None
        saved_widget_id = request.GET.get("saved_widget_id")
        if saved_widget_id:
            saved = SavedWidget.objects.filter(
                Q(owner=request.user) | Q(owner__isnull=True), pk=saved_widget_id
            ).first()

        # Build the report's own filter form, dropping internal FKs, and pre-fill
        # from the saved widget's stored querystring when editing.
        view = view_class()
        view.request = request
        view.args, view.kwargs = (), {}
        view.fkeys_filter_func_hook = lambda fkeys: {k: v for k, v in fkeys.items() if k not in INTERNAL_FKS}
        form_class = view.get_form_class()

        # Dates default to empty (=> report default range, i.e. "rolling") unless the
        # saved widget pinned them.
        initial = {"start_date": "", "end_date": ""}
        if saved and saved.extra_params:
            qd = QueryDict(saved.extra_params)
            for key in qd.keys():
                values = qd.getlist(key)
                initial[key] = values if len(values) > 1 else values[0]
        form = form_class(initial=initial)
        helper = form.get_crispy_helper()
        helper.form_tag = False
        form_html = render_crispy_form(form, helper)

        report = report_registry.get_report(report_url_name) or {}
        return JsonResponse(
            {
                "status": "ok",
                "form_html": form_html,
                "charts": report.get("charts", []),
                "report_title": report.get("title", ""),
                "name": saved.name if saved else report.get("title", ""),
                "chart_id": saved.chart_id if saved else (report.get("charts") or [{}])[0].get("id", "0"),
                "display_chart": saved.display_chart if saved else bool(report.get("charts")),
                "display_table": saved.display_table if saved else False,
                "column_span": saved.column_span if saved else 12,
            }
        )


class SavedWidgetView(LoginRequiredMixin, RequireDashboardEditMixin, View):
    """JSON CRUD for reusable SavedWidgets (the widget library)."""

    def get(self, request, *args, **kwargs):
        qs = SavedWidget.objects.filter(Q(owner=request.user) | Q(owner__isnull=True))
        widgets = [saved_widget_dict(w) for w in qs if _url_ok(w.report_url_name)]
        return JsonResponse({"status": "ok", "widgets": widgets})

    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            return JsonResponse({"status": "error", "message": "Invalid JSON"}, status=400)

        action = data.get("action", "save")

        if action == "delete":
            widget = self._get_editable(request, data.get("id"))
            if widget is None:
                return JsonResponse({"status": "error", "message": "Not found"}, status=404)
            if widget.placements.exists():
                return JsonResponse(
                    {"status": "error", "message": "Widget is in use on a dashboard; remove it there first."},
                    status=409,
                )
            widget.delete()
            return JsonResponse({"status": "ok"})

        report_url_name = (data.get("report_url_name") or "").strip()
        name = (data.get("name") or "").strip()
        if not name or not _url_ok(report_url_name):
            return JsonResponse({"status": "error", "message": "Name and a valid report are required"}, status=400)

        try:
            column_span = int(data.get("column_span", 12))
        except (TypeError, ValueError):
            column_span = 12
        column_span = min(12, max(1, column_span))

        fields = dict(
            name=name,
            report_url_name=report_url_name,
            chart_id=str(data.get("chart_id", "0")),
            display_chart=bool(data.get("display_chart", True)),
            display_table=bool(data.get("display_table", False)),
            column_span=column_span,
            extra_params=(data.get("extra_params") or "").strip(),
        )

        widget = self._get_editable(request, data.get("id"))
        if widget is not None:
            for key, value in fields.items():
                setattr(widget, key, value)
            widget.save()
        else:
            widget = SavedWidget.objects.create(owner=request.user, **fields)

        return JsonResponse({"status": "ok", "widget": saved_widget_dict(widget)})

    @staticmethod
    def _get_editable(request, widget_id):
        """A widget the user may edit: their own, or a shared one they can adopt-edit."""
        if not widget_id:
            return None
        return SavedWidget.objects.filter(Q(owner=request.user) | Q(owner__isnull=True), pk=widget_id).first()


class DashboardSaveView(LoginRequiredMixin, RequireDashboardEditMixin, DashboardMixin, View):
    """Persist the ordered list of SavedWidget placements on the user's dashboard."""

    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            return JsonResponse({"status": "error", "message": "Invalid JSON"}, status=400)

        items = data.get("widgets", [])
        with transaction.atomic():
            dashboard = self.get_or_create_user_dashboard(request)
            dashboard.widgets.all().delete()
            for order, item in enumerate(items):
                saved_widget_id = item.get("saved_widget_id")
                widget = SavedWidget.objects.filter(
                    Q(owner=request.user) | Q(owner__isnull=True), pk=saved_widget_id
                ).first()
                if widget is None:
                    continue
                DashboardWidget.objects.create(
                    dashboard=dashboard,
                    saved_widget=widget,
                    order=item.get("order", order),
                )
        return JsonResponse({"status": "ok"})


class AvailableReportsAPIView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        return JsonResponse({"reports": report_registry.get_available_reports()})

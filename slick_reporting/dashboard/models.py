from django.conf import settings
from django.db import models


class Dashboard(models.Model):
    name = models.CharField(max_length=200)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="slick_dashboard",
    )
    is_default = models.BooleanField(
        default=False,
        help_text="Mark as the shared fallback for users without a personal dashboard.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Dashboard"
        verbose_name_plural = "Dashboards"

    def __str__(self):
        if self.user:
            return f"{self.user}'s Dashboard"
        return f"{self.name} (shared)"


class SavedWidget(models.Model):
    """
    A reusable, named, fully-configured widget: a report plus a chosen chart, a
    serialized filter querystring (date range + fixed FK ids), and display flags.
    Built once via the dashboard widget builder and droppable onto any dashboard.
    """

    name = models.CharField(max_length=200, help_text="Shown as the widget title.")
    report_url_name = models.CharField(
        max_length=255,
        help_text="Django URL name of the ReportView (e.g. 'myapp:sales_report').",
    )
    chart_id = models.CharField(
        max_length=50,
        default="0",
        blank=True,
        help_text="Id of the chart from the report's chart_settings to display.",
    )
    display_chart = models.BooleanField(default=True)
    display_table = models.BooleanField(default=False)
    column_span = models.PositiveSmallIntegerField(
        default=12,
        help_text="Width of the widget on the dashboard, in Bootstrap's 12-column grid "
        "(12=full row, 6=half, 4=third, 3=quarter). Lets widgets sit side by side.",
    )
    extra_params = models.TextField(
        blank=True,
        default="",
        help_text="Serialized filter querystring replayed against the report "
        "(e.g. 'start_date=...&end_date=...&product_id=3&product_id=7').",
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="slick_saved_widgets",
        help_text="Owner of this widget; leave empty to share it with everyone.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Saved Widget"
        verbose_name_plural = "Saved Widgets"
        ordering = ["name"]

    def __str__(self):
        return self.name


class DashboardWidget(models.Model):
    """A placement of a SavedWidget on a Dashboard, at a given vertical order."""

    dashboard = models.ForeignKey(Dashboard, on_delete=models.CASCADE, related_name="widgets")
    saved_widget = models.ForeignKey(
        SavedWidget,
        on_delete=models.PROTECT,
        related_name="placements",
        help_text="The reusable widget shown here.",
    )
    order = models.IntegerField(default=0)

    class Meta:
        verbose_name = "Dashboard Widget"
        verbose_name_plural = "Dashboard Widgets"
        ordering = ["order"]

    def __str__(self):
        return f"{self.saved_widget} on {self.dashboard}"

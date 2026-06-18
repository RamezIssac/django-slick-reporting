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


class DashboardWidget(models.Model):
    dashboard = models.ForeignKey(Dashboard, on_delete=models.CASCADE, related_name="widgets")
    report_url_name = models.CharField(
        max_length=255,
        help_text="Django URL name of the ReportView (e.g. 'myapp:sales_report').",
    )
    title = models.CharField(max_length=200, blank=True, help_text="Overrides the report's own title.")
    # GridStack position (12-column grid)
    gs_x = models.IntegerField(default=0)
    gs_y = models.IntegerField(default=0)
    gs_w = models.IntegerField(default=6)
    gs_h = models.IntegerField(default=4)
    # Display options forwarded to {% get_widget %}
    display_chart = models.BooleanField(default=True)
    display_table = models.BooleanField(default=False)
    chart_id = models.IntegerField(default=0)

    class Meta:
        verbose_name = "Dashboard Widget"
        verbose_name_plural = "Dashboard Widgets"
        ordering = ["gs_y", "gs_x"]

    def __str__(self):
        return f"{self.report_url_name} on {self.dashboard}"

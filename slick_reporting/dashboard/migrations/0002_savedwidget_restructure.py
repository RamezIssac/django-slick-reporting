import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Introduce reusable SavedWidget and turn DashboardWidget into a thin placement
    (saved_widget + order). The dashboard feature is unreleased, so this drops and
    recreates DashboardWidget rather than migrating data; consumers reseed.
    """

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("slick_reporting_dashboard", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="SavedWidget",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(help_text="Shown as the widget title.", max_length=200)),
                (
                    "report_url_name",
                    models.CharField(
                        help_text="Django URL name of the ReportView (e.g. 'myapp:sales_report').",
                        max_length=255,
                    ),
                ),
                (
                    "chart_id",
                    models.CharField(
                        blank=True,
                        default="0",
                        help_text="Id of the chart from the report's chart_settings to display.",
                        max_length=50,
                    ),
                ),
                ("display_chart", models.BooleanField(default=True)),
                ("display_table", models.BooleanField(default=False)),
                (
                    "extra_params",
                    models.TextField(
                        blank=True,
                        default="",
                        help_text="Serialized filter querystring replayed against the report "
                        "(e.g. 'start_date=...&end_date=...&product_id=3&product_id=7').",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "owner",
                    models.ForeignKey(
                        blank=True,
                        help_text="Owner of this widget; leave empty to share it with everyone.",
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="slick_saved_widgets",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Saved Widget",
                "verbose_name_plural": "Saved Widgets",
                "ordering": ["name"],
            },
        ),
        migrations.DeleteModel(name="DashboardWidget"),
        migrations.CreateModel(
            name="DashboardWidget",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("order", models.IntegerField(default=0)),
                (
                    "dashboard",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="widgets",
                        to="slick_reporting_dashboard.dashboard",
                    ),
                ),
                (
                    "saved_widget",
                    models.ForeignKey(
                        help_text="The reusable widget shown here.",
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="placements",
                        to="slick_reporting_dashboard.savedwidget",
                    ),
                ),
            ],
            options={
                "verbose_name": "Dashboard Widget",
                "verbose_name_plural": "Dashboard Widgets",
                "ordering": ["order"],
            },
        ),
    ]

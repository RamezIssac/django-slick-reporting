import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Dashboard",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=200)),
                (
                    "is_default",
                    models.BooleanField(
                        default=False,
                        help_text="Mark as the shared fallback for users without a personal dashboard.",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.OneToOneField(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="slick_dashboard",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Dashboard",
                "verbose_name_plural": "Dashboards",
            },
        ),
        migrations.CreateModel(
            name="DashboardWidget",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "report_url_name",
                    models.CharField(
                        help_text="Django URL name of the ReportView (e.g. 'myapp:sales_report').",
                        max_length=255,
                    ),
                ),
                (
                    "title",
                    models.CharField(
                        blank=True, help_text="Overrides the report's own title.", max_length=200
                    ),
                ),
                ("gs_x", models.IntegerField(default=0)),
                ("gs_y", models.IntegerField(default=0)),
                ("gs_w", models.IntegerField(default=6)),
                ("gs_h", models.IntegerField(default=4)),
                ("display_chart", models.BooleanField(default=True)),
                ("display_table", models.BooleanField(default=False)),
                ("chart_id", models.IntegerField(default=0)),
                (
                    "dashboard",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="widgets",
                        to="slick_reporting_dashboard.dashboard",
                    ),
                ),
            ],
            options={
                "verbose_name": "Dashboard Widget",
                "verbose_name_plural": "Dashboard Widgets",
                "ordering": ["gs_y", "gs_x"],
            },
        ),
    ]

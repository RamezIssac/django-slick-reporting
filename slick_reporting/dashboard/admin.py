from django.contrib import admin

from .models import Dashboard, DashboardWidget


class DashboardWidgetInline(admin.TabularInline):
    model = DashboardWidget
    extra = 1
    fields = ["report_url_name", "title", "gs_x", "gs_y", "gs_w", "gs_h", "display_chart", "display_table"]


@admin.register(Dashboard)
class DashboardAdmin(admin.ModelAdmin):
    list_display = ["name", "user", "is_default", "updated_at"]
    list_filter = ["is_default"]
    search_fields = ["name", "user__username"]
    inlines = [DashboardWidgetInline]

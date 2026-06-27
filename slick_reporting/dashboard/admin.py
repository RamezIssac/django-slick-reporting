from django.contrib import admin

from .models import Dashboard, DashboardWidget, SavedWidget


class DashboardWidgetInline(admin.TabularInline):
    model = DashboardWidget
    extra = 1
    fields = ["saved_widget", "order"]
    autocomplete_fields = ["saved_widget"]


@admin.register(Dashboard)
class DashboardAdmin(admin.ModelAdmin):
    list_display = ["name", "user", "is_default", "updated_at"]
    list_filter = ["is_default"]
    search_fields = ["name", "user__username"]
    inlines = [DashboardWidgetInline]


@admin.register(SavedWidget)
class SavedWidgetAdmin(admin.ModelAdmin):
    list_display = ["name", "report_url_name", "chart_id", "owner", "updated_at"]
    list_filter = ["display_chart", "display_table"]
    search_fields = ["name", "report_url_name"]

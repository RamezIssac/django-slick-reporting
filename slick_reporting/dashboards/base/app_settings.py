from django.conf import settings
from django.urls import get_callable

ERP_FRAMEWORK_SETTINGS = {
    "site_name": "ERP Framework System",
    "site_header": "ERP Framework System",
    "index_title": "Dashboard Home",
    "index_template": "admin/index.html",
    "login_template": "admin/login.html",
    "logout_template": "admin/logout.html",
    "app_index_template": "admin/app_index.html",
    # a function to control be dbfield on all instances, Saves you time to subclass if
    # only you need to add a help text or something
    "admin_default_formfield_for_dbfield": (
        "slick_reporting.dashboards.base.helpers.default_formfield_for_dbfield"
    ),
    "admin_site_class": "slick_reporting.dashboards.base.admin.ERPFrameworkAdminSiteBase",
    "admin_site_namespace": "erp_framework",
    "enable_delete_all": False,
    "admin_site_access_permission": "slick_reporting.dashboards.base.helpers.admin_site_access_permission",
    "report_access_function": "slick_reporting.dashboards.base.helpers.report_access_function",
    "admin_base_site_template": "admin/base.html",
    "report_base_template": "erp_framework/base_site.html",
    "reports_list_view_class": "",  # todo
    "reports_root_view_class": "",  # todo
    "sites": {},
}

USER_FRAMEWORK_SETTINGS = getattr(settings, "ERP_FRAMEWORK_SETTINGS", {})

ERP_FRAMEWORK_SETTINGS.update(USER_FRAMEWORK_SETTINGS)

"""
UnDocumented
"""

RA_REPORT_LIST_MAP = getattr(settings, "RA_REPORT_LIST_MAP", {})

ERP_FRAMEWORK_THEME = getattr(settings, "ERP_FRAMEWORK_THEME", "admin")

# correct
ERP_ADMIN_SITE_TITLE = ERP_FRAMEWORK_SETTINGS.get("site_name", "ERP Framework System")

ERP_ADMIN_SITE_HEADER = ERP_FRAMEWORK_SETTINGS.get("site_name", "ERP Framework Header")

ERP_ADMIN_INDEX_TITLE = ERP_FRAMEWORK_SETTINGS.get("index_title", "")

ERP_ADMIN_INDEX_TEMPLATE = ERP_FRAMEWORK_SETTINGS.get("index_template", "")

ERP_ADMIN_DEFAULT_FORMFIELD_FOR_DBFIELD_FUNC = ERP_FRAMEWORK_SETTINGS.get(
    "admin_default_formfield_for_dbfield", ""
)

ERP_ADMIN_DEFAULT_FORMFIELD_FOR_DBFIELD_FUNC = get_callable(
    ERP_ADMIN_DEFAULT_FORMFIELD_FOR_DBFIELD_FUNC
)

ERP_FRAMEWORK_ADMIN_SITE_CLASS = ERP_FRAMEWORK_SETTINGS.get(
    "admin_site_class",
    "slick_reporting.dashboards.base.admin.ERPFrameworkAdminSiteBase",
)

ERP_FRAMEWORK_SITE_NAME = ERP_FRAMEWORK_SETTINGS.get(
    "admin_site_namespace", "erp_framework"
)

ERP_FRAMEWORK_LOGIN_TEMPLATE = ERP_FRAMEWORK_SETTINGS.get(
    "login_template", "admin/login.html"
)

ERP_FRAMEWORK_APP_INDEX_TEMPLATE = ERP_FRAMEWORK_SETTINGS.get(
    "app_index_template", "admin/app_index.html"
)

ERP_FRAMEWORK_LOGGED_OUT_TEMPLATE = ERP_FRAMEWORK_SETTINGS.get(
    "logout_template", "admin/logout.html"
)

ERP_FRAMEWORK_ENABLE_ADMIN_DELETE_ALL = ERP_FRAMEWORK_SETTINGS.get(
    "enable_delete_all", False
)


admin_site_access_permission = get_callable(
    ERP_FRAMEWORK_SETTINGS.get(
        "admin_site_access_permission",
        "erp_framework.base.helpers.admin_site_access_permission",
    )
)

report_access_function = get_callable(
    ERP_FRAMEWORK_SETTINGS.get(
        "report_access_function", "erp_framework.base.helpers.report_access_function"
    )
)

report_base_template = ERP_FRAMEWORK_SETTINGS.get(
    "report_base_template", "erp_framework/base_site.html"
)

admin_base_site_template = ERP_FRAMEWORK_SETTINGS.get(
    "admin_base_site_template", "erp_framework/base_site.html"
)


def get_admin_base_template(site=None):
    admin_base_site_template = ERP_FRAMEWORK_SETTINGS.get(
        "admin_base_site_template", "erp_framework/base_site.html"
    )

    if site:
        admin_base_site_template = (
            ERP_FRAMEWORK_SETTINGS["sites"]
            .get(site, {})
            .get("admin_base_site_template", admin_base_site_template)
        )
    return admin_base_site_template


def get_template(name, site=None):
    template = ERP_FRAMEWORK_SETTINGS.get(name, "")
    if site:
        template = ERP_FRAMEWORK_SETTINGS["sites"].get(site, {}).get(name, template)
    return template

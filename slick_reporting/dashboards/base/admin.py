from __future__ import unicode_literals

import logging
from typing import Any

from django.apps import apps
from django.contrib.admin import AdminSite
from django.http import JsonResponse
from django.shortcuts import render
from django.template.response import TemplateResponse
from django.urls import re_path as url, include
from django.utils.translation import gettext_lazy as _

from .helpers import get_each_context
from . import app_settings

logger = logging.getLogger(__name__)

print("Loaded")


class ERPFrameworkAdminSiteBase(AdminSite):
    site_title = app_settings.ERP_ADMIN_SITE_TITLE
    site_header = app_settings.ERP_ADMIN_SITE_HEADER
    index_title = app_settings.ERP_ADMIN_INDEX_TITLE

    # index_template = app_settings.ERP_ADMIN_INDEX_TEMPLATE
    # app_index_template = app_settings.ERP_FRAMEWORK_APP_INDEX_TEMPLATE
    # login_template = app_settings.ERP_FRAMEWORK_LOGIN_TEMPLATE
    # logout_template = app_settings.ERP_FRAMEWORK_LOGGED_OUT_TEMPLATE

    admin_base_site_template = None

    def __getattribute__(self, name: str) -> Any:
        output = super().__getattribute__(name)
        if (
            name
            in [
                "index_template",
                "login_template",
                "logout_template",
                "app_index_template",
            ]
            and output is None
        ):
            return app_settings.get_template(name, self.name)
        return output

    def has_permission(self, request):
        return app_settings.admin_site_access_permission(request)

    def get_urls(self):
        urls = super(ERPFrameworkAdminSiteBase, self).get_urls()
        help_center = [url(r"^i18n/", include("django.conf.urls.i18n"))]

        settings_update = [
            url(r"^manifest/$", self.manifest_view, name="manifest"),
            url(r"^sw.js$", self.service_worker_view, name="service-worker"),
        ]

        urlpatterns = [
            # url(
            #     r"^reports/(?P<base_model>[\w-]+)/$",
            #     get_report_list_class,
            #     name="report_list",
            # ),
            url(
                r"^reports/(?P<base_model>[\w-]+)/(?P<report_slug>[\w-]+)/$",
                self.get_report_view,
                name="report",
            ),
        ]

        return help_center + settings_update + urlpatterns + urls

    def get_report_view(self, request, base_model, report_slug):
        request.current_app = self.name
        from slick_reporting.dashboards.registry import report_registry

        klass = report_registry.get(base_model, report_slug, admin_site=self.name)
        return klass.as_view()(request)

    def service_worker_view(self, request):
        return render(
            request,
            f"erp_framework/service-worker.js.html",
            content_type="application/javascript",
        )

    def manifest_view(self, request):
        json = {
            "short_name": "ERP Framework System",
            "name": "ERP Framework System",
            "icons": [
                {
                    "src": "/static/erp_framework/images/ra_systems.png",
                    "type": "image/png",
                    "sizes": "147x147",
                },
                # {
                #     "src": "launcher-icon-2x.png",
                #     "type": "image/png",
                #     "sizes": "96x96"
                # },
                # {
                #     "src": "launcher-icon-4x.png",
                #     "type": "image/png",
                #     "sizes": "192x192"
                # }
            ],
            "start_url": "../?launcher=true",
            "display": "standalone",
            "theme_color": "#000066",
            "background_color": "#fff",
        }
        return JsonResponse(json, status=200)

    def app_index(self, request, app_label, extra_context=None):
        app_name = apps.get_app_config(app_label).verbose_name
        context = self.each_context(request)
        context.update(
            dict(
                title=_("%(app)s administration") % {"app": app_name},
                # current_app_list=[app_dict],
                # current_app_list=[current_app_list],
                app_label=app_label,
                app_name=app_name,
            )
        )
        context.update(extra_context or {})
        request.current_app = self.name

        return TemplateResponse(
            request,
            self.app_index_template
            or ["admin/%s/app_index.html" % app_label, "admin/app_index.html"],
            context,
        )

    def index(self, request, extra_context=None):
        app_list = self.get_app_list(request)
        context = {
            **self.each_context(request),
            "title": app_settings.ERP_ADMIN_INDEX_TITLE,
            "subtitle": None,
            "app_list": app_list,
            **(extra_context or {}),
        }

        request.current_app = self.name

        return TemplateResponse(
            request, self.index_template or "admin/index.html", context
        )

    def each_context(self, request):
        context = super(ERPFrameworkAdminSiteBase, self).each_context(request)
        context[
            "admin_base_site_template"
        ] = self.admin_base_site_template or app_settings.get_admin_base_template(
            self.name
        )
        context.update(get_each_context(request, self))
        return context

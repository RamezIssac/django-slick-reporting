from django.utils.functional import LazyObject
from django.utils.module_loading import import_string
from .base import app_settings


class DefaultERPSite(LazyObject):
    name = app_settings.ERP_FRAMEWORK_SITE_NAME
    def _setup(self):
        AdminSiteClass = import_string(app_settings.ERP_FRAMEWORK_ADMIN_SITE_CLASS)
        self._wrapped = AdminSiteClass(name=self.name)

    def __repr__(self):
        return repr(self._wrapped)


erp_admin_site = DefaultERPSite()

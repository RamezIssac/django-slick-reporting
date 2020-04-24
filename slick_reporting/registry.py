from __future__ import unicode_literals

from django.contrib.admin.sites import AlreadyRegistered, NotRegistered


class ReportFieldRegistry(object):
    def __init__(self):
        super(ReportFieldRegistry, self).__init__()
        self._registry = {}  # holds

    def register(self, report_field):
        if report_field.name in self._registry:
            raise AlreadyRegistered('This field is already registered')
        self._registry[report_field.name] = report_field
        return report_field

    def unregister(self, report_field):
        if report_field.name not in self._registry:
            raise NotRegistered(report_field)
        del self._registry[report_field.name]

    def get_field_by_name(self, name):
        if name in self._registry:
            return self._registry[name]
        else:
            raise NotRegistered(name)

    def get_all_report_fields_names(self):
        return list(self._registry.keys())


field_registry = ReportFieldRegistry()



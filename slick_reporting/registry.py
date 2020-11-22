from __future__ import unicode_literals

from django.contrib.admin.sites import AlreadyRegistered, NotRegistered


class ReportFieldRegistry(object):
    def __init__(self):
        super(ReportFieldRegistry, self).__init__()
        self._registry = {}  # holds

    def register(self, report_field, override=False):
        """
        Register a report_field into the registry,
        :param report_field:
        :param override: if True, a report_field will get replaced if found, else it would throw an AlreadyRegistered
        :return: report_field passed
        """
        if report_field.name in self._registry and not override:
            raise AlreadyRegistered(f'The field name {report_field.name} is used before and `override` is False')

        self._registry[report_field.name] = report_field
        return report_field

    def unregister(self, report_field):
        """
        To unregister a Report Field
        :param report_field: a Report field class or a ReportField Name
        :return: None
        """
        name = report_field if type(report_field) is str else report_field.name
        if name not in self._registry:
            raise NotRegistered(report_field)
        del self._registry[name]

    def get_field_by_name(self, name):
        if name in self._registry:
            return self._registry[name]
        else:
            raise KeyError(
                f'{name} is not found in the report field registry. Options are {",".join(self.get_all_report_fields_names())}')

    def get_all_report_fields_names(self):
        return list(self._registry.keys())


field_registry = ReportFieldRegistry()

from __future__ import unicode_literals

from django.contrib.admin.sites import AlreadyRegistered, NotRegistered
from django.core.exceptions import ImproperlyConfigured


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


class ReportRegistry(object):
    def __init__(self):
        super(ReportRegistry, self).__init__()
        self._registry = {}  # holds
        self._slugs_registry = []
        self._store = {}
        self._base_models = []

    def register(self, report_class):
        """
        Register report class
        :param report_class:
        :return:
        """
        if not report_class.hidden:

            try:
                namespace = report_class.base_model._meta.model_name
            except AttributeError:
                raise ImproperlyConfigured("Can not access base_model, is it set on class %s?" % report_class)
            try:
                if not report_class.report_title:
                    raise AttributeError
            except AttributeError:
                raise ImproperlyConfigured('Report %s is missing a `report_title`' % report_class)
            # try:
            #     assert type(report_class.form_settings) is dict
            # except (AttributeError, AssertionError):
            #     raise ImproperlyConfigured(
            #         'Report %s is missing a `form_settings` or form_settings is not a dict' % report_class)
            if not report_class.get_report_model():
                raise ImproperlyConfigured(
                    'Report %s is missing a `report_model`' % report_class)
            if report_class.must_exist_filter and not report_class.header_report:
                raise ImproperlyConfigured('%s: Must specify a view class or function in `header_report` '
                                           'if `must_exist_filter` is set' % report_class)

            self._register_report(report_class, namespace)

    def _register_report(self, report, namespace):
        """
        Actual registry function, recursive
        :param report:
        :param namespace:
        :return:
        """
        namespace_existing = namespace in self._registry
        full_name = '%s_%s' % (namespace, report.get_report_slug())
        if namespace_existing:
            if report in self._registry[namespace]:
                raise AlreadyRegistered('This report class is already registered %s' % report)

            if full_name in self._slugs_registry:
                raise AlreadyRegistered('report slug `%s` is already registered for `%s`' %
                                        (report.get_report_slug(), namespace))

            self._registry[namespace].append(report)
        else:
            self._registry[namespace] = [report]
            if report.base_model not in self._base_models:
                self._base_models.append(report.base_model)
        self._slugs_registry.append(full_name)
        self._store[full_name] = report

    def unregister(self, report_class, w_other_namespaces=True):
        self._unregister(report_class, report_class.namespace)
        if w_other_namespaces:
            other_namespaces = report_class.other_namespaces or []
            for e in other_namespaces:
                self._unregister(report_class, e)

    def unregister_namespace(self, namespace):
        reports = self._registry.pop(namespace, [])
        for r in reports:
            slug_id = '%s_%s' % (namespace, r.get_reprot_slug())
            self._store.pop(slug_id)
            self._slugs_registry.remove(slug_id)
        return reports

    def _unregister(self, report_class, namespace):
        if type(self._registry[namespace]) is list:
            if report_class not in self._registry[namespace]:
                raise NotRegistered('This report is not registered')
            self._registry[namespace].remove(report_class)
            slug_id = '%s_%s' % (report_class.namespace, report_class.get_report_slug())
            self._slugs_registry.remove(slug_id)
            self._base_models.append(report_class.base_model)

    def get_report_classes_by_namespace(self, namespace):
        if namespace in self._registry:
            return self._registry[namespace]
        return []
        # else:
        #     raise NotRegistered(namespace)

    def get_all_reports(self):
        reports = []
        for namespace in self._registry:
            reports += list(self._registry[namespace])
        return reports

    def get(self, namespace, report_slug):
        slug_id = '%s_%s' % (namespace, report_slug)
        try:
            return self._store[slug_id.lower()]
        except KeyError:
            raise NotRegistered(
                "Report '%s' base model '%s' not found, Did you register it? If yes, then maybe it's has different base model ?" % (
                    report_slug, namespace))

    def get_base_models(self):
        return self._base_models


report_registry = ReportRegistry()

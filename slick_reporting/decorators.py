from __future__ import unicode_literals


def report_field_register(report_field, *args, **kwargs):
    """
    Registers the given model(s) classes and wrapped ModelAdmin class with
    admin site:

    @register(Author)
    class AuthorAdmin(admin.ModelAdmin):
        pass

    A kwarg of `site` can be passed as the admin site, otherwise the default
    admin site will be used.
    """
    from .fields import BaseReportField
    from .registry import field_registry

    def _model_admin_wrapper(admin_class):
        if not issubclass(admin_class, BaseReportField):
            raise ValueError('Wrapped class must subclass BaseReportField.')

        field_registry.register(report_field)

    _model_admin_wrapper(report_field)
    return report_field


def register_report_view(report_class=None, condition=None):
    from .registry import report_registry

    if report_class:
        report_registry.register(report_class)
        return report_class

    def wrapper(report_class):
        if callable(condition):
            if not condition():
                return report_class
        report_registry.register(report_class)
        return report_class

    return wrapper

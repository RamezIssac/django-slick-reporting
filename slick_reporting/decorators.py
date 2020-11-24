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
    from .fields import SlickReportField
    from .registry import field_registry

    def _model_admin_wrapper(admin_class):
        if not issubclass(admin_class, SlickReportField):
            raise ValueError('Wrapped class must subclass SlickReportField.')

        field_registry.register(report_field)

    _model_admin_wrapper(report_field)
    return report_field

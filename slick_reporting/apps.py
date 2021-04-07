from django import apps



class ReportAppConfig(apps.AppConfig):
    verbose_name = 'Slick Reporting'
    name = 'slick_reporting'

    def ready(self):
        super().ready()

        from . import fields

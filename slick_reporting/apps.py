from django import apps



class ReportAppConfig(apps.AppConfig):
    label = 'Slick Reporting'
    name = 'slick_reporting'

    def ready(self):
        super().ready()

        from . import fields

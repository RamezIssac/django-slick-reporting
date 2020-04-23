from django import apps



class ReportAppConfig(apps.AppConfig):
    label = 'Slick Reports'
    name = 'reporting'

    def ready(self):
        super().ready()

        from . import fields

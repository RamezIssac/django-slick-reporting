from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import models

from django.utils.translation import gettext_lazy as _

User = get_user_model()


class Report(models.Model):
    code = models.CharField(
        max_length=255, editable=False, primary_key=True, verbose_name=_("Code")
    )
    deleted = models.BooleanField(default=False, verbose_name=_("deleted"))

    users = models.ManyToManyField(
        User, through="UserReportPermission", verbose_name=_("Users")
    )
    groups = models.ManyToManyField(
        Group,
        through="GroupReportPermission",
        verbose_name=_("Groups"),
    )

    def __str__(self):
        from .registry import report_registry

        report_klass = report_registry._store[self.code]
        return report_klass.get_report_title()


class ReportPermissionMixin(models.Model):
    view = models.BooleanField(default=True, verbose_name=_("View"))
    print = models.BooleanField(default=True, verbose_name=_("Print"))
    export = models.BooleanField(default=True, verbose_name=_("Export"))

    deleted = models.BooleanField(default=False, verbose_name=_("deleted"))
    report = models.ForeignKey(
        Report, on_delete=models.CASCADE, verbose_name=_("Report")
    )

    class Meta:
        abstract = True


class UserReportPermission(ReportPermissionMixin, models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_("User"))

    class Meta:
        verbose_name = _("User Report Permission")
        verbose_name_plural = _("User Report Permissions")


class GroupReportPermission(ReportPermissionMixin, models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE, verbose_name=_("Group"))

    class Meta:
        verbose_name = _("Group Report Permission")
        verbose_name_plural = _("Group Report Permissions")

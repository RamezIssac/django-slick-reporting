
import logging

from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse, HttpResponseRedirect
from django.template.defaultfilters import capfirst
from django.urls import reverse
from slick_reporting.forms import (
    report_form_factory,
)
from slick_reporting.views import ReportViewBase, SlickReportingListViewMixin

from .base import app_settings
# from .reporting.printing import HTMLPrintingClass


class DashboardMixin:
    # printing_class = HTMLPrintingClass # todo bring back

    # this report will not be visible on the menu or accessed on its own
    hidden = False

    admin_site_name = "erp_framework"
    template_name = "erp_framework/report.html"

    def get_base_template(self):
        """
        Returns the base template for the report.
        :return: a string representing the base template path (e.g. 'admin/base.html')
        """
        current_app = getattr(self.request, "current_app", "")
        return app_settings.get_admin_base_template(current_app)

    def get_context_data(self, **kwargs):
        from .sites import erp_admin_site

        context = super().get_context_data(**kwargs)
        extra_context = erp_admin_site.each_context(self.request)
        context.update(extra_context)
        context["is_report"] = True

        context["base_model"] = self.base_model
        context["report_slug"] = self.get_report_slug()
        context["CURRENT_REPORT"] = self.__class__
        context["report"] = self

        context["admin_base_site_template"] = self.get_base_template()

        return context


    @classmethod
    def get_base_model_name(cls):
        """
        A convenience method to get the base model name
        :return:
        """
        # try:
        #     return cls.base_model._meta.model_name
        # except:
        app_label = cls.__module__.split(".")[0]
        return app_label

    @classmethod
    def get_report_code(cls):
        return f"{cls.get_base_model_name()}.{cls.get_report_slug()}"

    @classmethod
    def get_url(cls, request=None):
        try:
            current_app = request.current_app
        except:
            current_app = cls.admin_site_name

        return reverse(
            "admin:report",
            args=(cls.get_base_model_name(), cls.get_report_slug()),
            current_app=current_app,
        )

    def get_test_func(self):
        """
        Override this method to use a different test_func method.
        """
        return self.test_func

    @classmethod
    def test_func(cls, request=None, permission="view"):
        return app_settings.report_access_function(request, permission, cls)

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            if self.request.META.get("HTTP_X_REQUESTED_WITH") == "XMLHttpRequest":
                return JsonResponse({}, status=403)
            else:
                raise PermissionDenied
        current_app = getattr(self.request, "current_app", self.admin_site_name)
        return HttpResponseRedirect(
            reverse("erp_framework:login", current_app=current_app)
        )

    @staticmethod
    def form_filter_func(fkeys_dict):
        output = {}
        for k, v in fkeys_dict.items():
            if k not in ["owner_id", "polymorphic_ctype_id", "lastmod_user_id"]:
                output[k] = v
        return output

    #
    # @classmethod
    # def get_form_class(cls):
    #     """
    #     As Report Model might be swapped, form_class cant be accurately generated on model load,
    #     hence this function.
    #     :return: form_class
    #     """
    #     return cls.form_class or report_form_factory(
    #         cls.get_report_model(),
    #         crosstab_model=cls.crosstab_field,
    #         display_compute_remainder=cls.crosstab_compute_remainder,
    #         excluded_fields=cls.excluded_fields,
    #         fkeys_filter_func=cls.form_filter_func,
    #         initial=cls.get_form_initial(),
    #         show_time_series_selector=cls.time_series_selector,
    #         time_series_selector_choices=cls.time_series_selector_choices,
    #         time_series_selector_default=cls.time_series_selector_default,
    #         time_series_selector_allow_empty=cls.time_series_selector_allow_empty,
    #     )

    def dispatch(self, request, *args, **kwargs):
        user_test_result = self.get_test_func()(request)
        if not user_test_result:
            return self.handle_no_permission()

        return super().dispatch(request, *args, **kwargs)

    @classmethod
    def get_report_title(cls):
        """
        :return: The report name
        """
        # name = 'name'
        name = ""
        if cls.report_title:
            name = cls.report_title

        return capfirst(name)

    # def order_results(self, data):
    #     """
    #     order the results based on GET parameter or default_order_by
    #     :param data: List of Dict to be ordered
    #     :return: Ordered data
    #     """
    #     if self.order_by:
    #         desc = self.order_by.startswith("-")
    #         order_field = self.order_by.lstrip("-")
    #         data = dictsort(data, order_field, desc)
    #     else:
    #         order_field, asc = OrderByForm(self.request.GET).get_order_by(
    #             self.default_order_by
    #         )
    #         if order_field:
    #             data = dictsort(data, order_field, asc)
    #     return data

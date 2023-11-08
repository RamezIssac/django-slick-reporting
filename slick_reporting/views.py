import csv
import datetime
import warnings

import simplejson as json
from django import forms
from django.conf import settings
from django.contrib.auth.mixins import UserPassesTestMixin
from django.db.models import Q
from django.forms import modelform_factory
from django.http import HttpResponse, StreamingHttpResponse, JsonResponse
from django.utils.encoding import force_str
from django.utils.functional import Promise
from django.views.generic import FormView

from .app_settings import SLICK_REPORTING_SETTINGS, get_access_function
from .forms import (
    report_form_factory,
    get_crispy_helper,
    default_formfield_callback,
    OrderByForm,
)
from .generator import (
    ReportGenerator,
    ListViewReportGenerator,
    ReportGeneratorAPI,
    Chart,  # noqa # needed for easier importing in other apps
)


def dictsort(value, arg, desc=False):
    """
    Takes a list of dicts, returns that list sorted by the property given in
    the argument.
    """
    return sorted(value, key=lambda x: x[arg], reverse=desc)


class ExportToCSV(object):
    def get_filename(self):
        return self.report_title

    def get_response(self):
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = "attachment; filename={filename}.csv".format(filename=self.get_filename())

        writer = csv.writer(response)
        for rows in self.get_rows():
            writer.writerow(rows)

        return response

    def get_rows(self):
        columns, verbose_names = self.get_columns()
        yield verbose_names
        for line in self.report_data["data"]:
            yield [line[col_name] for col_name in columns]

    def get_columns(self, extra_context=None):
        return list(zip(*[(x["name"], x["verbose_name"]) for x in self.report_data["columns"]]))

    def __init__(self, request, report_data, report_title, **kwargs):
        self.request = request
        self.report_data = report_data
        self.report_title = report_title
        self.kwargs = kwargs


class ExportToStreamingCSV(ExportToCSV):
    def get_response(self):
        # Copied form Djagno Docs
        class Echo:
            def write(self, value):
                return value

        pseudo_buffer = Echo()
        writer = csv.writer(pseudo_buffer)
        return StreamingHttpResponse(
            (writer.writerow(row) for row in self.get_rows()),
            content_type="text/csv",
            headers={
                "Content-Disposition": 'attachment; filename="{filename}.csv"'.format(filename=self.get_filename())
            },
        )


class ReportViewBase(ReportGeneratorAPI, UserPassesTestMixin, FormView):
    report_slug = None

    report_title = ""

    report_title_context_key = "report_title"

    report_generator_class = ReportGenerator

    base_model = None

    chart_settings = None

    excluded_fields = None

    time_series_selector = False
    time_series_selector_choices = None
    time_series_selector_default = None
    time_series_selector_allow_empty = False

    csv_export_class = ExportToStreamingCSV

    with_type = False
    doc_type_field_name = "doc_type"
    doc_type_plus_list = None
    doc_type_minus_list = None
    auto_load = True
    chart_engine = ""

    default_order_by = ""

    template_name = "slick_reporting/report.html"

    export_actions = None

    def test_func(self):
        access_function = get_access_function()
        return access_function(self)

    @classmethod
    def get_report_title(cls):
        """
        :return: The report name
        """
        name = cls.__name__
        if cls.report_title:
            name = cls.report_title
        return name

    def order_results(self, data):
        """
        order the results based on GET parameter or default_order_by
        :param data: List of Dict to be ordered
        :return: Ordered data
        """
        order_field, asc = OrderByForm(self.request.GET).get_order_by(self.default_order_by)
        if order_field:
            data = dictsort(data, order_field, asc)
        return data

    def get_doc_types_q_filters(self):
        if self.doc_type_plus_list or self.doc_type_minus_list:
            return (
                [Q(**{f"{self.doc_type_field_name}__in": self.doc_type_plus_list})] if self.doc_type_plus_list else []
            ), (
                [Q(**{f"{self.doc_type_field_name}__in": self.doc_type_minus_list})] if self.doc_type_minus_list else []
            )

        return [], []

    def get_export_actions(self):
        """
        Hook to get the export options
        :return: list of export options
        """
        actions = ["export_csv"] if self.csv_export_class else []

        if self.export_actions:
            actions = actions + self.export_actions

        export_actions = []

        for action in actions:
            func = getattr(self, action, None)
            parameter = action.replace("export_", "")

            export_actions.append(
                {
                    "name": action,
                    "title": getattr(func, "title", action.replace("_", " ").title()),
                    "icon": getattr(func, "icon", ""),
                    "css_class": getattr(func, "css_class", ""),
                    "parameter": parameter,
                }
            )
        return export_actions

    def get(self, request, *args, **kwargs):
        form_class = self.get_form_class()
        self.form = self.get_form(form_class)
        report_data = {}
        if self.form.is_valid():
            if self.request.GET or self.request.POST or request.headers.get("x-requested-with") == "XMLHttpRequest":
                # only display results if it's requested,
                # considered requested if it's ajax request, or a populated GET or POST.
                report_data = self.get_report_results()

                export_option = request.GET.get("_export", "")
                if export_option:
                    try:
                        return getattr(self, f"export_{export_option}")(report_data)
                    except AttributeError:
                        pass

                if request.headers.get("x-requested-with") == "XMLHttpRequest":
                    return self.ajax_render_to_response(report_data)

            return self.render_to_response(self.get_context_data(report_data=report_data))
        else:
            return self.form_invalid(self.form)

        # return self.render_to_response(self.get_context_data())

    def export_csv(self, report_data):
        return self.csv_export_class(self.request, report_data, self.report_title).get_response()

    export_csv.title = SLICK_REPORTING_SETTINGS["MESSAGES"]["export_to_csv"]
    export_csv.css_class = "btn btn-primary"
    export_csv.icon = ""

    @classmethod
    def get_report_model(cls):
        if cls.queryset is not None:
            return cls.queryset.model
        return cls.report_model

    def ajax_render_to_response(self, report_data):
        return HttpResponse(self.serialize_to_json(report_data), content_type="application/json")

    def serialize_to_json(self, response_data):
        """Returns the JSON string for the compiled data object."""

        def date_handler(obj):
            if type(obj) is datetime.datetime:
                return obj.strftime("%Y-%m-%d %H:%M")
            elif hasattr(obj, "isoformat"):
                return obj.isoformat()
            elif isinstance(obj, Promise):
                return force_str(obj)

        indent = None
        if settings.DEBUG:
            indent = 4

        return json.dumps(response_data, indent=indent, use_decimal=True, default=date_handler)

    def get_form_class(self):
        """
        Automatically instantiate a form based on details provided
        :return:
        """
        return self.form_class or report_form_factory(
            self.get_report_model(),
            crosstab_model=self.crosstab_field,
            display_compute_remainder=self.crosstab_compute_remainder,
            excluded_fields=self.excluded_fields,
            fkeys_filter_func=None,
            initial=self.get_initial(),
            show_time_series_selector=self.time_series_selector,
            time_series_selector_choices=self.time_series_selector_choices,
            time_series_selector_default=self.time_series_selector_default,
            time_series_selector_allow_empty=self.time_series_selector_allow_empty,
            add_start_date=self.start_date_field_name or self.date_field,
            add_end_date=self.end_date_field_name or self.date_field,
        )

    def get_form_kwargs(self):
        """
        Returns the keyword arguments for instantiating the form.
        """
        kwargs = {
            "initial": self.get_initial(),
            "prefix": self.get_prefix(),
        }

        if self.request.method in ("POST", "PUT"):
            kwargs.update(
                {
                    "data": self.request.POST,
                    "files": self.request.FILES,
                }
            )
        elif self.request.method in ("GET", "PUT"):
            if self.request.GET or self.request.headers.get("x-requested-with") == "XMLHttpRequest":
                kwargs.update(
                    {
                        "data": self.request.GET,
                    }
                )
        return kwargs

    def get_crosstab_ids(self):
        """
        Hook to get the crosstab ids
        :return:
        """
        return self.form.get_crosstab_ids()

    def get_group_by_custom_querysets(self):
        return self.group_by_custom_querysets

    def get_report_generator(self, queryset=None, for_print=False):
        queryset = queryset or self.get_queryset()
        q_filters, kw_filters = self.form.get_filters()
        crosstab_compute_remainder = False
        if self.crosstab_field:
            self.crosstab_ids = self.get_crosstab_ids()
        try:
            crosstab_compute_remainder = (
                self.form.get_crosstab_compute_remainder()
                if self.request.GET or self.request.POST
                else self.crosstab_compute_remainder
            )
        except NotImplementedError:
            pass

        time_series_pattern = self.time_series_pattern
        if self.time_series_selector:
            time_series_pattern = self.form.get_time_series_pattern()

        doc_type_plus_list, doc_type_minus_list = [], []

        if self.with_type:
            doc_type_plus_list, doc_type_minus_list = self.get_doc_types_q_filters()

        return self.report_generator_class(
            self.get_report_model(),
            start_date=self.form.get_start_date(),
            end_date=self.form.get_end_date(),
            q_filters=q_filters,
            kwargs_filters=kw_filters,
            date_field=self.date_field,
            main_queryset=queryset,
            print_flag=for_print,
            limit_records=self.limit_records,
            swap_sign=self.swap_sign,
            columns=self.columns,
            group_by=self.group_by,
            group_by_custom_querysets=self.get_group_by_custom_querysets(),
            group_by_custom_querysets_column_verbose_name=self.group_by_custom_querysets_column_verbose_name,
            time_series_pattern=time_series_pattern,
            time_series_columns=self.time_series_columns,
            time_series_custom_dates=self.time_series_custom_dates,
            crosstab_field=self.crosstab_field,
            crosstab_ids=self.crosstab_ids,
            crosstab_columns=self.crosstab_columns,
            crosstab_compute_remainder=crosstab_compute_remainder,
            crosstab_ids_custom_filters=self.crosstab_ids_custom_filters,
            format_row_func=self.format_row,
            container_class=self,
            doc_type_plus_list=doc_type_plus_list,
            doc_type_minus_list=doc_type_minus_list,
        )

    def format_row(self, row_obj):
        """
        A hook to format each row . This method gets called on each row in the results. <ust return the object
        :param row_obj: a dict representing a single row in the results
        :return: A dict representing a single row in the results
        """
        return row_obj

    @classmethod
    def get_columns_data(cls, generator):
        """
        Hook to get the columns information to front end
        :param generator: the SlickReportGenerator instance used
        :return:
        """
        return generator.get_columns_data()

    def get_report_results(self, for_print=False):
        """
        Gets the reports Data, and, its meta data used by datatables.net and highcharts
        :return: JsonResponse
        """

        queryset = self.get_queryset()
        report_generator = self.get_report_generator(queryset, for_print)
        data = report_generator.get_report_data()
        data = self.filter_results(data, for_print)
        data = self.order_results(data)

        return report_generator.get_full_response(
            data=data,
            report_slug=self.get_report_slug(),
            chart_settings=self.chart_settings,
            default_chart_title=self.report_title,
            default_chart_engine=self.chart_engine,
        )

    @classmethod
    def get_metadata(cls, generator):
        """
        A hook to send data about the report for front end which can later be used in charting
        :return:
        """
        return generator.get_metadata()

    def get_chart_settings(self, generator=None):
        """
        Ensure the sane settings are passed to the front end.
        """
        return self.report_generator_class.get_chart_settings(
            chart_settings=self.chart_settings or [],
            default_chart_title=self.report_title,
            chart_engine=self.chart_engine,
        )

    @classmethod
    def get_queryset(cls):
        if cls.queryset is None:
            return cls.get_report_model()._default_manager.all()
        return cls.queryset

    def filter_results(self, data, for_print=False):
        """
        Hook to Filter results based on computed data (like eliminate __balance__ = 0, etc)
        return None to remove the row from the results
        :param data: List of objects
        :param for_print: is print request
        :return: filtered data
        """
        return data

    @classmethod
    def get_report_slug(cls):
        return cls.report_slug or cls.__name__.lower()

    def get_initial(self):
        initial = self.initial.copy()
        initial.update(
            {
                "start_date": SLICK_REPORTING_SETTINGS["DEFAULT_START_DATE_TIME"],
                "end_date": SLICK_REPORTING_SETTINGS["DEFAULT_END_DATE_TIME"],
            }
        )
        return initial

    def get_form_crispy_helper(self):
        """
        A hook retuning crispy helper for the form
        :return:
        """
        if hasattr(self, "form"):
            return self.form.get_crispy_helper()
        return None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context[self.report_title_context_key] = self.get_report_title()
        context["crispy_helper"] = self.get_form_crispy_helper()
        context["auto_load"] = self.auto_load
        context["report"] = self

        if not (self.request.POST or self.request.GET):
            context["form"] = self.get_form_class()(**self.get_form_kwargs())
        return context

    def form_invalid(self, form):
        if self.request.META.get("HTTP_X_REQUESTED_WITH") == "XMLHttpRequest":
            return JsonResponse(form.errors, status=400)
        return super().form_invalid(form)


class ReportView(ReportViewBase):
    def __init_subclass__(cls) -> None:
        # date_field = getattr(cls, 'date_field', '')
        # if not date_field:
        #     raise TypeError(f'`date_field` is not set on {cls}')
        # cls.report_generator_class.check_columns([cls.date_field], False, cls.get_report_model())

        # sanity check, raises error if the columns or date fields is not set
        if cls.columns:
            cls.report_generator_class.check_columns(
                cls,
                cls.columns,
                cls.group_by,
                cls.get_report_model(),
                container_class=cls,
                group_by_custom_querysets=cls.group_by_custom_querysets,
            )

        super().__init_subclass__()


class SlickReportingListViewMixin(ReportViewBase):
    report_generator_class = ListViewReportGenerator
    filters = None

    def get_queryset(self):
        qs = self.queryset or self.report_model.objects
        if self.default_order_by:
            qs.order_by(self.default_order_by)
        return qs

    def get_form_filters(self, form):
        if self.form_class:
            return form.get_filters()

        kw_filters = {}

        for name, field in form.base_fields.items():
            if type(field) is forms.ModelMultipleChoiceField:
                value = form.cleaned_data[name]
                if value:
                    kw_filters[f"{name}__in"] = form.cleaned_data[name]
            elif type(field) is forms.BooleanField:
                # boolean field while checked on frontend , and have initial = True, give false value on cleaned_data
                #  Hence this check to see if it was indeed in the GET params,
                value = field.initial
                if self.request.GET:
                    value = form.cleaned_data.get(name, False)
                kw_filters[name] = value

            else:
                value = form.cleaned_data[name]
                if value:
                    kw_filters[name] = form.cleaned_data[name]

        return [], kw_filters

    def get_form_crispy_helper(self):
        return get_crispy_helper(self.filters)

    def get_report_generator(self, queryset=None, for_print=False):
        q_filters, kw_filters = self.get_form_filters(self.form)

        return self.report_generator_class(
            self.get_report_model(),
            # start_date=self.form.get_start_date(),
            # end_date=self.form.get_end_date(),
            q_filters=q_filters,
            kwargs_filters=kw_filters,
            date_field=self.date_field,
            main_queryset=queryset,
            print_flag=for_print,
            limit_records=self.limit_records,
            columns=self.columns,
            format_row_func=self.format_row,
            container_class=self,
        )

    def get_form_class(self):
        if self.form_class:
            return self.form_class

        elif self.filters:
            return modelform_factory(
                model=self.get_report_model(),
                fields=self.filters,
                formfield_callback=default_formfield_callback,
            )
        return forms.Form

    def get_report_results(self, for_print=False):
        """
        Gets the reports Data, and, its meta data used by datatables.net and highcharts
        :return: JsonResponse
        """

        queryset = self.get_queryset()
        report_generator = self.get_report_generator(queryset, for_print)
        data = report_generator.get_report_data()
        data = self.filter_results(data, for_print)

        return report_generator.get_full_response(
            data=data,
            report_slug=self.get_report_slug(),
            chart_settings=self.chart_settings,
            default_chart_title=self.report_title,
        )


class SlickReportingListView(SlickReportingListViewMixin, ReportViewBase):
    def __init_subclass__(cls) -> None:
        warnings.warn(
            "slick_reporting.view.SlickReportingListView is"
            "deprecated in favor of slick_reporting.view.ListReportView",
            Warning,
            stacklevel=2,
        )
        super().__init_subclass__()


class ListReportView(SlickReportingListViewMixin):
    pass


class SlickReportViewBase(ReportViewBase):
    """
    Deprecated in favor of slick_reporting.view.ReportViewBase
    """

    def __init_subclass__(cls) -> None:
        warnings.warn(
            "slick_reporting.view.SlickReportView and slick_reporting.view.SlickReportViewBase are "
            "deprecated in favor of slick_reporting.view.ReportView and slick_reporting.view.BaseReportView",
            Warning,
            stacklevel=2,
        )

        super().__init_subclass__()


class SlickReportView(ReportView):
    def __init_subclass__(cls) -> None:
        warnings.warn(
            "slick_reporting.view.SlickReportView and slick_reporting.view.SlickReportViewBase are "
            "deprecated in favor of slick_reporting.view.ReportView and slick_reporting.view.BaseReportView",
            Warning,
            stacklevel=2,
        )

        # cls.report_generator_class.check_columns(
        #     cls.columns, cls.group_by, cls.get_report_model(), container_class=cls
        # )

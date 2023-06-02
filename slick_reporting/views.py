import datetime
import csv

import simplejson as json
from django import forms
from django.conf import settings
from django.db.models import Q
from django.forms import modelform_factory
from django.http import HttpResponse, StreamingHttpResponse
from django.utils.encoding import force_str
from django.utils.functional import Promise
from django.views.generic import FormView

from .app_settings import (
    SLICK_REPORTING_DEFAULT_END_DATE,
    SLICK_REPORTING_DEFAULT_START_DATE,
    SLICK_REPORTING_DEFAULT_CHARTS_ENGINE,
)
from .forms import (
    report_form_factory,
    get_crispy_helper,
    default_formfield_callback,
)
from .generator import ReportGenerator, ListViewReportGenerator, Chart


class ExportToCSV(object):
    def get_filename(self):
        return self.report_title

    def get_response(self):
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = "attachment; filename={filename}.csv".format(
            filename=self.get_filename()
        )

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
        return list(
            zip(*[(x["name"], x["verbose_name"]) for x in self.report_data["columns"]])
        )

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
                "Content-Disposition": 'attachment; filename="{filename}.csv"'.format(
                    filename=self.get_filename()
                )
            },
        )


class SlickReportViewBase(FormView):
    report_slug = None
    group_by = None
    columns = None

    report_title = ""
    time_series_pattern = ""
    time_series_columns = None

    date_field = None

    swap_sign = False

    report_generator_class = ReportGenerator

    report_model = None

    base_model = None
    limit_records = None

    queryset = None

    chart_settings = None

    crosstab_model = None
    crosstab_field = None

    crosstab_ids = None
    crosstab_columns = None
    crosstab_compute_remainder = True
    excluded_fields = None
    report_title_context_key = "title"

    time_series_selector = False
    time_series_selector_choices = None
    time_series_selector_default = None
    time_series_selector_allow_empty = False

    csv_export_class = ExportToStreamingCSV

    with_type = False
    doc_type_field_name = "doc_type"
    doc_type_plus_list = None
    doc_type_minus_list = None

    """
    A list of chart settings objects instructing front end on how to plot the data.
    
    """

    template_name = "slick_reporting/simple_report.html"

    def get_doc_types_q_filters(self):
        if self.doc_type_plus_list or self.doc_type_minus_list:
            return (
                [Q(**{f"{self.doc_type_field_name}__in": self.doc_type_plus_list})]
                if self.doc_type_plus_list
                else []
            ), (
                [Q(**{f"{self.doc_type_field_name}__in": self.doc_type_minus_list})]
                if self.doc_type_minus_list
                else []
            )

        return [], []

    def get(self, request, *args, **kwargs):
        form_class = self.get_form_class()
        self.form = self.get_form(form_class)
        if self.form.is_valid():
            report_data = self.get_report_results()

            export_option = request.GET.get("_export", "")
            if export_option:
                try:
                    return getattr(self, f"export_{export_option}")(report_data)
                except AttributeError:
                    pass

            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return self.ajax_render_to_response(report_data)

            return self.render_to_response(
                self.get_context_data(report_data=report_data)
            )

        return self.render_to_response(self.get_context_data())

    def export_csv(self, report_data):
        return self.csv_export_class(
            self.request, report_data, self.report_title
        ).get_response()

    @classmethod
    def get_report_model(cls):
        return cls.report_model or cls.queryset.model

    def ajax_render_to_response(self, report_data):
        return HttpResponse(
            self.serialize_to_json(report_data), content_type="application/json"
        )

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

        return json.dumps(
            response_data, indent=indent, use_decimal=True, default=date_handler
        )

    def get_form_class(self):
        """
        Automatically instantiate a form based on details provided
        :return:
        """
        return self.form_class or report_form_factory(
            self.get_report_model(),
            crosstab_model=self.crosstab_model,
            display_compute_remainder=self.crosstab_compute_remainder,
            excluded_fields=self.excluded_fields,
            initial=self.get_form_initial(),
            show_time_series_selector=self.time_series_selector,
            time_series_selector_choices=self.time_series_selector_choices,
            time_series_selector_default=self.time_series_selector_default,
            time_series_selector_allow_empty=self.time_series_selector_allow_empty,
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
            # elif self.request.GET:
            kwargs.update(
                {
                    "data": self.request.GET,
                }
            )
        return kwargs

    def get_report_generator(self, queryset, for_print):
        q_filters, kw_filters = self.form.get_filters()
        if self.crosstab_model:
            self.crosstab_ids = self.form.get_crosstab_ids()

        crosstab_compute_remainder = (
            self.form.get_crosstab_compute_remainder()
            if self.request.GET or self.request.POST
            else self.crosstab_compute_remainder
        )

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
            time_series_pattern=time_series_pattern,
            time_series_columns=self.time_series_columns,
            crosstab_model=self.crosstab_model,
            crosstab_field=self.crosstab_field,
            crosstab_ids=self.crosstab_ids,
            crosstab_columns=self.crosstab_columns,
            crosstab_compute_remainder=crosstab_compute_remainder,
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

        return report_generator.get_full_response(
            data=data,
            report_slug=self.get_report_slug(),
            chart_settings=self.chart_settings,
            default_chart_title=self.report_title,
        )

    @classmethod
    def get_metadata(cls, generator):
        """
        A hook to send data about the report for front end which can later be used in charting
        :return:
        """
        return generator.get_metadata()

    def get_chart_settings(self, generator):
        """
        Ensure the sane settings are passed to the front end.
        """
        return generator.get_chart_settings(
            self.chart_settings or [], self.report_title
        )

    def get_queryset(self):
        return self.queryset or self.report_model.objects

    def filter_results(self, data, for_print=False):
        """
        Hook to Filter results based on computed data (like eliminate __balance__ = 0, etc)
        :param data: List of objects
        :param for_print: is print request
        :return: filtered data
        """
        return data

    @classmethod
    def get_report_slug(cls):
        return cls.report_slug or cls.__name__.lower()

    @staticmethod
    def get_form_initial():
        # todo revise why not actually displaying datetime on screen
        return {
            "start_date": SLICK_REPORTING_DEFAULT_START_DATE,
            "end_date": SLICK_REPORTING_DEFAULT_END_DATE,
        }

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
        context[self.report_title_context_key] = self.report_title
        context["crispy_helper"] = self.get_form_crispy_helper()

        if not (self.request.POST or self.request.GET):
            # initialize empty form with initials if the no data is in the get or the post
            context["form"] = self.get_form_class()()
        return context


class SlickReportView(SlickReportViewBase):
    def __init_subclass__(cls) -> None:
        # date_field = getattr(cls, 'date_field', '')
        # if not date_field:
        #     raise TypeError(f'`date_field` is not set on {cls}')
        # cls.report_generator_class.check_columns([cls.date_field], False, cls.get_report_model())

        # sanity check, raises error if the columns or date fields is not mapped

        cls.report_generator_class.check_columns(
            cls.columns, cls.group_by, cls.get_report_model(), container_class=cls
        )

        super().__init_subclass__()

    @staticmethod
    def check_chart_settings(chart_settings=None):
        # todo check on chart settings
        return


class SlickReportingListView(SlickReportViewBase):
    report_generator_class = ListViewReportGenerator
    filters = None

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

    def get_report_generator(self, queryset, for_print):
        q_filters, kw_filters = self.get_form_filters(self.form)

        return self.report_generator_class(
            self.get_report_model(),
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
                self.get_report_model(),
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

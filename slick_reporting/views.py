import datetime

import simplejson as json
from django.conf import settings
from django.http import HttpResponse
from django.utils.encoding import force_text
from django.utils.functional import Promise
from django.views.generic import FormView

from .form_factory import report_form_factory
from .generator import ReportGenerator


class SampleReportView(FormView):
    group_by = None
    columns = None

    time_series_pattern = ''
    time_series_columns = None

    date_field = 'doc_date'

    swap_sign = False

    report_generator_class = ReportGenerator

    report_model = None

    base_model = None
    limit_records = None

    queryset = None

    template_name = 'slick_reporting/simple_report.html'

    def get(self, request, *args, **kwargs):
        form_class = self.get_form_class()
        self.form = self.get_form(form_class)
        if self.form.is_valid():
            report_data = self.get_report_results()
            if request.is_ajax():
                return self.ajax_render_to_response(report_data)

            return self.render_to_response(self.get_context_data(report_data=report_data))

        return self.render_to_response(self.get_context_data())

    def ajax_render_to_response(self, report_data):
        return HttpResponse(self.serialize_to_json(report_data),
                            content_type="application/json")

    def serialize_to_json(self, response_data):
        """ Returns the JSON string for the compiled data object. """

        def date_handler(obj):
            if type(obj) is datetime.datetime:
                return obj.strftime('%Y-%m-%d %H:%M')
            elif hasattr(obj, 'isoformat'):
                return obj.isoformat()
            elif isinstance(obj, Promise):
                return force_text(obj)

        indent = None
        if settings.DEBUG:
            indent = 4

        return json.dumps(response_data, indent=indent, use_decimal=True, default=date_handler)

    def get_form_class(self):
        """
        Automatically instantiate a form based on details provided
        :return:
        """
        return self.form_class or report_form_factory(self.report_model)

    def get_form_kwargs(self):
        """
        Returns the keyword arguments for instantiating the form.
        """
        kwargs = {
            'initial': self.get_initial(),
            'prefix': self.get_prefix(),
        }

        if self.request.method in ('POST', 'PUT'):
            kwargs.update({
                'data': self.request.POST,
                'files': self.request.FILES,
            })
        elif self.request.method in ('GET', 'PUT'):

            # elif self.request.GET:
            kwargs.update({
                'data': self.request.GET,
                'files': self.request.FILES,
            })
        return kwargs

    def get_report_generator(self, queryset, for_print):
        q_filters, kw_filters = self.form.get_filters()
        return self.report_generator_class(self.report_model,
                                           kwargs_filters=kw_filters,
                                           date_field=self.date_field,
                                           main_queryset=queryset,
                                           print_flag=for_print,
                                           limit_records=self.limit_records, swap_sign=self.swap_sign,
                                           columns=self.columns,
                                           group_by=self.group_by,
                                           time_series_pattern=self.time_series_pattern,
                                           time_series_columns=self.time_series_columns,
                                           )

    def get_columns_data(self, columns):
        """
        Hook to get the columns information to front end
        :param columns:
        :return:
        """
        # columns = report_generator.get_list_display_columns()
        data = []
        for col in columns:
            data.append({
                'name': col['name'],
                'verbose_name': col['verbose_name'],
                'visible': col.get('visible', True),
                'type': col.get('type', 'text')
            })
        return data

    def get_report_results(self, for_print=False):
        """
        Gets the reports Data, and, its meta data used by datatables.net and highcharts
        :return: JsonResponse
        """

        queryset = self.get_queryset()
        report_generator = self.get_report_generator(queryset, for_print)
        data = report_generator.get_report_data()
        data = self.filter_results(data, for_print)
        data = {
            'data': data,
            'columns': self.get_columns_data(report_generator.get_list_display_columns())
        }
        return data

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

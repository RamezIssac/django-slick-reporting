import datetime

import simplejson as json
from django.conf import settings
from django.http import HttpResponse
from django.utils.encoding import force_text
from django.utils.functional import Promise
from django.views.generic import FormView

from .app_settings import SLICK_REPORTING_DEFAULT_END_DATE, SLICK_REPORTING_DEFAULT_START_DATE, \
    SLICK_REPORTING_DEFAULT_CHARTS_ENGINE
from .form_factory import report_form_factory
from .generator import ReportGenerator


class SlickReportViewBase(FormView):
    group_by = None
    columns = None

    report_title = ''
    time_series_pattern = ''
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
    crosstab_ids = None
    crosstab_columns = None
    crosstab_compute_reminder = True
    excluded_fields = None
    """
    A list of chart settings objects instructing front end on how to plot the data.
    
    """

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

    @classmethod
    def get_report_model(cls):
        return cls.report_model or cls.queryset.model

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
        return self.form_class or report_form_factory(self.get_report_model(), crosstab_model=self.crosstab_model,
                                                      display_compute_reminder=self.crosstab_compute_reminder,
                                                      excluded_fields=self.excluded_fields)

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
        if self.crosstab_model:
            self.crosstab_ids = self.form.get_crosstab_ids()

        crosstab_compute_reminder = self.form.get_crosstab_compute_reminder() if self.request.GET or self.request.POST \
            else self.crosstab_compute_reminder

        return self.report_generator_class(self.get_report_model(),
                                           start_date=self.form.cleaned_data['start_date'],
                                           end_date=self.form.cleaned_data['end_date'],
                                           q_filters=q_filters,
                                           kwargs_filters=kw_filters,
                                           date_field=self.date_field,
                                           main_queryset=queryset,
                                           print_flag=for_print,
                                           limit_records=self.limit_records, swap_sign=self.swap_sign,
                                           columns=self.columns,
                                           group_by=self.group_by,
                                           time_series_pattern=self.time_series_pattern,
                                           time_series_columns=self.time_series_columns,

                                           crosstab_model=self.crosstab_model,
                                           crosstab_ids=self.crosstab_ids,
                                           crosstab_columns=self.crosstab_columns,
                                           crosstab_compute_reminder=crosstab_compute_reminder,

                                           format_row_func=self.format_row
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

        return report_generator.get_full_response(data=data, report_slug=self.get_report_slug(),
                                                           chart_settings=self.chart_settings,
                                                           default_chart_title=self.report_title)

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
        return generator.get_chart_settings(self.chart_settings or [], self.report_title)

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
        return cls.__name__.lower()

    def get_initial(self):
        # todo revise why not actually displaying datetime on screen
        return {
            'start_date': SLICK_REPORTING_DEFAULT_START_DATE,
            'end_date': SLICK_REPORTING_DEFAULT_END_DATE
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if not (self.request.POST or self.request.GET):
            # initialize empty form with initials if the no data is in the get or the post
            context['form'] = self.get_form_class()()
        return context


class SlickReportView(SlickReportViewBase):

    def __init_subclass__(cls) -> None:
        date_field = getattr(cls, 'date_field', '')
        if not date_field:
            raise TypeError(f'`date_field` is not set on {cls}')

        # sanity check, raises error if the columns or date fields is not mapped
        cls.report_generator_class.check_columns([cls.date_field], False, cls.get_report_model())
        cls.report_generator_class.check_columns(cls.columns, cls.group_by, cls.get_report_model())

        super().__init_subclass__()

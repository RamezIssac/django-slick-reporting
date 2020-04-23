import copy
import datetime
import hashlib
import logging

import simplejson as json
from django.conf import settings
from django.contrib.auth.mixins import AccessMixin, UserPassesTestMixin
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured, PermissionDenied
from django.http import JsonResponse, HttpResponse, HttpResponseRedirect
# cache = get_cache('default')
from django.template.defaultfilters import capfirst
from django.urls import reverse, reverse_lazy
from django.utils.encoding import force_text
from django.utils.functional import Promise
from django.utils.translation import get_language_bidi, ugettext
from django.views.generic import FormView, TemplateView

from ra.base import app_settings, registry
from ra.base.app_settings import RA_ADMIN_SITE_NAME
from ra.base.helpers import dictsort
from ra.reporting.form_factory import report_form_factory
from ra.reporting.forms import OrderByForm
from ra.reporting.printing import regroup_data, HTMLPrintingClass, ExportToCSV
from .generator import ReportGenerator
from .meta_data import ReportMetaData

logger = logging.getLogger('ra.reporting')


class SimpleReportView(FormView):
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

    template_name = 'reporting/simple_report.html'

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
        return self.report_generator_class(self.report_model,
                                           kwargs_filters=self.form.get_fk_filters(),
                                           date_field=self.date_field,
                                           main_queryset=queryset,
                                           base_model=self.base_model, print_flag=for_print,
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


class RaMultiplePermissionsRequiredMixin(AccessMixin):
    """
    View mixin which allows you to specify two types of permission
    requirements. The `permissions` attribute must be a dict which
    specifies two keys, `all` and `any`. You can use either one on
    its own or combine them. The value of each key is required to be a
    list or tuple of permissions. The standard Django permissions
    style is not strictly enforced. If you have created your own
    permissions in a different format, they should still work.

    By specifying the `all` key, the user must have all of
    the permissions in the passed in list.

    By specifying The `any` key , the user must have ONE of the set
    permissions in the list.

    Class Settings
        `permissions` - This is required to be a dict with one or both
            keys of `all` and/or `any` containing a list or tuple of
            permissions.
        `login_url` - the login url of site
        `redirect_field_name` - defaults to "next"
        `raise_exception` - defaults to False - raise 403 if set to True

    Example Usage
        class SomeView(MultiplePermissionsRequiredMixin, ListView):
            ...
            #required
            permissions = {
                "all": ("blog.add_post", "blog.change_post"),
                "any": ("blog.delete_post", "user.change_user")
            }

            #optional
            login_url = "/signup/"
            redirect_field_name = "hollaback"
            raise_exception = True
    """
    permissions = None  # Default required perms to none
    permission_or_test = False
    login_url = reverse_lazy('%s:login' % RA_ADMIN_SITE_NAME)
    _bypass = False

    def get_or_test(self):
        return False

    def get_permissions(self):
        return self.permissions

    def return_access_denied(self):
        return HttpResponseRedirect(reverse('access_denied'))

    def dispatch(self, request, *args, **kwargs):
        from django.contrib.auth.views import redirect_to_login

        if request.user.is_anonymous:
            return redirect_to_login(request.get_full_path(),
                                     self.get_login_url(),
                                     self.get_redirect_field_name())

        self._check_permissions_attr()

        perms_all = self.get_permissions().get('all') or None
        perms_any = self.get_permissions().get('any') or None

        self._check_permissions_keys_set(perms_all, perms_any)
        self._check_perms_keys("all", perms_all)
        self._check_perms_keys("any", perms_any)

        # If perms_all, check that user has all permissions in the list/tuple
        access_denied = HttpResponseRedirect(reverse('%s:access-denied' % RA_ADMIN_SITE_NAME))
        if perms_all:

            if not request.user.has_perms(perms_all):
                if not (self.permission_or_test and self.get_or_test()):
                    if self.raise_exception:
                        raise PermissionDenied
                    return access_denied

        # If perms_any, check that user has at least one in the list/tuple
        if perms_any:
            has_one_perm = False
            for perm in perms_any:
                if request.user.has_perm(perm):
                    has_one_perm = True
                    break

            if not has_one_perm:
                if self.raise_exception:
                    raise PermissionDenied
                return access_denied

        return super(RaMultiplePermissionsRequiredMixin, self).dispatch(
            request, *args, **kwargs)

    def _check_permissions_attr(self):
        """
        Check permissions attribute is set and that it is a dict.
        """
        permissions = self.get_permissions()
        if permissions is None or not isinstance(permissions, dict):
            raise ImproperlyConfigured(
                "'PermissionsRequiredMixin' requires "
                "'permissions' attribute to be set to a dict.")

    def _check_permissions_keys_set(self, perms_all=None, perms_any=None):
        """
        Check to make sure the keys `any` or `all` are not both blank.
        If both are blank either an empty dict came in or the wrong keys
        came in. Both are invalid and should raise an exception.
        """
        if perms_all is None and perms_any is None and not self._bypass:
            raise ImproperlyConfigured(
                "'PermissionsRequiredMixin' requires"
                "'permissions' attribute to be set to a dict and the 'any' "
                "or 'all' key to be set.")

    def _check_perms_keys(self, key=None, perms=None):
        """
        If the permissions list/tuple passed in is set, check to make
        sure that it is of the type list or tuple.
        """
        if perms and not isinstance(perms, (list, tuple)):
            raise ImproperlyConfigured(
                "'MultiplePermissionsRequiredMixin' "
                "requires permissions dict '%s' value to be a list "
                "or tuple." % key)


class ReportListBase(RaMultiplePermissionsRequiredMixin, TemplateView):
    """
    Base class to create a report list page
    """

    def get_meta_data(self):
        """
        Gets Meta data used for Page title , breadcrumbs links etc.
        Make sure that opts is a model._meta or s sufficient dictionary
        :return: tuple (verbose_name, verbose_name_plural, page_title, model_meta)
        """
        raise NotImplemented

    def get_permissions(self):
        """
        Override of RAAccessControl.get_permissions
        :return: a dictionary with 'any' and/ or 'all' permission. required
        """
        raise NotImplemented

    def get_reports_map(self):
        """
        Hook to get reports. By default it uses the helper `get_reports_map` to get
         the reports based on the base_model, However you can override and return your list of reports

        :return: a dictionary with two values `slugs` and `reports`
        slugs: map to a list of report slugs
        reports: map to a list of ReportView classes
        """
        raise NotImplemented


class ReportList(ReportListBase):
    template_name = f'{app_settings.RA_THEME}/report_list.html'
    _bypass = True

    def get_order_list(self):
        from ra.admin.admin import ra_admin_site

        model_admin = ra_admin_site.get_admin_by_model_name(self.kwargs['base_model'])
        if model_admin:
            try:
                return model_admin['admin'].typed_reports_order_list or []
            except AttributeError:
                # The admin class does not have an order list for teh reports
                pass
        return []

    def get_permissions(self):
        return {}

    def get_reports_map(self):
        from ra.admin.admin import get_reports_map
        from ra.base.registry import get_ra_model_by_name
        model = get_ra_model_by_name(self.kwargs['base_model'])
        try:
            model_name = model.get_class_name().lower()
        except:
            model_name = model._meta.model_name
        val = get_reports_map(model_name, self.request.user, self.request, self.get_order_list())
        return val

    def get_meta_data(self):
        model = registry.get_ra_model_by_name(self.kwargs['base_model'])
        verbose_name = model._meta.verbose_name
        verbose_name_plural = model._meta.verbose_name_plural
        is_bidi = get_language_bidi()
        if is_bidi:
            page_title = '%s %s' % (ugettext('reports'), model._meta.verbose_name_plural)
        else:
            page_title = '%s %s' % (model._meta.verbose_name_plural, ugettext('reports'))
        opts = model._meta
        return verbose_name, verbose_name_plural, page_title, opts

    def get_context_data(self, **kwargs):
        from ra.admin.admin import ra_admin_site
        from ra.admin.helpers import get_each_context

        context = super(ReportList, self).get_context_data(**kwargs)

        context['reports'] = self.get_reports_map()

        v, vp, page_title, opts = self.get_meta_data()
        context['verbose_name'] = v
        context['verbose_name_plural'] = vp
        context['page_title'] = page_title
        context['title'] = page_title

        context['opts'] = opts

        context['RA_ADMIN_SITE_NAME'] = app_settings.RA_ADMIN_SITE_NAME
        context['has_detached_sidebar'] = True
        context['RA_ADMIN_SITE_NAME'] = app_settings.RA_ADMIN_SITE_NAME

        extra_context = get_each_context(self.request, ra_admin_site)
        context.update(extra_context)
        return context
class ReportView(UserPassesTestMixin, SimpleReportView):
    """
    The Base class for reports .
    It handles the report ajax request, load the report form which provides the needed filers,
    Load the report generator class , csv_export_class and the printing class.

    """
    # the class responsible for exporting to CSV
    csv_export_class = ExportToCSV

    # class responsible for generating the report, applying the filter and computing
    report_generator_class = ReportGenerator

    # class responsible for supplying meta data for front end
    report_meta_data_class = ReportMetaData

    # class responsible for customizing the output for print
    printing_class = HTMLPrintingClass

    # required. the model which holds the data
    report_model = None

    # required , the model which the report is about
    base_model = None

    # the report form, A subclass of ReportForm is to expected
    form_class = None

    # control the settings of report
    form_settings = None

    # control the chart settings, passed to front end as is.
    chart_settings = None

    other_namespaces = None

    report_slug = ''
    page_title = None
    report_title = None

    # default order by for the results.
    # ordering can also be controlled on run time by passing order_by='field_name'
    # For DESC order supply order_by='-field_name'
    default_order_by = None

    # this report will not be visible on the menu or accessed on its own
    hidden = False

    # will swap the sign on the report, useful when reporting on object which main side is credit

    # Control the header report function
    must_exist_filter = None
    header_report = None

    # to limit records not to exceed certain number, useful for very large reports
    limit_records = False

    perform_regroup_when_print = False  # Handling printing header & sub data

    # size for printing , useful on very large data
    print_buffer = 10000

    # control the caching
    cache = True
    cache_duration = 300

    # V2

    @classmethod
    def get_report_slug(cls):
        return cls.report_slug or cls.__name__.lower()

    @classmethod
    def get_base_model_name(cls):
        """
        A convenience method to get the base model name
        :return:
        """
        return cls.base_model._meta.model_name

    @classmethod
    def get_url(cls):
        url = reverse(f'{RA_ADMIN_SITE_NAME}:report_list', args=(cls.get_base_model_name(),))
        url += '%s/' % cls.get_report_slug()
        return url

    def test_func(self):
        app_label = self.base_model._meta.app_label
        codename = f'view_{self.get_report_slug()}'
        return self.request.user.has_perm(f'{app_label}.{codename}')

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            if self.request.is_ajax():
                return JsonResponse({}, status=403)
            else:
                return HttpResponseRedirect(reverse('ra_admin:access-denied'))
        # else:
        return HttpResponseRedirect(reverse('ra_admin:login'))

    @classmethod
    def get_absolute_url(cls):
        href = reverse('admin:report_list', args=(cls.get_base_model_name(),))
        href = '%s#tab_%s' % (href, cls.get_report_slug())
        return href

    @classmethod
    def get_report_model(cls):
        """
        Problem: During tests, override settings is used, making the report model always returning the model
        'first to be found' not the potentially swapped one ,raising an error. so , it is advised to use this method instead
            of declaring the report model on the module level.
        :return: the Model to use
        """
        return cls.report_model

    @classmethod
    def get_form_class(cls):
        """
        As Report Model might be swapped, form_class cant be accurately generated on model load,
        hence this function.
        :return: form_class
        """
        return cls.form_class or report_form_factory(cls.get_report_model())

    def dispatch(self, request, *args, **kwargs):
        report_slug = kwargs.get('report_slug', False)
        if report_slug:
            self.report_slug = report_slug
        val = super(ReportView, self).dispatch(request, *args, **kwargs)

        return val

    def get_printing_class(self, ):
        return self.printing_class

    def is_print_request(self):
        return self.request.GET.get('print', False)

    @classmethod
    def initialize_form(cls):
        #todo remove me
        form_class = cls.get_form_class()
        if hasattr(form_class, 'initial_settings'):
            settings = form_class.initial_settings.copy()
        else:
            settings = {}
        settings.update(cls.form_settings or {})
        settings['from_doc_date'] = cls.get_default_from_date()
        settings['to_doc_date'] = cls.get_default_to_date()
        # return form_class(support_doc_type=True, **{'form_settings': settings})
        return form_class()

    def get_form_settings(self):
        # todo : Review
        form_class = self.get_form_class()
        if hasattr(form_class, 'initial_settings'):
            settings = form_class.initial_settings.copy()
        else:
            settings = {}
        settings.update(self.form_settings or {})
        return settings

    @classmethod
    def get_all_print_settings(cls):
        # todo review
        return {}

    def return_header_report_or_none(self):
        """
        Check if we need to return o
        :return:
        """

        if self.must_exist_filter:
            filter_exist = self.request.GET.get(self.must_exist_filter, '')
            # if the filter exists but the the user choose several entities
            filter_exist = filter_exist.find(',') == -1 and bool(filter_exist)
            if not filter_exist:
                return self.header_report.as_view()(self.request, original_report_slug=self.get_report_slug(),
                                                    as_header=True)
        return None

    def get_print_response(self, response, header_report, must_exist_filter):
        """
        Invoke the printing class and return the printing response
        :return:  Response
        """

        if must_exist_filter and header_report:
            if self.perform_regroup_when_print:
                response['sub_data'] = regroup_data(response['data'], header_report, must_exist_filter)
                response['header_group'] = header_report
            else:
                _available_buffer = self.print_buffer
                must_exist_filter = must_exist_filter.replace('__slug', '_id')
                response['sub_data'] = {}
                json_data = json.loads(header_report.content)
                response['header_data'] = []
                response['header_group'] = must_exist_filter

                for line in json_data['data']:
                    pivot_id = line[must_exist_filter]
                    new_request = copy.copy(self.request)
                    get_data = new_request.GET.copy()
                    get_data[must_exist_filter] = pivot_id
                    get_data['print_recursive'] = True
                    get_data['get_group'] = False
                    new_request.GET = get_data
                    pivot_report = self.__class__.as_view()(new_request)
                    data_check = pivot_report.get('data', [])
                    if not len(data_check) > 0:
                        _available_buffer -= len(pivot_report.get('data', []))
                        response['sub_data'][pivot_id] = pivot_report
                        response['header_data'].append(line)
                        if _available_buffer < 0:
                            break

        return self.get_printing_class()(self.request, self.form_settings or {}, response, header_report,
                                         must_exist_filter, self).get_response()

    def cache_and_return(self, results):
        status, key = self.get_cache_status_and_key(self.request)
        if key:
            cache.set(key, results, self.cache_duration)
        return results

    def cache_view(self):
        return self.cache and app_settings.RA_CACHE_REPORTS

    def get_cache_status_and_key(self, request):
        if not self.cache or not app_settings.RA_CACHE_REPORTS:
            return False, None

        url = request.get_full_path()
        url_parts = url.split('&')
        url_parts = [x for x in url_parts if not x.startswith('csrf')]
        no_cache_request = 'no-cache' in url_parts
        if no_cache_request:
            url_parts.remove('no-cache')
        url = ''.join(url_parts)
        m = hashlib.md5()
        if app_settings.RA_CACHE_REPORTS_PER_USER:
            m.update(f'{request.user.pk}'.encode('utf-8'))
        m.update(url.encode('utf-8'))
        cache_key = m.hexdigest()
        return not no_cache_request, cache_key

    def get_export_response(self, response, header_report, must_exist_filter):
        return self.csv_export_class(self.request, self.form_settings or {}, response, header_report,
                                     must_exist_filter, self).get_response()

    def get(self, request, *args, **kwargs):

        cache_status, cache_key = self.get_cache_status_and_key(request)
        if cache_status and cache_key:
            cache_val = cache.get(cache_key)
            if cache_val:
                return cache_val

        # self.parse()

        form_class = self.get_form_class()
        self.form = self.get_form(form_class)
        enable_print = self.is_print_request()
        export_csv = request.GET.get('csv', False)

        if request.is_ajax() or enable_print or export_csv or (request.GET.get('ajax') == 'true' and settings.DEBUG):
            if self.form.is_valid():
                must_exist_filter = self.must_exist_filter or ''
                must_exist_filter = must_exist_filter.replace('_id', '__slug')
                header_report = self.return_header_report_or_none()
                # Case of a report that needs a specific filter to run,
                # in case it doesn't exist, we return the `header_report`
                if header_report and not enable_print:
                    return self.cache_and_return(header_report)
                as_header = self.kwargs.get('as_header', False)

                response = self.get_report_results(enable_print or export_csv)

                if (export_csv or enable_print) and not as_header:
                    response = self.prepare_results_for_printing(response)
                    if export_csv:
                        return self.get_export_response(response, header_report, must_exist_filter)

                    return self.get_print_response(response, header_report, must_exist_filter)
                return self.cache_and_return(HttpResponse(self.serialize_to_json(response),
                                                          content_type="application/json"))
            else:
                return self.form_invalid(self.form)
        else:
            # Accessing the report page directly is not allowed
            return HttpResponseRedirect(
                reverse(f'{RA_ADMIN_SITE_NAME}:report_list', args=(self.get_base_model_name(),)))

    @classmethod
    def get_report_title(cls):
        """
        :return: The report title
        """
        # title = 'TITLE'
        title = ''
        if cls.report_title:
            title = cls.report_title
        elif cls.page_title:
            title = cls.page_title
        return capfirst(title)


    def get_report_results(self, for_print=False):
        """
        Gets the reports Data, and, its meta data used by datatables.net and highcharts
        :return: JsonResponse
        """

        queryset = self.get_queryset()
        report_generator = self.get_report_generator(queryset, for_print)
        report_meta_data = {}  # self.report_meta_data_class(self.form, self.form_settings, self.chart_settings,
        # self.request.GET, self.get_report_title())
        data = report_generator.get_report_data()
        data = self.order_results(data)
        data = self.filter_results(data, for_print)
        # import pdb;
        # pdb.set_trace()
        data = {
            'report_slug': self.kwargs.get('original_report_slug', self.get_report_slug()),
            'form_settings': self.form_settings,
            'data': data,
            'columns': self.get_columns_data(report_generator.get_list_display_columns())
            # 'verbose_data': report_meta_data.get_verbose_data(),
        }
        # meta_data = report_meta_data.get_meta_data()
        # data.update(meta_data)
        data['chart_settings'] = self.get_chart_settings()
        return data

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


    def prepare_results_for_printing(self, results):
        """
        Hook before sending the results for teh printing generator
        :param results: dict containing the data, columns, column_names, verbose_data and other keys
        :return: adjusted results
        """
        return results


    def form_invalid(self, form):
        return JsonResponse(form.errors, status=400)

    def get_chart_settings(self):
        return self.chart_settings or []

    @classmethod
    def get_default_from_date(cls, **kwargs):
        return app_settings.RA_DEFAULT_FROM_DATETIME

    @classmethod
    def get_default_to_date(cls, **kwargs):
        return app_settings.RA_DEFAULT_TO_DATETIME

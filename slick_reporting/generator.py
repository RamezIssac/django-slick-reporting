from __future__ import unicode_literals

import datetime
import logging
from inspect import isclass

from django.core.exceptions import ImproperlyConfigured, FieldDoesNotExist
from django.db.models import Q, ForeignKey

from .app_settings import SLICK_REPORTING_DEFAULT_CHARTS_ENGINE
from .fields import SlickReportField
from .helpers import get_field_from_query_text
from .registry import field_registry

logger = logging.getLogger(__name__)


class ReportGenerator(object):
    """
    The main class responsible generating the report and managing the flow
    """

    field_registry_class = field_registry
    """You can have a custom computation field locator! It only needs a `get_field_by_name(string)` 
    and returns a ReportField`"""

    report_model = None
    """The main model where data is """

    """
    Class to generate a Json Object containing report data.
    """
    date_field = None
    """Main date field to use whenever date filter is needed"""

    print_flag = None
    list_display_links = []

    group_by = None
    """The field to use for grouping, if not set then the report is expected to be a sub version of the report model"""

    columns = None
    """A list of column names.
    Columns names can be 
    
    1. A Computation Field
    
    2. If group_by is set, then any field on teh group_by model
    
    3. If group_by is not set, then any field name on the report_model / queryset
     
    4. A callable on the generator
      
    5. Special __time_series__, and __crosstab__ 
       Those can be use to control the position of the time series inside the columns, defaults it's appended at the end
       
       Example:
       columns = ['product_id', '__time_series__', 'col_b']
       Same is true with __crosstab__ 
     """

    time_series_pattern = ''
    """
    If set the Report will compute a time series.
    
    Possible options are: daily, weekly, semimonthly, monthly, quarterly, semiannually, annually and custom.
    
    if `custom` is set, you'd need to override  `get_custom_time_series_dates`
    """
    time_series_columns = None
    """
    a list of Calculation Field names which will be included in the series calculation.
     Example: ['__total__', '__total_quantity__'] with compute those 2 fields for all the series
     
    """

    time_series_custom_dates = None
    """
    Used with `time_series_pattern` set to 'custom'
    It's a list of tuple, each tuple represent start date & end date
    Example: [ (start_date_1, end_date_1), (start_date_2, end_date_2), ....]
    """

    crosstab_model = None
    """
    If set, a cross tab over this model selected ids (via `crosstab_ids`)  
    """
    crosstab_columns = None
    """The computation fields which will be computed for each crosstab-ed ids """

    crosstab_ids = None
    """A list is the ids to create a crosstab report on"""

    crosstab_compute_reminder = True
    """Include an an extra crosstab_columns for the outer group ( ie: all expects those `crosstab_ids`) """

    show_empty_records = True
    """
    If group_by is set, this option control if the report result will include all objects regardless of appearing in the report_model/qs.
    If set False, only those objects which are found in the report_model/qs
    Example: Say you group by client
    show_empty_records = True will get the computation fields for all clients in the Client model (including those who 
    didnt make a transaction.
    
    show_empty_records = False will get the computation fields for all clients in the Client model (including those who 
    didnt make a transaction.
     
    """

    limit_records = None
    """Serves are a main limit to  the returned data of teh report_model.
    Can be beneficial if the results may be huge.
    """
    swap_sign = False

    def __init__(self, report_model=None, main_queryset=None, start_date=None, end_date=None, date_field=None,
                 q_filters=None, kwargs_filters=None,
                 group_by=None, columns=None,
                 time_series_pattern=None, time_series_columns=None, time_series_custom_dates=None,
                 crosstab_model=None, crosstab_columns=None, crosstab_ids=None, crosstab_compute_reminder=None,
                 swap_sign=False, show_empty_records=None,
                 print_flag=False,
                 doc_type_plus_list=None, doc_type_minus_list=None, limit_records=False, format_row_func=None):
        """

        :param report_model: Main model containing the data
        :param main_queryset: Default to report_model.objects
        :param start_date:
        :param end_date:
        :param date_field:
        :param q_filters:
        :param kwargs_filters:
        :param group_by:
        :param columns:
        :param time_series_pattern:
        :param time_series_columns:
        :param crosstab_model:
        :param crosstab_columns:
        :param crosstab_ids:
        :param crosstab_compute_reminder:
        :param swap_sign:
        :param show_empty_records:
        :param base_model:
        :param print_flag:
        :param doc_type_plus_list:
        :param doc_type_minus_list:
        :param limit_records:
        """
        from .app_settings import SLICK_REPORTING_DEFAULT_START_DATE, SLICK_REPORTING_DEFAULT_END_DATE

        super(ReportGenerator, self).__init__()

        self.report_model = self.report_model or report_model
        if not self.report_model:
            raise ImproperlyConfigured('report_model must be set on a class level or via init')

        self.start_date = start_date or datetime.datetime.combine(SLICK_REPORTING_DEFAULT_START_DATE.date(),
                                                                  SLICK_REPORTING_DEFAULT_START_DATE.time())

        self.end_date = end_date or datetime.datetime.combine(SLICK_REPORTING_DEFAULT_END_DATE.date(),
                                                              SLICK_REPORTING_DEFAULT_END_DATE.time())
        self.date_field = self.date_field or date_field
        if not self.date_field:
            raise ImproperlyConfigured('date_field must be set on a class level or via init')

        self.q_filters = q_filters or []
        self.kwargs_filters = kwargs_filters or {}

        self.crosstab_model = self.crosstab_model or crosstab_model
        self.crosstab_columns = crosstab_columns or self.crosstab_columns or []
        self.crosstab_ids = self.crosstab_ids or crosstab_ids or []
        self.crosstab_compute_reminder = self.crosstab_compute_reminder if crosstab_compute_reminder is None else crosstab_compute_reminder

        self.format_row = format_row_func or self._default_format_row

        main_queryset = main_queryset or self.report_model.objects
        main_queryset = main_queryset.order_by()

        self.columns = columns or self.columns or []
        self.group_by = group_by or self.group_by

        self.time_series_pattern = self.time_series_pattern or time_series_pattern
        self.time_series_columns = self.time_series_columns or time_series_columns
        self.time_series_custom_dates = self.time_series_custom_dates or time_series_custom_dates

        self._prepared_results = {}
        self.report_fields_classes = {}

        self._report_fields_dependencies = {'time_series': {}, 'crosstab': {}, 'normal': {}}
        self.existing_dependencies = {'series': [], 'matrix': [], 'normal': []}

        self.print_flag = print_flag or self.print_flag

        # todo validate columns is not empty (if no time series / cross tab)

        if self.group_by:
            group_by_split = self.group_by.split('__')
            search_field = group_by_split[0]
            try:
                self.group_by_field = [x for x in self.report_model._meta.get_fields() if x.name == search_field][0]

            except IndexError:
                raise ImproperlyConfigured(
                    f'Can not find group_by field:{self.group_by} in report_model {self.report_model} ')
            self.focus_field_as_key = self.group_by_field
            if '__' not in self.group_by:
                self.group_by_field_attname = self.group_by_field.attname
            else:
                self.group_by_field_attname = self.group_by

        else:
            self.focus_field_as_key = None
            self.group_by_field_attname = None

        # doc_types = form.get_doc_type_plus_minus_lists()
        doc_types = [], []
        self.doc_type_plus_list = list(doc_type_plus_list) if doc_type_plus_list else doc_types[0]
        self.doc_type_minus_list = list(doc_type_minus_list) if doc_type_minus_list else doc_types[1]

        self.swap_sign = self.swap_sign or swap_sign
        self.limit_records = self.limit_records or limit_records

        # passed to the report fields
        # self.date_field = date_field or self.date_field

        # in case of a group by, do we show a grouped by model data regardless of their appearance in the results
        # a client who didnt make a transaction during the date period.
        self.show_empty_records = False  # show_empty_records if show_empty_records else self.show_empty_records
        # Looks like this options is harder then what i thought as it interfere with the usual filtering of the report

        # Preparing actions
        self._parse()
        if self.group_by:

            if self.show_empty_records:
                pass
                # group_by_filter = self.kwargs_filters.get(self.group_by, '')
                # qs = self.group_by_field.related_model.objects
                # if group_by_filter:
                #     lookup = 'pk__in' if isinstance(group_by_filter, Iterable) else 'pk'
                #     qs = qs.filter(**{lookup: group_by_filter})
                # self.main_queryset = qs.values()

            else:
                self.main_queryset = self._apply_queryset_options(main_queryset)
                if type(self.group_by_field) is ForeignKey and '__' not in self.group_by:
                    ids = self.main_queryset.values_list(self.group_by_field_attname).distinct()
                    # uses the same logic that is in Django's query.py when fields is empty in values() call
                    concrete_fields = [f.name for f in self.group_by_field.related_model._meta.concrete_fields]
                    # add database columns that are not already in concrete_fields
                    final_fields = concrete_fields + list(set(self.get_database_columns()) - set(concrete_fields))
                    self.main_queryset = self.group_by_field.related_model.objects.filter(pk__in=ids).values(*final_fields)
                else:
                    self.main_queryset = self.main_queryset.distinct().values(self.group_by_field_attname)
        else:
            if self.time_series_pattern:
                self.main_queryset = [{}]
            else:
                self.main_queryset = self._apply_queryset_options(main_queryset, self.get_database_columns())
        self._prepare_report_dependencies()

    def _apply_queryset_options(self, query, fields=None):
        """
        Apply the filters to the main queryset which will computed results be mapped to
        :param query:
        :param fields:
        :return:
        """

        filters = {
            f'{self.date_field}__gt': self.start_date,
            f'{self.date_field}__lte': self.end_date,
        }
        filters.update(self.kwargs_filters)

        if filters:
            query = query.filter(**filters)
        if fields:
            return query.values(*fields)
        return query.values()

    def _construct_crosstab_filter(self, col_data):
        """
        In charge of adding the needed crosstab filter, specific to the case of is_reminder or not
        :param col_data:
        :return:
        """
        if col_data['is_reminder']:
            filters = [~Q(**{f"{col_data['model']}_id__in": self.crosstab_ids})]
        else:
            filters = [Q(**{f"{col_data['model']}_id": col_data['id']})]
        return filters

    def _prepare_report_dependencies(self):
        from .fields import SlickReportField
        all_columns = (
            ('normal', self._parsed_columns),
            ('time_series', self._time_series_parsed_columns),
            ('crosstab', self._crosstab_parsed_columns),
        )
        for window, window_cols in all_columns:
            for col_data in window_cols:
                klass = col_data['ref']

                if isclass(klass) and issubclass(klass, SlickReportField):
                    dependencies_names = klass.get_full_dependency_list()

                    # check if any of this dependencies is on the report
                    fields_on_report = [x for x in window_cols if x['ref'] in dependencies_names]
                    for field in fields_on_report:
                        self._report_fields_dependencies[window][field['name']] = col_data['name']
            for col_data in window_cols:
                klass = col_data['ref']
                name = col_data['name']

                # if column has a dependency then skip it
                if not (isclass(klass) and issubclass(klass, SlickReportField)):
                    continue
                if self._report_fields_dependencies[window].get(name, False):
                    continue

                report_class = klass(self.doc_type_plus_list, self.doc_type_minus_list,
                                     group_by=self.group_by,
                                     report_model=self.report_model, date_field=self.date_field)

                q_filters = None
                date_filter = {
                    f'{self.date_field}__gt': col_data.get('start_date', self.start_date),
                    f'{self.date_field}__lte': col_data.get('end_date', self.end_date),
                }
                date_filter.update(self.kwargs_filters)
                if window == 'crosstab':
                    q_filters = self._construct_crosstab_filter(col_data)

                report_class.init_preparation(q_filters, date_filter)
                self.report_fields_classes[name] = report_class

    def _get_record_data(self, obj, columns):
        """
        the function is run for every obj in the main_queryset
        :param obj: current row
        :param: columns： The columns we iterate on
        :return: a dict object containing all needed data
        """

        # todo , if columns are empty for whatever reason this will throw an error
        display_link = self.list_display_links or columns[0]
        data = {}
        group_by_val = None
        if self.group_by:
            column_data = obj.get(self.group_by_field_attname, obj.get('id'))
            group_by_val = str(column_data)

        for window, window_cols in columns:
            for col_data in window_cols:

                name = col_data['name']

                if (col_data.get('source', '') == 'magic_field' and self.group_by) or (
                        self.time_series_pattern and not self.group_by):
                    source = self._report_fields_dependencies[window].get(name, False)
                    if source:
                        computation_class = self.report_fields_classes[source]
                        value = computation_class.get_dependency_value(group_by_val,
                                                                       col_data['ref'].name)
                    else:
                        try:
                            computation_class = self.report_fields_classes[name]
                        except KeyError:
                            continue
                        value = computation_class.resolve(group_by_val, data)
                    if self.swap_sign: value = -value
                    data[name] = value

                else:
                    data[name] = obj.get(name, '')
                # if self.group_by and name in display_link:
                #     data[name] = make_linkable_field(self.group_by_field.related_model, group_by_val, data[name])
        return data

    def get_report_data(self):
        main_queryset = self.main_queryset[:self.limit_records] if self.limit_records else self.main_queryset

        all_columns = (
            ('normal', self._parsed_columns),
            ('time_series', self._time_series_parsed_columns),
            ('crosstab', self._crosstab_parsed_columns),
        )

        get_record_data = self._get_record_data
        format_row = self.format_row
        data = [format_row(get_record_data(obj, all_columns)) for obj in main_queryset]
        return data

    def _default_format_row(self, row_obj):
        """
        Hook where you can format row values like properly format a date
        :param row_obj:
        :return:
        """
        return row_obj

    @classmethod
    def check_columns(cls, columns, group_by, report_model, ):
        """
        Check and parse the columns, throw errors in case an item in the columns cant not identified
        :param columns: List of columns
        :param group_by: group by field if any
        :param report_model: the report model
        :return: List of dict, each dict contains relevant data to the respective field in `columns`
        """
        group_by_model = None
        if group_by:
            group_by_field = [x for x in report_model._meta.get_fields() if x.name == group_by.split('__')[0]][0]
            if group_by_field.is_relation:
                group_by_model = group_by_field.related_model
            else:
                group_by_model = report_model

        parsed_columns = []
        for col in columns:
            if col in ['__time_series__', '__crosstab__']:
                #     These are placeholder not real computation field
                continue

            magic_field_class = None
            attr = None

            if type(col) is str:
                attr = getattr(cls, col, None)
            elif issubclass(col, SlickReportField):
                magic_field_class = col

            try:
                magic_field_class = magic_field_class or field_registry.get_field_by_name(col)
            except KeyError:
                magic_field_class = None

            if attr:
                # todo Add testing here
                col_data = {'name': col,
                            'verbose_name': getattr(attr, 'verbose_name', col),
                            # 'type': 'method',
                            'ref': attr,
                            'type': 'text'
                            }
            elif magic_field_class:
                # a magic field
                col_data = {'name': magic_field_class.name,
                            'verbose_name': magic_field_class.verbose_name,
                            'source': 'magic_field',
                            'ref': magic_field_class,
                            'type': magic_field_class.type,
                            'is_summable': magic_field_class.is_summable
                            }
            else:
                # A database field
                model_to_use = group_by_model if group_by and '__' not in group_by else report_model
                try:
                    if '__' in col:
                        # A traversing link order__client__email
                        field = get_field_from_query_text(col, model_to_use)
                    else:
                        field = model_to_use._meta.get_field(col)
                except FieldDoesNotExist:
                    raise FieldDoesNotExist(
                        f'Field "{col}" not found either as an attribute to the generator class {cls}, '
                        f'or a computation field, or a database column for the model "{model_to_use}"')

                col_data = {'name': col,
                            'verbose_name': getattr(field, 'verbose_name', col),
                            'source': 'database',
                            'ref': field,
                            'type': field.get_internal_type()
                            }
            parsed_columns.append(col_data)
        return parsed_columns

    def _parse(self):
        self.parsed_columns = self.check_columns(self.columns, self.group_by, self.report_model)
        self._parsed_columns = list(self.parsed_columns)
        self._time_series_parsed_columns = self.get_time_series_parsed_columns()
        self._crosstab_parsed_columns = self.get_crosstab_parsed_columns()

    def get_database_columns(self):
        return [col['name'] for col in self.parsed_columns if 'source' in col and col['source'] == 'database']

    # def get_method_columns(self):
    #     return [col['name'] for col in self.parsed_columns if col['type'] == 'method']

    def get_list_display_columns(self):
        columns = self.parsed_columns
        if self.time_series_pattern:
            time_series_columns = self.get_time_series_parsed_columns()
            try:
                index = self.columns.index('__time_series__')
                columns[index:index] = time_series_columns
            except ValueError:
                columns += time_series_columns

        if self.crosstab_model:
            crosstab_columns = self.get_crosstab_parsed_columns()

            try:
                index = self.columns.index('__crosstab__')
                columns[index:index] = crosstab_columns
            except ValueError:
                columns += crosstab_columns

        return columns

    def get_time_series_parsed_columns(self):
        """
        Return time series columns with all needed data attached
        :param plain: if True it returns '__total__' instead of '__total_TS011212'
        :return: List if columns
        """
        _values = []

        cols = self.time_series_columns or []
        series = self._get_time_series_dates(self.time_series_pattern)

        for index, dt in enumerate(series):
            for col in cols:
                magic_field_class = None

                if type(col) is str:
                    magic_field_class = field_registry.get_field_by_name(col)
                elif issubclass(col, SlickReportField):
                    magic_field_class = col

                _values.append({
                    'name': magic_field_class.name + 'TS' + dt[1].strftime('%Y%m%d'),
                    'original_name': magic_field_class.name,
                    'verbose_name': self.get_time_series_field_verbose_name(magic_field_class, dt, index, series),
                    'ref': magic_field_class,
                    'start_date': dt[0],
                    'end_date': dt[1],
                    'source': 'magic_field' if magic_field_class else '',
                    'is_summable': magic_field_class.is_summable,
                })
        return _values

    def get_time_series_field_verbose_name(self, computation_class, date_period, index, series, pattern=None):
        """
        Sent the column data to construct a verbose name.
        Default implementation is delegated to the ReportField.get_time_series_field_verbose_name
        (which is  name + the end date %Y%m%d)

        :param computation_class: the computation field_name
        :param date_period: a tuple of (start_date, end_date)
        :return: a verbose string
        """
        pattern = pattern or self.time_series_pattern
        return computation_class.get_time_series_field_verbose_name(date_period, index, series,
                                                                    pattern)

    def get_custom_time_series_dates(self):
        """
        Hook to get custom , maybe separated date periods
        :return: [ (date1,date2) , (date3,date4), .... ]
        """
        return self.time_series_custom_dates or []

    def _get_time_series_dates(self, series=None, start_date=None, end_date=None):
        from dateutil.relativedelta import relativedelta
        series = series or self.time_series_pattern
        start_date = start_date or self.start_date
        end_date = end_date or self.end_date
        _values = []

        if series:
            if series == 'daily':
                time_delta = datetime.timedelta(days=1)
            elif series == 'weekly':
                time_delta = relativedelta(weeks=1)
            elif series == 'semimonthly':
                time_delta = relativedelta(weeks=2)
            elif series == 'monthly':
                time_delta = relativedelta(months=1)
            elif series == 'quarterly':
                time_delta = relativedelta(months=3)
            elif series == 'semiannually':
                time_delta = relativedelta(months=6)
            elif series == 'annually':
                time_delta = relativedelta(years=1)
            elif series == 'custom':
                return self.get_custom_time_series_dates()
            else:
                raise NotImplementedError(f'"{series}" is not implemented for time_series_pattern')

            done = False

            while not done:
                to_date = start_date + time_delta
                _values.append((start_date, to_date))
                start_date = to_date
                if to_date >= end_date:
                    done = True
        return _values

    def get_crosstab_parsed_columns(self):
        """
        Return a list of the columns analyzed , with reference to computation field and everything
        :return:
        """
        report_columns = self.crosstab_columns or []
        ids = list(self.crosstab_ids)
        if self.crosstab_compute_reminder:
            ids.append('----')
        output_cols = []
        ids_length = len(ids) - 1
        for counter, id in enumerate(ids):
            for col in report_columns:
                magic_field_class = None
                if type(col) is str:
                    magic_field_class = field_registry.get_field_by_name(col)
                elif issubclass(col, SlickReportField):
                    magic_field_class = col

                output_cols.append({
                    'name': f'{magic_field_class.name}CT{id}',
                    'original_name': magic_field_class.name,
                    'verbose_name': self.get_crosstab_field_verbose_name(magic_field_class, self.crosstab_model, id),
                    'ref': magic_field_class,
                    'id': id,
                    'model': self.crosstab_model,
                    'is_reminder': counter == ids_length,
                    'source': 'magic_field' if magic_field_class else '',
                    'is_summable': magic_field_class.is_summable,
                })

        return output_cols

    def get_crosstab_field_verbose_name(self, computation_class, model, id):
        """
        Hook to change the crosstab field verbose name, default it delegate this function to the ReportField
        :param computation_class: ReportField Class
        :param model: the model name as string
        :param id: the current crosstab id
        :return: a verbose string
        """
        return computation_class.get_crosstab_field_verbose_name(model, id)

    def get_metadata(self):
        """
                A hook to send data about the report for front end which can later be used in charting
                :return:
                """
        time_series_columns = self.get_time_series_parsed_columns()
        crosstab_columns = self.get_crosstab_parsed_columns()
        metadata = {
            'time_series_pattern': self.time_series_pattern,
            'time_series_column_names': [x['name'] for x in time_series_columns],
            'time_series_column_verbose_names': [x['verbose_name'] for x in time_series_columns],
            'crosstab_model': self.crosstab_model or '',
            'crosstab_column_names': [x['name'] for x in crosstab_columns],
            'crosstab_column_verbose_names': [x['verbose_name'] for x in crosstab_columns],
        }
        return metadata

    def get_columns_data(self):
        """
        Hook to get the columns information to front end
        :param columns:
        :return:
        """
        columns = self.get_list_display_columns()
        data = []

        for col in columns:
            data.append({
                'name': col['name'],
                'computation_field': col.get('original_name', ''),
                'verbose_name': col['verbose_name'],
                'visible': col.get('visible', True),
                'type': col.get('type', 'text'),
                'is_summable': col.get('is_summable', ''),
            })
        return data

    def get_full_response(self, data=None, report_slug=None, chart_settings=None, default_chart_title=None):
        data = data or self.get_report_data()
        data = {
            'report_slug': report_slug or self.__class__.__name__,
            'data': data,
            'columns': self.get_columns_data(),
            'metadata': self.get_metadata(),
            'chart_settings': self.get_chart_settings(chart_settings, default_chart_title=default_chart_title)
        }
        return data

    def get_chart_settings(self, chart_settings=None, default_chart_title=None):
        """
        Ensure the sane settings are passed to the front end.
        """
        output = []
        chart_settings = chart_settings or []
        report_title = default_chart_title or ''
        for i, x in enumerate(chart_settings):
            x['id'] = x.get('id', f"{x['type']}-{i}")
            if not x.get('title', False):
                x['title'] = report_title
            x['engine_name'] = x.get('engine_name', SLICK_REPORTING_DEFAULT_CHARTS_ENGINE)
            output.append(x)
        return output


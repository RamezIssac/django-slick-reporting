from __future__ import unicode_literals

import datetime
from django.template.defaultfilters import date as _date_display
from django.utils.text import capfirst
from django.utils.translation import ugettext_lazy as _
from django.utils.timezone import now

from ra.base import app_settings
from ra.reporting.helpers import apply_order_to_list
from ra.utils.translation import ugettext
from ra.utils.views import re_time_series


class ReportMetaData(object):
    """
    Return Meta data associated with the report to render a verbose meaningful report;
    Its service is used by the frontend, or Printing end.
    Ex: Object Verbose Name(s), Entity name, Dates.
    """

    def __init__(self, form, form_settings, chart_settings, applied_filters, report_title=None):
        super(ReportMetaData, self).__init__()
        self.form = form
        self.form_settings = form_settings
        self.chart_settings = chart_settings
        self.applied_filters = applied_filters
        self.report_title = report_title or ''

    def get_meta_data(self):
        verbose_data = self.get_verbose_data()
        meta_data = {
            'verbose_data': verbose_data,
            'report_title': self.report_title,
            'report_sub_title': verbose_data['date_verbose']
        }
        meta_data.update(self.get_datatable_options())

        return meta_data

    def get_datatable_options(self):

        is_group = True
        if self.form.is_time_series(is_group):
            original_columns = self.form.get_datatable_columns(is_group, wTimeSeries=False)
            time_series_colums = self.form.get_time_series_columns(is_group)
            options = self.get_ordered_columns(original_columns, [], is_group, True, time_series_colums)

        elif self.form.is_matrix_support(is_group):
            original_columns = self.form.get_datatable_columns(is_group, wMatrix=False)
            time_series_colums = [] #self.form.get_matrix_fields()
            options = self.get_ordered_columns(original_columns, [], is_group, True, time_series_colums)


        else:
            options = self.form.get_datatable_columns(is_group)
            options = self.get_ordered_columns(options, [], is_group)

        options = {'columns': options}

        column_names = self.get_column_names(options['columns'], is_group)
        options['column_names'] = [capfirst(e) for e in column_names]
        if self.form.is_time_series(is_group):
            series = self.form.get_time_series()
            series_col = [dt.strftime('%Y%m%d') for dt in series]
            options['series'] = series_col
            options['series_column_names'] = self._get_time_series_verbose(series, self.form.cleaned_data[
                'time_series_pattern'])
        if self.form.is_matrix_support(is_group):
            # todo revise and maybe bring back
            pass
            # series =
            # options['matrix_core_columns'] = self.form.get_matrix_core_columns()

        return options

    def get_ordered_columns(self, columns, order_list=None, is_group=None, is_time_series=False,
                            time_series_columns=None, **kwargs):

        if not order_list:
            order_list = self.form_settings.get('group_column_order', []) if is_group else self.form_settings.get(
                'details_column_order', [])

            put_back_control = False
            if columns[0] == '_control_':
                columns = columns[1:]
                put_back_control = True

            if is_time_series:
                columns = self.apply_order_time_series(columns, time_series_columns, order_list)
            else:
                columns = apply_order_to_list(columns, order_list)

            if put_back_control:
                columns = ['_control_'] + columns

            return columns

        return apply_order_to_list(columns, order_list)

    def get_column_names(self, columns, is_group):
        if self.form.is_time_series(is_group):
            translation_dict = self.form_settings.get('group_time_series_column_names',
                                                      {}) if is_group else self.form_settings.get(
                'details_time_series_column_names', {})
            names = []
            extract_time_series = self.extract_time_series
            for column in columns:
                is_time_field = extract_time_series(column)
                if is_time_field:
                    field = column.replace(is_time_field[0], '')
                    name = self.get_time_series_column_name(field, is_time_field[0], translation_dict)
                else:
                    magic_field_name = column
                    name = translation_dict[
                        magic_field_name] if magic_field_name in translation_dict else capfirst(
                        ugettext(magic_field_name))

                names.append(capfirst(name))
            return names
        else:
            translation_dict = self.form_settings.get('group_column_names', {})

            return [translation_dict[x] if x in translation_dict else capfirst(ugettext(x).strip()) for x in
                    columns]

    def apply_order_time_series(self, main_columns, time_series_columns, order_list):
        values = []
        unordered = list(main_columns)
        if time_series_columns and '__time_series__' not in order_list:
            unordered = unordered + time_series_columns

        for o in order_list:
            o = o.strip()
            if o in main_columns:
                values.append(o)
                unordered.remove(o)
            elif o in ['__time_series__', '__matrix__']:
                values += time_series_columns
                # unordered.remove(o)
        values += unordered
        return values

    def get_time_series_column_name(self, column_name, message, translation_dict):
        # re_time_series = re.compile('TS\d+')
        # is_time_field = re_time_series.findall(message)
        # if is_time_field:
        time_series_option = message
        # field = message.replace(time_series_option,'_')

        field = translation_dict[column_name] if column_name in translation_dict else ugettext(column_name)
        field = capfirst(field)
        ts_translation = self.form_settings.get('time_series_TS_name', _('in'))
        if not ts_translation:
            ts = ugettext('TS')
        else:
            ts = ts_translation

        time_series_option = time_series_option.split('TS')[1]
        if self.form.cleaned_data['time_series_pattern'] == 'monthly':
            time_series_option = _date_display(datetime.datetime.strptime(time_series_option, "%Y%m%d").date(), "F Y")
        else:
            time_series_option = datetime.datetime.strptime(time_series_option, "%Y%m%d").date().strftime('%Y-%m-%d')
        return '%s %s %s' % (field, ts, time_series_option)

    def _get_time_series_verbose(self, series, series_pattern):
        '''
        Provide a cleaner translation for the time series pattern
        i.e for monthly pattern , column name would drop the day & show month name
        :param series: list of series to return translated names
        :param series_pattern: the pattern upon which the translation would occur
        :return: list of translated series name
        '''

        if series_pattern == 'monthly':
            return [_date_display(serie, "F-Y") for serie in series]
        elif series_pattern == 'daily':
            return [_date_display(serie, "D-d-F") for serie in series]
        elif series_pattern == 'yearly':
            return [_date_display(serie, "Y") for serie in series]

        return series

    def extract_time_series(self, name):
        # if name.startswith('__'):

        is_time_field = re_time_series.findall(name)
        # if is_time_field:
        #     return is_time_field
        return is_time_field or False

    def get_verbose_data(self):
        """
        Used in Charts, (maybe other places)
        :return: a dict with keys mapping translations
        """
        from ra.base import cache, registry
        from django.utils.translation import ugettext_lazy as original_ugettext

        ret_val = {}
        form_settings = self.form_settings
        _date, to_date = self._get_verbose_date(form_settings)
        ret_val['date_verbose'] = _date
        ret_val['to_date'] = to_date

        form_filters = self.form._fkeys  # ('fkeys', [])

        for f in form_filters:
            if '_id' in f:
                pass
                # main_filter = self.applied_filters.get(f, '')
                # model_name = f[:-3]
                # model_klass = registry.get_ra_model_by_name(model_name)
                # if not main_filter and model_klass:
                #     header = '%s %s' % (original_ugettext('for all'), model_klass._meta.verbose_name_plural)
                # else:
                #     ids = main_filter.split(',')
                #     length = len(ids)
                #     if length == 1:
                #         ''' One Selected '''
                #         header = cache.get_cached_name(model_name, ids[0])
                #     else:
                #         header = '%s %s' % (original_ugettext('several'), model_klass._meta.verbose_name_plural)
                # ret_val[model_name] = header
        ret_val['time_series_pattern'] = ugettext(form_settings.get('time_series_pattern', 'n/A'))

        return ret_val

    def _get_verbose_date(self, form_settings, append_in=False):
        from django.utils.translation import ugettext_lazy as original_ugettext

        doc_date = form_settings.get('doc_date', False)
        if not doc_date:
            from_date = form_settings.get('from_doc_date', app_settings.RA_DEFAULT_FROM_DATETIME).strftime('%Y-%m-%d')
            to_date = form_settings.get('to_doc_date', now()).strftime('%Y-%m-%d')
            from_date_verbose = ugettext('from')
            to_date_verbose = ugettext('to')
            date_text = '%s %s - %s %s' % (from_date_verbose, from_date, to_date_verbose, to_date)
            to_date_text = '%s %s' % (original_ugettext('in') if append_in else '', to_date)

        else:
            date_text = '%s %s' % (original_ugettext('in') if append_in else '', doc_date.strftime('%Y-%m-%d'))
            to_date_text = date_text

        return date_text, to_date_text

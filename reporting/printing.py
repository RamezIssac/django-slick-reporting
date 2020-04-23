# from __future__ import unicode_literals
import logging

import unicodecsv as csv
from django.http import HttpResponse
from django.shortcuts import render

from ra.utils.views import re_time_series
from ra.base import app_settings
logger = logging.getLogger(__name__)


def regroup_data(obj_list, header_report, key):
    values = {}
    for line in obj_list:
        key_value = line[key]
        if key_value not in values:
            values[key_value] = []
        values[key_value].append(line)
    return values


def is_time_series(name):
    is_time_field = re_time_series.findall(name)
    return is_time_field or False


def is_partial_text_in_list(text, lst):
    check = False
    for item in lst:
        if text in item:
            check = True
            break
    return check


class HTMLPrintingClass(object):
    def __init__(self, request, form_settings, response, header_report=None, header_group=None, report_view=None,
                 print_settings=None):
        self.reverse_when_bidi = True
        self.request = request
        self.response = response
        self.form_settings = form_settings
        self.get_group = True
        self.header_report = header_report
        self.group_by = form_settings.get('group_by', '')
        self.header_group = header_group
        self.report_view = report_view
        self.print_settings = print_settings
        self.report_title = self.report_view.get_report_title() if getattr(report_view, 'get_report_title',
                                                                           False) else ''
        self.template_name = f'{app_settings.RA_THEME}/print_base.html'

    def get_response(self, template_name=None, extra_context=None):
        template_name = template_name or self.template_name
        extra_context = extra_context or {}
        context = {'response': self.response, 'is_print': True}
        context.update(extra_context)
        return render(self.request, template_name, context)


class ExportToCSV(object):
    def get_filename(self):
        return self.report_view.get_report_title() if getattr(self.report_view, 'get_report_title',
                                                              False) else ''

    def get_response(self, template_name=None, extra_context=None):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="%s.csv"' % self.get_filename()

        writer = csv.writer(response)
        # for col_name in response['data']:
        # writer.writerow()
        col, col_names = self.get_columns(extra_context)
        writer.writerow(col_names)
        for line in self.response['data']:
            export_line = []
            for c in col:
                export_line.append(line[c])

            writer.writerow(export_line)

        return response

    def get_columns(self, extra_context=None):
        cols = self.response['columns']
        col_names = self.response['column_names']
        result_cols = []
        result_col_names = []
        for i, c in enumerate(cols):
            if '_id' not in c and c != '_control_':
                result_cols.append(c)
                result_col_names.append(col_names[i])
        return result_cols, result_col_names

    def __init__(self, request, form_settings, response, header_report=None, header_group=None, report_view=None,
                 print_settings=None):
        self.reverse_when_bidi = True
        self.request = request
        self.response = response
        self.form_settings = form_settings
        self.get_group = True
        self.header_report = header_report
        self.group_by = form_settings.get('group_by', '')
        self.header_group = header_group
        self.report_view = report_view
        self.print_settings = print_settings
        self.report_title = self.report_view.get_report_title() if getattr(report_view, 'get_report_title',
                                                                           False) else ''

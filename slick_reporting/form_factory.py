from collections import OrderedDict

from django import forms
from django.utils.translation import ugettext_lazy as _

from . import app_settings
from .helpers import get_foreign_keys


class BaseReportForm(object):
    '''
    Holds basic function
    '''

    def get_filters(self):
        """
        Get the foreign key filters for report queryset,
        :return: a dicttionary of filters to be used with QuerySet.filter(**returned_value)
        """
        # todo: implement cross tab support
        _values = {}
        if self.is_valid():
            for key, field in self.foreign_keys.items():
                if key in self.cleaned_data:
                    val = self.cleaned_data[key]
                    if val:
                        val = [x for x in val.values_list('pk', flat=True)]
                        _values['%s__in' % key] = val
            return None, _values

    def get_crispy_helper(self, foreign_keys_map=None, crosstab_model=None, **kwargs):
        from crispy_forms.helper import FormHelper
        from crispy_forms.layout import Column, Layout, Div, Row, Field

        helper = FormHelper()
        helper.form_class = 'form-horizontal'
        helper.label_class = 'col-sm-2 col-md-2 col-lg-2'
        helper.field_class = 'col-sm-10 col-md-10 col-lg-10'
        helper.form_tag = False
        helper.disable_csrf = True

        foreign_keys_map = foreign_keys_map or self.foreign_keys

        helper.layout = Layout(
            Row(
                Column(
                    Field('start_date'), css_class='col-sm-6'),
                Column(
                    Field('end_date'), css_class='col-sm-6'),

                css_class='raReportDateRange'),
            Div(css_class="mt-20", style='margin-top:20px')
        )

        # if crosstab_model:
        #     entry_point.append(Row(
        #         Div('matrix_entities', css_class='col-sm-9'),
        #         Div('matrix_show_other', css_class='col-sm-3')
        #         , css_class='matrixField')
        #     )

        for k in foreign_keys_map:
            if k[:-3] != crosstab_model:
                helper.layout.fields[1].append(Field(k))

        return helper


def _default_foreign_key_widget(f_field):
    return {'form_class': forms.ModelMultipleChoiceField,
            'required': False, }


def report_form_factory(model, fkeys_filter_func=None, foreign_key_widget_func=None, **kwargs):
    foreign_key_widget_func = foreign_key_widget_func or _default_foreign_key_widget
    fkeys_filter_func = fkeys_filter_func or (lambda x: x)

    # gather foreign keys
    fkeys_map = get_foreign_keys(model)
    fkeys_map = fkeys_filter_func(fkeys_map)

    fkeys_list = []
    fields = OrderedDict()

    fields['start_date'] = forms.SplitDateTimeField(required=False, label=_('From date'),
                                                    initial=app_settings.SLICK_REPORTING_DEFAULT_START_DATE,
                                                    # widget=RaBootstrapDateTime(),
                                                    input_date_formats=['%Y-%m-%d', '%Y-%m-%d'],
                                                    input_time_formats=['%H:%M', '%H:%M:%S'],
                                                    )

    fields['end_date'] = forms.SplitDateTimeField(required=False, label=_('To  date'),
                                                  initial=app_settings.SLICK_REPORTING_DEFAULT_END_DATE,
                                                  # widget=RaBootstrapDateTime(),
                                                  )

    for name, f_field in fkeys_map.items():
        fkeys_list.append(name)

        fields[name] = f_field.formfield(
            **foreign_key_widget_func(f_field))

    new_form = type('ReportForm', (BaseReportForm, forms.BaseForm,),
                    {"base_fields": fields,
                     '_fkeys': fkeys_list,
                     'foreign_keys': fkeys_map,
                     })
    return new_form

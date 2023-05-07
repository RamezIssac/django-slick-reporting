from collections import OrderedDict

from django import forms
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _

from . import app_settings
from .helpers import get_foreign_keys

TIME_SERIES_CHOICES = (
    ("monthly", _("Monthly")),
    ("weekly", _("Weekly")),
    ("annually", _("Yearly")),
    ("daily", _("Daily")),
)


def default_formfield_callback(f, **kwargs):
    kwargs["required"] = False
    kwargs["help_text"] = ""
    return f.formfield(**kwargs)


def get_crispy_helper(
    foreign_keys_map=None,
    crosstab_model=None,
    crosstab_key_name=None,
    crosstab_display_compute_reminder=False,
    add_date_range=True,
):
    from crispy_forms.helper import FormHelper
    from crispy_forms.layout import Column, Layout, Div, Row, Field

    helper = FormHelper()
    helper.form_class = "form-horizontal"
    helper.label_class = "col-sm-2 col-md-2 col-lg-2"
    helper.field_class = "col-sm-10 col-md-10 col-lg-10"
    helper.form_tag = False
    helper.disable_csrf = True
    helper.render_unmentioned_fields = True

    helper.layout = Layout()
    if add_date_range:
        helper.layout.fields.append(
            Row(
                Column(Field("start_date"), css_class="col-sm-6"),
                Column(Field("end_date"), css_class="col-sm-6"),
                css_class="raReportDateRange",
            ),
        )
    filters_container = Div(css_class="mt-20", style="margin-top:20px")
    # first add the crosstab model and its display reimder then the rest of the fields
    if crosstab_model:
        filters_container.append(Field(crosstab_key_name))
        if crosstab_display_compute_reminder:
            filters_container.append(Field("crosstab_compute_reminder"))

    for k in foreign_keys_map:
        if k != crosstab_key_name:
            filters_container.append(Field(k))
    helper.layout.fields.append(filters_container)

    return helper


class BaseReportForm:
    """
    Holds basic function
    """

    @property
    def media(self):
        from .app_settings import SLICK_REPORTING_FORM_MEDIA

        return forms.Media(
            css=SLICK_REPORTING_FORM_MEDIA.get("css", {}),
            js=SLICK_REPORTING_FORM_MEDIA.get("js", []),
        )

    def get_filters(self):
        """
        Get the foreign key filters for report queryset, excluding crosstab ids, handled by `get_crosstab_ids()`
        :return: a dicttionary of filters to be used with QuerySet.filter(**returned_value)
        """
        _values = {}
        if self.is_valid():
            fk_keys = getattr(self, "foreign_keys", [])
            if fk_keys:
                fk_keys = fk_keys.items()
            for key, field in fk_keys:
                if key in self.cleaned_data and not key == self.crosstab_key_name:
                    val = self.cleaned_data[key]
                    if val:
                        val = [x for x in val.values_list("pk", flat=True)]
                        _values["%s__in" % key] = val
            return None, _values

    @cached_property
    def crosstab_key_name(self):
        """
        return the actual foreignkey field name by simply adding an '_id' at the end.
        This is hook is to customize this naieve approach.
        :return: key: a string that should be in self.cleaned_data
        """
        return f"{self.crosstab_model}_id"

    def get_crosstab_ids(self):
        """
        Get the crosstab ids so they can be sent to the report generator.
        :return:
        """
        if self.crosstab_model:
            qs = self.cleaned_data.get(self.crosstab_key_name)
            return [x for x in qs.values_list("pk", flat=True)]
        return []

    def get_crosstab_compute_reminder(self):
        return self.cleaned_data.get("crosstab_compute_reminder", True)

    def get_crispy_helper(self, foreign_keys_map=None, crosstab_model=None, **kwargs):
        return get_crispy_helper(
            self.foreign_keys,
            crosstab_model=getattr(self, "crosstab_model", None),
            crosstab_key_name=getattr(self, "crosstab_key_name", None),
            crosstab_display_compute_reminder=getattr(
                self, "crosstab_display_compute_reminder", False
            ),
            **kwargs,
        )


def _default_foreign_key_widget(f_field):
    return {
        "form_class": forms.ModelMultipleChoiceField,
        "required": False,
    }


def report_form_factory(
    model,
    crosstab_model=None,
    display_compute_reminder=True,
    fkeys_filter_func=None,
    foreign_key_widget_func=None,
    excluded_fields=None,
    initial=None,
    required=None,
    show_time_series_selector=False,
    time_series_selector_choices=None,
    time_series_selector_default="",
    time_series_selector_label=None,
    time_series_selector_allow_empty=False,
):
    """
    Create a Report Form based on the report_model passed by
    1. adding a start_date and end_date fields
    2. extract all ForeignKeys on the report_model

    :param model: the report_model
    :param crosstab_model: crosstab model if any
    :param display_compute_reminder:  relevant only if crosstab_model is specified. Control if we show the check to
    display the rest.
    :param fkeys_filter_func:  a receives an OrderedDict of Foreign Keys names and their model field instances found on the model, return the OrderedDict that would be used
    :param foreign_key_widget_func: receives a Field class return the used widget like this {'form_class': forms.ModelMultipleChoiceField, 'required': False, }
    :param excluded_fields: a list of fields to be excluded from the report form
    :param initial a dict for fields initial
    :param required a list of fields that should be marked as required
    :return:
    """
    foreign_key_widget_func = foreign_key_widget_func or _default_foreign_key_widget
    fkeys_filter_func = fkeys_filter_func or (lambda x: x)

    # gather foreign keys
    initial = initial or {}
    required = required or []
    fkeys_map = get_foreign_keys(model)
    excluded_fields = excluded_fields or []
    for excluded in excluded_fields:
        del fkeys_map[excluded]

    fkeys_map = fkeys_filter_func(fkeys_map)

    fkeys_list = []
    fields = OrderedDict()

    fields["start_date"] = forms.DateTimeField(
        required=False,
        label=_("From date"),
        initial=initial.get(
            "start_date", app_settings.SLICK_REPORTING_DEFAULT_START_DATE
        ),
        widget=forms.DateTimeInput(attrs={"autocomplete": "off"}),
    )

    fields["end_date"] = forms.DateTimeField(
        required=False,
        label=_("To  date"),
        initial=initial.get("end_date", app_settings.SLICK_REPORTING_DEFAULT_END_DATE),
        widget=forms.DateTimeInput(attrs={"autocomplete": "off"}),
    )

    if show_time_series_selector:
        time_series_choices = tuple(TIME_SERIES_CHOICES)
        if time_series_selector_allow_empty:
            time_series_choices.insert(0, ("", "---------"))

        fields["time_series_pattern"] = forms.ChoiceField(
            required=False,
            initial=time_series_selector_default,
            label=time_series_selector_label or _("Period Pattern"),
            choices=time_series_selector_choices or TIME_SERIES_CHOICES,
        )

    for name, f_field in fkeys_map.items():
        fkeys_list.append(name)
        field_attrs = foreign_key_widget_func(f_field)
        if name in required:
            field_attrs["required"] = True
        fields[name] = f_field.formfield(**field_attrs)

    if crosstab_model and display_compute_reminder:
        fields["crosstab_compute_reminder"] = forms.BooleanField(
            required=False, label=_("Display the crosstab reminder"), initial=True
        )

    bases = (
        BaseReportForm,
        forms.BaseForm,
    )
    new_form = type(
        "ReportForm",
        bases,
        {
            "base_fields": fields,
            "_fkeys": fkeys_list,
            "foreign_keys": fkeys_map,
            "crosstab_model": crosstab_model,
            "crosstab_display_compute_reminder": display_compute_reminder,
        },
    )
    return new_form

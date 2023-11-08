from collections import OrderedDict

from crispy_forms.helper import FormHelper
from django import forms
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _

from . import app_settings
from .helpers import get_foreign_keys, get_field_from_query_text

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
    crosstab_display_compute_remainder=False,
    add_date_range=True,
):
    from crispy_forms.helper import FormHelper
    from crispy_forms.layout import Column, Layout, Div, Row, Field

    foreign_keys_map = foreign_keys_map or []
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
        if crosstab_display_compute_remainder:
            filters_container.append(Field("crosstab_compute_remainder"))

    for k in foreign_keys_map:
        if k != crosstab_key_name:
            filters_container.append(Field(k))
    helper.layout.fields.append(filters_container)

    return helper


def get_choices_form_queryset_list(qs):
    choices = []
    for row in qs:
        choices.append((row, row))
    return choices


class OrderByForm(forms.Form):
    order_by = forms.CharField(required=False)

    def get_order_by(self, default_field=None):
        """
        Get the order by specified by teh form or the default field if provided
        :param default_field:
        :return: tuple of field and direction
        """
        if self.is_valid():
            order_field = self.cleaned_data["order_by"]
            order_field = order_field or default_field
            if order_field:
                return self.parse_order_by_field(order_field)
        return None, None

    def parse_order_by_field(self, order_field):
        """
        Specify the field and direction
        :param order_field: the field to order by
        :return: tuple of field and direction
        """
        if order_field:
            asc = True
            if order_field[0:1] == "-":
                order_field = order_field[1:]
                asc = False
            return order_field, not asc
        return None, None


class BaseReportForm:
    def get_filters(self):
        raise NotImplementedError(
            "get_filters() must be implemented in subclass,"
            "should return a tuple of (Q objects, kwargs filter) to be passed to QuerySet.filter()"
        )

    def get_start_date(self):
        raise NotImplementedError("get_start_date() must be implemented in subclass," "should return a datetime object")

    def get_end_date(self):
        raise NotImplementedError("get_end_date() must be implemented in subclass," "should return a datetime object")

    def get_crosstab_compute_remainder(self):
        raise NotImplementedError(
            "get_crosstab_compute_remainder() must be implemented in subclass," "should return a boolean value"
        )

    def get_crosstab_ids(self):
        raise NotImplementedError(
            "get_crosstab_ids() must be implemented in subclass," "should return a list of ids to be used for crosstab"
        )

    def get_time_series_pattern(self):
        raise NotImplementedError(
            "get_time_series_pattern() must be implemented in subclass,"
            "should return a string value of a valid time series pattern"
        )

    def get_crispy_helper(self):
        # return a default helper
        helper = FormHelper()
        helper.form_class = "form-horizontal"
        helper.label_class = "col-sm-2 col-md-2 col-lg-2"
        helper.field_class = "col-sm-10 col-md-10 col-lg-10"
        helper.form_tag = False
        helper.disable_csrf = True
        helper.render_unmentioned_fields = True
        return helper


class SlickReportForm(BaseReportForm):
    """
    Holds basic function
    """

    def get_start_date(self):
        return self.cleaned_data.get("start_date")

    def get_end_date(self):
        return self.cleaned_data.get("end_date")

    def get_time_series_pattern(self):
        return self.cleaned_data.get("time_series_pattern")

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
        # todo get the model more accurately
        """
        return the actual foreignkey field name by simply adding an '_id' at the end.
        This is hook is to customize this naieve approach.
        :return: key: a string that should be in self.cleaned_data
        """
        if self.crosstab_field_klass:
            return self.crosstab_field_klass.attname
        return f"{self.crosstab_model}_id"

    def get_crosstab_ids(self):
        """
        Get the crosstab ids so they can be sent to the report generator.
        :return:
        """
        if self.crosstab_field_klass:
            if self.crosstab_field_klass.is_relation:
                qs = self.cleaned_data.get(self.crosstab_key_name)
                return [x for x in qs.values_list(self.crosstab_field_related_name, flat=True)]
            else:
                return self.cleaned_data.get(self.crosstab_key_name)
        return []

    def get_crosstab_compute_remainder(self):
        return self.cleaned_data.get("crosstab_compute_remainder", True)

    def get_crispy_helper(self, foreign_keys_map=None, crosstab_model=None, **kwargs):
        return get_crispy_helper(
            self.foreign_keys,
            crosstab_model=getattr(self, "crosstab_model", None),
            crosstab_key_name=getattr(self, "crosstab_key_name", None),
            crosstab_display_compute_remainder=getattr(self, "crosstab_display_compute_remainder", False),
            add_date_range=self.add_start_date or self.add_end_date,
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
    display_compute_remainder=True,
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
    add_start_date=True,
    add_end_date=True,
):
    """
    Create a Report Form based on the report_model passed by
    1. adding a start_date and end_date fields
    2. extract all ForeignKeys on the report_model

    :param model: the report_model
    :param crosstab_model: crosstab model if any
    :param display_compute_remainder:  relevant only if crosstab_model is specified. Control if we show the check to
    display the rest.
    :param fkeys_filter_func:  a receives an OrderedDict of Foreign Keys names and their model field instances found on
           the model, return the OrderedDict that would be used
    :param foreign_key_widget_func: receives a Field class return the used widget like this
           {'form_class': forms.ModelMultipleChoiceField, 'required': False, }
    :param excluded_fields: a list of fields to be excluded from the report form
    :param initial a dict for fields initial
    :param required a list of fields that should be marked as required
    :return:
    """
    crosstab_field_related_name = ""
    crosstab_field_klass = None
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
    if add_start_date:
        fields["start_date"] = forms.DateTimeField(
            required=False,
            label=_("From date"),
            initial=initial.get("start_date", "") or app_settings.SLICK_REPORTING_SETTINGS["DEFAULT_START_DATE_TIME"],
            widget=forms.DateTimeInput(attrs={"autocomplete": "off"}),
        )
    if add_end_date:
        fields["end_date"] = forms.DateTimeField(
            required=False,
            label=_("To  date"),
            initial=initial.get("end_date", "") or app_settings.SLICK_REPORTING_SETTINGS["DEFAULT_END_DATE_TIME"],
            widget=forms.DateTimeInput(attrs={"autocomplete": "off"}),
        )

    if show_time_series_selector:
        time_series_choices = list(TIME_SERIES_CHOICES)
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
        field_attrs["initial"] = initial.get(name, "")
        fields[name] = f_field.formfield(**field_attrs)

    if crosstab_model:
        # todo Enhance, add tests , cover cases
        # Crosstab is a foreign key on model
        # crosstab is a Char field on model
        # crosstab is a traversing fk field
        # crosstab is a traversing Char / choice field

        if display_compute_remainder:
            fields["crosstab_compute_remainder"] = forms.BooleanField(
                required=False, label=_("Display the crosstab remainder"), initial=True
            )

        crosstab_field_klass = get_field_from_query_text(crosstab_model, model)
        if crosstab_field_klass.is_relation:
            crosstab_field_related_name = crosstab_field_klass.to_fields[0]
        else:
            crosstab_field_related_name = crosstab_field_klass.name

        if "__" in crosstab_model:  # traversing field, it won't be added naturally to the form
            if crosstab_field_klass.is_relation:
                pass
            else:
                fields[crosstab_field_related_name] = forms.MultipleChoiceField(
                    choices=get_choices_form_queryset_list(
                        list(
                            crosstab_field_klass.model.objects.values_list(
                                crosstab_field_related_name, flat=True
                            ).distinct()
                        )
                    ),
                    required=False,
                    label=crosstab_field_klass.verbose_name,
                )

    bases = (
        SlickReportForm,
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
            "crosstab_display_compute_remainder": display_compute_remainder,
            "crosstab_field_related_name": crosstab_field_related_name,
            "crosstab_field_klass": crosstab_field_klass,
            "add_start_date": add_start_date,
            "add_end_date": add_end_date,
        },
    )
    return new_form

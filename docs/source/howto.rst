=======
How To
=======

Customize the form
------------------

The filter form is automatically generated for convenience
but you can override it and add your own Form.

The system expect that the form used with the ``ReportView`` to implement the ``slick_reporting.forms.BaseReportForm`` interface.
The interface is simple, only 3 mandatory methods to implement, The rest are mandatory only if you are working with a crosstab report or a time series report.

#. get_filters: return the filters to be used in the report in a tuple
   The first element is a list of Q filters (is any)
   The second element is a dict of filters to be used in the queryset
   These filters will be passed to the report_model.objects.filter(*q_filters, **kw_filters)

#. get_start_date: return the start date to be used in the report
#. get_end_date: return the end date to be used in the report



.. code-block:: python

    # forms.py
    from slick_reporting.forms import BaseReportForm

    class RequestFilterForm(BaseReportForm, forms.Form):

        SECURE_CHOICES = (
            ("all", "All"),
            ("secure", "Secure"),
            ("non-secure", "Not Secure"),
        )

        start_date = forms.DateField(
            required=False,
            label="Start Date",
            widget=forms.DateInput(attrs={"type": "date"}),
        )
        end_date = forms.DateField(
            required=False, label="End Date", widget=forms.DateInput(attrs={"type": "date"})
        )
        secure = forms.ChoiceField(
            choices=SECURE_CHOICES, required=False, label="Secure", initial="all"
        )
        method = forms.CharField(required=False, label="Method")

        other_people_only = forms.BooleanField(
            required=False, label="Show requests from other People Only"
        )

        def __init__(self, request=None, *args, **kwargs):
            self.request = request
            super().__init__(*args, **kwargs)
            self.fields["start_date"].initial = datetime.date.today()
            self.fields["end_date"].initial = datetime.date.today()

        def get_filters(self):
            q_filters = []
            kw_filters = {}

            if self.cleaned_data["secure"] == "secure":
                kw_filters["is_secure"] = True
            elif self.cleaned_data["secure"] == "non-secure":
                kw_filters["is_secure"] = False
            if self.cleaned_data["method"]:
                kw_filters["method"] = self.cleaned_data["method"]
            if self.cleaned_data["response"]:
                kw_filters["response"] = self.cleaned_data["response"]
            if self.cleaned_data["other_people_only"]:
                q_filters.append(~Q(user=self.request.user))

            return q_filters, kw_filters

        def get_start_date(self):
            return self.cleaned_data["start_date"]

        def get_end_date(self):
            return self.cleaned_data["end_date"]

For a complete reference of the ``BaseReportForm`` interface, check :ref:`filter_form_customization`


Use the report view in our own template
---------------------------------------
To use the report template with your own project templates, you simply need to override the ``slick_reporting/base.html`` template to make it extends your own base template
You only need to have a ``{% block content %}`` in your base template to be able to use the report template
and a ``{% block extrajs %}`` block to add the javascript implementation.


The example below assumes you have a ``base.html`` template in your project templates folder and have a content block and a project_extrajs block in it.

.. code-block:: html

    {% extends "base.html" %}
    {% load static %}

    {% block content %}

    {% endblock %}

    {% block project_extrajs %}
        {% include "slick_reporting/js_resources.html" %}
        {% block extrajs %}
        {% endblock %}

    {% endblock %}


Work with tree data & Nested categories
---------------------------------------





Change the report structure in response to User input
-----------------------------------------------------


Create your own Chart Engine
-----------------------------

Create a Custom ComputationField and reuse it
---------------------------------------------

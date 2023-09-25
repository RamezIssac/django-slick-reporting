.. _filter_form:

Customizing Filter Form
=======================

The filter form is a form that is used to filter the data to be used in the report.


The generated form
-------------------

Behind the scene, The view calls ``slick_reporting.form_factory.report_form_factory`` in ``get_form_class`` method.
``report_form_factory`` is a helper method which generates a form containing start date and end date, as well as all foreign keys on the report_model.

Changing the generated form API is still private, however, you can use your own form easily.

Overriding the Form
--------------------

The system expect that the form used with the ``ReportView`` to implement the ``slick_reporting.forms.BaseReportForm`` interface.

The interface is simple, only 3 mandatory methods to implement, The rest are mandatory only if you are working with a crosstab report or a time series report.


* ``get_filters``: Mandatory, return a tuple (Q_filers , kwargs filter) to be used in filtering.
  q_filter: can be none or a series of Django's Q queries
  kwargs_filter: None or a dictionary of filters

* ``get_start_date``: Mandatory, return the start date of the report.

* ``get_end_date``: Mandatory, return the end date of the report.

* ``get_crispy_helper`` : return a crispy form helper to be used in rendering the form. (optional)

In case you are working with a crosstab report, you need to implement the following methods:

* ``get_crosstab_compute_remainder``: return a boolean indicating if the remainder should be computed or not.

* ``get_crosstab_ids``: return a list of ids to be used in the crosstab report.


And in case you are working with a time series report, with a selector on, you need to implement the following method:

* ``get_time_series_pattern``: return a string representing the time series pattern. ie: ``ie: daily, monthly, yearly``

Example a full example of a custom form:

.. code-block:: python

    # forms.py
    from slick_reporting.forms import BaseReportForm

    # A Normal form , Inheriting from BaseReportForm
    class RequestLogForm(BaseReportForm, forms.Form):

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
        response = forms.ChoiceField(
            choices=HTTP_STATUS_CODES,
            required=False,
            label="Response",
            initial="200",
        )
        other_people_only = forms.BooleanField(
            required=False, label="Show requests from other People Only"
        )

        def __init__(self, request=None, *args, **kwargs):
            self.request = request
            super(RequestLogForm, self).__init__(*args, **kwargs)
            # provide initial values and ay needed customization
            self.fields["start_date"].initial = datetime.date.today()
            self.fields["end_date"].initial = datetime.date.today()

        def get_filters(self):
            # return the filters to be used in the report
            # Note: the use of Q filters and kwargs filters
            filters = {}
            q_filters = []
            if self.cleaned_data["secure"] == "secure":
                filters["is_secure"] = True
            elif self.cleaned_data["secure"] == "non-secure":
                filters["is_secure"] = False
            if self.cleaned_data["method"]:
                filters["method"] = self.cleaned_data["method"]
            if self.cleaned_data["response"]:
                filters["response"] = self.cleaned_data["response"]
            if self.cleaned_data["other_people_only"]:
                q_filters.append(~Q(user=self.request.user))

            return q_filters, filters

        def get_start_date(self):
            return self.cleaned_data["start_date"]

        def get_end_date(self):
            return self.cleaned_data["end_date"]

        # ----
        # in views.py

        from .forms import RequestLogForm

        class RequestCountByPath(ReportView):
            form_class = RequestLogForm

You can view this code snippet in action on the demo project https://django-slick-reporting.com/total-product-sales-with-custom-form/

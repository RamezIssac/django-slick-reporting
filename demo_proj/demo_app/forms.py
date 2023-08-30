from django import forms
from django.db.models import Q
from slick_reporting.forms import BaseReportForm


class TotalSalesFilterForm(BaseReportForm, forms.Form):
    PRODUCT_SIZE_CHOICES = (
        ("all", "All"),
        ("big-only", "Big Only"),
        ("small-only", "Small Only"),
        ("medium-only", "Medium Only"),
        ("all-except-extra-big", "All except extra Big"),
    )
    start_date = forms.DateField(
        required=False,
        label="Start Date",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    end_date = forms.DateField(
        required=False, label="End Date", widget=forms.DateInput(attrs={"type": "date"})
    )
    product_size = forms.ChoiceField(
        choices=PRODUCT_SIZE_CHOICES, required=False, label="Product Size", initial="all"
    )

    def get_filters(self):
        # return the filters to be used in the report
        # Note: the use of Q filters and kwargs filters
        kw_filters = {}
        q_filters = []
        if self.cleaned_data["product_size"] == "big-only":
            kw_filters["product__size__in"] = ["extra_big", "big"]
        elif self.cleaned_data["product_size"] == "small-only":
            kw_filters["product__size__in"] = ["extra_small", "small"]
        elif self.cleaned_data["product_size"] == "medium-only":
            kw_filters["product__size__in"] = ["medium"]
        elif self.cleaned_data["product_size"] == "all-except-extra-big":
            q_filters.append(~Q(product__size__in=["extra_big", "big"]))
        return q_filters, kw_filters

    def get_start_date(self):
        return self.cleaned_data["start_date"]

    def get_end_date(self):
        return self.cleaned_data["end_date"]

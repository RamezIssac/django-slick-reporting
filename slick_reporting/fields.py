from __future__ import annotations

from warnings import warn

from django.db.models import Sum, Q
from django.template.defaultfilters import date as date_filter
from django.utils.translation import gettext_lazy as _

from .registry import field_registry


class ComputationField(object):
    """
    Computation field responsible for making the calculation unit
    """

    _field_registry = field_registry
    name = ""
    """The name to be used in the ReportGenerator"""

    calculation_field = "value"
    """the Field to compute on"""

    calculation_method = Sum
    """The computation Method"""

    verbose_name = None
    """Verbose name to be used in front end when needed"""

    requires = None
    """This can be a list of sibling classes,
    they will be asked to compute and their value would be available to you in the `resolve` method
    requires = [BasicCalculationA, BasicCalculationB]
    """

    type = "number"
    """Just a string describing what this computation field return, usually passed to frontend"""

    is_summable = True
    """Indicate if this computation can be summed over. Useful to be passed to frontend or whenever needed"""

    report_model = None
    """The model on which the computation would occur"""

    queryset = None
    """The queryset on which the computation would occur"""

    group_by = None
    group_by_custom_querysets = None
    plus_side_q = None
    minus_side_q = None

    base_kwargs_filters = None
    base_q_filters = None

    _require_classes = None
    _debit_and_credit = True

    prevent_group_by = False
    """Will prevent group by calculation for this specific field, serves when you want to compute overall results"""

    def __new__(cls, *args, **kwargs):
        """
        This is where we register the class in the registry
        :param args:
        :param kwargs:
        :return:
        """
        if not cls.name:
            raise ValueError(f"ReportField {cls} must have a name")
        return super(ComputationField, cls).__new__(cls)

    @classmethod
    def create(cls, method, field, name=None, verbose_name=None, is_summable=True):
        """
        Creates a ReportField class on the fly
        :param method: The computation Method to be used
        :param field: The field on which the computation would occur
        :param name: a name to refer to this field else where
        :param verbose_name: Verbose name
        :param is_summable:
        :return:
        """
        if not name:
            name = name or f"{method.name.lower()}__{field}"
            assert name not in cls._field_registry.get_all_report_fields_names()

        verbose_name = verbose_name or f"{method.name} {field}"
        report_klass = type(
            f"ReportField_{name}",
            (cls,),
            {
                "name": name,
                "verbose_name": verbose_name,
                "calculation_field": field,
                "calculation_method": method,
                "is_summable": is_summable,
            },
        )
        return report_klass

    def __init__(
        self,
        plus_side_q=None,
        minus_side_q=None,
        report_model=None,
        queryset=None,
        calculation_field=None,
        calculation_method=None,
        date_field="",
        group_by=None,
        group_by_custom_querysets=None,
    ):
        super(ComputationField, self).__init__()
        self.date_field = date_field
        self.report_model = self.report_model or report_model
        self.queryset = self.queryset or queryset
        self.queryset = self.report_model._default_manager.all() if self.queryset is None else self.queryset

        self.group_by_custom_querysets = self.group_by_custom_querysets or group_by_custom_querysets

        self.calculation_field = calculation_field if calculation_field else self.calculation_field
        self.calculation_method = calculation_method if calculation_method else self.calculation_method
        self.plus_side_q = self.plus_side_q or plus_side_q
        self.minus_side_q = self.minus_side_q or minus_side_q
        self.requires = self.requires or []
        self.group_by = self.group_by or group_by
        self._cache = None, None, None
        self._require_classes = self._get_required_classes()
        self._required_prepared_results = None

        self._debit_and_credit = self.plus_side_q or self.minus_side_q

    @classmethod
    def _get_required_classes(cls):
        requires = cls.requires or []
        return [field_registry.get_field_by_name(x) if isinstance(x, str) else x for x in requires]

    def apply_aggregation(self, queryset, group_by=""):
        annotation = self.calculation_method(self.calculation_field)
        if self.group_by_custom_querysets:
            return queryset.aggregate(annotation)
        elif group_by:
            queryset = queryset.values(group_by).annotate(annotation)
            queryset = {str(x[self.group_by]): x for x in queryset}
        else:
            queryset = queryset.aggregate(annotation)
        return queryset

    def init_preparation(self, q_filters=None, kwargs_filters=None, **kwargs):
        """
        Called by the generator to prepare the calculation of this field + it's requirements
        :param q_filters:
        :param kwargs_filters:
        :param kwargs:
        :return:
        """
        kwargs_filters = kwargs_filters or {}

        required_prepared_results = self._prepare_required_computations(q_filters, kwargs_filters.copy())
        queryset = self.get_queryset()
        if self.group_by_custom_querysets:
            debit_results, credit_results = self.prepare_custom_group_by_queryset(q_filters, kwargs_filters, **kwargs)
        else:
            debit_results, credit_results = self.prepare(
                q_filters,
                kwargs_filters,
                queryset,
                self.group_by,
                self.prevent_group_by,
                **kwargs,
            )
        self._cache = debit_results, credit_results
        self._required_prepared_results = required_prepared_results

    def prepare_custom_group_by_queryset(self, q_filters=None, kwargs_filters=None, **kwargs):
        debit_output, credit_output = [], []
        for index, queryset in enumerate(self.group_by_custom_querysets):
            debit, credit = self.prepare(q_filters, kwargs_filters, queryset, **kwargs)
            if debit:
                debit_output.append(debit)
            if credit:
                credit_output.append(credit)
        return debit_output, credit_output

    def prepare(
        self,
        q_filters: list | object = None,
        kwargs_filters: dict = None,
        main_queryset=None,
        group_by: str = None,
        prevent_group_by=None,
        **kwargs,
    ):
        """
        This is the first hook where you can customize the calculation away from the Django Query aggregation method
        This method is called with all available arguments, so you can prepare the results for the whole set and save
        it in a local cache (like self._cache) .
        The flow will later call the method `resolve`,  giving you the id, for you to return it respective calculation

        :param q_filters:
        :param kwargs_filters:
        :param main_queryset:
        :param group_by:
        :param prevent_group_by:
        :param kwargs:
        :return:
        """

        queryset = main_queryset.all()
        group_by = "" if prevent_group_by else group_by
        credit_results = None

        if q_filters:
            if type(q_filters) is Q:
                q_filters = [q_filters]
            queryset = queryset.filter(*q_filters)
        if kwargs_filters:
            queryset = queryset.filter(**kwargs_filters)

        if self.plus_side_q:
            queryset = queryset.filter(*self.plus_side_q)
        debit_results = self.apply_aggregation(queryset, group_by)

        if self._debit_and_credit:
            queryset = main_queryset.all()
            if kwargs_filters:
                queryset = queryset.filter(**kwargs_filters)
            if q_filters:
                queryset = queryset.filter(*q_filters)
            if self.minus_side_q:
                queryset = queryset.filter(*self.minus_side_q)
            credit_results = self.apply_aggregation(queryset, group_by)

        return debit_results, credit_results

    def get_queryset(self):
        queryset = self.queryset
        if self.base_q_filters:
            queryset = queryset.filter(*self.base_q_filters)
        if self.base_kwargs_filters:
            queryset = queryset.filter(**self.base_kwargs_filters)
        return queryset.order_by()

    def _prepare_required_computations(
        self,
        q_filters=None,
        extra_filters=None,
    ):
        values = {}
        for required_klass in self._require_classes:
            dep = required_klass(
                self.plus_side_q,
                self.minus_side_q,
                self.report_model,
                date_field=self.date_field,
                group_by=self.group_by,
                queryset=self.queryset,
                group_by_custom_querysets=self.group_by_custom_querysets,
            )
            results = dep.init_preparation(q_filters, extra_filters)
            values[dep.name] = {"results": results, "instance": dep}
        return values

    def resolve(self, prepared_results, required_computation_results: dict, current_pk, current_row=None) -> float:
        """
        Reponsible for getting the exact data from the prepared value
        :param prepared_results: the returned data from prepare
        :param required_computation_results: the returned data from prepare
        :param current_pk: he value of group by id
        :param current_row: the row in iteration
        :return: a solid number or value
        """
        debit_value, credit_value = self.extract_data(prepared_results, current_pk)
        value = debit_value or 0 - credit_value or 0
        return value

    def do_resolve(self, current_obj, current_row=None):
        prepared_result = self._cache
        dependencies_value = self._resolve_dependencies(current_obj)
        return self.resolve(prepared_result, dependencies_value, current_obj, current_row)

    def get_dependency_value(self, current_obj, name):
        """
        Get the values of the ReportFields specified in `requires`

        :param current_obj: the current object which we want the calculation for
        :param name: the name of the specific dependency you want.

        :return: a dict containing dependencies names as keys and their calculation as values
                 or a specific value if name is specified.
        """
        values = self._resolve_dependencies(current_obj, name=name)
        return values.get(name)

    def _resolve_dependencies(self, current_obj, name=None):
        dep_results = {}
        dependencies_value = self._required_prepared_results
        dependencies_value = dependencies_value or {}
        needed_values = [name] if name else dependencies_value.keys()
        for d in needed_values:
            d_instance = dependencies_value[d]["instance"]
            dep_results[d] = d_instance.do_resolve(current_obj)
        return dep_results

    def extract_data(self, prepared_results, current_obj):
        group_by = "" if self.prevent_group_by else (self.group_by or self.group_by_custom_querysets)
        annotation = "__".join([self.calculation_field.lower(), self.calculation_method.name.lower()])

        cached_debit, cached_credit = prepared_results

        cached = [cached_debit, cached_credit]
        output = []
        for results in cached:
            value = 0
            if results:
                if not group_by:
                    x = list(results.keys())[0]
                    value = results[x]
                elif self.group_by_custom_querysets:
                    value = results[int(current_obj)][annotation]
                else:
                    value = results.get(str(current_obj), {}).get(annotation, 0)
            output.append(value)
        return output

    @classmethod
    def get_full_dependency_list(cls):
        """
        Get the full Hirearchy of dependencies and dependencies dependency.
        :return: List of dependecies classes
        """

        def get_dependency(field_class):
            dependencies = field_class._get_required_classes()
            klasses = []
            for klass in dependencies:
                klasses.append(klass)
                other = get_dependency(klass)
                if other:
                    klasses += other
            return klasses

        return get_dependency(cls)

    @classmethod
    def get_crosstab_field_verbose_name(cls, model, id):
        """
        Construct a verbose name for the crosstab field
        :param model: the model name
        :param id: the id of the current crosstab object
        :return: a verbose string
        """
        if id == "----":
            return _("The remainder")
        return f"{cls.verbose_name} {model} {id}"

    @classmethod
    def get_time_series_field_verbose_name(cls, date_period, index, dates, pattern):
        """
        Get the name of the verbose name of a computation field that's in a time_series.
        should be a mix of the date period of the column and it's verbose name.
        :param date_period: a tuple of (start_date, end_date)
        :param index: the index of the current field in the whole dates to be calculated
        :param dates a list of tuples representing the start and the end date
        :param pattern it's the pattern name. monthly, daily, custom, ...
        :return: a verbose string
        """
        dt_format = "%Y/%m/%d"

        if pattern == "monthly":
            month_name = date_filter(date_period[0], "F Y")
            return f"{cls.verbose_name} {month_name}"
        elif pattern == "daily":
            return f"{cls.verbose_name} {date_period[0].strftime(dt_format)}"
        elif pattern == "weekly":
            return f' {cls.verbose_name} {_("Week")} {index + 1} {date_period[0].strftime(dt_format)}'
        elif pattern == "yearly":
            year = date_filter(date_period[0], "Y")
            return f"{cls.verbose_name} {year}"

        return f"{cls.verbose_name} {date_period[0].strftime(dt_format)} - {date_period[1].strftime(dt_format)}"


class FirstBalanceField(ComputationField):
    name = "__fb__"
    verbose_name = _("opening balance")

    def prepare(
        self,
        q_filters: list | object = None,
        kwargs_filters: dict = None,
        main_queryset=None,
        group_by: str = None,
        prevent_group_by=None,
        **kwargs,
    ):
        extra_filters = kwargs_filters or {}
        if self.date_field:
            from_date_value = extra_filters.get(f"{self.date_field}__gte")
            extra_filters.pop(f"{self.date_field}__gte", None)
            extra_filters[f"{self.date_field}__lt"] = from_date_value
        return super(FirstBalanceField, self).prepare(
            q_filters, kwargs_filters, main_queryset, group_by, prevent_group_by, **kwargs
        )

    def resolve(self, prepared_results, required_computation_results: dict, current_pk, current_row=None) -> float:
        if not self.date_field:
            return 0
        return super().resolve(prepared_results, required_computation_results, current_pk, current_row)


field_registry.register(FirstBalanceField)


class TotalReportField(ComputationField):
    name = "__total__"
    verbose_name = _("Sum of value")
    requires = ["__debit__", "__credit__"]


field_registry.register(TotalReportField)


class BalanceReportField(ComputationField):
    name = "__balance__"
    verbose_name = _("Closing Total")
    requires = ["__fb__"]

    def resolve(self, prepared_results, required_computation_results: dict, current_pk, current_row=None) -> float:
        result = super().resolve(prepared_results, required_computation_results, current_pk, current_row)
        fb = required_computation_results.get("__fb__") or 0

        return result + fb


field_registry.register(BalanceReportField)


class PercentageToTotalBalance(ComputationField):
    requires = [BalanceReportField]
    name = "__percent_to_total_balance__"
    verbose_name = _("%")

    prevent_group_by = True

    def resolve(self, prepared_results, required_computation_results: dict, current_pk, current_row=None) -> float:
        result = super().resolve(prepared_results, required_computation_results, current_pk, current_row)
        return required_computation_results.get("__balance__") / result * 100


class CreditReportField(ComputationField):
    name = "__credit__"
    verbose_name = _("Credit")

    def resolve(self, prepared_results, required_computation_results: dict, current_pk, current_row=None) -> float:
        debit_value, credit_value = self.extract_data(prepared_results, current_pk)
        return credit_value


field_registry.register(CreditReportField)


@field_registry.register
class DebitReportField(ComputationField):
    name = "__debit__"
    verbose_name = _("Debit")

    def resolve(self, prepared_results, required_computation_results: dict, current_pk, current_row=None) -> float:
        debit_value, credit_value = self.extract_data(prepared_results, current_pk)
        return debit_value


@field_registry.register
class CreditQuantityReportField(ComputationField):
    name = "__credit_quantity__"
    verbose_name = _("Credit QTY")
    calculation_field = "quantity"
    is_summable = False

    def resolve(self, prepared_results, required_computation_results: dict, current_pk, current_row=None) -> float:
        debit_value, credit_value = self.extract_data(prepared_results, current_pk)
        return credit_value


@field_registry.register
class DebitQuantityReportField(ComputationField):
    name = "__debit_quantity__"
    calculation_field = "quantity"
    verbose_name = _("Debit QTY")
    is_summable = False

    def resolve(self, prepared_results, required_computation_results: dict, current_pk, current_row=None) -> float:
        debit_value, credit_value = self.extract_data(prepared_results, current_pk)
        return debit_value


class TotalQTYReportField(ComputationField):
    name = "__total_quantity__"
    verbose_name = _("Total QTY")
    calculation_field = "quantity"
    is_summable = False


field_registry.register(TotalQTYReportField)


class FirstBalanceQTYReportField(FirstBalanceField):
    name = "__fb_quantity__"
    verbose_name = _("Opening QTY")
    calculation_field = "quantity"
    is_summable = False


field_registry.register(FirstBalanceQTYReportField)


class BalanceQTYReportField(ComputationField):
    name = "__balance_quantity__"
    verbose_name = _("Closing QTY")
    calculation_field = "quantity"
    requires = ["__fb_quantity__"]
    is_summable = False

    def resolve(self, prepared_results, required_computation_results: dict, current_pk, current_row=None) -> float:
        result = super().resolve(prepared_results, required_computation_results, current_pk, current_row)
        fb = required_computation_results.get("__fb_quantity__") or 0
        return result + fb


field_registry.register(BalanceQTYReportField)


class SlickReportField(ComputationField):
    @staticmethod
    def warn():
        warn(
            "SlickReportField name is deprecated, please use ComputationField instead.",
            DeprecationWarning,
            stacklevel=2,
        )

    @classmethod
    def create(cls, method, field, name=None, verbose_name=None, is_summable=True):
        cls.warn()
        return super().create(method, field, name, verbose_name, is_summable)

    def __new__(cls, *args, **kwargs):
        cls.warn()
        return super().__new__(cls, *args, **kwargs)

import uuid

from django.db.models import Sum
from django.template.defaultfilters import date as date_filter
from django.utils.translation import gettext_lazy as _

from .helpers import get_calculation_annotation
from .registry import field_registry


class SlickReportField(object):
    """
    Computation field responsible for making the calculation unit
    """

    _field_registry = field_registry
    name = ''
    """The name to be used in the ReportGenerator"""

    calculation_field = 'value'
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

    type = 'number'
    """Just a string describing what this computation field return, usually passed to frontend"""

    is_summable = True
    """Indicate if this computation can be summed over. Useful to be passed to frontend or whenever needed"""

    report_model = None
    group_by = None
    plus_side_q = None
    minus_side_q = None

    _require_classes = None
    _debit_and_credit = True

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
            identifier = str(uuid.uuid4()).split('-')[-1]
            name = name or f"{method.name.lower()}__{field}"
            assert name not in cls._field_registry.get_all_report_fields_names()

        verbose_name = verbose_name or f'{method.name} {field}'
        report_klass = type(f'ReportField_{name}', (cls,), {
            'name': name,
            'verbose_name': verbose_name,
            'calculation_field': field,
            'calculation_method': method,
            'is_summable': is_summable,
        })
        return report_klass

    def __init__(self, plus_side_q=None, minus_side_q=None,
                 report_model=None,
                 qs=None,
                 calculation_field=None, calculation_method=None, date_field='', group_by=None):
        super(SlickReportField, self).__init__()
        self.date_field = date_field
        self.report_model = self.report_model or report_model
        self.calculation_field = calculation_field if calculation_field else self.calculation_field
        self.calculation_method = calculation_method if calculation_method else self.calculation_method
        self.plus_side_q = self.plus_side_q or plus_side_q
        self.minus_side_q = self.minus_side_q or minus_side_q
        self.requires = self.requires or []
        self.group_by = self.group_by or group_by
        self._cache = None, None, None
        self._require_classes = [field_registry.get_field_by_name(x) for x in self.requires]

        if not self.plus_side_q and not self.minus_side_q:
            self._debit_and_credit = False

    @classmethod
    def _get_required_classes(cls):
        requires = cls.requires or []
        return [field_registry.get_field_by_name(x) for x in requires]

    def apply_q_plus_filter(self, qs):
        return qs.filter(*self.plus_side_q)

    def apply_q_minus_filter(self, qs):
        return qs.filter(*self.minus_side_q)

    def apply_aggregation(self, queryset, group_by=''):
        annotation = self.calculation_method(self.calculation_field)
        if group_by:
            queryset = queryset.values(group_by).annotate(annotation)
        else:
            queryset = queryset.aggregate(annotation)
        return queryset

    def init_preparation(self, q_filters=None, kwargs_filters=None, **kwargs):
        """
        Called by the generator to preparet he calculation of this field + it's requirements
        :param q_filters:
        :param kwargs_filters:
        :param kwargs:
        :return:
        """
        kwargs_filters = kwargs_filters or {}

        dep_values = self._prepare_dependencies(q_filters, kwargs_filters.copy())

        debit_results, credit_results = self.prepare(q_filters, kwargs_filters, **kwargs)
        self._cache = debit_results, credit_results, dep_values

    def prepare(self, q_filters=None, kwargs_filters=None, **kwargs):
        """
        This is the first hook where you can customize the calculation away from the Django Query aggregation method
        This method et called with all available parameters , so you can prepare the results for the whole set and save
        it in a local cache (like self._cache) .
        The flow will later call the method `resolve`,  giving you the id, for you to return it respective calculation

        :param q_filters:
        :param kwargs_filters:
        :param kwargs:
        :return:
        """
        queryset = self.get_queryset()
        if q_filters:
            queryset = queryset.filter(*q_filters)
        if kwargs_filters:
            queryset = queryset.filter(**kwargs_filters)

        if self.plus_side_q:
            queryset = self.apply_q_plus_filter(queryset)
        debit_results = self.apply_aggregation(queryset, self.group_by)

        credit_results = None
        if self._debit_and_credit:
            queryset = self.get_queryset()
            if kwargs_filters:
                queryset = queryset.filter(**kwargs_filters)
            if q_filters:
                queryset = queryset.filter(*q_filters)
            if self.minus_side_q:
                queryset = self.apply_q_minus_filter(queryset)

            credit_results = self.apply_aggregation(queryset, self.group_by)

        return debit_results, credit_results

    def get_queryset(self):
        queryset = self.report_model.objects
        return queryset.order_by()

    def get_annotation_name(self):
        """
        Get the annotation per the database
        :return: string used ex:
        """
        return get_calculation_annotation(self.calculation_field, self.calculation_method)

    def _prepare_dependencies(self, q_filters=None, extra_filters=None, ):
        values = {}
        for dep_class in self._require_classes:
            dep = dep_class(self.plus_side_q, self.minus_side_q, self.report_model,
                            date_field=self.date_field, group_by=self.group_by)
            values[dep.name] = {'results': dep.init_preparation(q_filters, extra_filters),
                                'instance': dep}
        return values

    def resolve(self, current_obj, current_row=None):
        '''
        Reponsible for getting the exact data from the prepared value
        :param cached: the returned data from prepare
        :param current_obj: he value of group by id
        :param current_row: the row in iteration
        :return: a solid number or value
        '''
        cached = self._cache
        debit_value, credit_value = self.extract_data(cached, current_obj)
        dependencies_value = self._resolve_dependencies(current_obj)

        return self.final_calculation(debit_value, credit_value, dependencies_value)

    def get_dependency_value(self, current_obj, name=None):
        """
        Get the values of the ReportFields specified in `requires`

        :param current_obj: the current object which we want the calculation for
        :param name: Optional, the name of the specific dependency you want.

        :return: a dict containing dependencies names as keys and their calculation as values
                 or a specific value if name is specified.
        """
        values = self._resolve_dependencies(current_obj)
        if name:
            return values.get(name)
        return values

    def _resolve_dependencies(self, current_obj):

        dep_results = {}
        cached_debit, cached_credit, dependencies_value = self._cache
        dependencies_value = dependencies_value or {}
        for d in dependencies_value.keys():
            d_instance = dependencies_value[d]['instance']
            dep_results[d] = d_instance.resolve(current_obj)
        return dep_results

    def extract_data(self, cached, current_obj):
        group_by = self.group_by
        debit_value = 0
        credit_value = 0
        annotation = self.get_annotation_name()

        cached_debit, cached_credit, dependencies_value = cached

        if cached_debit or cached_credit:
            debit = None
            if cached_debit is not None:
                if not group_by:
                    x = list(cached_debit.keys())[0]
                    debit_value = cached_debit[x]
                else:
                    for i, x in enumerate(cached_debit):
                        if str(x[group_by]) == current_obj:
                            debit = cached_debit[i]
                            break
                    if debit:
                        debit_value = debit[annotation]

            if cached_credit is not None:
                credit = None
                if cached_credit is not None:
                    if not group_by:
                        x = list(cached_credit.keys())[0]
                        credit_value = cached_credit[x]
                    else:
                        for i, x in enumerate(cached_credit):
                            if str(x[group_by]) == current_obj:
                                credit = cached_credit[i]
                                break
                        if credit:
                            credit_value = credit[annotation]
        return debit_value, credit_value

    def final_calculation(self, debit, credit, dep_dict):
        debit = debit or 0
        credit = credit or 0
        return debit - credit

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
        if id == '----':
            return _('The reminder')
        return f'{cls.verbose_name} {model} {id}'

    @classmethod
    def get_time_series_field_verbose_name(cls, date_period, index, dates, pattern):
        """
        Get the name of the verbose name of a computaion field that's in a time_series.
        should be a mix of the date period if the column an it's verbose name.
        :param date_period: a tuple of (start_date, end_date)
        :param index: the index of the current field in the whole dates to be calculated
        :param dates a list of tuples representing the start and the end date
        :return: a verbose string
        """
        dt_format = '%Y/%m/%d'

        if pattern == 'monthly':
            month_name = date_filter(date_period[0], 'F Y')
            return f'{cls.verbose_name} {month_name}'
        elif pattern == 'daily':
            return f'{cls.verbose_name} {date_period[0].strftime(dt_format)}'
        elif pattern == 'weekly':
            return f' {cls.verbose_name} {_("Week")} {index} {date_period[0].strftime(dt_format)}'
        elif pattern == 'yearly':
            year = date_filter(date_period[0], 'Y')
            return f'{cls.verbose_name} {year}'

        return f'{cls.verbose_name} {date_period[0].strftime(dt_format)} - {date_period[1].strftime(dt_format)}'


class FirstBalanceField(SlickReportField):
    name = '__fb__'
    verbose_name = _('first balance')

    def prepare(self, q_filters=None, extra_filters=None, **kwargs):
        extra_filters = extra_filters or {}

        from_date_value = extra_filters.get(f'{self.date_field}__gt')
        extra_filters.pop(f'{self.date_field}__gt', None)
        extra_filters[f'{self.date_field}__lte'] = from_date_value
        return super(FirstBalanceField, self).prepare(q_filters, extra_filters)


field_registry.register(FirstBalanceField)


class TotalReportField(SlickReportField):
    name = '__total__'
    verbose_name = _('Sum of value')
    requires = ['__debit__', '__credit__']


field_registry.register(TotalReportField)


class BalanceReportField(SlickReportField):
    name = '__balance__'
    verbose_name = _('Cumulative Total')
    requires = ['__fb__']

    def final_calculation(self, debit, credit, dep_dict):
        fb = dep_dict.get('__fb__')
        debit = debit or 0
        credit = credit or 0
        fb = fb or 0
        return fb + debit - credit


field_registry.register(BalanceReportField)


class CreditReportField(SlickReportField):
    name = '__credit__'
    verbose_name = _('Credit')

    def final_calculation(self, debit, credit, dep_dict):
        return credit


field_registry.register(CreditReportField)


class DebitReportField(SlickReportField):
    name = '__debit__'
    verbose_name = _('Debit')

    def final_calculation(self, debit, credit, dep_dict):
        return debit


field_registry.register(DebitReportField)


class TotalQTYReportField(SlickReportField):
    name = '__total_quantity__'
    verbose_name = _('Total QTY')
    calculation_field = 'quantity'
    is_summable = False


field_registry.register(TotalQTYReportField)


class FirstBalanceQTYReportField(FirstBalanceField):
    name = '__fb_quan__'
    verbose_name = _('starting QTY')
    calculation_field = 'quantity'
    is_summable = False


field_registry.register(FirstBalanceQTYReportField)


class BalanceQTYReportField(SlickReportField):
    name = '__balance_quantity__'
    verbose_name = _('Cumulative QTY')
    calculation_field = 'quantity'
    requires = ['__fb_quan__']

    def final_calculation(self, debit, credit, dep_dict):
        # Use `get` so it fails loud if its not there
        fb = dep_dict.get('__fb_quan__')
        fb = fb or 0
        return fb + debit - credit


field_registry.register(BalanceQTYReportField)

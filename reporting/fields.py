from __future__ import unicode_literals

from django.db.models import Sum
from django.utils.translation import ugettext_lazy as _

from .helpers import get_calculation_annotation
from .decorators import report_field_register
from .registry import field_registry


class BaseReportField(object):
    # date_field = 'doc_date'
    plus_minus_modifier_field = 'doc_type'
    calculation_field = 'value'
    calculation_method = Sum
    report_model = None
    plus_side_q = None
    minus_side_q = None
    _debit_and_credit = True
    component_of = None
    name = None
    verbose_name = None
    type = 'date'
    requires = None
    _require_classes = None

    group_by = None

    def __init__(self, plus_side_q=None, minus_side_q=None,
                 report_model=None,
                 qs=None,
                 calculation_field=None, calculation_method=None, date_field='', group_by=None):
        super(BaseReportField, self).__init__()
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

    def prepare(self, q_filters=None, kwargs_filters=None, **kwargs):
        kwargs_filters = kwargs_filters or {}

        dep_values = self._prepare_dependencies(q_filters, kwargs_filters.copy())

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

        self._cache = debit_results, credit_results, dep_values
        return debit_results, credit_results, dep_values

    def get_queryset(self):
        queryset = self.report_model.objects
        return queryset

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
            values[dep.name] = {'results': dep.prepare(q_filters, extra_filters),
                                'instance': dep}
        return values

    def resolve(self, current_obj):
        '''
        Reponsible for getting the exact data from the prepared value
        :param cached: the returned data from prepare
        :param current_obj:
        :return: a solid number or value
        '''
        cached = self._cache
        debit_value, credit_value = self.extract_data(cached, current_obj)
        dependencies_value = self._resolve_dependencies(current_obj)

        return self.final_calculation(debit_value, credit_value, dependencies_value)

    def get_dependency_value(self, current_obj, name=None):
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
                    x = cached_debit.keys()[0]
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
                        x = cached_credit.keys()[0]
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


class FirstBalanceField(BaseReportField):
    name = '__fb__'
    verbose_name = _('first balance')

    def prepare(self, q_filters=None, extra_filters=None, **kwargs):
        extra_filters = extra_filters or {}

        from_date_value = extra_filters.get(f'{self.date_field}__gt')
        extra_filters.pop(f'{self.date_field}__gt', None)
        extra_filters[f'{self.date_field}__lte'] = from_date_value
        return super(FirstBalanceField, self).prepare(q_filters, extra_filters)


field_registry.register(FirstBalanceField)


class TotalReportField(BaseReportField):
    name = '__total__'
    verbose_name = _('total')
    requires = ['__debit__', '__credit__']


field_registry.register(TotalReportField)


class BalanceReportField(BaseReportField):
    name = '__balance__'
    verbose_name = _('balance')
    requires = ['__fb__']

    def final_calculation(self, debit, credit, dep_dict):
        fb = dep_dict.get('__fb__')
        debit = debit or 0
        credit = credit or 0
        fb = fb or 0
        return fb + debit - credit


field_registry.register(BalanceReportField)


class CreditReportField(BaseReportField):
    name = '__credit__'
    verbose_name = _('credit')

    def final_calculation(self, debit, credit, dep_dict):
        return credit


field_registry.register(CreditReportField)


class DebitReportField(BaseReportField):
    name = '__debit__'
    verbose_name = _('debit')

    def final_calculation(self, debit, credit, dep_dict):
        return debit


field_registry.register(DebitReportField)


@report_field_register
class DocCount(BaseReportField):
    name = '__doc_count__'
    verbose_name = _('document count')


@report_field_register
class LineCount(BaseReportField):
    name = '__line_count__'
    verbose_name = 'Line Count'


# @report_field_register
# class DocValue

class TotalQTYReportField(BaseReportField):
    name = '__total_quan__'
    verbose_name = _('total QTY')
    calculation_field = 'quantity'


field_registry.register(TotalQTYReportField)


class FirstBalanceQTYReportField(FirstBalanceField):
    name = '__fb_quan__'
    verbose_name = _('first balance QTY')
    calculation_field = 'quantity'


field_registry.register(FirstBalanceQTYReportField)


class BalanceQTYReportField(BaseReportField):
    name = '__balance_quan__'
    verbose_name = _('balance QTY')
    calculation_field = 'quantity'
    requires = ['__fb_quan__']

    def final_calculation(self, debit, credit, dep_dict):
        # Use `get` so it fails loud if its not there
        fb = dep_dict.get('__fb_quan__')
        fb = fb or 0
        return fb + debit - credit


field_registry.register(BalanceQTYReportField)

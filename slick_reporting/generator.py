import datetime
import logging
from dataclasses import dataclass
from inspect import isclass

from django.core.exceptions import ImproperlyConfigured, FieldDoesNotExist
from django.db.models import Q, ForeignKey

from .app_settings import SLICK_REPORTING_DEFAULT_CHARTS_ENGINE
from .fields import ComputationField
from .helpers import get_field_from_query_text
from .registry import field_registry
from . import app_settings

logger = logging.getLogger(__name__)


@dataclass
class Chart:
    title: str
    type: str
    data_source: list
    title_source: list
    plot_total: bool = False
    stacking: bool = False  # only for highcharts
    engine: str = ""
    entryPoint: str = ""
    COLUMN = "column"
    LINE = "line"
    PIE = "pie"
    BAR = "bar"
    AREA = "area"

    def to_dict(self):
        return dict(
            title=self.title,
            type=self.type,
            data_source=self.data_source,
            title_source=self.title_source,
            plot_total=self.plot_total,
            engine=self.engine,
            entryPoint=self.entryPoint,
            stacking=self.stacking,
        )


class ReportGeneratorAPI:
    report_model = None
    """The main model where data is """

    queryset = None
    """If set, the report will use this queryset instead of the report_model"""

    """
    Class to generate a Json Object containing report data.
    """
    date_field = ""
    """Main date field to use whenever date filter is needed"""

    start_date_field_name = None
    """If set, the report will use this field to filter the start date, default to date_field"""

    end_date_field_name = None
    """If set, the report will use this field to filter the end date, default to date_field"""

    print_flag = None

    group_by = None
    """The field to use for grouping, if not set then the report is expected to be a sub version of the report model"""

    group_by_custom_querysets = None
    """A List of querysets representing different group by options"""
    group_by_custom_querysets_column_verbose_name = None

    columns = None
    """A list of column names.
    Columns names can be 

    1. A Computation Field

    2. If group_by is set, then any field on the group_by model

    3. If group_by is not set, then any field name on the report_model / queryset

    4. A callable on the generator

    5. Special __time_series__, and __crosstab__ 
       Those can be use to control the position of the time series inside the columns, defaults it's appended at the end

       Example:
       columns = ['product_id', '__time_series__', 'col_b']
       Same is true with __crosstab__ 

    You can customize aspects of the column by adding it as a tuple like this 
        ('field_name', dict(verbose_name=_('My Enhanced Verbose_name'))


     """

    time_series_pattern = ""
    """
    If set the Report will compute a time series.

    Possible options are: daily, weekly, semimonthly, monthly, quarterly, semiannually, annually and custom.

    if `custom` is set, you'd need to override  `get_custom_time_series_dates`
    """
    time_series_columns = None
    """
    a list of Calculation Field names which will be included in the series calculation.
     Example: ['__total__', '__total_quantity__'] with compute those 2 fields for all the series

    """

    time_series_custom_dates = None
    """
    Used with `time_series_pattern` set to 'custom'
    It's a list of tuple, each tuple represent start date & end date
    Example: [ (start_date_1, end_date_1), (start_date_2, end_date_2), ....]
    """

    crosstab_model = None  # deprecated

    crosstab_field = None
    """
    If set, a cross tab over this model selected ids (via `crosstab_ids`)  
    """

    crosstab_columns = None
    """The computation fields which will be computed for each crosstab-ed ids """

    crosstab_ids = None
    """A list is the ids to create a crosstab report on"""

    crosstab_ids_custom_filters = None

    crosstab_compute_remainder = True
    """Include an an extra crosstab_columns for the outer group ( ie: all expects those `crosstab_ids`) """

    limit_records = None
    """Serves are a main limit to  the returned data of the report_model.
    Can be beneficial if the results may be huge.
    """
    swap_sign = False


class ReportGenerator(ReportGeneratorAPI, object):
    """
    The main class responsible generating the report and managing the flow
    """

    field_registry_class = field_registry
    """You can have a custom computation field locator! It only needs a `get_field_by_name(string)` 
    and returns a ReportField`"""

    def __init__(
        self,
        report_model=None,
        main_queryset=None,
        start_date=None,
        end_date=None,
        date_field=None,
        q_filters=None,
        kwargs_filters=None,
        group_by=None,
        group_by_custom_querysets=None,
        group_by_custom_querysets_column_verbose_name=None,
        columns=None,
        time_series_pattern=None,
        time_series_columns=None,
        time_series_custom_dates=None,
        crosstab_field=None,
        crosstab_columns=None,
        crosstab_ids=None,
        crosstab_ids_custom_filters=None,
        crosstab_compute_remainder=None,
        swap_sign=False,
        show_empty_records=None,
        print_flag=False,
        doc_type_plus_list=None,
        doc_type_minus_list=None,
        limit_records=False,
        format_row_func=None,
        container_class=None,
        start_date_field_name=None,
        end_date_field_name=None,
    ):
        """

        :param report_model: Main model containing the data
        :param main_queryset: Default to report_model.objects
        :param start_date:
        :param end_date:
        :param date_field:
        :param q_filters:
        :param kwargs_filters:
        :param group_by:
        :param columns:
        :param time_series_pattern:
        :param time_series_columns:
        :param crosstab_model:
        :param crosstab_columns:
        :param crosstab_ids:
        :param crosstab_compute_remainder:
        :param swap_sign:
        :param show_empty_records:
        :param base_model:
        :param print_flag:
        :param doc_type_plus_list:
        :param doc_type_minus_list:
        :param limit_records:
        """
        from .app_settings import (
            SLICK_REPORTING_DEFAULT_START_DATE,
            SLICK_REPORTING_DEFAULT_END_DATE,
        )

        super().__init__()

        self.report_model = self.report_model or report_model
        if self.queryset is None:
            self.queryset = main_queryset

        if not self.report_model and self.queryset is None:
            raise ImproperlyConfigured("report_model or queryset must be set on a class level or via init")

        main_queryset = self.report_model.objects if self.queryset is None else self.queryset

        self.start_date = start_date or datetime.datetime.combine(
            SLICK_REPORTING_DEFAULT_START_DATE.date(),
            SLICK_REPORTING_DEFAULT_START_DATE.time(),
        )

        self.end_date = end_date or datetime.datetime.combine(
            SLICK_REPORTING_DEFAULT_END_DATE.date(),
            SLICK_REPORTING_DEFAULT_END_DATE.time(),
        )
        self.date_field = self.date_field or date_field

        self.start_date_field_name = self.start_date_field_name or start_date_field_name or self.date_field
        self.end_date_field_name = self.end_date_field_name or end_date_field_name or self.date_field

        self.q_filters = q_filters or []
        self.kwargs_filters = kwargs_filters or {}
        self.crosstab_field = self.crosstab_field or crosstab_field

        self.crosstab_columns = crosstab_columns or self.crosstab_columns or []
        self.crosstab_ids = self.crosstab_ids or crosstab_ids or []
        self.crosstab_ids_custom_filters = self.crosstab_ids_custom_filters or crosstab_ids_custom_filters or []

        self.crosstab_compute_remainder = (
            self.crosstab_compute_remainder if crosstab_compute_remainder is None else crosstab_compute_remainder
        )

        self.format_row = format_row_func or self._default_format_row

        main_queryset = self.report_model.objects if main_queryset is None else main_queryset
        # todo revise & move somewhere nicer, List Report need to override the resetting of order
        main_queryset = self._remove_order(main_queryset)

        self.columns = columns or self.columns or []
        self.group_by = group_by or self.group_by

        self.group_by_custom_querysets = group_by_custom_querysets or self.group_by_custom_querysets or []

        self.group_by_custom_querysets_column_verbose_name = (
            group_by_custom_querysets_column_verbose_name or self.group_by_custom_querysets_column_verbose_name or ""
        )
        self.time_series_pattern = self.time_series_pattern or time_series_pattern
        self.time_series_columns = self.time_series_columns or time_series_columns
        self.time_series_custom_dates = self.time_series_custom_dates or time_series_custom_dates
        self.container_class = container_class

        if (
            not (self.date_field or (self.start_date_field_name and self.end_date_field_name))
            and self.time_series_pattern
        ):
            raise ImproperlyConfigured(
                f"date_field or [start_date_field_name and end_date_field_name] must "
                f"be set for {container_class or self}"
            )

        self._prepared_results = {}
        self.report_fields_classes = {}

        self._report_fields_dependencies = {
            "time_series": {},
            "crosstab": {},
            "normal": {},
        }
        self.existing_dependencies = {"series": [], "matrix": [], "normal": []}

        self.print_flag = print_flag or self.print_flag

        # todo validate columns is not empty (if no time series / cross tab)

        if self.group_by:
            try:
                self.group_by_field = get_field_from_query_text(self.group_by, self.report_model)

            except (IndexError, AttributeError):
                raise ImproperlyConfigured(
                    f"Can not find group_by field:{self.group_by} in report_model {self.report_model} "
                )
            if "__" not in self.group_by:
                self.group_by_field_attname = self.group_by_field.attname
            else:
                self.group_by_field_attname = self.group_by

        else:
            self.group_by_field_attname = None

        # doc_types = form.get_doc_type_plus_minus_lists()
        doc_types = [], []
        self.doc_type_plus_list = list(doc_type_plus_list) if doc_type_plus_list else doc_types[0]
        self.doc_type_minus_list = list(doc_type_minus_list) if doc_type_minus_list else doc_types[1]

        self.swap_sign = self.swap_sign or swap_sign
        self.limit_records = self.limit_records or limit_records

        # todo delete this
        self.show_empty_records = False  # show_empty_records if show_empty_records else self.show_empty_records

        # Preparing actions
        self._parse()

        self.main_queryset = self.prepare_queryset(main_queryset)
        self._prepare_report_dependencies()

    def prepare_queryset(self, queryset):
        if self.group_by_custom_querysets:
            return [{"__index__": i} for i, v in enumerate(self.group_by_custom_querysets)]
        elif self.group_by:
            main_queryset = self._apply_queryset_options(queryset)

            if type(self.group_by_field) is ForeignKey:
                ids = main_queryset.values_list(self.group_by_field_attname).distinct()
                # uses the same logic that is in Django's query.py when fields is empty in values() call
                concrete_fields = [f.name for f in self.group_by_field.related_model._meta.concrete_fields]
                # add database columns that are not already in concrete_fields
                final_fields = concrete_fields + list(set(self.get_database_columns()) - set(concrete_fields))
                return self.group_by_field.related_model.objects.filter(
                    **{f"{self.group_by_field.target_field.name}__in": ids}
                ).values(*final_fields)
            else:
                return main_queryset.distinct().values(self.group_by_field_attname)

        return [{}]

    def _remove_order(self, main_queryset):
        """
        Remove order_by from the main queryset
        :param main_queryset:
        :return:
        """
        # if main_queryset.query.order_by:
        main_queryset = main_queryset.order_by()
        return main_queryset

    def _apply_queryset_options(self, query, fields=None):
        """
        Apply the filters to the main queryset which will computed results be mapped to
        :param query:
        :param fields:
        :return:
        """
        filters = {}
        if self.date_field:
            filters = {
                f"{self.start_date_field_name}__gt": self.start_date,
                f"{self.end_date_field_name}__lte": self.end_date,
            }
        filters.update(self.kwargs_filters)

        if filters:
            query = query.filter(**filters)
        if self.q_filters:
            query = query.filter(*self.q_filters)
        if fields:
            return query.values(*fields)
        return query.values()

    def _construct_crosstab_filter(self, col_data, queryset_filters=None):
        """
        In charge of adding the needed crosstab filter, specific to the case of is_remainder or not
        :param col_data:
        :return:
        """
        if queryset_filters:
            return queryset_filters[0], queryset_filters[1]

        if "__" in col_data["crosstab_field"]:
            column_name = col_data["crosstab_field"]
        else:
            field = get_field_from_query_text(col_data["crosstab_field"], self.report_model)
            column_name = field.column
        if col_data["is_remainder"] and not queryset_filters:
            filters = [~Q(**{f"{column_name}__in": self.crosstab_ids})]
        else:
            filters = [Q(**{f"{column_name}": col_data["id"]})]
        return filters, {}

    def _prepare_report_dependencies(self):
        from .fields import ComputationField

        all_columns = (
            ("normal", self._parsed_columns),
            ("time_series", self._time_series_parsed_columns),
            ("crosstab", self._crosstab_parsed_columns),
        )
        for window, window_cols in all_columns:
            for col_data in window_cols:
                klass = col_data["ref"]

                if isclass(klass) and issubclass(klass, ComputationField):
                    dependencies_names = klass.get_full_dependency_list()

                    # check if any of these dependencies is on the report, if found we call the child to
                    # resolve the value for its parent avoiding extra database call
                    fields_on_report = [
                        x
                        for x in window_cols
                        if x["ref"] in dependencies_names
                        and (
                            (
                                window == "time_series"
                                and x.get("start_date", "") == col_data.get("start_date", "")
                                and x.get("end_date") == col_data.get("end_date")
                            )
                            or window == "crosstab"
                            and x.get("id") == col_data.get("id")
                        )
                    ]
                    for field in fields_on_report:
                        self._report_fields_dependencies[window][field["name"]] = col_data["name"]
            for col_data in window_cols:
                klass = col_data["ref"]
                name = col_data["name"]

                # if column has a dependency then skip it
                if not (isclass(klass) and issubclass(klass, ComputationField)):
                    continue
                if self._report_fields_dependencies[window].get(name, False):
                    continue

                report_class = klass(
                    self.doc_type_plus_list,
                    self.doc_type_minus_list,
                    group_by=self.group_by,
                    report_model=self.report_model,
                    date_field=self.date_field,
                    queryset=self.queryset,
                    group_by_custom_querysets=self.group_by_custom_querysets,
                )

                q_filters = None
                date_filter = {}
                if self.start_date_field_name:
                    date_filter[f"{self.start_date_field_name}__gte"] = col_data.get("start_date", self.start_date)
                if self.end_date_field_name:
                    date_filter[f"{self.end_date_field_name}__lt"] = col_data.get("end_date", self.end_date)

                date_filter.update(self.kwargs_filters)
                if window == "crosstab" or col_data.get("computation_flag", "") == "crosstab":
                    q_filters, kw_filters = col_data["queryset_filters"]
                    date_filter.update(kw_filters)

                report_class.init_preparation(q_filters, date_filter)
                self.report_fields_classes[name] = report_class

    # @staticmethod
    def get_primary_key_name(self, model):
        if self.group_by_custom_querysets:
            return "__index__"
        for field in model._meta.fields:
            if field.primary_key:
                return field.attname
        return ""

    def _get_record_data(self, obj, columns):
        """
        the function is run for every obj in the main_queryset
        :param obj: current row
        :param: columns： The columns we iterate on
        :return: a dict object containing all needed data
        """

        data = {}
        group_by_val = None
        if self.group_by_custom_querysets:
            group_by_val = str(obj["__index__"])

        elif self.group_by:
            if self.group_by_field.related_model and "__" not in self.group_by:
                primary_key_name = self.get_primary_key_name(self.group_by_field.related_model)
            else:
                primary_key_name = self.group_by_field_attname

            column_data = obj.get(primary_key_name, obj.get("id"))
            group_by_val = str(column_data)

        for window, window_cols in columns:
            for col_data in window_cols:
                name = col_data["name"]

                if col_data.get("source", "") == "attribute_field":
                    data[name] = col_data["ref"](obj, data)
                elif col_data.get("source", "") == "container_class_attribute_field":
                    data[name] = col_data["ref"](obj, data)

                elif (
                    col_data.get("source", "") == "magic_field" and (self.group_by or self.group_by_custom_querysets)
                ) or (not (self.group_by or self.group_by_custom_querysets)):
                    source = self._report_fields_dependencies[window].get(name, False)

                    if source:
                        computation_class = self.report_fields_classes[source]
                        # the computation field is being asked from another computation field that requires it.
                        value = computation_class.get_dependency_value(group_by_val, col_data["ref"].name)
                    else:
                        try:
                            computation_class = self.report_fields_classes[name]
                        except KeyError:
                            continue
                        value = computation_class.do_resolve(group_by_val, data)
                    if self.swap_sign:
                        value = -value
                    data[name] = value

                else:
                    data[name] = obj.get(name, "")
        return data

    def get_report_data(self):
        main_queryset = self.main_queryset[: self.limit_records] if self.limit_records else self.main_queryset

        all_columns = (
            ("normal", self._parsed_columns),
            ("time_series", self._time_series_parsed_columns),
            ("crosstab", self._crosstab_parsed_columns),
        )

        get_record_data = self._get_record_data
        format_row = self.format_row
        data = [format_row(get_record_data(obj, all_columns)) for obj in main_queryset]
        return data

    def _default_format_row(self, row_obj):
        """
        Hook where you can format row values like properly format a date
        :param row_obj:
        :return:
        """
        return row_obj

    @staticmethod
    def check_columns(
        cls,
        columns,
        group_by,
        report_model,
        container_class=None,
        group_by_custom_querysets=None,
    ):
        """
        Check and parse the columns, throw errors in case an item in the columns cant not identified
        :param columns: List of columns
        :param group_by: group by field if any
        :param report_model: the report model
        :param container_class: a class to search for custom columns attribute in, typically the ReportView
        :param group_by_custom_querysets a list of group by custom queries Or None.
        :return: List of dict, each dict contains relevant data to the respective field in `columns`
        """

        group_by_model = None
        if group_by_custom_querysets:
            if "__index__" not in columns:
                columns.insert(0, "__index__")

        if group_by:
            try:
                group_by_field = [x for x in report_model._meta.get_fields() if x.name == group_by.split("__")[0]][0]
            except IndexError:
                raise ImproperlyConfigured(
                    f"ReportView {cls}: Could not find the group_by field: `{group_by}` in "
                    f"report_model: `{report_model}`"
                )
            if group_by_field.is_relation:
                group_by_model = group_by_field.related_model
            else:
                group_by_model = report_model

        parsed_columns = []
        for col in columns:
            options = {}
            if type(col) is tuple:
                col, options = col

            if col in ["__time_series__", "__crosstab__"]:
                #     These are placeholder not real computation field
                continue

            magic_field_class = None
            attribute_field = None
            is_container_class_attribute = False

            if isinstance(col, str):
                attribute_field = getattr(cls, col, None)
                if attribute_field is None:
                    is_container_class_attribute = True
                    attribute_field = getattr(container_class, col, None)

            elif issubclass(col, ComputationField):
                magic_field_class = col

            try:
                magic_field_class = magic_field_class or field_registry.get_field_by_name(col)
            except KeyError:
                magic_field_class = None

            if attribute_field:
                col_data = {
                    "name": col,
                    "verbose_name": getattr(attribute_field, "verbose_name", col),
                    "source": "container_class_attribute_field" if is_container_class_attribute else "attribute_field",
                    "ref": attribute_field,
                    "type": "text",
                }
            elif magic_field_class:
                # a magic field
                col_data = {
                    "name": magic_field_class.name,
                    "verbose_name": magic_field_class.verbose_name,
                    "source": "magic_field",
                    "ref": magic_field_class,
                    "type": magic_field_class.type,
                    "is_summable": magic_field_class.is_summable,
                }
            else:
                # A database field
                if group_by_custom_querysets and col == "__index__":
                    # group by custom queryset special case: which is the index
                    col_data = {
                        "name": col,
                        "verbose_name": cls.group_by_custom_querysets_column_verbose_name,
                        "source": "database",
                        "ref": "",
                        "type": "text",
                    }
                    col_data.update(options)
                    parsed_columns.append(col_data)
                    continue

                model_to_use = group_by_model if group_by and "__" not in group_by else report_model
                group_by_str = str(group_by)
                if "__" in group_by_str:
                    related_model = get_field_from_query_text(group_by, model_to_use).related_model
                    model_to_use = related_model if related_model else model_to_use

                try:
                    if "__" in col:
                        # A traversing link order__client__email
                        field = get_field_from_query_text(col, model_to_use)
                    else:
                        field = model_to_use._meta.get_field(col)
                except FieldDoesNotExist:
                    field = getattr(container_class, col, False)

                    if not field:
                        raise FieldDoesNotExist(
                            f'Field "{col}" not found either as an attribute to the generator class {cls}, '
                            f'{f"Container class {container_class}," if container_class else ""}'
                            f'or a computation field, or a database column for the model "{model_to_use}"'
                        )

                col_data = {
                    "name": col,
                    "verbose_name": getattr(field, "verbose_name", col),
                    "source": "database",
                    "ref": field,
                    "type": "choice" if field.choices else field.get_internal_type(),
                }
            col_data.update(options)
            parsed_columns.append(col_data)
        return parsed_columns

    def _parse(self):
        self.parsed_columns = self.check_columns(
            self,
            self.columns,
            self.group_by,
            self.report_model,
            self.container_class,
            self.group_by_custom_querysets,
        )
        self._parsed_columns = list(self.parsed_columns)
        self._crosstab_parsed_columns = self.get_crosstab_parsed_columns()
        self._time_series_parsed_columns = self.get_time_series_parsed_columns()

    def get_database_columns(self):
        return [col["name"] for col in self.parsed_columns if "source" in col and col["source"] == "database"]

    # def get_method_columns(self):
    #     return [col['name'] for col in self.parsed_columns if col['type'] == 'method']

    def get_list_display_columns(self):
        columns = self.parsed_columns
        if self.time_series_pattern:
            time_series_columns = self.get_time_series_parsed_columns()
            try:
                index = self.columns.index("__time_series__")
                columns[index:index] = time_series_columns
            except ValueError:
                columns += time_series_columns

        if self.crosstab_field:
            crosstab_columns = self.get_crosstab_parsed_columns()

            try:
                index = self.columns.index("__crosstab__")
                columns[index:index] = crosstab_columns
            except ValueError:
                columns += crosstab_columns

        return columns

    def get_time_series_parsed_columns(self):
        """
        Return time series columns with all needed data attached
        :param plain: if True it returns '__total__' instead of '__total_TS011212'
        :return: List if columns
        """
        _values = []

        cols = self.time_series_columns or []
        series = self._get_time_series_dates(self.time_series_pattern)

        for index, dt in enumerate(series):
            for col in cols:
                magic_field_class = None

                if isinstance(col, str):
                    magic_field_class = field_registry.get_field_by_name(col)
                elif issubclass(col, ComputationField):
                    magic_field_class = col

                _values.append(
                    {
                        "name": magic_field_class.name + "TS" + dt[1].strftime("%Y%m%d"),
                        "original_name": magic_field_class.name,
                        "verbose_name": self.get_time_series_field_verbose_name(magic_field_class, dt, index, series),
                        "ref": magic_field_class,
                        "start_date": dt[0],
                        "end_date": dt[1],
                        "source": "magic_field" if magic_field_class else "",
                        "is_summable": magic_field_class.is_summable,
                    }
                )

            # append the crosstab fields, if they exist, on the time_series
            if self._crosstab_parsed_columns:
                for parsed_col in self._crosstab_parsed_columns:
                    parsed_col = parsed_col.copy()
                    parsed_col["name"] = parsed_col["name"] + "TS" + dt[1].strftime("%Y%m%d")
                    parsed_col["start_date"] = dt[0]
                    parsed_col["end_date"] = dt[1]
                    _values.append(parsed_col)

        return _values

    def get_time_series_field_verbose_name(self, computation_class, date_period, index, series, pattern=None):
        """
        Sent the column data to construct a verbose name.
        Default implementation is delegated to the ReportField.get_time_series_field_verbose_name
        (which is  name + the end date %Y%m%d)

        :param computation_class: the computation field_name
        :param date_period: a tuple of (start_date, end_date)
        :return: a verbose string
        """
        pattern = pattern or self.time_series_pattern
        return computation_class.get_time_series_field_verbose_name(date_period, index, series, pattern)

    def get_custom_time_series_dates(self):
        """
        Hook to get custom , maybe separated date periods
        :return: [ (date1,date2) , (date3,date4), .... ]
        """
        return self.time_series_custom_dates or []

    def _get_time_series_dates(self, series=None, start_date=None, end_date=None):
        from dateutil.relativedelta import relativedelta

        series = series or self.time_series_pattern
        start_date = start_date or self.start_date
        end_date = end_date or self.end_date
        _values = []

        if series:
            if series == "daily":
                time_delta = datetime.timedelta(days=1)
            elif series == "weekly":
                time_delta = relativedelta(weeks=1)
            elif series == "bi-weekly":
                time_delta = relativedelta(weeks=2)
            elif series == "monthly":
                time_delta = relativedelta(months=1)
            elif series == "quarterly":
                time_delta = relativedelta(months=3)
            elif series == "semiannually":
                time_delta = relativedelta(months=6)
            elif series == "annually":
                time_delta = relativedelta(years=1)
            elif series == "custom":
                return self.get_custom_time_series_dates()
            else:
                raise NotImplementedError(f'"{series}" is not implemented for time_series_pattern')

            done = False

            while not done:
                to_date = start_date + time_delta
                _values.append((start_date, to_date))
                start_date = to_date
                if to_date >= end_date:
                    done = True
        return _values

    def get_crosstab_parsed_columns(self):
        """
        Return a list of the columns analyzed , with reference to computation field and everything
        :return:
        """
        report_columns = self.crosstab_columns or []

        ids = list(self.crosstab_ids) or list(self.crosstab_ids_custom_filters)
        if self.crosstab_compute_remainder and not self.crosstab_ids_custom_filters:
            ids.append("----")
        output_cols = []

        ids_length = len(ids) - 1
        for counter, crosstab_id in enumerate(ids):
            queryset_filters = None

            if self.crosstab_ids_custom_filters:
                queryset_filters = crosstab_id
                crosstab_id = counter

            for col in report_columns:
                magic_field_class = None
                if isinstance(col, str):
                    magic_field_class = field_registry.get_field_by_name(col)
                elif issubclass(col, ComputationField):
                    magic_field_class = col

                crosstab_column = {
                    "name": f"{magic_field_class.name}CT{crosstab_id}",
                    "original_name": magic_field_class.name,
                    "verbose_name": self.get_crosstab_field_verbose_name(
                        magic_field_class, self.crosstab_field, crosstab_id
                    ),
                    "ref": magic_field_class,
                    "id": crosstab_id,
                    "crosstab_field": self.crosstab_field,
                    "is_remainder": counter == ids_length if self.crosstab_compute_remainder else False,
                    "source": "magic_field" if magic_field_class else "",
                    "is_summable": magic_field_class.is_summable,
                    "computation_flag": "crosstab",  # a flag, todo find a better way probably
                }
                crosstab_column["queryset_filters"] = self._construct_crosstab_filter(crosstab_column, queryset_filters)

                output_cols.append(crosstab_column)

        return output_cols

    def get_crosstab_field_verbose_name(self, computation_class, model, id):
        """
        Hook to change the crosstab field verbose name, default it delegate this function to the ReportField
        :param computation_class: ReportField Class
        :param model: the model name as string
        :param id: the current crosstab id
        :return: a verbose string
        """
        return computation_class.get_crosstab_field_verbose_name(model, id)

    def get_metadata(self):
        """
        A hook to send data about the report for front end which can later be used in charting
        :return:
        """
        time_series_columns = self.get_time_series_parsed_columns()
        crosstab_columns = self.get_crosstab_parsed_columns()
        metadata = {
            "time_series_pattern": self.time_series_pattern,
            "time_series_column_names": [x["name"] for x in time_series_columns],
            "time_series_column_verbose_names": [x["verbose_name"] for x in time_series_columns],
            "crosstab_model": self.crosstab_field or "",
            "crosstab_column_names": [x["name"] for x in crosstab_columns],
            "crosstab_column_verbose_names": [x["verbose_name"] for x in crosstab_columns],
        }
        return metadata

    def get_columns_data(self):
        """
        Hook to get the columns information to front end
        :param columns:
        :return:
        """
        columns = self.get_list_display_columns()
        data = []

        for col in columns:
            data.append(
                {
                    "name": col["name"],
                    "computation_field": col.get("original_name", ""),
                    "verbose_name": col["verbose_name"],
                    "visible": col.get("visible", True),
                    "type": col.get("type", "text"),
                    "is_summable": col.get("is_summable", ""),
                }
            )
        return data

    def get_full_response(
        self, data=None, report_slug=None, chart_settings=None, default_chart_title=None, default_chart_engine=None
    ):
        data = data or self.get_report_data()
        data = {
            "report_slug": report_slug or self.__class__.__name__,
            "data": data,
            "columns": self.get_columns_data(),
            "metadata": self.get_metadata(),
            "chart_settings": self.get_chart_settings(
                chart_settings, default_chart_title=default_chart_title, chart_engine=default_chart_engine
            ),
        }
        return data

    @staticmethod
    def get_chart_settings(chart_settings=None, default_chart_title=None, chart_engine=None):
        """
        Ensure the sane settings are passed to the front end. ?
        """
        chart_engine = chart_engine or SLICK_REPORTING_DEFAULT_CHARTS_ENGINE
        output = []
        chart_settings = chart_settings or []
        report_title = default_chart_title or ""
        for i, chart in enumerate(chart_settings):
            if type(chart) is Chart:
                chart = chart.to_dict()
            chart["id"] = chart.get("id", f"{i}")
            chart_type = chart.get("type", "line")
            if chart_type == "column" and SLICK_REPORTING_DEFAULT_CHARTS_ENGINE == "chartsjs":
                chart["type"] = "bar"

            if not chart.get("title", False):
                chart["title"] = report_title
            chart["engine_name"] = chart.get("engine_name", chart_engine)
            chart["entryPoint"] = (
                chart.get("entryPoint")
                or app_settings.SLICK_REPORTING_SETTINGS["CHARTS"][chart["engine_name"]]["entryPoint"]
            )
            chart["stacking"] = chart.get("stacking", False)

            output.append(chart)
        return output


class ListViewReportGenerator(ReportGenerator):
    def prepare_queryset(self, queryset):
        return self._apply_queryset_options(queryset, self.get_database_columns())

    def _apply_queryset_options(self, query, fields=None):
        """
        Apply the filters to the main queryset which will computed results be mapped to
        :param query:
        :param fields:
        :return:
        """
        filters = {}
        if self.date_field:
            filters = {
                f"{self.date_field}__gt": self.start_date,
                f"{self.date_field}__lte": self.end_date,
            }
        filters.update(self.kwargs_filters)

        if filters:
            query = query.filter(**filters)
        if fields:
            return query.values(*fields)
        return query

    def _get_record_data(self, obj, columns):
        """
        the function is run for every obj in the main_queryset
        :param obj: current row
        :param: columns： The columns we iterate on
        :return: a dict object containing all needed data
        """

        data = {}
        group_by_val = None
        if self.group_by:
            if self.group_by_field.related_model and "__" not in self.group_by:
                primary_key_name = self.get_primary_key_name(self.group_by_field.related_model)
            else:
                primary_key_name = self.group_by_field_attname

            column_data = obj.get(primary_key_name, obj.get("id"))
            group_by_val = str(column_data)

        for window, window_cols in columns:
            for col_data in window_cols:
                name = col_data["name"]

                if col_data.get("source", "") == "attribute_field":
                    data[name] = col_data["ref"](self, obj, data)
                    # changed line
                elif col_data.get("source", "") == "container_class_attribute_field":
                    data[name] = col_data["ref"](obj)

                elif (col_data.get("source", "") == "magic_field" and self.group_by) or (
                    self.time_series_pattern and not self.group_by
                ):
                    source = self._report_fields_dependencies[window].get(name, False)
                    if source:
                        computation_class = self.report_fields_classes[source]
                        value = computation_class.get_dependency_value(group_by_val, col_data["ref"].name)
                    else:
                        try:
                            computation_class = self.report_fields_classes[name]
                        except KeyError:
                            continue
                        value = computation_class.do_resolve(group_by_val, data)
                    if self.swap_sign:
                        value = -value
                    data[name] = value

                else:
                    data[name] = obj[name]
        return data

    def _remove_order(self, main_queryset):
        return main_queryset

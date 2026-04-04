from django.db import models, connections

_model_cache = {}

FIELD_TYPE_MAP = {
    "AutoField": models.AutoField,
    "BigAutoField": models.BigAutoField,
    "SmallAutoField": models.SmallAutoField,
    "BigIntegerField": models.BigIntegerField,
    "BooleanField": models.BooleanField,
    "CharField": models.CharField,
    "DateField": models.DateField,
    "DateTimeField": models.DateTimeField,
    "DecimalField": models.DecimalField,
    "DurationField": models.DurationField,
    "FloatField": models.FloatField,
    "IntegerField": models.IntegerField,
    "PositiveIntegerField": models.PositiveIntegerField,
    "PositiveBigIntegerField": models.PositiveBigIntegerField,
    "PositiveSmallIntegerField": models.PositiveSmallIntegerField,
    "SmallIntegerField": models.SmallIntegerField,
    "TextField": models.TextField,
    "TimeField": models.TimeField,
    "BinaryField": models.BinaryField,
    "UUIDField": models.UUIDField,
    "JSONField": models.JSONField,
    "GenericIPAddressField": models.GenericIPAddressField,
    "IPAddressField": models.GenericIPAddressField,
    "SlugField": models.SlugField,
    "URLField": models.URLField,
    "FilePathField": models.FilePathField,
}


def _make_field(field_type_str, column_info, is_pk):
    """Create a Django field instance from introspection data."""
    field_class = FIELD_TYPE_MAP.get(field_type_str, models.TextField)
    kwargs = {}

    if is_pk:
        if field_class in (models.AutoField, models.BigAutoField, models.SmallAutoField):
            return field_class(primary_key=True)
        kwargs["primary_key"] = True
    else:
        if column_info.null_ok:
            kwargs["null"] = True
            kwargs["blank"] = True

    if field_class == models.CharField:
        max_length = column_info.display_size
        if not max_length or max_length < 0 or max_length > 10000:
            max_length = 255
        kwargs["max_length"] = max_length

    elif field_class == models.DecimalField:
        kwargs["max_digits"] = column_info.precision if column_info.precision else 19
        kwargs["decimal_places"] = column_info.scale if column_info.scale else 2

    elif field_class in (models.SlugField, models.URLField):
        max_length = column_info.display_size
        if not max_length or max_length < 0 or max_length > 10000:
            max_length = 255 if field_class == models.SlugField else 200
        kwargs["max_length"] = max_length

    return field_class(**kwargs)


def get_dynamic_model(table_name, database="default", schema=None):
    """
    Introspect a database table and return a Django model class for it.

    The returned model is a real Django model with ``managed = False``,
    so all ORM operations (filter, annotate, aggregate, etc.) work natively.
    Results are cached so repeated calls for the same table return the same class.

    Args:
        table_name: The database table name to introspect.
        database: The database alias to use (default: 'default').
        schema: Optional database schema name (e.g. 'analytics').
            On PostgreSQL, the schema must be in the connection's ``search_path``
            for introspection to find the table. If provided, the model's
            ``db_table`` will be set to ``"schema"."table"`` so ORM queries
            reference the correct schema.

    Returns:
        A Django model class mapped to the given table.

    Raises:
        ValueError: If the table does not exist in the database.
    """
    db_table = f'"{schema}"."{table_name}"' if schema else table_name
    cache_key = f"{database}:{db_table}"
    if cache_key in _model_cache:
        return _model_cache[cache_key]

    connection = connections[database]
    with connection.cursor() as cursor:
        tables = connection.introspection.table_names(cursor)
        if table_name not in tables:
            raise ValueError(
                f"Table '{table_name}' does not exist in the '{database}' database. "
                f"Available tables: {', '.join(sorted(tables))}"
            )

        table_description = connection.introspection.get_table_description(cursor, table_name)
        try:
            pk_columns = connection.introspection.get_primary_key_columns(cursor, table_name)
        except AttributeError:
            # Fallback for older Django versions
            pk_column = connection.introspection.get_primary_key_column(cursor, table_name)
            pk_columns = [pk_column] if pk_column else []

    fields = {}
    has_pk = False

    for col_info in table_description:
        result = connection.introspection.get_field_type(col_info.type_code, col_info)
        # get_field_type returns a string in modern Django, or (string, params) in older versions
        if isinstance(result, tuple):
            field_type_str = result[0]
        else:
            field_type_str = result
        is_pk = col_info.name in pk_columns

        if is_pk:
            has_pk = True

        field = _make_field(field_type_str, col_info, is_pk)
        field.db_column = col_info.name
        fields[col_info.name] = field

    if not has_pk:
        # Table has no PK — add a synthetic one on the first column
        if table_description:
            first_col = table_description[0].name
            result = connection.introspection.get_field_type(
                table_description[0].type_code, table_description[0]
            )
            ft = result[0] if isinstance(result, tuple) else result
            fields[first_col] = _make_field(ft, table_description[0], is_pk=True)
            fields[first_col].db_column = first_col

    # Build a valid Python class name from the table name
    name_parts = table_name.replace(".", "_").split("_")
    if schema:
        name_parts = schema.replace(".", "_").split("_") + name_parts
    model_name = "".join(part.capitalize() for part in name_parts)
    if not model_name:
        model_name = "DynamicModel"

    attrs = {
        "__module__": __name__,
        "Meta": type(
            "Meta",
            (),
            {
                "managed": False,
                "db_table": db_table,
                "app_label": "slick_reporting",
            },
        ),
    }
    attrs.update(fields)

    model = type(model_name, (models.Model,), attrs)

    # Register in Django's app registry
    from django.apps import apps

    app_models = apps.all_models.get("slick_reporting", {})
    model_key = model_name.lower()
    if model_key in app_models:
        # Already registered — reuse the existing model
        model = app_models[model_key]
    else:
        apps.register_model("slick_reporting", model)

    _model_cache[cache_key] = model
    return model

.. _computation_field_ref:

ComputationField API
--------------------

.. autoclass:: slick_reporting.fields.ComputationField

    .. autoattribute:: name
    .. autoattribute:: calculation_field
    .. autoattribute:: calculation_method
    .. autoattribute:: verbose_name
    .. autoattribute:: requires
    .. autoattribute:: type

    .. rubric:: Below are some data passed by the `ReportGenerator`, for extra manipulation, you can change them

    .. autoattribute:: report_model
    .. autoattribute:: group_by
    .. autoattribute:: plus_side_q
    .. autoattribute:: minus_side_q

    .. rubric:: You can customize those methods for maximum control where you can do pretty much whatever you want.

    .. automethod:: prepare
    .. automethod:: resolve
    .. automethod:: get_dependency_value




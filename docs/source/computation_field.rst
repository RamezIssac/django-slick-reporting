.. _computation_field:


Computation Field API
=====================

Responsible for preforming the calculation.

You can create your computation field following this analogy.

.. code-block:: python

    from slick_reporting.fields import BaseReportField


    class NetQTYReportField(BaseReportField):

        # The name to use when using this field in the generator
        name = '__total_quantity__'

        # the field we want to compute on
        calculation_field = 'quantity'

        # What method we want
        calculation_method = Sum  # the default

        # This enables you to reuse calculation field classes
        requires = [ReturnedQuantityReportField]

        # A verbose name
        verbose name = 'Net quantity'


BaseReportField
---------------

.. autoclass:: slick_reporting.fields.BaseReportField

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




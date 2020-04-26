.. _computation_field:


Computation Field API
=====================

Responsible for preforming the calculation.


ReportField Basic Structure:
----------------------

Earlier in he docs you saw the computation fields ``'__total__quantity__'``
Let's see how it's written in `slick_reporting.fields`


.. code-block:: python

    from slick_reporting.fields import BaseReportField
    from slick_reporting.decorators import report_field_register


    @report_field_register
    class TotalQTYReportField(BaseReportField):

        # The name to use when using this field in the generator
        name = '__total_quantity__'

        # the field we want to compute on
        calculation_field = 'quantity'

        # What method we want
        calculation_method = Sum  # the default

        # A verbose name
        verbose name = 'Total quantity'


If you want AVG to the field `price` then the ReportField would look like this

.. code-block:: python

    from django.db.models import Avg

    @report_field_register
    class TotalQTYReportField(BaseReportField):

        name = '__avg_price__'
        calculation_field = 'price'
        calculation_method = Avg
        verbose name = 'Avg. Price'



Registering Report Field
------------------------

To make this ReportField class available to the report, it has to be registered via ``report_field_register``


Say you want to further customize your calculation, maybe you need to run a complex query

You can override both of those method and control the calculation

Calculation Flow:
-----------------

ReportGenerator call

1. prepare
2. resolve


Two side calculation
--------------------

# todo:
# Document how a single field can be computed like a debit and credit.


BaseReportField API
-------------------

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




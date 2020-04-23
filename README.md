.. image:: https://img.shields.io/pypi/v/django-slick-reporting.svg
    :target: https://pypi.org/project/django-ra

.. image:: https://img.shields.io/pypi/pyversions/django-slick-reporting.svg
    :target: https://pypi.org/project/django-ra

.. image:: https://img.shields.io/readthedocs/django-slick-reporting
    :target: https://django-slick-reporting.readthedocs.io/

.. image:: https://api.travis-ci.org/ra-systems/django-slick-reporting.svg?branch=master
    :target: https://travis-ci.org/ra-systems/django-slick-reporting

.. image:: https://img.shields.io/codecov/c/github/ra-systems/django-slick-reporting
    :target: https://codecov.io/gh/ra-systems/django-slick-reporting




# Django Slick Reporting
A one stop reports and analytics tool for Django

# Features
1- Simple Reporting over the content of a model
2- Preform Different computation grouping over the content of model
3- Those computation can also be computed on Time Series report, with custom dates ability
4- Also can be used on Crosstab reports
5- Custom computation with smart dependency management to optimize calculations
6- ... and much more 

## Installation

Use the package manager [pip](https://pip.pypa.io/en/stable/) to install django-slick-reporting.

```bash
pip install django-slick-reporting
```

## Usage
From high Level: you can use `SampleReportView` which is a subclass of `django.views.generic.FormView` like this

```python
from slick_reporting.views import SampleReportView

class MonthlyProductSales(SampleReportView):
    report_model = MySalesItems
    date_field = 'order__date_placed'
    group_by = 'product'
    columns = ['title', 'SKU']
    time_series_pattern = 'monthly'
    time_series_columns = ['__total_quantity__']

``` 
And this would return a something like this, _and a form where you can customize foreign keys filters by default_:

| Product Name 	| SKU                  	| Total Quantity  in Jan 20 	| Total Quantity in Feb 20 	| Total Quantity in ... 	| Total Quantity in December 20 	|
|--------------	|----------------------	|---------------------------	|--------------------------	|-----------------------	|-------------------------------	|
| Product 1    	| <from product model> 	| 10                        	| 15                       	| ...                   	| 14                            	|
| Product 2    	| <from product model> 	| 11                        	| 12                       	| ...                   	| 12                            	|
| Product 3    	| <from product model> 	| 17                        	| 12                       	| ...                   	| 17                            	|


On a low level, you can interact with the `ReportGenerator` using same syntax as used with the `SampleReportView` .

```python
from slick_reporting import ReportGenerator
from . models import MySalesModel

report = ReportGenerator(report_model=MySalesModel, 
                        group_by='product',
)
report.get_report_data()

```

This is just a scratch, for more please visit the documentation 

## Documentation

Available on `Read The Docs <https://django-slick-reporting.readthedocs.io/en/latest/>`_



## Running the tests
First create a virtual environment (maybe with `virtual slick_reports_test`), activate it then ,
 
```textmate
    
    $ git clone git+git@github.com:ra-systems/django-slick-reporting.git
    $ cd tests
    $ python -m pip install -e ..
    $ python runtests.py

        # And for Coverage report
    $ coverage run --include=../* runtests.py [-k]
    $ coverage html



```
Tests tests the proper computation and structure generation ,

## Contributing

We honor `Django's guidelines <https://docs.djangoproject.com/en/dev/internals/contributing/writing-code/unit-tests/>`_ guidelines.

## Versioning

We use [SemVer](http://semver.org/) for versioning. For the versions available, see the [tags on this repository](https://github.com/ra-systems/django-slick-reporting/tags). 

## Authors

* **Ramez Ashraf** - *Initial work* - [RamezIssac](https://github.com/RamezIssac)

See also the list of [contributors](https://github.com/your/project/contributors) who participated in this project.

## License

This project is licensed under the BSD License - see the [LICENSE.md](LICENSE.md) file for details

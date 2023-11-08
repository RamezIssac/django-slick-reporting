Integrating reports into your front end
=======================================

To integrate Slick Reporting into your application, you need to do override "slick_reporting/base.html" template,
and/or, for more fine control over the report layout, override "slick_reporting/report.html" template.

Example 1: Override base.html

.. code-block:: html+django

        {% extends "base.html" %}

        {% block meta_page_title %} {{ report_title }}{% endblock %}
        {% block page_title %} {{ report_title }} {% endblock %}

        {% block extrajs %}
            {{ block.super }}
            {% include "slick_reporting/js_resources.html" %}
        {% endblock %}



Let's see what we did there
1. We made our slick_reporting/base.html extend the main base.html
2. We added the ``report_title`` context variable (which hold the current report title) to the meta_page_title and page_title blocks.
   Use your version of these blocks, you might have them named differently.
3. We added the slick_reporting/js_resources.html template to the extrajs block. This template contains the javascript resources needed for slick_reporting to work.
   Also, use your version of the extrajs block. You might have it named differently.

And that's it ! You can now use slick_reporting in your application.


Example 2: Override report.html

Maybe you want to add some extra information to the report, or change the layout of the report.
You can do this by overriding the slick_reporting/report.html template.

Here is how it looks like:

.. code-block:: html+django

    {% extends 'slick_reporting/base.html' %}
    {% load crispy_forms_tags i18n %}

    {% block content %}
        <div class="col-12">
            {% if form %}
                <form id="reportForm" class="card">
                    <div class="card-header">
                        <h3 class="card-title">{% trans "Filters" %}</h3>
                    </div>
                    <div class="card-body">
                        {% crispy form crispy_helper %}
                    </div>
                    <div class="card-footer text-end">
                        <input type="submit" value="{% trans "Filter" %}"
                               class="btn btn-primary  refreshReport">
                        <input type="button" value="{% trans "Export CSV" %}" class="btn btn-secondary exportCsvBtn">
                    </div>
                </form>
            {% endif %}

            <div class="card" id="{{ report_data.report_slug }}">
                <div class="card-header">
                    <h5 class="card-title">{% trans "Results" %}</h5>
                </div>
                <div class="card-body">
                    <div data-report-widget
                         data-report-url="{{ request.path }}"
                         data-extra-params=""
                         data-form-selector="#reportForm"
                            {% if not auto_load %} data-no-auto-load{% endif %}
                         data-display-chart-selector="True">
                        <div data-report-chart>
                        </div>
                        <div data-report-table>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    {% endblock %}


Integrating reports into your Admin site
=========================================

1. Most probably you would want to override the default admin to add the extra report urls
https://docs.djangoproject.com/en/4.2/ref/contrib/admin/#overriding-the-default-admin-site

2. Add the report url to your admin site main get_urls

.. code-block:: python

    class CustomAdminAdminSite(admin.AdminSite):
        def get_urls(self):
            from my_apps.reports import MyAwesomeReport

            urls = super().get_urls()
            urls = [
                path(
                    "reports/my-awesome-report/",
                    MyAwesomeReport.as_view(),
                    name="my-awesome-report",
                ),
            ] + urls
            return urls

Note that you need to add the reports urls to the top, or else the wildcard catch will raise a 404

3. Override slick_reporting/base.html to extend the admin site

.. code-block:: html+django

    {% extends 'admin/base_site.html' %}
    {% load i18n static slick_reporting_tags %}

    {% block title %}{{ report_title }}{% endblock %}

    {% block extrahead %}
        {% include "slick_reporting/js_resources.html" %}
        {% get_charts_media "all" %}
    {% endblock %}

    {% block breadcrumbs %}
        <ul class="breadcrumb heading-text">
            <a href="{% url 'admin:index' %}" class="breadcrumb-item">
                <i class="icon-home2 mx-2"></i> {% trans 'Home' %} </a>
            <a class="breadcrumb-item"> {% trans 'Reports' %}</a>
            <a class="breadcrumb-item"> {{ report_title }}</a>
        </ul>
    {% endblock %}


4. You might want to override the report.html as well to set your styles, You can also use a different template for the crispy form






# Changelog

All notable changes to this project will be documented in this file.

## [1.3.0] - 2023-11-08
- Implement Slick reporting media override feature + docs
- Add `Integrating reports into your Admin site` section to the docs
- Group by and crosstab reports do not need date_field set anymore. Only time series do.
- Fix in FirstBalance Computation field if no date is supplied
- Add `REPORT_VIEW_ACCESS_FUNCTION` to control access to the report view


## [1.2.0] - 2023-10-10
- Add ``get_slick_reporting_media`` and ``get_charts_media`` templatetags
- Add `get_group_by_custom_querysets` hook to ReportView
- Enhance and document adding export options and customizing the builtin export to csv button
- Enhance and document adding custom buttons to the report page
- Enhance and document adding a new chart engine
- Fix in SlickReportingListView
- Move all css and js resources to be handled by `Media` governed by `settings.SLICK_REPORTING_SETTINGS`

 
## [1.1.1] - 2023-09-25
- Change settings to be a dict , adding support JQUERY_URL and FONT AWESOME customization #79 & #81
- Fix issue with chartjs not being loaded  #80
- Remove `SLICK_REPORTING_FORM_MEDIA`

## [1.1.0] -
- Breaking: changed ``report_title_context_key`` default value to `report_title`
- Breaking: Renamed simple_report.html to report.html
- Breaking: Renamed ``SlickReportField`` to ``ComputationField``. SlickReportField will continue to work till next release.
- Revised and renamed js files
- Add dashboard capabilities.
- Added auto_load option to ReportView
- Unified report loading to use the report loader
- Fix issue with group_by_custom_queryset with time series
- Fix issue with No group by report 
- Fix issue with traversing fields not showing up on ListViewReport
- Fix issue with date filter not being respected in ListViewReport

## [1.0.2] - 2023-08-31
- Add a demo project for exploration and also containing all documentation code for proofing.
- Revise and Enhancing Tutorial , Group by and Time series documentation.
- Fix issue with error on dev console on report page due to resources duplication
- Fix issue with Custom querysets not being correctly connected in the view
- Fix issue with time series custom dates
- Fix issue with Crosstab on traversing fields


## [1.0.1] - 2023-07-03

- Added missing js files ported from erp_framework package. 
- Document the need for "crispy_bootstrap4" in the docs and add it as a dependency in the setup.

## [1.0.0] - 2023-07-03

- Added crosstab_ids_custom_filters to allow custom filters on crosstab ids
- Added ``group_by_custom_querysets`` to allow custom querysets as group 
- Added ability to have crosstab report in a time series report
- Enhanced Docs content and structure.

## [0.9.0] - 2023-06-07

- Deprecated ``form_factory`` in favor of ``forms``, to be removed next version.
- Deprecated `crosstab_model` in favor of ``crosstab_field``, to be removed next version.
- Deprecated ``slick_reporting.view.SlickReportView`` and ``slick_reporting.view.SlickReportViewBase`` in favor of ``slick_reporting.view.ReportView`` and ``slick_reporting.view.BaseReportView``, to be removed next version.
- Allowed cross tab on fields other than ForeignKey
- Added support for start_date_field_name and end_date_field_name
- Added support to crosstab on traversing fields
- Added support for document types / debit and credit calculations
- Added support for ordering via ``ReportView.default_order_by`` and/or passing the parameter ``order_by`` to the view
- Added return of Ajax response in case of error and request is Ajax
- Made it easy override to the search form. Create you own form and subclass BaseReportForm and implement the mandatory method(s).
- Consolidated the needed resources in ``slick_reporting/js_resource.html`` template, so to use your own template you just need to include it.
- Fixed an issue with report fields not respecting the queryset on the ReportView.
- Fixed an issue if a foreign key have a custom `to_field` set either in ``group_by`` and/or `crosstab_field` .
- Enhancing and adding to the documentation.
- Black format the code and the documentation


## [0.8.0]

- Breaking: [Only if you use Crosstab reports] renamed crosstab_compute_reminder to crosstab_compute_remainder
- Breaking : [Only if you set the templates statics by hand] renamed slick_reporting to ra.hightchart.js and ra.chartjs.js to 
  erp_framework.highchart.js and erp_framework.chartjs.js respectively
- Fix an issue with Crosstab when there crosstab_compute_remainder = False

## [0.7.0]

- Added SlickReportingListView: a Report Class to display content of the model (like a ModelAdmin ChangeList)
- Added `show_time_series_selector` capability to SlickReportView allowing User to change the time series pattern from
  the UI.
- Added ability to export to CSV from UI, using `ExportToStreamingCSV` & `ExportToCSV`
- Now you can have a custom column defined on the SlickReportView (and not needing to customise the report generator).
- You don't need to set date_field if you don't have calculations on the report
- Easier customization of the crispy form layout
- Enhance weekly time series default column name
- Add `Chart` data class to hold chart data

## [0.6.8]

- Add report_title to context
- Enhance SearchForm to be easier to override. Still needs more enhancements.

## [0.6.7]

- Fix issue with `ReportField` when it has a `requires` in time series and crosstab reports

## [0.6.6]

- Now a method on a generator can be effectively used as column
- Use correct model when traversing on group by

## [0.6.5]

- Fix Issue with group_by field pointing to model with custom primary key Issue #58

## [0.6.4]

- Fix highchart cache to target the specific chart
- Added initial and required to report_form_factory
- Added base_q_filters and base_kwargs_filters to SlickReportField to control the base queryset
- Add ability to customize ReportField on the fly
- Adds `prevent_group_by` option to SlickReportField Will prevent group by calculation for this specific field, serves
  when you want to compute overall results.
- Support reference to SlickReportField class directly in `requires` instead of its "registered" name.
- Adds PercentageToBalance report field

## [0.6.3]

- Change the deprecated in Django 4 `request.is_ajax` .

## [0.6.2]

- Fix an issue with time series calculating first day of the month to be of the previous month #46

## [0.6.1]

- Fix Django 4 compatibility (@squio)

## [0.6.0]

- Breaking [ONLY] if you have overridden ReportView.get_report_results()
- Moved the collecting of total report data to the report generator to make easier low level usage.
- Fixed an issue with Charts.js `get_row_data`
- Added ChartsOption 'time_series_support',in both chart.js and highcharts
- Fixed `SlickReportField.create` to use the issuing class not the vanilla one.

## [0.5.8]

- Fix compatibility with Django 3.2

## [0.5.7]

- Add ability to refer to related fields in a group by report(@jrutila)

## [0.5.6]

- Add exclude_field to report_form_factory (@gr4n0t4)
- Added support for group by Many To Many field (@gr4n0t4)

## [0.5.5]

- Add datepicker initialization function call (@squio)
- Fixed an issue with default dates not being functional.

## [0.5.4]

- Added missing prefix on integrity hash (@squio)

## [0.5.3]

- Enhanced Field prepare flow
- Add traversing for group_by
- Allowed tests to run specific tests instead of the whole suit
- Enhanced templates structure for easier override/customization

## [0.5.2]

- Enhanced Time Series Plot total HighChart by accenting the categories
- Enhanced the default verbose names of time series.
- Expanding test coverage

## [0.5.1]

- Allow for time series to operate on a non-group by report
- Allow setting time series custom dates on ReportGenerator attr and init
- Fix a bug with setting the queryset (but not the report model) on SlickReportView
- Fixed an issue if GenericForeignKey is on the report model
- Fixed an issue with Time series annual pattern

## [0.5.0] - 2020-12-11

- Created the demo site https://django-slick-reporting.com/
- Add support to group by date field
- Add `format_row` hook to SlickReportingView
- Add support for several chart engine per same report
- Add `SLICK_REPORTING_FORM_MEDIA` &`SLICK_REPORTING_DEFAULT_CHARTS_ENGINE` setting.
- Documenting SlickReportView response structure.
- Fix issue with special column names `__time_series__` and `__crosstab__`
- Fix issue with Crosstab reminder option.

## [0.4.2] - 2020-11-29

- Properly initialize Datepicker (#12 @squio)
- Use previous date-range for initialization if it exists

## [0.4.1] - 2020-11-26

- Bring back calculateTotalOnObjectArray (#11)
- Bypassing default ordering by when generating the report (#10)
- Fix in dates in template and view

## [0.4.0] - 2020-11-24 [BREAKING]

- Renamed `SampleReportView` to `SlickReportView`
- Renamed `BaseReportField` to `SlickReportField`
- Added `SlickReportViewBase` leaving sanity checks for the `SlickReportView`

## [0.3.0] - 2020-11-23

- Add Sanity checks against incorrect entries in columns or date_field
- Add support to create ReportField on the fly in all report types
- Enhance exception verbosity.
- Removed `doc_date` field reference .

## [0.2.9] - 2020-10-22

### Updated

- Fixed an issue getting a db field verbose column name
- Fixed an issue with the report demo page's filter button not working correctly.

## [0.2.8] - 2020-10-05

### Updated

- Fixed an error with ManyToOne Relation not being able to get its verbose name (@mswastik)

## [0.2.7] - 2020-07-24

### Updates

- Bring back crosstab capability
- Rename `quan` to the more verbose `quantity`
- Minor enhancements around templates

## [0.2.6] - 2020-06-06

### Added

- Adds `is_summable` option for ReportFields, and pass it to response
- Add option to override a report fields while registering it.
- Test ajax Request

### Updates and fixes

- Fix a bug with time series adding one extra period.
- Fix a bug with Crosstab data not passed to `report_form_factory`
- Enhance Time series default column verbose name
- testing: brought back ReportField after unregister test
- Fix Pypi package not including statics.

## [0.2.5] - 2020-06-04

### Added

- Crosstab support
- Chart title defaults to report_title
- Enhance fields naming

## [0.2.4] - 2020-05-27

### Added

- Fix a naming issue with license (@iLoveTux)

## [0.2.3] - 2020-05-13

### Added

- Ability to create a ReportField on the fly.
- Document SLICK_REPORTING_DEFAULT_START_DATE & SLICK_REPORTING_DEFAULT_START_DATE settings
- Test Report Field Registry
- Lift the assumption that a Report field name should start and end with "__". This is only a convention now.

## [0.2.2] - 2020-04-26

- Port Charting from [Ra Framework](https://github.com/ra-systems/RA)
- Enhance ReportView HTML response

## [0.0.1] - 2020-04-24

### Added

- Ported from [Ra Framework](https://github.com/ra-systems/RA) 

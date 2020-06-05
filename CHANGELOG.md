# Changelog
All notable changes to this project will be documented in this file.

## [0.2.6] - Unreleased
### Added

- Fix a bug with time series adding one extra period.
- Adds `is_summable` option for ReportFields, and pass it to response 
- Enhance Time series default column verbose name
- Add option to override a report fields while registering it.


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

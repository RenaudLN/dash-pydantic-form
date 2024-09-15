# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.5.1] - 2024-09-16
### Added
- New Transferlist field allowing custom data fetching based on search input

## [0.5.0] - 2024-09-05
### Added
- Improved warning log for conditional visibility without default
- Datetime and time in table field

### Changed
- Pinned dmc >= 0.14.4 for datetime bugfix
- Renamed `EditableTable` to `Table`, `EditableTable` kept for backwards compatibility and deprecated
- Deprecation warning message for ModelList and EditableTable
- Use dmc 0.14.4 `readOnly` wherever possible rather than the custom made read_only renderer

### Fixed
- Cannot edit key on Dict fields in read_only mode.

## [0.4.0] - 2024-08-16
### Added
- Possibility to set default repr type and kwargs directly in the pydantic model using repr_type and repr_kwargs

## [0.3.6] - 2024-08-14
### Added
- Date an number columns have the proper filter in the editable table

### Fixed
- Filtering the editable table does not remove the data from the form

## [0.3.5] - 2024-07-19
### Fixed
- Nested dict fields were not working and are fixed with added tests

## [0.3.4] - 2024-07-14
### Fixed
- Minor fix for list fields iwht recent discriminated union fixes

## [0.3.3] - 2024-07-13
### Fixed
- Discriminated unions can now have nested models within them
- Discriminated unions can now be part of nested models

### Changed
- Checkbox and switch now have a default of False rather than None
- Changed warning to debug log about ignored args

## [0.3.2] - 2024-07-05
### Fixed
- Remove the need to model_dump("json") in get_model_value which was breaking the fields.List item name str render
- Fixed usage.py on discriminated model

## [0.3.1] - 2024-06-27
### Fixed
- Fixed issues with list fields not updating ids properly
- Fixed from_form_data issue

## [0.3.0] - 2024-06-25
### Changed
- Hidden fields (from conditional visibility) are not returned in form data

### Added
- New `from_form_data` function allowing to use default values on validation error.
- Added `from_form_data` and `get_model_cls` to the main dash_pydantic_form namespace.

## [0.2.2] - 2024-06-25
### Fixed
- Fixed an issue in get_subitem that didn't get the right value for list of scalars

## [0.2.1] - 2024-06-17
### Fixed
- Added missing scalar option for fields.Dict
- Fixed issue with updating modal text in fields.Dict

## [0.2.0] - 2024-06-16
### Added
- Dict field to allow dict[str, scalar] and dict[str, model] field types

### Changed
- Renamed ModelList to List as it allows to do scalar lists as well. ModelList is kept for backwards compatibility

## [0.1.19] - 2024-06-01
### Fixed
- Rm unused dependency flatdict

## [0.1.18] - 2024-06-01
### Fixed
- Issue with ModelList accordion render whereby AccordionItems have the same value
- Issue with scalar list whereby React hydration was messing things, fixed by adding a unique key

## [0.1.17] - 2024-06-01
### Changed
- ModelList add/delete is now done clientside.

## [0.1.16] - 2024-06-01
### Changed
- Improved ModelList styling.

## [0.1.15] - 2024-06-01
### Fixed
- Better handling of ids on the model list when deleting items in the middle of the list.

## [0.1.14] - 2024-06-01
### Added
- List of scalar barebone working, defaulting to the right input for str, numbers, datetimes.

## [0.1.12] - 2024-05-24
### Added
- Allow passing errors to the form to add to inputs, use `Output(ModelForm.ids.errors(MATCH, MATCH), "data")`
- `debounce_inputs` ModelForm argument allowing to debounce all debounce-able fields at once
- Allow passing `input_kwargs` via extra arguments to the field_repr's init

## [0.1.11] - 2024-05-23
### Added
- read_only option on the ModelForm to simply dislpay the values

## [0.1.10] - 2024-05-22
### Added
- fields.Datetime leveraging dmc.DateTimePicker
  NOTE: the PM times are not working atm but a fix is incoming, workaround is to wrap the app with a DatesProvider with timezone=UTC
- ModelForm container_kwargs to pass kwargs to the wrapping Div

### Changed
- fields.Date now leverages dmc.DateInput to allow manually typing the date
- EditableTable now allows to stop editing on click outside

## [0.1.8] - 2024-05-20
### Added
- ModelForm container_kwargs argument

## [0.1.7] - 2024-05-20
### Changed
- Use container query to ensure the columns shrink when the form container is small

## [0.1.6] - 2024-05-20
### Changed
- Always store form specs in in a `ids.form_specs_store`, not just for discriminated unions

## [0.1.5] - 2024-05-20
### Changed
- BREAKING: Moved `excluded_fields` from `Sections` to `ModelForm`

## [0.1.4] - 2024-05-19
### Added
- Allow form submit on Enter press (optional as it may break some field renders and more complex forms)

## [0.1.3] - 2024-05-16
### Added
- Discriminated Model union #2

## [0.1.2] - 2024-05-16
### Added
- MarkdownField
- Fields auto-generated docstrings

## Changed
- Allow Python>=3.10,<3.13 #1

## [0.1.0] - 2024-05-13
### Added
- Working initial version

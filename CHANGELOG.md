# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
### Added
- Allow pydantic's `RootModel` in the `ModelForm`

## [0.15.3] - 2025-04-23
### Changed
- Allow python 3.13 in pypi

## [0.15.2] - 2025-04-06
### Changed
- For list items, display the 'name' attribute if it exists before it is synced with callbacks

### Fixed
- Use SerializeAsAny on `form_layout` attribute of List and Model fields

## [0.15.1] - 2025-03-26
### Fixed
- Edge case for nested fields_repr not working as expected
- Edge case in get_subitem when called on a model built with model_construct (like discriminated unions)

## [0.15.0] - 2025-03-25
### Changed
- Allow Dash 3.0 in deps
- Made some MATCH callbacks prevent_initial_call to avoid performance issues in large forms
  NOTE: This means the __str__ method needs to be defined on the models to get the initial
  name in accordion/modal title for list fields

## [0.14.9] - 2025-03-16
### Fixed
- Working nested fields_repr serialization when using fields.X explicitly

## [0.14.8] - 2025-02-15
### Changed
- Use display rather than opacity on delete buttons to avoid issues on mobile

### Fixed
- Adding to an accordion list opens the added item

## [0.14.7] - 2025-02-12
### Changed
- `debounce` now works on the clientside callback ensuring the whole form changes are debounced
- Deprecated `debounce_inputs` in favor of `debounce`

## [0.14.6] - 2025-02-11
### Added
- Model field "simple" render with only title, description and sub-form

### Changed
- Possibility to pass Components to fields `title` and `description`

### Fixed
- `debounce_inputs` is properly passed down to nested submodels

## [0.14.5] - 2025-02-06
### Changed
- Minor styling change on position of Table title
- Table add row is now clientside

### Fixed
- Issue with form_layout validation in field.Model and field.List
- Quantity field issue

## [0.14.4] - 2025-02-04
### Added
- Working right multiplication and division with dataframes

### Fixed
- Nested fields_repr were not being serialised/deserialised properly

## [0.14.3] - 2025-02-03
### Added
- Unit tests for Quantity

### Changed
- Improved pandas support in Quantity
- Moved quantity.pandas to quantity.pandas_engine

## [0.14.2] 2025-01-31
### Added
- `with_download` parameter in Table field

### Changed
- Removed pandas dependency

### Fixed
- Improved robustness of get_subitem_cls with nesting of lists and unions

## [0.14.0] - 2025-01-28
### Changed
- Split dash-pydantic-form and dash-pydantic-utils to allow using the utils without requirinf Dash dependencies

### Added
- `excluded_fields` and `fields_order` available in Model, List and Table fields
- Speed and Acceleration categories in Quantity
- Quantity for arrays and pandas dataframes.

## [0.13.3] - 2025-01-20
### Fixed
- Issue with model_construct_recursive with optional values
- Issue with FormLayout in List and Model fields in discriminated unions

## [0.13.2] - 2025-01-20
### Fixed
- Working list of union in list of union

## [0.13.1] - 2025-01-19
### Added
- `wrapper_kwargs` parameter in List and Dict fields
- `read_only` and `form_cols` passed to FormLayout.render

### Changed
- Improved List and Dict fields structure
- Keyword-only params in FormLayout

## [0.13.0] - 2025-01-18
### Added
- Stored form data can now be restored automatically or with user confirmation
- Added missing translations for a few text items

### Changed
- Sections is deprecated, use FormLayout instead
- FormLayout allows to define custom form layout renderers, default existing layouts are accordion, tabs and steps, as previously

## [0.12.0] - 2025-01-15
### Added
- `fields_order` in `ModelForm` to allow changing the fields order without sections nor re-arranging the model fields
- Allow to update the form content via the ids.form data-update attribute
- Allow to store form edition progress and retrieve it on page load

### Fixed
- Issue with visibility filter when other fields start with the same path prefix

## [0.11.0] - 2024-12-16
### Added
- Possibility to omit ``aio_id`` and/or ``form_id`` in ``ModelForm``'s instanciation so they get auto-generated
- Possibility to use the ModelForm instance ids in a callback
- Discriminated unions at the top level ModelForm
- Dict of discriminated unions

### Fixed
- Table fields required cells are not highlighted when '0' is input
- Sections render_kwargs are properly passed to renderers
- Steps sections additional_steps can be serialised correctly

## [0.10.1] - 2024-12-16
### Fixed
- read_only was forced False on nested form elements when unset on the parent
- read_only working for ChipGroup and MultiSelect
- form_cols is now passed to the form fields which fixes issues with modal renders

## [0.10.0] - 2024-12-04
### Added
- List of discriminated union now available

### Fixed
- QuantityField and TransferList ids inherit from BaseField ids
- fields_repr working for conditional fields on discriminated unions

## [0.9.2] - 2024-12-03
### Added
- Option to change the available number of columns in the form. For backwards compatibility, the default is set to 4.
- Possibility to use a float in fields repr `n_cols`, representing a fraction of the form columns.

### Fixed
- List field allows discriminated models in nesting

## [0.9.1] - 2024-11-19
### Fixed
- Date comparator in Table field works with Datetimes

## [0.9.0] - 2024-11-13
### Added
- Add new components MonthPicker and YearPicker for Table
- Chip and ChipGroup fields

## [0.8.3] - 2024-11-13
### Fixed
- Time field does not need conversion from date hack anymore

### Added
- Ability to pass additional kwargs to the AgGrid instance in Table field

## [0.8.2] - 2024-11-06
### Fixed
- Table with data_getter Selects
- Improved ag-grid cell selector
- Allow passing additional styles to the model form container
- Fix console warning on ForwardRef in table field

## [0.8.0] - 2024-10-28
### Added
- Path field to retrieve of path using fsspec
- Internationalisation of components, with i18n (FR translation available)
- Added unitless quantity, % and ‰

## [0.7.1] - 2024-10-22
### Added
- Option to add unit labels by passing a mapping in QuantityField unit_options

## [0.7.0] - 2024-10-21
### Added
- Quantity field for (value, unit) pairs, allowing auto-conversion for standard units

### Changed
- Improved readonly render for checkboxes and radios

## [0.6.0] - 2024-10-13
### Added
- More dmc inputs: Year, Month, Tags, Rating
- Dynamic options in Table field for select-type columns
- MultiSelect in Table

### Changed
- Color now uses ColorInput rather than ColorPicker

## [0.5.9] - 2024-10-10
### Changed
- Make all values uncontrolled if they come in as None

## [0.5.8] - 2024-10-10
### Fixed
- Ensure MultiSelect only receives strings or it crashes

## [0.5.7] - 2024-10-10
### Changed
- Allow model-specific excluded_fields via 'private_fields' in the model_config

## [0.5.6] - 2024-10-09
### Fixed
- utils issues

## [0.5.5] - 2024-10-09
### Fixed
- utils issues

## [0.5.4] - 2024-10-09
### Fixed
- Issue with List with modal render

## [0.5.3] - 2024-10-06
### Fixed
- Avoid passing None value to dmc component as it errs on some (e.g. MultiSelect)
- Fixed issue with discriminated model when parent is ullable and None

## Changed
- Mode read_only improvements

## [0.5.2] - 2024-10-05
### Changed
- Improved read_only styling

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

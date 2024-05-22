# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

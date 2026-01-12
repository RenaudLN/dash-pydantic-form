import base64

import dash_mantine_components as dmc
from dash import no_update

from dash_pydantic_form.fields.table_field import csv_to_table


def test_csv_to_table_success():
    """Test successful CSV parsing into row data."""
    csv_content = "col1,col2\nval1,1\nval2,2"
    contents = "data:text/csv;base64," + base64.b64encode(csv_content.encode()).decode()
    column_defs = [
        {"field": "col1", "dtype": "str"},
        {"field": "col2", "dtype": "int"},
    ]

    row_data, notification = csv_to_table(contents, column_defs)

    assert row_data == [
        {"col1": "val1", "col2": 1},
        {"col1": "val2", "col2": 2},
    ]
    assert notification is None


def test_csv_to_table_success_BOM():
    """Test successful CSV parsing into row data when it has a Byte Order Mark (BOM)."""
    csv_content = "\ufeffcol1,col2\nval1,1\nval2,2"  # \ufeff is microsoft BOM, checking it reads fine
    contents = "data:text/csv;base64," + base64.b64encode(csv_content.encode()).decode()
    column_defs = [
        {"field": "col1", "dtype": "str"},
        {"field": "col2", "dtype": "int"},
    ]

    row_data, notification = csv_to_table(contents, column_defs)

    assert row_data == [
        {"col1": "val1", "col2": 1},
        {"col1": "val2", "col2": 2},
    ]
    assert notification is None


def test_csv_to_table_missing_required():
    """Test error notification when mandatory columns are missing."""
    csv_content = "col1\nval1"
    contents = "data:text/csv;base64," + base64.b64encode(csv_content.encode()).decode()
    column_defs = [
        {"field": "col1", "required": True},
        {"field": "col2", "required": True},
    ]

    row_data, notification = csv_to_table(contents, column_defs)

    assert row_data is no_update
    assert isinstance(notification, dmc.Notification)
    assert notification.color == "red"
    assert "Wrong column names" in notification.title


def test_csv_to_table_duplicate_columns():
    """Test error notification when duplicate columns are present."""
    csv_content = "col1,col1\nval1,val2"
    contents = "data:text/csv;base64," + base64.b64encode(csv_content.encode()).decode()
    column_defs = [
        {"field": "col1", "required": True},
    ]

    row_data, notification = csv_to_table(contents, column_defs)

    assert row_data is no_update
    assert isinstance(notification, dmc.Notification)
    assert "Duplicate column names" in notification.title
    assert "col1" in str(notification.message)


def test_csv_to_table_aliases():
    """Test mapping of CSV column aliases to canonical field names."""
    csv_content = "alias1,col2\nval1,1"
    contents = "data:text/csv;base64," + base64.b64encode(csv_content.encode()).decode()
    column_defs = [
        {"field": "col1", "field_aliases": ["alias1", "alias2"]},
        {"field": "col2"},
    ]

    row_data, notification = csv_to_table(contents, column_defs)

    assert row_data == [{"col1": "val1", "col2": 1}]
    assert notification is None


def test_csv_to_table_duplicate_with_alias():
    """Test error notification when both a field and its alias are present for multiple columns."""
    csv_content = "col1,alias1,col2,alias2\nval1,val2,val3,val4"
    contents = "data:text/csv;base64," + base64.b64encode(csv_content.encode()).decode()
    column_defs = [
        {"field": "col1", "field_aliases": ["alias1"], "required": True},
        {"field": "col2", "field_aliases": ["alias2"], "required": False},
    ]

    row_data, notification = csv_to_table(contents, column_defs)

    assert row_data is no_update
    assert isinstance(notification, dmc.Notification)
    assert "Duplicate column names" in notification.title
    message_str = str(notification.message)
    assert "col1" in message_str
    assert "col2" in message_str


def test_csv_to_table_options_mapping():
    """Test translation of labels in CSV to option values."""
    # "Label A" is a label that should be mapped to "value_a"
    # "value_b" is already a value, so it should be kept
    csv_content = "col1\nLabel A\nvalue_b"
    contents = "data:text/csv;base64," + base64.b64encode(csv_content.encode()).decode()
    column_defs = [
        {
            "field": "col1",
            "cellEditorParams": {
                "options": [
                    {"label": "Label A", "value": "value_a"},
                    {"label": "Label B", "value": "value_b"},
                ]
            },
        },
    ]

    row_data, notification = csv_to_table(contents, column_defs)

    assert row_data == [{"col1": "value_a"}, {"col1": "value_b"}]
    assert notification is None


def test_csv_to_table_none_contents():
    """Test handling of None input contents."""
    row_data, notification = csv_to_table(None, [])

    assert row_data is no_update
    assert notification is None

import json
from datetime import date
from enum import Enum

import dash_mantine_components as dmc
from dash import Dash, Input, Output
from pydantic import BaseModel, Field
from tests.utils import (
    set_checkbox,
    set_input,
    set_select,
)

from dash_pydantic_form import ModelForm, ids

class E(Enum):
    """Test enum."""

    A = "A"
    B = "B"


class Basic(BaseModel):
    """Basic model."""

    a: int = Field(title="Field A")
    b: str = Field(title="Field A")
    c: str = Field(title="Field C", json_schema_extra={'repr_type': 'Select', 'repr_kwargs': {
        'clientside_data_getter': 'get_field_c'
    }})
    d: bool = Field(title="Field D")
    e: E = Field(title="Field E")
    f: date = Field(title="Field F")


basic_data = {"a": 1, "b": "foo", "c": "a", "d": True, "e": "B", "f": "2022-01-01"}


def test_cdg0001_clientside_data_getter(dash_duo):
    """Test a basic form, retrieving its form data."""
    app = Dash(__name__)
    item = Basic(**basic_data)
    aio_id = "basic"
    form_id = "form"
    app.layout = dmc.MantineProvider(
        [
            ModelForm(item, aio_id=aio_id, form_id=form_id),
            dmc.Text(id="output"),
        ]
    )

    @app.callback(
        Output("output", "children"),
        Input(ModelForm.ids.main(aio_id, form_id), "data"),
    )
    def display(form_data):
        return json.dumps(form_data, sort_keys=True)

    dash_duo.start_server(app)

    set_input(dash_duo, ids.value_field(aio_id, form_id, "a"), basic_data["a"])
    dash_duo.wait_for_text_to_equal("#output", json.dumps(basic_data, sort_keys=True))

    set_input(dash_duo, ids.value_field(aio_id, form_id, "a"), 123)
    set_select(dash_duo, ids.value_field(aio_id, form_id, "c"), "b")
    set_checkbox(dash_duo, ids.checked_field(aio_id, form_id, "d"), False)
    dash_duo.wait_for_text_to_equal(
        "#output", json.dumps(basic_data | {"a": 123, "c": "b", "d": False}, sort_keys=True)
    )
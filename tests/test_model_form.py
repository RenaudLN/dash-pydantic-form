import json
from datetime import date
from enum import Enum
from typing import Literal

import dash_mantine_components as dmc
from dash import Dash, _dash_renderer
from pydantic import BaseModel, Field

from dash_pydantic_form import ModelForm, ids
from tests.utils import check_elem_values, check_ids_exist, get_field_ids

_dash_renderer._set_react_version("18.2.0")
external_stylesheets = [
    "https://unpkg.com/@mantine/dates@7/styles.css",
    "https://unpkg.com/@mantine/code-highlight@7/styles.css",
    "https://unpkg.com/@mantine/charts@7/styles.css",
    "https://unpkg.com/@mantine/carousel@7/styles.css",
    "https://unpkg.com/@mantine/notifications@7/styles.css",
    "https://unpkg.com/@mantine/nprogress@7/styles.css",
]


class E(Enum):
    """Test enum."""

    A = "A"
    B = "B"


class Basic(BaseModel):
    """Basic model."""

    a: int = Field(title="Field A")
    b: str = Field(title="Field A")
    c: Literal["a", "b"] = Field(title="Field C")
    d: bool = Field(title="Field D")
    e: E = Field(title="Field E")
    f: date = Field(title="Field F")


basic_data = {"a": 1, "b": "foo", "c": "a", "d": True, "e": "B", "f": "2022-01-01"}


def test_0001_basic_form():
    """Test a basic form."""
    aio_id = "basic"
    form_id = "form"
    form = ModelForm(Basic, aio_id=aio_id, form_id=form_id)
    check_ids_exist(form, list(get_field_ids(Basic, aio_id, form_id)))
    check_elem_values(form, {json.dumps(fid): None for fid in get_field_ids(Basic, aio_id, form_id)})

    assert list(basic_data) == list(Basic.model_fields)
    item = Basic(**basic_data)
    form_filled = ModelForm(item, aio_id=aio_id, form_id=form_id)
    check_ids_exist(form_filled, list(get_field_ids(Basic, aio_id, form_id)))
    check_elem_values(
        form_filled,
        {
            json.dumps(fid): val
            for fid, val in zip(get_field_ids(Basic, aio_id, form_id), item.model_dump().values(), strict=True)
        },
    )


def test_0002_basic_form_in_browser(dash_duo):
    """Test a basic form in browser."""
    app = Dash(
        __name__, external_stylesheets=external_stylesheets, serve_locally=False, suppress_callback_exceptions=False
    )
    item = Basic(**basic_data)
    aio_id = "basic"
    form_id = "form"
    app.layout = dmc.MantineProvider(
        ModelForm(item, aio_id=aio_id, form_id=form_id),
        defaultColorScheme="dark",
    )

    dash_duo.start_server(app)
    for fid, val in zip(get_field_ids(Basic, aio_id, form_id), item.model_dump(mode="json").values(), strict=True):
        str_id = json.dumps(fid, sort_keys=True).replace(" ", "").replace('"', r"\"")
        elem = dash_duo.driver.find_element_by_id(str_id)
        if ids.value_field.args[0] in str_id:
            assert elem.get_property("value") == str(val)
        else:
            assert elem.get_property("checked") == val

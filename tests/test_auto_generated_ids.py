import json
from datetime import date
from enum import Enum
from typing import Literal

import dash_mantine_components as dmc
import pytest
from dash import Dash, Input, Output
from pydantic import BaseModel, Field

from dash_pydantic_form import ModelForm, ids
from dash_pydantic_form.model_form import rd
from tests.utils import (
    check_elem_values,
    check_ids_exist,
    get_field_ids,
    set_checkbox,
    set_input,
    set_select,
)


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


@pytest.fixture(autouse=True)
def reset_random_numbers():
    """Resets the seed so each test works as single test or in a bunch."""
    rd.seed(0)


def test_agi0001_auto_generation():
    """Test a basic form."""
    # expected values for aio_id and form_id as they are pseudo-generated but deterministic as long as
    # the "program flow" keeps the same
    aio_id = "e3e70682-c209-4cac-629f-6fbed82c07cd"
    form_id = "82e2e662-f728-b4fa-4248-5e3a0a5d2f34"

    form = ModelForm(Basic)
    assert form.id == form.ids.form  # type: ignore
    assert form.ids.form == {"part": "_pydf-form", "aio_id": aio_id, "form_id": form_id, "parent": ""}
    assert form.ids.main == {"part": "_pydf-main", "aio_id": aio_id, "form_id": form_id, "parent": ""}
    assert form.ids.errors == {"part": "_pydf-errors", "aio_id": aio_id, "form_id": form_id, "parent": ""}

    check_ids_exist(form, list(get_field_ids(Basic, aio_id, form_id)))
    check_elem_values(
        form,
        {
            json.dumps(fid): None if fid["component"] == ids.value_field.args[0] else False
            for fid in get_field_ids(Basic, aio_id, form_id)
        },
    )

    assert list(basic_data) == list(Basic.model_fields)
    # expected pseudo-random ids
    aio_id = "d4713d60-c8a7-0639-eb11-67b367a9c378"
    form_id = "23a7711a-8133-2876-37eb-dcd9e87a1613"

    item = Basic(**basic_data)
    form_filled = ModelForm(item)
    assert form_filled.ids.form["aio_id"] == aio_id
    assert form_filled.ids.form["form_id"] == form_id
    check_ids_exist(form_filled, list(get_field_ids(Basic, aio_id, form_id)))
    check_elem_values(
        form_filled,
        {
            json.dumps(fid): val
            for fid, val in zip(get_field_ids(Basic, aio_id, form_id), item.model_dump().values(), strict=True)
        },
    )


def test_agi0002_usage_in_browser_and_callback(dash_duo):
    """Test a basic form, retrieving its form data."""
    app = Dash(__name__)
    item = Basic(**basic_data)
    # expected pseudo-random ids
    aio_id = "e3e70682-c209-4cac-629f-6fbed82c07cd"
    form_id = "82e2e662-f728-b4fa-4248-5e3a0a5d2f34"

    app.layout = dmc.MantineProvider(
        [
            form := ModelForm(item),
            dmc.Text(id="output"),
        ]
    )

    @app.callback(
        Output("output", "children"),
        Input(form.ids.main, "data"),
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

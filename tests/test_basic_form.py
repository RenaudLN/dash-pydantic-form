import json
from datetime import date
from enum import Enum
from typing import Literal

import dash_mantine_components as dmc
from dash import Dash, Input, Output
from pydantic import BaseModel, Field
from selenium.webdriver.common.by import By

from dash_pydantic_form import ModelForm, fields, ids
from tests.utils import (
    check_elem_values,
    check_ids_exist,
    find_ids,
    get_field_ids,
    set_checkbox,
    set_input,
    set_select,
    stringify_id,
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


def test_bf0001_basic_form():
    """Test a basic form."""
    aio_id = "basic"
    form_id = "form"
    form = ModelForm(Basic, aio_id=aio_id, form_id=form_id)
    check_ids_exist(form, list(get_field_ids(Basic, aio_id, form_id)))
    check_elem_values(
        form,
        {
            json.dumps(fid): None if fid["component"] == ids.value_field.args[0] else False
            for fid in get_field_ids(Basic, aio_id, form_id)
        },
    )

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


def test_bf0002_basic_form_in_browser(dash_duo):
    """Test a basic form in browser."""
    app = Dash(__name__)
    item = Basic(**basic_data)
    aio_id = "basic"
    form_id = "form"
    app.layout = dmc.MantineProvider(ModelForm(item, aio_id=aio_id, form_id=form_id))

    dash_duo.start_server(app)
    for fid, val in zip(get_field_ids(Basic, aio_id, form_id), item.model_dump(mode="json").values(), strict=True):
        str_id = stringify_id(fid)
        elem = dash_duo.driver.find_element(By.ID, str_id)
        if ids.value_field.args[0] in str_id:
            assert elem.get_property("value") == str(val)
        else:
            assert elem.get_property("checked") == val


def test_bf0003_basic_form_form_data(dash_duo):
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


def test_bf0005_use_repr_types():
    """Test using repr_type and repr_kwargs in model."""

    class Basic2(BaseModel):
        """Basic model."""

        a: int = Field(title="Field A", repr_kwargs={"placeholder": "Some placeholder"})
        b: Literal["a", "b"] = Field(
            title="Field B",
            json_schema_extra={"repr_type": "RadioItems", "repr_kwargs": {"options_labels": {"a": "A", "b": "B"}}},
        )
        c: bool = Field(title="Field C", json_schema_extra={"repr_type": "Switch"})
        d: Literal["fr", "uk"] = Field(
            title="Field D",
            json_schema_extra={"repr_kwargs": {"options_labels": {"fr": "France", "uk": "United Kingdom"}}},
        )
        e: str = Field(title="Field E", json_schema_extra={"repr_type": "SomeUnknownType"})

    aio_id = "basic"
    form_id = "form"
    form = ModelForm(
        Basic2,
        aio_id=aio_id,
        form_id=form_id,
        fields_repr={
            "c": fields.Checkbox(),
            "d": {"options_labels": {"fr": "France", "uk": "Grande Bretagne"}},
        },
    )

    # Added repr_kwargs
    matches, _ = find_ids(form, [ids.value_field(aio_id, form_id, "a")], whole_elem=True)
    assert len(matches) == 1
    assert matches[0].placeholder == "Some placeholder"

    # Added non-default repr_type and repr_kwargs
    matches, _ = find_ids(form, [ids.value_field(aio_id, form_id, "b")], whole_elem=True)
    assert len(matches) == 1
    assert isinstance(matches[0], dmc.RadioGroup)
    radio1, radio2 = matches[0].children.children
    assert radio1.label == "A" and radio1.value == "a" and radio2.label == "B" and radio2.value == "b"

    # repr_type overridden in ModelForm
    matches, _ = find_ids(form, [ids.checked_field(aio_id, form_id, "c")], whole_elem=True)
    assert len(matches) == 1
    assert isinstance(matches[0], dmc.Checkbox)

    # repr_kwargs overridden in ModelForm
    matches, _ = find_ids(form, [ids.value_field(aio_id, form_id, "d")], whole_elem=True)
    assert len(matches) == 1
    assert matches[0].data == [{"label": "France", "value": "fr"}, {"label": "Grande Bretagne", "value": "uk"}]

    # Unkown repr types get the default
    matches, _ = find_ids(form, [ids.value_field(aio_id, form_id, "e")], whole_elem=True)
    assert len(matches) == 1
    assert isinstance(matches[0], dmc.TextInput)

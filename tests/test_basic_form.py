import json
from datetime import date
from enum import Enum
from typing import Literal

import dash_mantine_components as dmc
from dash import Dash, Input, Output
from dash.testing.wait import until
from pydantic import BaseModel, Field
from selenium.webdriver.common.by import By
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

from dash_pydantic_form import ModelForm, fields, ids


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


def test_bf0004_use_repr_types():
    """Test using repr_type and repr_kwargs in model."""

    class Basic2(BaseModel):
        """Basic model."""

        a: int = Field(title="Field A", json_schema_extra={"repr_kwargs": {"placeholder": "Some placeholder"}})
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


def test_bf0005_store_progress_auto(dash_duo):
    """Test that the store_progress=True option works."""
    app = Dash(__name__)
    aio_id = "basic"
    form_id = "form"
    form = ModelForm(Basic, aio_id=aio_id, form_id=form_id, store_progress="session", restore_behavior="auto")
    app.layout = dmc.MantineProvider(form)

    dash_duo.start_server(app)
    set_input(dash_duo, ids.value_field(aio_id, form_id, "a"), basic_data["a"])
    set_input(dash_duo, ids.value_field(aio_id, form_id, "b"), basic_data["b"])

    for field in ["a", "b"]:
        fid = ids.value_field(aio_id, form_id, field)
        str_id = stringify_id(fid)
        elem = dash_duo.driver.find_element(By.ID, str_id)
        assert elem.get_property("value") == str(basic_data[field])

    dash_duo.driver.refresh()
    dash_duo.wait_for_page()

    for field in ["a", "b"]:
        fid = ids.value_field(aio_id, form_id, field)
        str_id = stringify_id(fid)
        elem = dash_duo.driver.find_element(By.ID, str_id)
        assert elem.get_property("value") == str(basic_data[field])

    set_input(dash_duo, ids.value_field(aio_id, form_id, "b"), "test")
    assert elem.get_property("value") == "test"


def test_bf0006_store_progress_notify(dash_duo):
    """Test that the store_progress=True option works."""
    app = Dash(__name__)
    aio_id = "basic"
    form_id = "form"
    form = ModelForm(Basic, aio_id=aio_id, form_id=form_id, store_progress="session", restore_behavior="notify")
    app.layout = dmc.MantineProvider(form)

    dash_duo.start_server(app)
    set_input(dash_duo, ids.value_field(aio_id, form_id, "a"), basic_data["a"])
    set_input(dash_duo, ids.value_field(aio_id, form_id, "b"), basic_data["b"])

    for field in ["a", "b"]:
        fid = ids.value_field(aio_id, form_id, field)
        str_id = stringify_id(fid)
        until(
            lambda str_id=str_id, field=field: dash_duo.driver.find_element(By.ID, str_id).get_property("value")
            == str(basic_data[field]),
            timeout=3,
        )

    dash_duo.driver.refresh()
    dash_duo.wait_for_page()

    elem = dash_duo.driver.find_element(By.ID, stringify_id(form.ids.restore_btn))
    elem.click()

    for field in ["a", "b"]:
        fid = ids.value_field(aio_id, form_id, field)
        str_id = stringify_id(fid)
        until(
            lambda str_id=str_id, field=field: dash_duo.driver.find_element(By.ID, str_id).get_property("value")
            == str(basic_data[field]),
            timeout=3,
        )

    dash_duo.driver.refresh()
    dash_duo.wait_for_page()

    elem = dash_duo.driver.find_element(By.ID, stringify_id(form.ids.cancel_restore_btn))
    elem.click()

    for field in ["a", "b"]:
        fid = ids.value_field(aio_id, form_id, field)
        str_id = stringify_id(fid)
        elem = dash_duo.driver.find_element(By.ID, str_id)
        assert elem.get_property("value") == ""


def test_bf0007_nested_fields_repr():
    """Test nested fields_repr."""

    class Nested(BaseModel):
        val: str

    class Basic(BaseModel):
        a: Nested | None = None
        b: list[Nested] = Field(default_factory=list)
        c: list[Nested] = Field(default_factory=list)

    form = ModelForm(
        Basic(
            a=Nested(val="1"),
            b=[Nested(val="2"), Nested(val="3")],
            c=[Nested(val="1"), Nested(val="3")],
        ),
        aio_id="basic",
        form_id="form",
        fields_repr={
            "a": fields.Model(fields_repr={"val": fields.Select(data=["1", "2", "3"])}),
            "b": fields.List(fields_repr={"val": fields.Select(data=["1", "2", "3"])}),
            "c": fields.Table(fields_repr={"val": fields.Select(data=["1", "2", "3"])}),
        },
    )

    assert isinstance(form[ids.value_field("basic", "form", "val", "a")], dmc.Select)
    assert form[ids.value_field("basic", "form", "val", "a")].data == ["1", "2", "3"]
    assert isinstance(form[ids.value_field("basic", "form", "val", "b:1")], dmc.Select)
    assert form[fields.Table.ids.editable_table("basic", "form", "c")].columnDefs[1]["cellEditorParams"]["options"] == [
        {"label": o, "value": o} for o in ["1", "2", "3"]
    ]

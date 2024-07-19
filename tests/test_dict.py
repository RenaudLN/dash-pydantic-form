import json
from datetime import date, time

import dash_mantine_components as dmc
from dash import Dash, Input, Output
from pydantic import BaseModel, Field
from selenium.webdriver.common.by import By

from dash_pydantic_form import ModelForm, fields, ids
from tests.utils import (
    check_ids_exist,
    set_input,
    stringify_id,
)


def test_di0001_basic_dict(dash_duo):
    """Test a basic list."""

    class Basic(BaseModel):
        a: dict[str, int] = Field(title="Dict", default_factory=dict)

    app = Dash(__name__)
    aio_id = "aio"
    form_id = "form"
    app.layout = dmc.MantineProvider(
        [
            ModelForm(Basic, aio_id=aio_id, form_id=form_id),
            dmc.Text(id="output"),
        ],
    )
    check_ids_exist(
        app.layout,
        [fields.List.ids.add(aio_id, form_id, "a")],
    )

    @app.callback(
        Output("output", "children"),
        Input(ModelForm.ids.main(aio_id, form_id), "data"),
    )
    def display(form_data):
        return json.dumps(form_data)

    dash_duo.start_server(app)

    dash_duo.wait_for_text_to_equal("#output", "{}")
    add_btn = dash_duo.driver.find_element(By.ID, stringify_id(fields.List.ids.add(aio_id, form_id, "a")))
    add_btn.click()
    set_input(dash_duo, ids.value_field(aio_id, form_id, "0", parent="a"), 123)
    set_input(dash_duo, fields.Dict.ids.item_key(aio_id, form_id, "a", meta="0"), "aa")
    dash_duo.wait_for_text_to_equal("#output", '{"a": {"aa": 123}}')
    add_btn.click()
    set_input(dash_duo, fields.Dict.ids.item_key(aio_id, form_id, "a", meta="1"), "bb")
    set_input(dash_duo, ids.value_field(aio_id, form_id, "1", parent="a"), 456)
    dash_duo.wait_for_text_to_equal("#output", '{"a": {"aa": 123, "bb": 456}}')

    del_btn0 = dash_duo.driver.find_element(By.ID, stringify_id(fields.List.ids.delete(aio_id, form_id, "a", meta="0")))
    # 2 clicks required, on to bring to the foreground one to actually click
    del_btn0.click()
    del_btn0.click()
    dash_duo.wait_for_text_to_equal("#output", '{"a": {"bb": 456}}')


def test_di0002_dict_all_scalar_types(dash_duo):
    """Test a list of all scalar types."""

    class Basic(BaseModel):
        a: dict[str, int]
        b: dict[str, str]
        c: dict[str, date]
        d: dict[str, time]

    app = Dash(__name__)
    item = Basic(
        a={"int0": 1, "int1": 2},
        b={"str0": "a", "str1": "b"},
        c={"date0": date(2020, 1, 1), "date1": date(2020, 1, 2)},
        d={"time0": "12:00", "time1": "13:00"},
    )
    aio_id = "aio"
    form_id = "form"
    app.layout = dmc.MantineProvider(
        [
            ModelForm(item, aio_id=aio_id, form_id=form_id),
            dmc.Text(id="output"),
        ],
    )

    @app.callback(
        Output("output", "children"),
        Input(ModelForm.ids.main(aio_id, form_id), "data"),
    )
    def display(form_data):
        return json.dumps(form_data)

    dash_duo.start_server(app)

    dash_duo.wait_for_text_to_equal(
        "#output",
        '{"a": {"int0": 1, "int1": 2}, "b": {"str0": "a", "str1": "b"}, '
        '"c": {"date0": "2020-01-01", "date1": "2020-01-02"}, '
        '"d": {"time0": "2000-01-01T12:00:00", "time1": "2000-01-01T13:00:00"}}',
    )


def test_di0003_model_dict(dash_duo):
    """Test a model list."""

    class Nested(BaseModel):
        b: dict[str, str] = Field(default_factory=dict)

    class Basic(BaseModel):
        a: dict[str, Nested] = Field(default_factory=dict)

    app = Dash(__name__)
    item = Basic()
    aio_id = "aio"
    form_id = "form"
    app.layout = dmc.MantineProvider(
        [
            ModelForm(item, aio_id=aio_id, form_id=form_id),
            dmc.Text(id="output"),
        ],
    )

    @app.callback(
        Output("output", "children"),
        Input(ModelForm.ids.main(aio_id, form_id), "data"),
    )
    def display(form_data):
        return json.dumps(form_data, sort_keys=True)

    dash_duo.start_server(app)

    dash_duo.wait_for_text_to_equal("#output", "{}")

    dash_duo.driver.find_element(By.ID, stringify_id(fields.List.ids.add(aio_id, form_id, "a"))).click()
    dash_duo.driver.find_element(By.CSS_SELECTOR, ".mantine-Accordion-control").click()
    dash_duo.driver.find_element(By.ID, stringify_id(fields.List.ids.add(aio_id, form_id, "b", parent="a:0"))).click()
    set_input(dash_duo, ids.value_field(aio_id, form_id, "0", parent="a:0:b"), 1)
    set_input(dash_duo, fields.Dict.ids.item_key(aio_id, form_id, "a", meta="0"), "a0")
    set_input(dash_duo, fields.Dict.ids.item_key(aio_id, form_id, "b", parent="a:0", meta="0"), "b0")
    dash_duo.wait_for_text_to_equal("#output", '{"a": {"a0": {"b": {"b0": "1"}}}}')

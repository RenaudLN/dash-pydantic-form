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


def test_li0001_basic_list(dash_duo):
    """Test a basic list."""

    class Basic(BaseModel):
        a: list[int] = Field(title="List", default_factory=list)

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
    dash_duo.wait_for_text_to_equal("#output", '{"a": [123]}')
    add_btn.click()
    dash_duo.wait_for_text_to_equal("#output", '{"a": [123, null]}')
    set_input(dash_duo, ids.value_field(aio_id, form_id, "1", parent="a"), 456)
    dash_duo.wait_for_text_to_equal("#output", '{"a": [123, 456]}')

    del_btn0 = dash_duo.driver.find_element(By.ID, stringify_id(fields.List.ids.delete(aio_id, form_id, "a", meta="0")))
    # 2 clicks required, on to bring to the foreground one to actually click
    del_btn0.click()
    del_btn0.click()
    dash_duo.wait_for_text_to_equal("#output", '{"a": [456]}')


def test_li0002_list_all_scalar_types(dash_duo):
    """Test a list of all scalar types."""

    class Basic(BaseModel):
        a: list[int]
        b: list[str]
        c: list[date]
        d: list[time]

    app = Dash(__name__)
    item = Basic(
        a=[1, 2, 3],
        b=["a", "b", "c"],
        c=[date(2020, 1, 1), date(2020, 1, 2), date(2020, 1, 3)],
        d=[time(12, 0), time(13, 0), time(14, 0)],
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
        '{"a": [1, 2, 3], "b": ["a", "b", "c"], "c": ["2020-01-01", "2020-01-02", "2020-01-03"], '
        '"d": ["2000-01-01T12:00:00", "2000-01-01T13:00:00", "2000-01-01T14:00:00"]}',
    )


def test_li0003_model_list(dash_duo):
    """Test a model list."""

    class Nested2(BaseModel):
        bb: str = ""

    class Nested(BaseModel):
        aa: list[str] = Field(default_factory=list)

    class Basic(BaseModel):
        a: list[Nested] = Field(default_factory=list)
        b: Nested2 = Field(default_factory=Nested2)

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

    dash_duo.wait_for_text_to_equal("#output", '{"b": {"bb": ""}}')

    dash_duo.driver.find_element(By.ID, stringify_id(fields.List.ids.add(aio_id, form_id, "a"))).click()
    dash_duo.driver.find_element(By.CSS_SELECTOR, ".mantine-Accordion-control").click()
    dash_duo.driver.find_element(By.ID, stringify_id(fields.List.ids.add(aio_id, form_id, "aa", parent="a:0"))).click()
    set_input(dash_duo, ids.value_field(aio_id, form_id, "0", parent="a:0:aa"), 1)
    dash_duo.wait_for_text_to_equal("#output", '{"a": [{"aa": ["1"]}], "b": {"bb": ""}}')

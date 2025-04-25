import json

import dash_mantine_components as dmc
from dash import Dash, Input, Output
from pydantic import BaseModel, RootModel
from selenium.webdriver.common.by import By
from tests.utils import (
    check_ids_exist,
    set_input,
    stringify_id,
)

from dash_pydantic_form import ModelForm, fields, ids

ROOT_FIELD = "rootmodel_root_"


def test_rm0001_root_model_list_scalar(dash_duo):
    """Test a form with a simple RootModel."""
    Files = RootModel[list[str]]

    aio_id = "test"
    form_id = "test"
    form = ModelForm(Files, aio_id=aio_id, form_id=form_id)
    app = Dash(__name__)
    app.layout = dmc.MantineProvider([form, dmc.Text(id="output")])
    check_ids_exist(
        app.layout,
        [fields.List.ids.add(aio_id, form_id, ROOT_FIELD)],
    )

    @app.callback(
        Output("output", "children"),
        Input(ModelForm.ids.main(aio_id, form_id), "data"),
    )
    def display(form_data):
        return json.dumps(form_data)

    dash_duo.start_server(app)
    add_btn = dash_duo.driver.find_element(By.ID, stringify_id(fields.List.ids.add(aio_id, form_id, ROOT_FIELD)))
    add_btn.click()
    set_input(dash_duo, ids.value_field(aio_id, form_id, "0", parent=ROOT_FIELD), "123")
    dash_duo.wait_for_text_to_equal("#output", '["123"]')


def test_rm0002_root_model_list_model(dash_duo):
    """Test a form with a simple RootModel."""

    class File(BaseModel):
        name: str
        path: str

    Files = RootModel[list[File]]

    aio_id = "test"
    form_id = "test"
    form = ModelForm(Files, aio_id=aio_id, form_id=form_id)
    app = Dash(__name__)
    app.layout = dmc.MantineProvider([form, dmc.Text(id="output")])
    check_ids_exist(
        app.layout,
        [fields.List.ids.add(aio_id, form_id, ROOT_FIELD)],
    )

    @app.callback(
        Output("output", "children"),
        Input(ModelForm.ids.main(aio_id, form_id), "data"),
    )
    def display(form_data):
        return json.dumps(form_data)

    dash_duo.start_server(app)
    add_btn = dash_duo.driver.find_element(By.ID, stringify_id(fields.List.ids.add(aio_id, form_id, ROOT_FIELD)))
    add_btn.click()
    set_input(dash_duo, ids.value_field(aio_id, form_id, "name", parent=f"{ROOT_FIELD}:0"), "Test file")
    set_input(dash_duo, ids.value_field(aio_id, form_id, "path", parent=f"{ROOT_FIELD}:0"), "/home/test/test.txt")
    dash_duo.wait_for_text_to_equal("#output", '[{"name": "Test file", "path": "/home/test/test.txt"}]')


def test_rm003_root_model_as_annotation(dash_duo):
    """Test a form with RootModel used as annotation in a BaseModel."""
    Files = RootModel[list[str]]

    class Folder(BaseModel):
        name: str
        files: Files

    aio_id = "test"
    form_id = "test"
    form = ModelForm(Folder, aio_id=aio_id, form_id=form_id)
    app = Dash(__name__)
    app.layout = dmc.MantineProvider([form, dmc.Text(id="output")])

    check_ids_exist(
        app.layout,
        [fields.List.ids.add(aio_id, form_id, ROOT_FIELD, "files")],
    )

    @app.callback(
        Output("output", "children"),
        Input(ModelForm.ids.main(aio_id, form_id), "data"),
    )
    def display(form_data):
        return json.dumps(form_data)

    dash_duo.start_server(app)
    add_btn = dash_duo.driver.find_element(
        By.ID, stringify_id(fields.List.ids.add(aio_id, form_id, ROOT_FIELD, "files"))
    )
    add_btn.click()
    set_input(dash_duo, ids.value_field(aio_id, form_id, "0", parent=f"files:{ROOT_FIELD}"), "Test file")
    set_input(dash_duo, ids.value_field(aio_id, form_id, "name"), "Home folder")
    dash_duo.wait_for_text_to_equal("#output", '{"name": "Home folder", "files": ["Test file"]}')

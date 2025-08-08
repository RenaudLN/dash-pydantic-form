import json
from typing import Any

import dash_mantine_components as dmc
import flask
from dash import Dash, Input, Output, html
from pydantic import BaseModel, create_model
from selenium.webdriver.common.by import By

from dash_pydantic_form import ModelForm
from dash_pydantic_utils import DEV_CONFIG


def create_employees_model():
    """Create a simple Employees model."""
    employee = create_model(
        "Employee",
        name=(str, ...),
        age=(int, ...),
        is_active=(bool, True),
    )

    return create_model(
        "Employees",
        employees=(list[employee], ...),
    )


called = {"value": False}


def find_model_class_test(model_name: str):
    """Find and return the Employees model class."""
    called["value"] = True
    if model_name == "Employees":
        return create_employees_model()
    return None


DEV_CONFIG["find_model_class"] = find_model_class_test


def test_dmr0001_dynamic_model_recall(dash_duo):
    """Test a form with a simple RootModel."""

    class Employees(BaseModel):
        name: str

    aio_id = "test"
    form_id = "test"
    form = ModelForm(Employees, aio_id=aio_id, form_id=form_id)
    app = Dash(__name__)
    app.layout = dmc.MantineProvider(
        [
            form,
            dmc.Button("Load Saved Data", id="load-saved-data", variant="outline"),
            dmc.Text(id="output"),
        ]
    )

    @app.callback(
        Output(ModelForm.ids.form(aio_id, form_id), "data-update", allow_duplicate=True),
        Input("load-saved-data", "n_clicks"),
        prevent_initial_call=True,
    )
    def load_saved_data(_: int) -> Any:
        """Load saved data into the form."""
        # Simulate loading data from a source
        saved_data = {"employees": [{"name": "John Doe"}]}
        return saved_data

    @app.callback(
        Output("output", "children"),
        Input(ModelForm.ids.main(aio_id, form_id), "data"),
    )
    def display(form_data):
        return json.dumps(form_data)

    dash_duo.start_server(app)
    load_btn = dash_duo.driver.find_element(By.ID, "load-saved-data")
    load_btn.click()
    dash_duo.wait_for_text_to_equal("#output", '{"employees": [{"name": "John Doe", "is_active": true}]}', timeout=10)
    assert called["value"], "find_model_class_test should have been called"


def test_dmr0002_dynamic_model_recall(dash_duo):
    """Test a form with a simple RootModel."""
    app = Dash(__name__)
    aio_id = "test"
    form_id = "test"

    def layout():
        """Define the layout of the app."""
        if not flask.request:
            return html.Div("This test requires a Flask request context.")

        form = ModelForm(create_employees_model(), aio_id=aio_id, form_id=form_id)
        return dmc.MantineProvider(
            [
                form,
                dmc.Button("Load Saved Data", id="load-saved-data", variant="outline"),
                dmc.Text(id="output"),
            ]
        )

    app.layout = layout

    @app.callback(
        Output(ModelForm.ids.form(aio_id, form_id), "data-update", allow_duplicate=True),
        Input("load-saved-data", "n_clicks"),
        prevent_initial_call=True,
    )
    def load_saved_data(_: int) -> Any:
        """Load saved data into the form."""
        # Simulate loading data from a source
        saved_data = {"employees": [{"name": "John Doe"}]}
        return saved_data

    @app.callback(
        Output("output", "children"),
        Input(ModelForm.ids.main(aio_id, form_id), "data"),
    )
    def display(form_data):
        return json.dumps(form_data)

    dash_duo.start_server(app)
    port = dash_duo.server.port
    dash_duo.driver.find_element(By.ID, "load-saved-data")
    dash_duo.server.stop()
    dash_duo.server.start(app, port=port)
    import time

    time.sleep(5)  # Allow the server to start properly
    load_btn = dash_duo.driver.find_element(By.ID, "load-saved-data")
    load_btn.click()
    dash_duo.wait_for_text_to_equal("#output", '{"employees": [{"name": "John Doe", "is_active": true}]}', timeout=10)
    assert called["value"], "find_model_class_test should have been called"

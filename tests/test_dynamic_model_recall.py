import json
from typing import Any

import dash_mantine_components as dmc
import flask
from dash import Dash, Input, Output, html
from pydantic import BaseModel, Field, create_model
from selenium.webdriver.common.by import By

from dash_pydantic_form import ModelForm
from dash_pydantic_utils import DEV_CONFIG

called = {"value": False}

cached_models = {
    "Employees1": {
        "$defs": {
            "Employee1": {
                "properties": {
                    "name": {"title": "Name", "type": "string"},
                    "age": {"title": "Age", "type": "integer"},
                    "is_active": {"default": True, "title": "Is Active", "type": "boolean"},
                },
                "required": ["name", "age"],
                "title": "Employee1",
                "type": "object",
            }
        },
        "properties": {"employees": {"items": {"$ref": "#/$defs/Employee1"}, "title": "Employees", "type": "array"}},
        "required": ["employees"],
        "title": "Employees1",
        "type": "object",
    }
}


def find_model_class_test(model_name: str):
    """Find and return the Employees model class."""
    called["value"] = True
    if model_name == "Employees":
        return create_employees_model()
    return None


DEV_CONFIG["find_model_class"] = find_model_class_test


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


def cache_model_and_dependencies(model, cache):
    """Cache the model and its JSON schema, including definitions."""
    schema = model.model_json_schema()
    cache[model.__name__] = schema
    definitions = schema.get("definitions", {})
    for def_name, def_schema in definitions.items():
        if def_name not in cache:
            cache[def_name] = def_schema


def reconstruct_model_from_schema(schema, definitions):
    """Reconstruct a Pydantic model from a JSON schema."""
    type_map = {
        "string": str,
        "integer": int,
        "number": float,
        "boolean": bool,
        "object": dict,
        "array": list,
        "null": type(None),
        "any": object,
    }
    fields = {}
    for field_name, field_info in schema.get("properties", {}).items():
        if "$ref" in field_info:
            ref = field_info["$ref"].split("/")[-1]
            nested_schema = definitions[ref]
            py_type = reconstruct_model_from_schema(nested_schema, definitions)
        elif field_info.get("type") == "array" and "items" in field_info:
            items = field_info["items"]
            if "$ref" in items:
                ref = items["$ref"].split("/")[-1]
                item_model = reconstruct_model_from_schema(definitions[ref], definitions)
                py_type = list[item_model]
            else:
                py_type = list
        else:
            py_type = type_map.get(field_info.get("type"), str)
        field_args = {k: v for k, v in field_info.items() if k not in ("type", "items", "title", "$ref")}
        fields[field_name] = (py_type, Field(**field_args))
    return create_model(schema["title"], **fields)


def test_dmr0001_dynamic_model_recall(dash_duo):
    """Test a form with a simple dynamic model."""

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
    """Test a form with a simple dynamic model that reloads from a cached schema."""

    # Function to find and load model from cache
    def find_cached_model_class(model_name: str):
        """Find and return a cached model class by its name."""
        cached_model = cached_models.get(model_name)
        if cached_model:
            called["value"] = True
            return reconstruct_model_from_schema(cached_model, cached_model.get("$defs", {}))
        return None

    DEV_CONFIG["find_model_class"] = find_cached_model_class

    app = Dash(__name__, suppress_callback_exceptions=True)
    aio_id = "test"
    form_id = "test"

    class BasicForm(BaseModel):
        name: str

    app.layout = dmc.MantineProvider(
        [
            ModelForm(BasicForm, aio_id=aio_id, form_id=form_id),
            dmc.Button("Load Saved Data", id="load-saved-data", variant="outline"),
            dmc.Text(id="output"),
        ]
    )

    @app.callback(
        Output(ModelForm.ids.form(aio_id, form_id), "data-update", allow_duplicate=True),
        Output(ModelForm.ids.model_store(aio_id, form_id), "data", allow_duplicate=True),
        Input("load-saved-data", "n_clicks"),
        prevent_initial_call=True,
    )
    def load_saved_data(_: int) -> Any:
        """Load saved data into the form."""
        # Simulate loading data from a source
        saved_data = {"employees": [{"name": "John Doe"}]}
        return saved_data, "Employees1"

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

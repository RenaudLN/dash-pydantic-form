from typing import Literal

import dash_mantine_components as dmc
from dash import Dash
from pydantic import BaseModel, Field

from dash_pydantic_form import ModelForm, ids
from tests.utils import (
    check_ids_absent,
    check_ids_exist,
    set_checkbox,
    set_input,
    set_select,
)


def test_du0001_basic_discriminated_union(dash_duo):
    """Test a basic discriminated union."""

    class Cat(BaseModel):
        species: Literal["cat"]
        meows: bool = True

    class Dog(BaseModel):
        species: Literal["dog"]
        barks: bool = True

    class Basic(BaseModel):
        pet: Cat | Dog | None = Field(title="Pet", discriminator="species", default=None)

    app = Dash(__name__)
    item = Basic()
    aio_id = "basic"
    form_id = "form"
    app.layout = dmc.MantineProvider(ModelForm(item, aio_id=aio_id, form_id=form_id))
    check_ids_absent(
        app.layout,
        [
            ids.checked_field(aio_id, form_id, "meows", parent="pet"),
            ids.checked_field(aio_id, form_id, "barks", parent="pet"),
        ],
    )

    dash_duo.start_server(app)
    set_select(dash_duo, ids.value_field(aio_id, form_id, "species", parent="pet", meta="discriminator"), "cat")
    set_checkbox(dash_duo, ids.checked_field(aio_id, form_id, "meows", parent="pet"), False)
    set_select(dash_duo, ids.value_field(aio_id, form_id, "species", parent="pet", meta="discriminator"), "dog")
    set_checkbox(dash_duo, ids.checked_field(aio_id, form_id, "barks", parent="pet"), False)


def test_du0002_discriminated_union_nested(dash_duo):
    """Test a discriminated union nested in a model."""

    class Cat(BaseModel):
        species: Literal["cat"]
        meows: bool = True

    class Dog(BaseModel):
        species: Literal["dog"]
        barks: bool = True

    class Nested(BaseModel):
        pet: Cat | Dog | None = Field(title="Pet", discriminator="species", default=None)

    class Basic(BaseModel):
        nested: Nested

    app = Dash(__name__)
    item = Basic(nested={"pet": {"species": "cat"}})
    aio_id = "basic"
    form_id = "form"
    app.layout = dmc.MantineProvider(ModelForm(item, aio_id=aio_id, form_id=form_id))
    check_ids_exist(
        app.layout,
        [ids.checked_field(aio_id, form_id, "meows", parent="nested:pet")],
    )
    dash_duo.start_server(app)
    set_checkbox(dash_duo, ids.checked_field(aio_id, form_id, "meows", parent="nested:pet"), False)
    set_select(dash_duo, ids.value_field(aio_id, form_id, "species", parent="nested:pet", meta="discriminator"), "dog")
    set_checkbox(dash_duo, ids.checked_field(aio_id, form_id, "barks", parent="nested:pet"), False)


def test_du0003_discriminated_union_with_nested_submodel(dash_duo):
    """Test a discriminated union with a nested submodel."""

    class CatOptions(BaseModel):
        meows: bool = True

    class DogOptions(BaseModel):
        barks: bool = True

    class Cat(BaseModel):
        species: Literal["cat"]
        options: CatOptions = Field(default_factory=CatOptions)

    class Dog(BaseModel):
        species: Literal["dog"]
        options: DogOptions = Field(default_factory=DogOptions)

    class Basic(BaseModel):
        pet: Cat | Dog | None = Field(title="Pet", discriminator="species", default=None)

    app = Dash(__name__)
    item = Basic(pet={"species": "cat"})
    aio_id = "basic"
    form_id = "form"
    app.layout = dmc.MantineProvider(ModelForm(item, aio_id=aio_id, form_id=form_id))
    check_ids_exist(
        app.layout,
        [ids.checked_field(aio_id, form_id, "meows", parent="pet:options")],
    )

    dash_duo.start_server(app)
    set_checkbox(dash_duo, ids.checked_field(aio_id, form_id, "meows", parent="pet:options"), False)
    set_select(dash_duo, ids.value_field(aio_id, form_id, "species", parent="pet", meta="discriminator"), "dog")
    set_checkbox(dash_duo, ids.checked_field(aio_id, form_id, "barks", parent="pet:options"), False)


def test_du004_discriminated_in_discriminated(dash_duo):
    """Test a model with nesting of discriminated unions."""

    class BlackOptions(BaseModel):
        color: Literal["black"]
        a: str = "A"

    class OrangeOptions(BaseModel):
        color: Literal["orange"]
        b: str = "B"

    class Cat(BaseModel):
        species: Literal["cat"]
        options: BlackOptions | OrangeOptions | None = Field(discriminator="color", default=None)

    class Dog(BaseModel):
        species: Literal["dog"]
        barks: bool = True

    class Basic(BaseModel):
        pet: Cat | Dog | None = Field(title="Pet", discriminator="species", default=None)

    app = Dash(__name__)
    item = Basic(pet={"species": "cat", "options": {"color": "black"}})
    aio_id = "basic"
    form_id = "form"
    app.layout = dmc.MantineProvider(ModelForm(item, aio_id=aio_id, form_id=form_id))
    check_ids_exist(
        app.layout,
        [
            ids.value_field(aio_id, form_id, "a", parent="pet:options"),
            ids.value_field(aio_id, form_id, "color", parent="pet:options", meta="discriminator"),
            ids.value_field(aio_id, form_id, "species", parent="pet", meta="discriminator"),
        ],
    )

    dash_duo.start_server(app)
    set_input(dash_duo, ids.value_field(aio_id, form_id, "a", parent="pet:options"), "123")
    set_select(
        dash_duo, ids.value_field(aio_id, form_id, "color", parent="pet:options", meta="discriminator"), "orange"
    )
    set_input(dash_duo, ids.value_field(aio_id, form_id, "b", parent="pet:options"), "456")
    set_select(dash_duo, ids.value_field(aio_id, form_id, "species", parent="pet", meta="discriminator"), "dog")
    set_checkbox(dash_duo, ids.checked_field(aio_id, form_id, "barks", parent="pet"), False)

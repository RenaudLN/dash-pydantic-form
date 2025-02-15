import time
from typing import Annotated, Literal

import dash_mantine_components as dmc
from dash import Dash
from pydantic import BaseModel, Field
from selenium.webdriver.common.by import By
from tests.utils import (
    check_ids_absent,
    check_ids_exist,
    set_checkbox,
    set_input,
    set_select,
    stringify_id,
)

from dash_pydantic_form import ModelForm, fields, ids


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


def test_du0005_list_nested_discriminated_union(dash_duo):
    """Test a list of nested models with discriminated union field."""

    class Cat(BaseModel):
        species: Literal["cat"]
        meows: bool = True

    class Dog(BaseModel):
        species: Literal["dog"]
        barks: bool = True

    class Nested(BaseModel):
        pet: Cat | Dog | None = Field(title="Pet", discriminator="species", default=None)

    class Basic(BaseModel):
        nested: list[Nested] = Field(default_factory=list)

    app = Dash(__name__)
    item = Basic(nested=[{"pet": {"species": "cat"}}])
    aio_id = "basic"
    form_id = "form"
    app.layout = dmc.MantineProvider(ModelForm(item, aio_id=aio_id, form_id=form_id))
    check_ids_exist(
        app.layout,
        [ids.checked_field(aio_id, form_id, "meows", parent="nested:0:pet")],
    )
    dash_duo.start_server(app)
    dash_duo.driver.find_element(By.CSS_SELECTOR, ".mantine-Accordion-control").click()
    set_checkbox(dash_duo, ids.checked_field(aio_id, form_id, "meows", parent="nested:0:pet"), False)
    set_select(
        dash_duo, ids.value_field(aio_id, form_id, "species", parent="nested:0:pet", meta="discriminator"), "dog"
    )
    set_checkbox(dash_duo, ids.checked_field(aio_id, form_id, "barks", parent="nested:0:pet"), False)


def test_du0006_list_discriminated_union(dash_duo):
    """Test a list of discriminated unions."""

    class Cat(BaseModel):
        species: Literal["cat"]
        meows: bool = True

    class Dog(BaseModel):
        species: Literal["dog"]
        barks: bool = True

    class Basic(BaseModel):
        pets: list[Annotated[Cat | Dog, Field(discriminator="species")]] = Field(default_factory=list)

    app = Dash(__name__)
    item = Basic(pets=[{"species": "cat"}])
    aio_id = "basic"
    form_id = "form"
    app.layout = dmc.MantineProvider(ModelForm(item, aio_id=aio_id, form_id=form_id))
    check_ids_exist(
        app.layout,
        [ids.checked_field(aio_id, form_id, "meows", parent="pets:0")],
    )
    dash_duo.start_server(app)
    dash_duo.driver.find_element(By.CSS_SELECTOR, ".mantine-Accordion-control").click()
    set_checkbox(dash_duo, ids.checked_field(aio_id, form_id, "meows", parent="pets:0"), False)
    set_select(dash_duo, ids.value_field(aio_id, form_id, "species", parent="pets:0", meta="discriminator"), "dog")
    set_checkbox(dash_duo, ids.checked_field(aio_id, form_id, "barks", parent="pets:0"), False)


def test_du0007_top_level_union(dash_duo):
    """Test a top level discriminated union."""

    class Cat(BaseModel):
        species: Literal["cat"] = "cat"
        meows: bool = True

    class Dog(BaseModel):
        species: Literal["dog"] = "dog"
        barks: bool = True

    PetUnion = Annotated[Cat | Dog, Field(discriminator="species")]

    app = Dash(__name__)
    aio_id = "basic"
    form_id = "form"
    app.layout = dmc.MantineProvider(ModelForm(Cat(), aio_id=aio_id, form_id=form_id, data_model=PetUnion))
    check_ids_exist(
        app.layout,
        [ids.checked_field(aio_id, form_id, "meows", parent="")],
    )
    dash_duo.start_server(app)
    set_checkbox(dash_duo, ids.checked_field(aio_id, form_id, "meows", parent=""), False)
    set_select(dash_duo, ids.value_field(aio_id, form_id, "species", parent="", meta="discriminator"), "dog")
    set_checkbox(dash_duo, ids.checked_field(aio_id, form_id, "barks", parent=""), False)


def test_du0008_list_union_in_list_union(dash_duo):
    """Test a list of discriminated unions in a list of discriminated unions."""

    class Cat(BaseModel):
        species: Literal["cat"]
        meows: bool = True

    class Dog(BaseModel):
        species: Literal["dog"]
        barks: bool = True

    class Base1(BaseModel):
        kind: Literal["base1"] = "base1"
        pets: list[Annotated[Cat | Dog, Field(discriminator="species")]] = Field(default_factory=list)

    class Base2(BaseModel):
        kind: Literal["base2"] = "base2"
        name: str
        pets: list[Annotated[Cat | Dog, Field(discriminator="species")]] = Field(default_factory=list)

    class Wrapper(BaseModel):
        bases: list[Annotated[Base1 | Base2, Field(discriminator="kind")]] = Field(default_factory=list)

    app = Dash(__name__)
    item = Wrapper(bases=[{"kind": "base1", "pets": [{"species": "cat"}]}])
    aio_id = "basic"
    form_id = "form"
    app.layout = dmc.MantineProvider(ModelForm(item, aio_id=aio_id, form_id=form_id))
    check_ids_exist(
        app.layout,
        [ids.checked_field(aio_id, form_id, "meows", parent="bases:0:pets:0")],
    )
    dash_duo.start_server(app)
    for elem in dash_duo.driver.find_elements(By.CSS_SELECTOR, ".mantine-Accordion-control"):
        elem.click()
    set_checkbox(dash_duo, ids.checked_field(aio_id, form_id, "meows", parent="bases:0:pets:0"), False)
    set_select(
        dash_duo, ids.value_field(aio_id, form_id, "species", parent="bases:0:pets:0", meta="discriminator"), "dog"
    )
    set_checkbox(dash_duo, ids.checked_field(aio_id, form_id, "barks", parent="bases:0:pets:0"), False)

    add_base_btn = dash_duo.driver.find_element(By.ID, stringify_id(fields.List.ids.add(aio_id, form_id, "bases")))
    add_base_btn.click()
    time.sleep(0.5)
    set_select(dash_duo, ids.value_field(aio_id, form_id, "kind", parent="bases:1", meta="discriminator"), "base2")
    set_input(dash_duo, ids.value_field(aio_id, form_id, "name", parent="bases:1"), "yay")

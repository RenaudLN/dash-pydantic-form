# ruff: noqa
from typing import Annotated, Literal

import dash_mantine_components as dmc
from dash import Dash, _dash_renderer
from pydantic import BaseModel, Field

from dash_pydantic_form import ModelForm
from dash_pydantic_form.quantity import Quantity

_dash_renderer._set_react_version("18.2.0")
app = Dash(
    __name__,
    external_stylesheets=[
        "https://unpkg.com/@mantine/dates@7/styles.css",
        "https://unpkg.com/@mantine/code-highlight@7/styles.css",
        "https://unpkg.com/@mantine/charts@7/styles.css",
        "https://unpkg.com/@mantine/carousel@7/styles.css",
        "https://unpkg.com/@mantine/notifications@7/styles.css",
        "https://unpkg.com/@mantine/nprogress@7/styles.css",
    ],
)

server = app.server


class Pet(BaseModel):
    species: str
    name: str
    age: Quantity = Field(
        repr_kwargs={"unit_options": ["%", "MW"], "read_only": True},
        repr_type="Quantity",
        default_factory=lambda: Quantity(100, "%"),
    )


class Dog(Pet):
    species: Literal["dog"]
    barks: bool = Field(repr_kwargs={"n_cols": 1.0}, default=True)


class Cat(Pet):
    species: Literal["cat"]
    meows: bool = Field(repr_kwargs={"n_cols": 1.0}, default=True)


class Person(BaseModel):
    # name: str
    # age: int
    pets: dict[str, Annotated[Dog | Cat, Field(discriminator="species")]] = Field(default_factory=list)


app.layout = dmc.MantineProvider(dmc.Container(ModelForm(Person, aio_id="person", form_id="form"), py="xl"))


if __name__ == "__main__":
    app.run(debug=True)

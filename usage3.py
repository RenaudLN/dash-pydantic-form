# ruff: noqa
from typing import Annotated, Literal

import dash_mantine_components as dmc
from dash import Dash
from pydantic import BaseModel, Field

from dash_pydantic_form import ModelForm, fields


class Pet(BaseModel):
    species: str
    name: str


class Cat(Pet):
    species: Literal["cat"] = "cat"
    meows: bool = True


class Dog(Pet):
    species: Literal["dog"] = "dog"
    barks: bool = True


PetUnion = Annotated[Cat | Dog, Field(discriminator="species")]


app = Dash(__name__, external_stylesheets=dmc.styles.ALL)
server = app.server

app.layout = dmc.MantineProvider(
    dmc.Container(
        ModelForm(
            Cat(name="Cookie"),
            aio_id="test",
            form_id="test",
            data_model=PetUnion,
            fields_repr={
                "species": fields.RadioItems(options_labels={"cat": "Cat", "dog": "Dog"}),
            },
        ),
        py="xl",
    ),
)

if __name__ == "__main__":
    app.run(debug=True)

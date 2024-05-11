from datetime import date
from enum import Enum
from typing import Literal

import dash_mantine_components as dmc
from dash import Dash
from pydantic import BaseModel, Field

from dash_pydantic_form import FormSection, ModelForm, Sections, fields

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


class Office(Enum):
    """Office enum."""

    AU = "au"
    FR = "fr"
    UK = "uk"


class Species(Enum):
    """Species enum."""

    CAT = "cat"
    DOG = "dog"


class Metadata(BaseModel):
    """Metadata model."""

    languages: list[Literal["fr", "en", "sp", "cn"]] = Field(title="Languages spoken", default_factory=list)
    param2: int | None = Field(title="Parameter 2", default=None)


class Pet(BaseModel):
    """Pet model."""

    name: str = Field(title="Name", description="Name of the pet")
    species: Species = Field(title="Species", description="Species of the pet")
    dob: date | None = Field(title="Date of birth", description="Date of birth of the pet", default=None)
    alive: bool = Field(title="Alive", description="Is the pet alive", default=True)


class Employee(BaseModel):
    """Employee model."""

    name: str = Field(title="Name", description="Name of the employee")
    age: int = Field(title="Age", description="Age of the employee, starting from their birth")
    joined: date = Field(title="Joined", description="Date when the employee joined the company")
    office: Office = Field(title="Office", description="Office of the employee")
    metadata: Metadata | None = Field(title="Employee metadata", default=None, description="Lorem Ipsum")
    pets: list[Pet] = Field(title="Pets", description="Employee pets", default_factory=list)


bob = Employee(name="Bob", age=30, joined="2020-01-01", office="au", pets=[{"name": "Rex", "species": "dog"}])


app.layout = dmc.MantineProvider(
    # defaultColorScheme="dark",
    children=dmc.Container(
        [
            dmc.Title("Dash Pydantic form", mb=32),
            ModelForm(
                bob,
                "home",
                "bob-form",
                fields_repr={
                    "office": fields.RadioItems(
                        options_labels={"au": "Australia", "fr": "France"},
                    ),
                    "metadata": fields.Model(
                        render_type="accordion",
                        fields_repr={
                            "languages": fields.Checklist(
                                options_labels={"fr": "French", "en": "English", "sp": "Spanish", "cn": "Chinese"},
                            ),
                        },
                    ),
                    "pets": fields.EditableTable(
                        fields_repr={
                            "species": fields.Select(options_labels={"dog": "Dog", "cat": "Cat"}),
                        }
                    ),
                },
                sections=Sections(
                    sections=[
                        FormSection(name="General", fields=["name", "age"], default_open=True),
                        FormSection(name="HR", fields=["office", "joined", "metadata"], default_open=True),
                        FormSection(name="Other", fields=["pets"], default_open=True),
                    ],
                    render="tabs",
                    remaining_fields_position="bottom",
                ),
            ),
        ]
    )
)

server = app.server

if __name__ == "__main__":
    app.run_server(debug=True)

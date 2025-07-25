import json
from datetime import date
from enum import Enum
from typing import Literal

import dash
import dash_mantine_components as dmc
from dash import MATCH, Dash, Input, Output, State, callback, clientside_callback
from dash_iconify import DashIconify
from pydantic import BaseModel, Field, ValidationError

from dash_pydantic_form import AccordionFormLayout, FormSection, ModelForm, fields, get_model_cls, ids
from dash_pydantic_utils import SEP, Quantity

if dash.__version__ < "3":
    from dash import _dash_renderer

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


fields.Select.register_data_getter(
    lambda: [
        {"label": "French", "value": "fr"},
        {"label": "English", "value": "en"},
        {"label": "Spanish", "value": "sp"},
        {"label": "Chinese", "value": "cn"},
    ],
    "languages",
)


class Species(Enum):
    """Species enum."""

    CAT = "cat"
    DOG = "dog"


class Pet(BaseModel):
    """Pet model."""

    name: str = Field(title="Name", description="Name of the pet")
    species: Species = Field(title="Species", description="Species of the pet")
    dob: date | None = Field(title="Date of birth", description="Date of birth of the pet", default=None)
    alive: bool = Field(title="Alive", description="Is the pet alive", default=True)

    def __str__(self) -> str:
        """String representation."""
        return str(self.name)


class Desk(BaseModel):
    """Desk model."""

    height: Quantity = Field(
        repr_type="Quantity",
        repr_kwargs={"unit_options": ["m", "cm", "mm", "ft", "in"], "decimalScale": 3, "n_cols": 1 / 3},
    )
    material: str = Field(repr_kwargs={"n_cols": 1 / 3})
    color: str | None = Field(default=None, repr_type="Color", repr_kwargs={"n_cols": 1 / 3})


class WorkStation(BaseModel):
    """Work station model."""

    has_desk: bool = Field(title="Has desk", repr_type="Chip")
    has_monitor: bool = Field(title="Has monitor", repr_type="Switch")
    desk: Desk | None = Field(
        title="Desk",
        default=None,
        json_schema_extra={"repr_kwargs": {"visible": ("has_desk", "==", True)}},
    )
    room_temperature: Quantity = Field(
        repr_type="Quantity",
        repr_kwargs={"unit_options": {"C": "°C", "F": "°F"}},
        default_factory=lambda: Quantity(24, "C"),
    )


class HomeOffice(BaseModel):
    """Home office model."""

    type: Literal["home_office"]
    has_workstation: bool = Field(title="Has workstation", description="Does the employee have a suitable workstation")
    workstation: WorkStation | None = Field(
        title="Workstation",
        default=None,
        json_schema_extra={"repr_kwargs": {"visible": ("has_workstation", "==", True)}},
    )


class WorkOffice(BaseModel):
    """Work office model."""

    type: Literal["work_office"]
    commute_time: int = Field(title="Commute time", ge=0, multiple_of=5, repr_kwargs={"suffix": " min"})


class Metadata(BaseModel):
    """Metadata model."""

    languages: list[str] = Field(
        title="Languages spoken",
        default_factory=list,
        json_schema_extra={
            "repr_type": "ChipGroup",
            "repr_kwargs": {"multiple": True, "orientation": "horizontal", "data_getter": "languages"},
        },
    )
    siblings: int | None = Field(title="Siblings", default=None, ge=0)
    location: HomeOffice | WorkOffice | None = Field(
        title="Work location",
        default=None,
        discriminator="type",
        repr_kwargs={
            "fields_repr": {"type": fields.RadioItems(options_labels={"home_office": "Home", "work_office": "Work"})}
        },
    )
    private_field: str | None = None


class Employee(BaseModel):
    """Employee model."""

    name: str = Field(title="Name", description="Name of the employee", min_length=2)
    age: int = Field(title="Age", description="Age of the employee, starting from their birth", ge=18)
    mini_bio: str | None = Field(
        title="Mini bio",
        description="Short bio of the employee",
        default=None,
        json_schema_extra={"repr_type": "Markdown"},
    )
    joined: date = Field(title="Joined", description="Date when the employee joined the company", repr_type="Month")
    office: Literal["au", "fr", "uk"] = Field(
        title="Office",
        description="Office of the employee",
        json_schema_extra={
            "repr_type": "RadioItems",
            "repr_kwargs": {"options_labels": {"au": "Australia", "fr": "France", "uk": "United Kingdom"}},
        },
    )
    resume_file: str | None = Field(
        title="Resume file path",
        repr_type="Path",
        repr_kwargs={
            "backend": "gs",
            "prefix": "gs://ecmwf-open-data",
            "path_type": "directory",
            "n_cols": 1.0,
            "value_includes_prefix": True,
        },
        default=None,
    )
    metadata: Metadata | None = Field(title="Employee metadata", default=None)
    pets: list[Pet] = Field(title="Pets", description="Employee pets", default_factory=list)
    jobs: list[str] = Field(
        title="Past jobs", description="List of previous jobs the employee has held", default_factory=list
    )


bob = Employee(
    name="Bob",
    age=30,
    joined="2020-01-01",
    mini_bio="### Birth\nSomething something\n\n### Education\nCollege",
    office="au",
    metadata={
        "languages": ["fr", "en"],
        "siblings": 2,
        "location": {
            "type": "home_office",
            "has_workstation": True,
            "workstation": {
                "has_desk": True,
                "has_monitor": False,
                "desk": {"height": {"value": 125, "unit": "cm"}, "material": "wood", "color": "#89284a"},
            },
        },
    },
    pets=[{"name": "Rex", "species": "dog"}],
    jobs=["Engineer", "Lawyer"],
    # resume_file="gs://ecmwf-open-data/20240406/06z/ifs/0p4-beta/scda",
)


AIO_ID = "home"
FORM_ID = "Bob"

app.layout = dmc.MantineProvider(
    id="mantine-provider",
    defaultColorScheme="auto",
    children=dmc.AppShell(
        [
            dmc.NotificationProvider(),
            dmc.AppShellMain(
                dmc.Container(
                    [
                        dmc.Group(
                            [
                                dmc.Title("Dash Pydantic form", order=3),
                                dmc.Switch(
                                    offLabel=DashIconify(icon="radix-icons:moon", height=18),
                                    onLabel=DashIconify(icon="radix-icons:sun", height=18),
                                    size="md",
                                    color="yellow",
                                    persistence=True,
                                    checked=True,
                                    id="scheme-switch",
                                ),
                            ],
                            align="center",
                            justify="space-between",
                            mb="1rem",
                        ),
                        ModelForm(
                            # Employee,
                            bob,
                            AIO_ID,
                            FORM_ID,
                            # read_only=True,
                            # submit_on_enter=True,
                            debounce=500,
                            # locale="fr",
                            store_progress="session",
                            restore_behavior="notify",
                            form_cols=12,
                            fields_repr={
                                "name": {"placeholder": "Enter your name"},
                                "metadata": {
                                    "render_type": "accordion",
                                    "visible": ("_root_:office", "==", "au"),
                                    "excluded_fields": ["private_field"],
                                },
                                "pets": fields.Table(
                                    fields_repr={
                                        "species": fields.Select(options_labels={"dog": "Dog", "cat": "Cat"}),
                                    },
                                    table_height=200,
                                    dynamic_options={
                                        "species": {"namespace": "pydf_usage", "function_name": "getSpecies"}
                                    },
                                    column_defs_overrides={
                                        "species": {
                                            "cellEditorParams": {
                                                "catNames": ["Felix", "Cookie"],
                                                "dogNames": ["Rex", "Brownie"],
                                            }
                                        }
                                    },
                                    grid_kwargs={"dashGridOptions": {"suppressCellFocus": False}},
                                    excluded_fields=["alive"],
                                    fields_order=["species"],
                                ),
                                "jobs": {"placeholder": "A job name"},
                            },
                            form_layout=AccordionFormLayout(
                                sections=[
                                    FormSection(name="General", fields=["name", "age", "mini_bio"], default_open=True),
                                    FormSection(
                                        name="HR",
                                        fields=["office", "joined", "location", "resume_file", "metadata"],
                                        default_open=True,
                                    ),
                                    FormSection(name="Other", fields=["pets", "jobs"], default_open=True),
                                ],
                            ),
                        ),
                    ],
                    pt="1rem",
                )
            ),
            dmc.AppShellAside(
                dmc.ScrollArea(
                    dmc.Text(
                        id=ids.form_dependent_id("output", AIO_ID, FORM_ID),
                        style={"whiteSpace": "pre-wrap"},
                        p="1rem 0.5rem",
                    ),
                ),
            ),
        ],
        aside={"width": 350},
    ),
)


@callback(
    Output(ids.form_dependent_id("output", MATCH, MATCH), "children"),
    Output(ModelForm.ids.errors(MATCH, MATCH), "data"),
    Input(ModelForm.ids.main(MATCH, MATCH), "data"),
    State(ModelForm.ids.model_store(MATCH, MATCH), "data"),
    prevent_initial_call=True,
)
def display(form_data, model_name):
    """Display form data."""
    children = dmc.Stack(
        [
            dmc.Text("Form data", mb="-0.5rem", fw=600),
            dmc.Code(
                json.dumps(form_data, indent=2),
            ),
        ]
    )
    errors = None
    try:
        model_cls = get_model_cls(model_name)
        item = model_cls.model_validate(form_data)
        children.children[1].children = item.model_dump_json(indent=2)
    except ValidationError as e:
        children.children.extend(
            [
                dmc.Text("Validation errors", mb="-0.5rem", fw=500, c="red"),
                dmc.List(
                    [
                        dmc.ListItem(
                            [SEP.join([str(x) for x in error["loc"]]), f" : {error['msg']}, got {error['input']}"],
                        )
                        for error in e.errors()
                    ],
                    size="sm",
                    c="red",
                ),
            ]
        )
        errors = None
        errors = {SEP.join([str(x) for x in error["loc"]]): error["msg"] for error in e.errors()}

    return children, errors


clientside_callback(
    """(isLightMode) => isLightMode ? 'light' : 'dark'""",
    Output("mantine-provider", "forceColorScheme"),
    Input("scheme-switch", "checked"),
    prevent_initial_callback=True,
)


if __name__ == "__main__":
    if dash.__version__ < "3":
        app.run_server(debug=True)
    else:
        app.run(debug=True)

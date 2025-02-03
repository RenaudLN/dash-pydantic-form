# ruff: noqa: D101, D102, D103, D104, D105
from datetime import date, datetime, time
from typing import Annotated, ClassVar, Literal, get_args

import dash_mantine_components as dmc
from dash import Dash, Input, Output, State, _dash_renderer, dcc
from pydantic import BaseModel, Field, ValidationError, create_model, field_validator
from pydantic_core import PydanticUndefined

from dash_pydantic_form import ModelForm, fields
from dash_pydantic_form.form_layouts.form_layout import FormLayout
from dash_pydantic_form.form_section import FormSection, Position
from dash_pydantic_utils import SEP, model_construct_recursive

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


def make_default_field(repr_type=None, **kwargs):
    return Field(default=None, json_schema_extra={"repr_type": repr_type, "repr_kwargs": {"n_cols": 2} | kwargs})


class FieldModel(BaseModel):
    name: str = Field(pattern="^[a-z][a-z0-9_]*$", json_schema_extra={"repr_kwargs": {"n_cols": 3}})
    type_: str = "string"
    title: str | None = Field(default=None, json_schema_extra={"repr_kwargs": {"n_cols": 2}})
    default: str | None = make_default_field()
    required: bool = Field(True, title="Required field", json_schema_extra={"repr_kwargs": {"n_cols": 2, "mt": "2rem"}})
    n_cols: int | None = Field(
        None, title="Columns", ge=1, json_schema_extra={"repr_kwargs": {"n_cols": 2, "decimalScale": 0}}
    )
    description: str | None = Field(default=None, json_schema_extra={"repr_kwargs": {"n_cols": 4}})
    repr_kwargs: dict[str, str] | None = Field(title="Representation options", default_factory=dict)

    annotation: ClassVar[type | None] = None
    default_repr: ClassVar[dict | None] = None

    @field_validator("default", mode="before")
    @classmethod
    def validate_default(cls, v):
        if v == "":
            return None
        return v

    def get_annotation(self):
        if self.annotation is not None:
            return self.annotation
        raise NotImplementedError(f"Annotation not implemented for {self.type_}")

    def get_repr_type(self):
        return self.default_repr.get("repr_type")

    def to_dynamic_field(self) -> tuple[type, ...]:
        repr_kwargs = {k: v for k, v in (self.repr_kwargs or {}).items() if k and v}
        if self.n_cols is not None:
            repr_kwargs["n_cols"] = self.n_cols

        default_repr = self.default_repr or {}
        annotation = self.get_annotation()
        if self.default is not None:
            default = self.default
        elif not self.required:
            default = None
        else:
            default = PydanticUndefined
        return (
            annotation if self.required else annotation | None,
            Field(
                default=default,
                title=self.title,
                description=self.description,
                json_schema_extra={
                    "repr_type": self.get_repr_type(),
                    "repr_kwargs": {**default_repr.get("repr_kwargs", {}), **repr_kwargs},
                },
            ),
        )

    def __repr__(self):
        return f"{self.type_}({self['name']})"

    def __str__(self):
        return str(self["name"])


class StringFieldModel(FieldModel):
    type_: Literal["string"] = "string"

    annotation = str


class TextareaFieldModel(FieldModel):
    type_: Literal["textarea"] = "textarea"

    annotation = str
    default_repr = {"repr_type": "Textarea"}


class IntegerFieldModel(FieldModel):
    type_: Literal["integer"] = "integer"
    default: int | None = make_default_field(decimalScale=0)

    annotation = int
    default_repr = {"repr_kwargs": {"decimalScale": 0}}


class FloatFieldModel(FieldModel):
    type_: Literal["float"] = "float"
    default: float | None = make_default_field()

    annotation = float


class DateFieldModel(FieldModel):
    type_: Literal["date"] = "date"
    default: date | None = make_default_field(clearable=True)

    annotation = date


class DatetimeFieldModel(FieldModel):
    type_: Literal["datetime"] = "datetime"
    default: datetime | None = make_default_field(clearable=True)

    annotation = datetime


class TimeFieldModel(FieldModel):
    type_: Literal["time"] = "time"
    default: time | None = make_default_field(clearable=True)

    annotation = time


class SelectFieldModel(FieldModel):
    type_: Literal["select"] = "select"
    options: list[str] = Field(json_schema_extra={"repr_type": "Tags"})
    repr_type: Literal["Select", "RadioItems"] = Field("Select", json_schema_extra={"repr_type": "RadioItems"})

    def get_annotation(self):
        return Literal[tuple(self.options)]

    def get_repr_type(self):
        return self.repr_type


class MultiSelectFieldModel(FieldModel):
    type_: Literal["multiselect"] = "multiselect"
    options: list[str] = Field(json_schema_extra={"repr_type": "Tags"})
    default: list[str] | None = make_default_field(repr_type="Tags")

    def get_annotation(self):
        return list[Literal[tuple(self.options)]]


BaseFieldModelUnion = Annotated[
    StringFieldModel
    | IntegerFieldModel
    | FloatFieldModel
    | SelectFieldModel
    | DateFieldModel
    | DatetimeFieldModel
    | TimeFieldModel
    | MultiSelectFieldModel,
    Field(discriminator="type_"),
]


class TableFieldModel(FieldModel):
    type_: Literal["table"] = "table"
    columns: list[BaseFieldModelUnion]

    default_repr = {"repr_type": "Table"}

    def get_annotation(self):
        submodel = create_model(
            f"Table{self['name'].title()}", **{col.name: col.to_dynamic_field() for col in self.columns}
        )
        return list[submodel]


AllFieldModelUnion = Annotated[
    StringFieldModel
    | TextareaFieldModel
    | IntegerFieldModel
    | FloatFieldModel
    | SelectFieldModel
    | DateFieldModel
    | DatetimeFieldModel
    | TableFieldModel
    | TimeFieldModel
    | MultiSelectFieldModel,
    Field(discriminator="type_"),
]

options = [get_args(f.model_fields["type_"].annotation)[0] for f in get_args(get_args(AllFieldModelUnion)[0])]

type_mapper = {
    "string": str,
    "integer": int,
    "float": float,
    "select": str,
}


class LayoutOptions(BaseModel):
    sections: list[FormSection]
    remaining_fields_position: Position = Field("top", json_schema_extra={"repr_type": "RadioItems"})


class CustomModel(BaseModel):
    model_name: str = Field(default="Custom", json_schema_extra={"repr_kwargs": {"n_cols": 3}})
    form_cols: int = Field(default=12, title="Number of form columns", json_schema_extra={"repr_kwargs": {"n_cols": 3}})
    layout: Literal["grid", "accordion", "tabs", "steps"] = Field(
        "grid", json_schema_extra={"repr_kwargs": {"n_cols": 3}}
    )
    layout_options: LayoutOptions | None = Field(
        None, json_schema_extra={"repr_kwargs": {"visible": ("layout", "!=", "grid")}}
    )
    fields: list[AllFieldModelUnion] = Field(default_factory=list)

    def to_model(self):
        try:
            return create_model(
                f"Custom{self.model_name.title()}", **{field.name: field.to_dynamic_field() for field in self.fields}
            )
        except Exception as exc:
            import traceback

            traceback.print_exc()
            raise exc


dummy_output_store = dcc.Store(data={}, id=ModelForm.ids.main("form-definition", "dynamic"))
app.layout = dmc.MantineProvider(
    dmc.Container(
        dmc.Stack(
            [
                dmc.Box(
                    [
                        dmc.Text("Custom form definition", fw="bold", mb="md"),
                        ModelForm(
                            CustomModel,
                            aio_id="form-definition",
                            form_id="base",
                            store_progress="session",
                            restore_behavior="auto",
                            submit_on_enter=True,
                            form_cols=12,
                            fields_repr={
                                "fields": {
                                    "fields_repr": {
                                        "type_": fields.SegmentedControl(
                                            title="",
                                            default="string",
                                            data=[{"label": x.title(), "value": x} for x in ["-"] + options],
                                        ),
                                    },
                                },
                            },
                        ),
                    ],
                    p="0.5rem",
                ),
                dmc.Paper(
                    [
                        dmc.Text("Custom form output", fw="bold", mb="md"),
                        dmc.Box(dummy_output_store, id="form-container"),
                    ],
                    withBorder=True,
                    p="0.5rem 1rem",
                    radius="md",
                ),
            ],
        ),
        p="2rem",
    ),
    defaultColorScheme="dark",
)


@app.callback(
    Output("form-container", "children"),
    Output(ModelForm.ids.errors("form-definition", "base"), "data"),
    Input(ModelForm.ids.main("form-definition", "base"), "data"),
    State(ModelForm.ids.main("form-definition", "dynamic"), "data"),
)
def create_form(form_definition, current_data):
    try:
        custom_model = CustomModel(**(form_definition or {}))
    except ValidationError as exc:
        errors = {
            SEP.join([str(x) for i, x in enumerate(error["loc"]) if i != 2]): "Invalid value" for error in exc.errors()
        }
        return dmc.Skeleton(dummy_output_store, h="4rem"), errors

    try:
        dynamic_model = custom_model.to_model()
        item = model_construct_recursive(current_data, dynamic_model)
        form_layout = None
        if custom_model.layout != "grid" and custom_model.layout_options is not None:
            form_layout = FormLayout.load(
                layout=custom_model.layout,
                **custom_model.layout_options.model_dump(),
            )

        return ModelForm(
            item or dynamic_model,
            aio_id="form-definition",
            form_id="dynamic",
            form_cols=custom_model.form_cols,
            form_layout=form_layout,
        ), None
    except Exception:
        import traceback

        traceback.print_exc()
        return dmc.Skeleton(dummy_output_store, h="4rem"), None


if __name__ == "__main__":
    app.run(debug=True)

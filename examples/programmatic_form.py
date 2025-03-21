# ruff: noqa: D101, D102, D103, D104, D105
import json
from datetime import date, datetime, time
from types import UnionType
from typing import Annotated, ClassVar, Literal, Union, get_args, get_origin

import dash_mantine_components as dmc
from dash import ALL, Dash, Input, Output, State, dcc, no_update
from pydantic import BaseModel, Field, TypeAdapter, ValidationError, create_model, field_validator
from pydantic_core import PydanticUndefined

from dash_pydantic_form import FormLayout, ModelForm, TabsFormLayout, fields
from dash_pydantic_form.form_section import FormSection, Position
from dash_pydantic_form.ids import value_field
from dash_pydantic_utils import SEP, model_construct_recursive

app = Dash(__name__, external_stylesheets=dmc.styles.ALL)

server = app.server


def make_default_field(repr_type=None, **kwargs):
    return Field(default=None, json_schema_extra={"repr_type": repr_type, "repr_kwargs": {"n_cols": 2} | kwargs})


class FieldModel(BaseModel):
    type_: str = "string"
    name: str = Field(
        pattern="^[a-z][a-z0-9_]*$",
        json_schema_extra={"repr_kwargs": {"n_cols": 3, "placeholder": "snake_case"}},
    )
    title: str | None = Field(default=None, json_schema_extra={"repr_kwargs": {"n_cols": 3}})
    default: str | None = make_default_field()
    required: bool = Field(True, title="Required field", json_schema_extra={"repr_kwargs": {"n_cols": 2, "mt": "2rem"}})
    n_cols: int | None = Field(
        None, title="Columns", ge=1, json_schema_extra={"repr_kwargs": {"n_cols": 2, "decimalScale": 0}}
    )
    description: str | None = Field(default=None, json_schema_extra={"repr_kwargs": {"n_cols": 12}})
    repr_kwargs: dict[str, str] = Field(title="Representation options", default_factory=dict)
    pydantic_kwargs: dict[str, str] = Field(title="Pydantic field options", default_factory=dict)

    annotation: ClassVar[type | None] = None
    default_repr: ClassVar[dict | None] = None

    @field_validator("title", mode="before")
    @classmethod
    def validate_title(cls, v):
        if v == "":
            return None
        return v

    @field_validator("n_cols", mode="before")
    @classmethod
    def validate_n_cols(cls, v):
        if v == "":
            return None
        return v

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
        return (self.default_repr or {}).get("repr_type")

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
                **self.pydantic_kwargs,
            ),
        )

    def to_field_string(self):
        """String representation."""
        annotation, field = self.to_dynamic_field()
        annotation_str = getattr(annotation, "__name__", str(annotation))

        def parse_arg(arg):
            if arg is type(None):
                return "None"
            if isinstance(arg, str):
                return f'"{arg}"'
            if isinstance(arg, type):
                base = arg.__name__
                if get_args(arg):
                    base += "[" + ", ".join([parse_arg(x) for x in get_args(arg)]) + "]"
                return base
            return str(arg)

        if get_origin(annotation) in [Union, UnionType]:
            annotation_str = " | ".join([parse_arg(x) for x in get_args(annotation)])
        elif get_origin(annotation) not in [Union, UnionType] and get_args(annotation):
            annotation_str += "[" + ", ".join([parse_arg(x) for x in get_args(annotation)]) + "]"
        base = f"    {self['name']}: {annotation_str}"
        parts = []
        if field.default is not PydanticUndefined:
            parts.append(f"default={TypeAdapter(field.annotation).dump_json(field.default).decode('utf-8')}")
        if field.title is not None:
            parts.append(f"title={json.dumps(field.title)}")
        if field.description is not None:
            parts.append(f"description={json.dumps(field.description)}")
        for k, v in self.pydantic_kwargs.items():
            parts.append(f"{k}={json.dumps(v)}")
        extra = {}
        if field.json_schema_extra is not None:
            if field.json_schema_extra.get("repr_type"):
                extra["repr_type"] = field.json_schema_extra["repr_type"]
            if field.json_schema_extra.get("repr_kwargs"):
                extra["repr_kwargs"] = field.json_schema_extra["repr_kwargs"]
        if extra:
            parts.append(f"json_schema_extra={json.dumps(extra)}")
        out = base + " = Field(\n        " + ",\n        ".join(parts) + ",\n    )" if parts else base
        return out.replace("null", "None")

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

table_options = [get_args(f.model_fields["type_"].annotation)[0] for f in get_args(get_args(BaseFieldModelUnion)[0])]


class TableFieldModel(FieldModel):
    type_: Literal["table"] = "table"
    columns: list[BaseFieldModelUnion] = Field(
        json_schema_extra={
            "repr_kwargs": {
                "fields_repr": {
                    "type_": fields.Select(
                        title="",
                        data=[{"label": x.title(), "value": x} for x in sorted(table_options)],
                        searchable=True,
                    ),
                    "n_cols": {"visible": False},
                    "description": {"n_cols": 6},
                }
            }
        }
    )

    default_repr = {"repr_type": "Table"}

    def get_annotation(self):
        submodel = create_model(
            f"{self['name'].title()}_", **{col.name: col.to_dynamic_field() for col in self.columns}
        )
        return list[submodel]

    def to_model_string(self):
        parts = [f"class {self.name.title()}_(BaseModel):"]
        for column in self.columns:
            parts.append(column.to_field_string())
        return "\n".join(parts)


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
    sections: list[FormSection] = Field(
        json_schema_extra={
            "repr_kwargs": {
                "fields_repr": {
                    "icon": fields.Text(),
                    "fields": fields.MultiSelect(data=[]),
                    "default_open": {"visible": ("_root_:layout", "==", "accordion"), "mt": "2rem"},
                },
            }
        }
    )
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
                f"{self.model_name.title()}_", **{field.name: field.to_dynamic_field() for field in self.fields}
            )
        except Exception as exc:
            import traceback

            traceback.print_exc()
            raise exc

    def to_model_string(self):
        table_models = [f.to_model_string() for f in self.fields if f.type_ == "table"]

        parts = [f"class {self.model_name.title()}(BaseModel):"]
        for field in self.fields:
            parts.append(field.to_field_string())
        out = "\n".join(parts)

        return "\n\n".join(table_models + [out])


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
                                        "type_": fields.Select(
                                            title="",
                                            data=[{"label": x.title(), "value": x} for x in sorted(options)],
                                            searchable=True,
                                        ),
                                    },
                                },
                            },
                            form_layout=TabsFormLayout(
                                sections=[
                                    FormSection(
                                        name="Model",
                                        fields=["model_name", "fields"],
                                    ),
                                    FormSection(
                                        name="Form",
                                        fields=["form_cols", "layout", "layout_options"],
                                    ),
                                ]
                            ),
                        ),
                    ],
                    p="0.5rem",
                ),
                dmc.Paper(
                    [
                        dmc.Text("Form output", fw="bold", mb="md"),
                        dmc.Box(dummy_output_store, id="form-container"),
                    ],
                    withBorder=True,
                    p="0.5rem 1rem",
                    radius="md",
                ),
                dmc.Paper(
                    [
                        dmc.Text("Equivalent model", fw="bold", mb="md"),
                        dmc.Box(id="model-container"),
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
    Output("model-container", "children"),
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
        return dmc.Skeleton(dummy_output_store, h="4rem"), None, errors

    model_content = dmc.CodeHighlight(code=custom_model.to_model_string(), language="python")

    try:
        dynamic_model = custom_model.to_model()
        item = model_construct_recursive(current_data, dynamic_model)
        form_layout = None
        if custom_model.layout != "grid" and custom_model.layout_options is not None:
            form_layout = FormLayout.load(
                layout=custom_model.layout,
                **custom_model.layout_options.model_dump(),
            )

        return (
            ModelForm(
                item or dynamic_model,
                aio_id="form-definition",
                form_id="dynamic",
                form_cols=custom_model.form_cols,
                form_layout=form_layout,
                submit_on_enter=True,
            ),
            model_content,
            None,
        )
    except Exception:
        import traceback

        traceback.print_exc()
        return dmc.Skeleton(dummy_output_store, h="4rem"), model_content, None


@app.callback(
    Output(ModelForm.ids.errors("form-definition", "dynamic"), "data"),
    Input(ModelForm.ids.form("form-definition", "dynamic"), "data-submit"),
    State(ModelForm.ids.main("form-definition", "dynamic"), "data"),
    State(ModelForm.ids.main("form-definition", "base"), "data"),
    prevent_initial_call=True,
)
def check_dynamic_form(trigger, form_data, form_definition):
    if not trigger:
        return no_update
    dynamic_model = CustomModel(**(form_definition or {})).to_model()
    try:
        dynamic_model.model_validate(form_data)
    except ValidationError as exc:
        errors = {
            SEP.join([str(x) for i, x in enumerate(error["loc"]) if i != 2]): "Invalid value" for error in exc.errors()
        }
        return errors
    return None


app.clientside_callback(
    """(formData, ids) => {
        availableFields = formData.fields.filter(f => !!f.name).map(f => f.name);
        return Array(ids.length).fill(availableFields);
    }""",
    Output(value_field("form-definition", "base", "fields", ALL), "data"),
    Input(ModelForm.ids.main("form-definition", "base"), "data"),
    State(value_field("form-definition", "base", "fields", ALL), "id"),
)


if __name__ == "__main__":
    app.run(debug=True)

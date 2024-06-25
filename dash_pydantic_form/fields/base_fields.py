import inspect
import json
import logging
import os
from collections.abc import Callable
from datetime import time
from enum import Enum, EnumMeta
from functools import partial
from textwrap import TextWrapper
from types import UnionType
from typing import Any, ClassVar, Literal, Union, get_args, get_origin

import dash_mantine_components as dmc
from dash import ALL, MATCH, ClientsideFunction, Input, Output, State, clientside_callback, html
from dash.development.base_component import Component
from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator
from pydantic.fields import FieldInfo
from pydantic.types import annotated_types
from pydantic_core import PydanticUndefined

from dash_pydantic_form import ids as common_ids
from dash_pydantic_form.utils import (
    SEP,
    Type,
    get_all_subclasses,
    get_fullpath,
    get_model_value,
    get_non_null_annotation,
)

CHECKED_COMPONENTS = [
    dmc.Checkbox,
    dmc.Switch,
]
NO_LABEL_COMPONENTS = [
    dmc.SegmentedControl,
    dmc.ChipGroup,
    dmc.RangeSlider,
    dmc.Slider,
    dmc.ColorPicker,
]
MAX_OPTIONS_INLINE = 4

FilterOperator = Literal["==", "!=", "in", "not in", "array_contains", "array_contains_any"]
VisibilityFilter = tuple[str, FilterOperator, Any]


class BaseField(BaseModel):
    """Base field representation class."""

    base_component: ClassVar[type[Component] | None] = None
    reserved_attributes: ClassVar = ("value", "label", "description", "id", "required")
    full_width: ClassVar[bool] = False

    title: str | None = Field(
        default=None, description="Field label, overrides the title defined in the pydantic Field."
    )
    description: str | None = Field(
        default=None, description="Field helper text, overrides the description defined in the pydantic Field."
    )
    required: bool | None = Field(
        default=None,
        description="Whether to display a required asterisk. If not provided, uses pydantic's field `is_required`.",
    )
    n_cols: int | None = Field(default=None, description="Number of columns in the form, out of 4. Default 2.")
    visible: bool | VisibilityFilter | list[VisibilityFilter] | None = Field(
        default=None,
        description=(
            "Define visibility conditions based on other form fields.\n"
            "Accepts a boolean, a 3-tuple or list of 3-tuples with format: (field, operator, value).\n"
            "The available operators are:\n"
            "* '=='\n"
            "* '!='\n"
            "* 'in'\n"
            "* 'not in'\n"
            "* 'array_contains'\n"
            "* 'array_contains_any'\n"
            "NOTE: The field in the 3-tuples is a ':' separated path relative to the current field's "
            "level of nesting.\n"
            "If you need to reference a field from a parent or the root "
            "use the special values `_parent_` or `_root_`.\n"
            "E.g. visible=('_root_:first_name', '==', 'Bob')"
            ""
        ),
    )
    input_kwargs: dict | None = Field(
        default=None,
        description=(
            "Arguments to be passed to the underlying rendered component. "
            "NOTE: these are updated with extra arguments passed to the field."
        ),
    )
    field_id_meta: str | None = Field(default=None, description="Optional str to be set in the field id's 'meta' key.")
    read_only: bool = Field(default=False, description="Read only field.")

    model_config = ConfigDict(extra="allow")

    @classmethod
    def __pydantic_init_subclass__(cls):
        """Add docstring in subclasses."""
        tw = TextWrapper(width=89, initial_indent="    ", subsequent_indent="    ")
        result = (cls.__doc__ or "") + "\n\nParameters\n----------\n"
        for field_name, field_info in cls.model_fields.items():
            annotation = str(field_info.annotation)
            description = tw.fill(field_info.description) if field_info.description else "    (missing description)"
            result += f"{field_name}: {annotation}\n{description}\n"

        cls.__doc__ = result

    def model_post_init(self, _context):
        """Model post init."""
        if self.n_cols is None:
            self.n_cols = 4 if self.full_width else 2
        if self.input_kwargs is None:
            self.input_kwargs = {}
        if self.model_extra:
            self.input_kwargs.update(self.model_extra)
        if self.base_component:
            valid_input_kwargs = {
                k: v for k, v in self.input_kwargs.items() if k in inspect.signature(self.base_component).parameters
            }
            ignored_kwargs = set(self.input_kwargs) - set(valid_input_kwargs)
            self.input_kwargs = valid_input_kwargs
            if ignored_kwargs:
                logging.warning("The following kwargs were ignored for %s: %s", self.__class__.__name__, ignored_kwargs)
        if self.field_id_meta is None:
            self.field_id_meta = ""

    class ids:
        """Form ids."""

        visibility_wrapper = partial(common_ids.field_dependent_id, "_pydf-field-visibility-wrapper")

    def to_dict(self) -> dict:
        """Return a dictionary representation of the field."""
        return {"__class__": str(self.__class__)} | self.model_dump(mode="json")

    @classmethod
    def from_dict(cls, data: dict) -> "BaseField":
        """Create a field from a dictionary."""
        data = data.copy()
        str_repr = data.pop("__class__")
        field_cls = next(c for c in get_all_subclasses(BaseField) if str(c) == str_repr)
        return field_cls(**data)

    def render(  # noqa: PLR0913
        self,
        *,
        item: BaseModel,
        aio_id: str,
        form_id: str,
        field: str,
        parent: str = "",
        field_info: FieldInfo,
    ) -> Component:
        """Render the field."""
        """Create a form input to interact with the field, and conditional visibility wrapper."""
        title = None
        if os.getenv("DEBUG"):
            title = f"Field path: {get_fullpath(parent, field)}"

        inputs = self._render(
            item=item, aio_id=aio_id, form_id=form_id, field=field, parent=parent, field_info=field_info
        )
        visible = self.visible

        if visible is None or visible is True:
            return html.Div(inputs, style={"gridColumn": f"span var(--col-{self.n_cols}-4)"}, title=title)

        if field_info.default == PydanticUndefined and field_info.default_factory is None:
            logging.warning(
                "Conditional visibility is set on a field without default value, "
                "this will likely lead to validation errors."
            )

        if visible is False:
            return html.Div(inputs, style={"display": "none"}, title=title)

        if isinstance(visible, tuple) and isinstance(visible[0], str):
            visible = [visible]

        for i, vis in enumerate(visible):
            inputs, title = self._add_visibility_wrapper(
                inputs=inputs,
                aio_id=aio_id,
                form_id=form_id,
                item=item,
                visibility=vis,
                parent=parent,
                field=field,
                index=i,
                n_visibility_fields=len(visible),
                title=title,
            )

        return inputs

    def _render(  # noqa: PLR0913
        self,
        *,
        item: BaseModel,
        aio_id: str,
        form_id: str,
        field: str,
        parent: str = "",
        field_info: FieldInfo | None = None,
    ) -> Component:
        """Create a form input to interact with the field."""
        if not self.base_component:
            raise NotImplementedError("This is an abstract class.")

        value = self.get_value(item, field, parent)

        if self.read_only:
            return self._render_read_only(value, field, field_info)

        id_ = (common_ids.checked_field if self.base_component in CHECKED_COMPONENTS else common_ids.value_field)(
            aio_id, form_id, field, parent, meta=self.field_id_meta
        )
        value_kwarg = (
            {
                "checked": value,
                "label": self.get_title(field_info, field_name=field),
            }
            if self.base_component in CHECKED_COMPONENTS
            else (
                {
                    "label": self.get_title(field_info, field_name=field),
                    "value": value,
                    "description": self.get_description(field_info),
                    "required": self.is_required(field_info),
                }
                if self.base_component not in NO_LABEL_COMPONENTS
                else {"value": value}
            )
        )

        component = self.base_component(
            id=id_,
            **self.input_kwargs
            | self._additional_kwargs(item=item, aio_id=aio_id, field=field, parent=parent, field_info=field_info)
            | value_kwarg,
        )

        if self.base_component not in NO_LABEL_COMPONENTS:
            return component

        title = self.get_title(field_info, field_name=field)
        description = self.get_description(field_info)
        return dmc.Stack(
            (title is not None)
            * [
                dmc.Text(
                    [title]
                    + [
                        html.Span(" *", style={"color": "var(--input-asterisk-color, var(--mantine-color-error))"}),
                    ]
                    * self.is_required(field_info),
                    size="sm",
                    mt=3,
                    mb=5,
                    fw=500,
                    lh=1.55,
                )
            ]
            + (title is not None and description is not None)
            * [dmc.Text(description, size="xs", c="dimmed", mt=-5, mb=5, lh=1.2)]
            + [component],
            gap=0,
        )

    def _render_read_only(self, value: Any, field: str, field_info: FieldInfo):
        """Render a read only field."""
        title = self.get_title(field_info, field_name=field)
        description = self.get_description(field_info)

        outputs = dmc.Stack(
            (title is not None) * [dmc.Text(title, size="sm", mt=3, mb=5, fw=500, lh=1.55)]
            + (title is not None and description is not None)
            * [dmc.Text(description, size="xs", c="dimmed", mt=-5, mb=5, lh=1.2)],
            gap=0,
        )

        value_repr = self._get_value_repr(value, field_info)

        outputs.children.append(
            dmc.Paper(
                value_repr,
                withBorder=True,
                radius="sm",
                p="0.375rem 0.75rem",
                style={
                    "display": "flex",
                    "alignItems": "center",
                    "gap": "0.5rem",
                    "borderColor": "color-mix(in srgb, var(--mantine-color-default-border), transparent 70%)",
                },
            )
        )

        return outputs

    @staticmethod
    def _get_value_repr(value: Any, field_info: FieldInfo):
        val_type = Type.classify(field_info.annotation)
        value_repr = str(value)
        if val_type == Type.SCALAR:
            if isinstance(value, bool):
                value_repr = "✅" if value else "❌"
            if isinstance(value, Enum):
                value_repr = value.name
            if value is None:
                value_repr = "-"
        elif val_type in [Type.SCALAR_LIST, Type.LITERAL_LIST]:
            value_repr = [dmc.Badge(str(val), variant="light", radius="sm", tt="unset") for val in value]

        return value_repr

    @staticmethod
    def _get_dependent_field_and_parent(dependent_field: str, parent: str):
        """Get the dependent field and parent.

        Manages the special pointers _root_ and _parent_.
        """
        dependent_parent_parts = parent.split(SEP) if parent else []
        for part in dependent_field.split(SEP)[:-1]:
            if part == "_root_":
                dependent_parent_parts = []
            elif part == "_parent_":
                dependent_parent_parts = dependent_parent_parts[:-1]
            else:
                dependent_parent_parts.append(part)

        dependent_parent = SEP.join(dependent_parent_parts) if dependent_parent_parts else ""
        dependent_field = dependent_field.split(SEP)[-1]

        return dependent_parent, dependent_field

    def _add_visibility_wrapper(  # noqa: PLR0913
        self,
        *,
        inputs,
        aio_id: str,
        form_id: str,
        item: BaseModel,
        visibility: tuple,
        parent: str,
        field: str,
        index: int,
        n_visibility_fields: int,
        title: str,
    ):
        """Wrap the inputs with a layer of togglable visibility."""
        dependent_field, operator, expected_value = visibility
        dependent_parent, dependent_field = self._get_dependent_field_and_parent(dependent_field, parent)

        current_value = self.get_value(item, dependent_field, dependent_parent)
        if isinstance(current_value, Enum):
            current_value = current_value.value
        if os.getenv("DEBUG"):
            keyword = "Visible" if index == 0 else "   AND"
            title += f"\n{keyword}: {get_fullpath(dependent_parent , dependent_field)}" f" {operator} {expected_value}"

        inputs = html.Div(
            inputs,
            id=self.ids.visibility_wrapper(
                aio_id,
                form_id,
                dependent_field,
                parent=dependent_parent,
                meta=f"{get_fullpath(parent, field)}|{operator}|{json.dumps(expected_value)}",
            ),
            style={
                "display": None if self.check_visibility(current_value, operator, expected_value) else "none",
                "gridColumn": f"span var(--col-{self.n_cols}-4)" if index == n_visibility_fields - 1 else None,
            },
            title=title if index == n_visibility_fields - 1 else None,
        )

        return inputs, title

    def get_title(self, field_info: FieldInfo, field_name: str | None = None) -> str:
        """Get the input title."""
        if self.title is not None:
            return self.title or None
        return field_info.title or field_name.replace("_", " ").title()

    def get_description(self, field_info: FieldInfo) -> str:
        """Get the input description."""
        return self.description or field_info.description

    def is_required(self, field_info: FieldInfo) -> bool:
        """Get the required status of the field."""
        return self.required or field_info.is_required()

    @classmethod
    def _additional_kwargs(cls, **_kwargs) -> dict:
        """Additional kwargs."""
        return {}

    @staticmethod
    def check_visibility(value: Any, operator: str, expected_value: Any) -> bool:
        """Check whether a field should be visible based on value, operator and expected value."""
        if operator == "==":
            return value == expected_value
        if operator == "!=":
            return value != expected_value
        if operator == "in":
            return value in expected_value
        if operator == "not in":
            return value not in expected_value
        if operator == "array_contains":
            return expected_value in value
        if operator == "array_contains_any":
            return bool(set(value).intersection(expected_value))
        raise ValueError(f"Invalid operator: {operator}")

    @classmethod
    def get_value(cls, item: BaseModel, field: str, parent: str) -> Any:
        """Get the value of a model (parent, field) pair. Defined to allow overriding."""
        return get_model_value(item, field, parent)


class TextField(BaseField):
    """Text field."""

    base_component = dmc.TextInput


class TextareaField(TextField):
    """Textarea field."""

    base_component = dmc.Textarea


class NumberField(TextField):
    """Number field."""

    base_component = dmc.NumberInput

    def _additional_kwargs(self, field_info: FieldInfo, **_kwargs) -> dict:
        kwargs = {}
        for meta in field_info.metadata:
            if isinstance(meta, annotated_types.Ge):
                kwargs["min"] = meta.ge
            if isinstance(meta, annotated_types.Gt):
                kwargs["min"] = meta.gt + 1e-12
            if isinstance(meta, annotated_types.Le):
                kwargs["max"] = meta.le
            if isinstance(meta, annotated_types.Lt):
                kwargs["max"] = meta.lt - 1e-12

        return kwargs


class PasswordField(TextField):
    """Password field."""

    base_component = dmc.PasswordInput


class JsonField(TextField):
    """Json field."""

    base_component = dmc.JsonInput


class ColorField(BaseField):
    """Color field."""

    base_component = dmc.ColorPicker


class SliderField(BaseField):
    """Slider field."""

    base_component = dmc.Slider


class RangeField(BaseField):
    """Range field."""

    base_component = dmc.RangeSlider


class CheckboxField(BaseField):
    """Checkbox field."""

    base_component = dmc.Checkbox


class SwitchField(BaseField):
    """Switch field."""

    base_component = dmc.Switch


class DateField(BaseField):
    """Date field."""

    base_component = dmc.DateInput

    def model_post_init(self, _context):
        """Add defaults for date input."""
        super().model_post_init(_context)
        self.input_kwargs.setdefault("valueFormat", "YYYY-MM-DD")


class TimeField(BaseField):
    """Time field."""

    base_component = dmc.TimeInput

    @classmethod
    def get_value(cls, item: BaseModel, field: str, parent: str) -> Any:
        """Handle the fact dmc.TimeInput uses datetime rather than plain time."""
        value = super().get_value(item, field, parent)
        if value and isinstance(value, time):
            value = f"2000-01-01T{value}"

        return value


class DatetimeField(BaseField):
    """Datetime field."""

    base_component = dmc.DateTimePicker

    def model_post_init(self, _context):
        """Add defaults for date input."""
        super().model_post_init(_context)
        self.input_kwargs.setdefault("valueFormat", "YYYY-MM-DD HH:mm")
        # self.input_kwargs.setdefault("withSeconds", True)


class SelectField(BaseField):
    """Select field."""

    data_getter: Callable[[], list] | None = Field(
        default=None, description="Function to retrieve a list of options. This function takes no argument."
    )
    options_labels: dict | None = Field(
        default=None, description="Mapper from option to label. Especially useful for Literals and Enums."
    )

    base_component = dmc.Select
    getters: ClassVar[dict[str, Callable]] = {}

    def model_post_init(self, _context):
        """Convert data_getter from serialised version to function."""
        super().model_post_init(_context)
        if self.data_getter is not None:
            self.getters[str(self.data_getter)] = self.data_getter

    @field_serializer("data_getter")
    def serialize_data_getter(self, value):
        """Serialize data_getter."""
        if value is None:
            return None
        return str(value)

    @field_validator("data_getter", mode="before")
    @classmethod
    def validate_data_getter(cls, value):
        """Validate data_getter."""
        if isinstance(value, str) and value in cls.getters:
            return cls.getters[value]
        return value

    def _get_data(self, field_info: FieldInfo, **kwargs) -> list[dict]:
        """Gets option list from annotations."""
        non_null_annotation = get_non_null_annotation(field_info.annotation)
        data = self._get_data_list(non_null_annotation=non_null_annotation, **kwargs)
        options = self._format_data(data, **kwargs)

        values, filtered = [], []
        for option in options:
            if option["value"] not in values:
                values.append(option["value"])
                filtered.append(option)

        return filtered

    def _get_data_list(
        self,
        non_null_annotation: type,
        **kwargs,
    ) -> list[dict]:
        """Get list of possible values from annotation."""
        data = self._get_data_list_recursive(non_null_annotation, **kwargs)
        return data

    def _get_data_list_recursive(self, non_null_annotation: type, **kwargs) -> list:
        """Get list of possible values from annotation recursively."""
        data = []
        # if the annotation is a union of types, recursively calls this function on each type.
        if get_origin(non_null_annotation) in [Union, UnionType]:
            data.extend(
                sum(
                    [self._get_data_list_recursive(sub_annotation) for sub_annotation in get_args(non_null_annotation)],
                    [],
                )
            )

        elif get_origin(non_null_annotation) == list:
            annotation_args = get_args(non_null_annotation)
            if len(annotation_args) == 1:
                return self._get_data_list_recursive(annotation_args[0], **kwargs)
        elif get_origin(non_null_annotation) == Literal:
            data = list(get_args(non_null_annotation))
        elif isinstance(non_null_annotation, EnumMeta):
            data = [{"value": x.value, "label": x.name} for x in non_null_annotation]

        return data

    def _format_data(self, data, **_kwargs):
        """Formats the list of options into a `value, label` pair."""
        if self.options_labels:
            return [
                {"value": x["value"], "label": self.options_labels.get(x["value"], x["label"])}
                if isinstance(x, dict)
                else {"value": x, "label": str(self.options_labels.get(x, x))}
                for x in data
            ]

        return [x if isinstance(x, dict) else {"value": x, "label": x} for x in data]

    def _additional_kwargs(self, **kwargs) -> dict:
        """Retrieve data from Literal annotation if data is not present in input_kwargs."""
        return {
            "data": self.data_getter() if self.data_getter else self.input_kwargs.get("data", self._get_data(**kwargs))
        }

    def _get_value_repr(self, value: Any, field_info: FieldInfo):
        value_repr = super()._get_value_repr(value, field_info)
        data = self._get_data(field_info)

        def _get_label(value, data, value_repr):
            if isinstance(value, Enum):
                value = value.value
            option = next(
                (x for x in data if (x.get("value") if isinstance(x, dict) else getattr(x, "value", None)) == value),
                None,
            )
            label = (
                option.get("label")
                if isinstance(option, dict)
                else getattr(option, "label", getattr(option, "children", None))
            )
            return label if label is not None else value_repr

        if Type.classify(field_info.annotation) == Type.SCALAR:
            return _get_label(value, data, value_repr)
        if Type.classify(field_info.annotation) == Type.SCALAR_LIST:
            return [dmc.Badge(_get_label(x, data, value_repr), radius="sm", variant="light", tt="unset") for x in value]
        return value_repr


class MultiSelectField(SelectField):
    """MultiSelect field."""

    base_component = dmc.MultiSelect


class RadioItemsField(SelectField):
    """Radio items field."""

    base_component = dmc.RadioGroup

    def _additional_kwargs(self, *, field: str = None, field_info: FieldInfo, **kwargs) -> dict:
        """Retrieve data from Literal annotation if data is not present in input_kwargs."""
        kwargs = super()._additional_kwargs(field_info=field_info, **kwargs)
        data = kwargs["data"] or []
        children = [
            x
            if isinstance(x, dmc.Radio)
            else (dmc.Radio(**x) if isinstance(x, dict) else dmc.Radio(label=str(x), value=x))
            for x in data
        ]
        mt = "5px" if self.get_title(field_info, field_name=field) and self.get_description(field_info) else 0
        if len(data) <= MAX_OPTIONS_INLINE:
            return {"children": dmc.Group(children, mt=mt, py="0.5rem")}
        return {"children": dmc.Stack(children, mt=mt, py="0.25rem")}


class ChecklistField(MultiSelectField):
    """Checklist field."""

    base_component = dmc.CheckboxGroup

    def _additional_kwargs(self, *, field: str = None, field_info: FieldInfo, **kwargs) -> dict:
        """Retrieve data from Literal annotation if data is not present in input_kwargs."""
        kwargs = super()._additional_kwargs(field_info=field_info, **kwargs)
        data = kwargs["data"] or []
        children = [
            x
            if isinstance(x, dmc.Checkbox)
            else (dmc.Checkbox(**x) if isinstance(x, dict) else dmc.Checkbox(label=str(x), value=x))
            for x in (kwargs["data"] or [])
        ]
        mt = "5px" if self.get_title(field_info, field_name=field) and self.get_description(field_info) else 0
        if len(data) <= MAX_OPTIONS_INLINE:
            return {"children": dmc.Group(children, mt=mt, py="0.5rem")}
        return {"children": dmc.Stack(children, mt=mt, py="0.25rem")}


class SegmentedControlField(SelectField):
    """Segmented control field."""

    base_component = dmc.SegmentedControl

    def model_post_init(self, _context):
        """Add default style."""
        super().model_post_init(_context)
        self.input_kwargs.setdefault("style", {"alignSelf": "baseline"})


clientside_callback(
    ClientsideFunction(namespace="pydf", function_name="updateFieldVisibility"),
    Output(BaseField.ids.visibility_wrapper(MATCH, MATCH, MATCH, MATCH, ALL), "style"),
    Input(common_ids.value_field(MATCH, MATCH, MATCH, MATCH, ALL), "value"),
    Input(common_ids.checked_field(MATCH, MATCH, MATCH, MATCH, ALL), "checked"),
    State(BaseField.ids.visibility_wrapper(MATCH, MATCH, MATCH, MATCH, ALL), "style"),
    prevent_initial_call=True,
)

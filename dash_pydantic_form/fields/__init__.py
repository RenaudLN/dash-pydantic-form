from datetime import date, time
from enum import Enum
from typing import Literal, get_origin

from pydantic import BaseModel
from pydantic.fields import FieldInfo

from dash_pydantic_form.utils import Type, get_non_null_annotation, is_subclass

from . import all_fields as fields
from .base_fields import BaseField, VisibilityFilter

DEFAULT_FIELDS_REPR: dict[type, BaseField] = {
    str: fields.Text,
    int: fields.Number,
    float: fields.Number,
    bool: fields.Checkbox,
    date: fields.Date,
    time: fields.Time,
    list: fields.MultiSelect,
    Literal: fields.Select,
    Enum: fields.Select,
    BaseModel: fields.Model,
}
DEFAULT_REPR = fields.Json


def get_default_repr(field_info: FieldInfo, **kwargs) -> BaseField:
    """Get default field representation."""
    ann = get_non_null_annotation(field_info.annotation)
    type_ = Type.classify(field_info.annotation, discriminator=field_info.discriminator)

    if type_ == Type.SCALAR:
        return DEFAULT_FIELDS_REPR.get(ann, DEFAULT_REPR)(**kwargs)

    if type_ in [Type.MODEL, Type.DISCRIMINATED_MODEL]:
        return fields.Model(**kwargs)

    if type_ == Type.MODEL_LIST:
        return fields.ModelList(**kwargs)

    # Test for type origin
    origin = get_origin(ann)
    if origin in DEFAULT_FIELDS_REPR:
        return DEFAULT_FIELDS_REPR[origin](**kwargs)

    # Test for subclass
    for type_, field_repr in DEFAULT_FIELDS_REPR.items():
        if is_subclass(ann, type_):
            return field_repr(**kwargs)

    return DEFAULT_REPR(**kwargs)


__all__ = [
    "BaseField",
    "VisibilityFilter",
    "fields",
]

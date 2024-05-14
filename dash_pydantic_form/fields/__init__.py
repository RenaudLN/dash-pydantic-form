import logging
from datetime import date, time
from enum import Enum
from types import UnionType
from typing import Literal, Union, get_args, get_origin

from pydantic import BaseModel
from pydantic.fields import FieldInfo

from dash_pydantic_form.utils import get_non_null_annotation, is_subclass

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

    # Test for model list
    if get_origin(ann) == list and is_subclass(get_args(ann)[0], BaseModel):
        return fields.ModelList(**kwargs)

    # Test for discriminated model
    if field_info.discriminator:
        if get_origin(ann) in [Union, UnionType] and all(is_subclass(x, BaseModel) for x in get_args(ann)):
            # return fields.DiscriminatedModel(**kwargs)
            logging.info("Discriminated model fields not yet supported.")
        else:
            logging.info(f"Discriminator not supported for {field_info.annotation}")

    # Test for simple types
    if ann in DEFAULT_FIELDS_REPR:
        return DEFAULT_FIELDS_REPR[ann](**kwargs)

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

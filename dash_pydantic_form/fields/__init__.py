import contextlib
from datetime import date, time
from enum import Enum
from typing import Literal, get_args, get_origin

from pydantic import BaseModel

from dash_pydantic_form.utils import get_non_null_annotation

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


def get_default_repr(ann: type, **kwargs) -> BaseField:
    """Get default field representation."""
    ann = get_non_null_annotation(ann)
    with contextlib.suppress(Exception):
        if get_origin(ann) == list and issubclass(get_args(ann)[0], BaseModel):
            return fields.ModelList(**kwargs)

    if ann in DEFAULT_FIELDS_REPR:
        return DEFAULT_FIELDS_REPR[ann](**kwargs)
    with contextlib.suppress(Exception):
        origin = get_origin(ann)
        if origin in DEFAULT_FIELDS_REPR:
            return DEFAULT_FIELDS_REPR[origin](**kwargs)
    for type_, field_repr in DEFAULT_FIELDS_REPR.items():
        with contextlib.suppress(Exception):
            if issubclass(ann, type_):
                return field_repr(**kwargs)
    return DEFAULT_REPR(**kwargs)


__all__ = [
    "BaseField",
    "VisibilityFilter",
    "fields",
]

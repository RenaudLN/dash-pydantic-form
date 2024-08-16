import logging
from datetime import date, datetime, time
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
    datetime: fields.Datetime,
    time: fields.Time,
    list: fields.MultiSelect,
    Literal: fields.Select,
    Enum: fields.Select,
    BaseModel: fields.Model,
}
DEFAULT_REPR = fields.Json


def get_default_repr(field_info: FieldInfo | None, annotation: type | None = None, **kwargs) -> BaseField:  # noqa: PLR0911, PLR0912
    """Get default field representation."""
    if field_info is not None:
        # Add default repr kwargs
        if (
            field_info.json_schema_extra
            and (repr_kwargs := field_info.json_schema_extra.get("repr_kwargs")) is not None
        ):
            kwargs = repr_kwargs | kwargs

        # Use repr_type if provided and exists
        if field_info.json_schema_extra and (repr_type := field_info.json_schema_extra.get("repr_type")) is not None:
            repr_cls = getattr(fields, repr_type, None)
            if repr_cls is not None:
                return repr_cls(**kwargs)
            logging.warning("Unknown repr_type: %s", repr_type)

        ann = get_non_null_annotation(field_info.annotation)
        type_ = Type.classify(field_info.annotation, discriminator=field_info.discriminator)
    else:
        if annotation is None:
            raise ValueError("Either field_info or annotation must be provided")
        ann = annotation
        type_ = Type.classify(ann)

    if type_ in [Type.MODEL, Type.DISCRIMINATED_MODEL]:
        return fields.Model(**kwargs)

    if type_ in [Type.MODEL_LIST, Type.SCALAR_LIST]:
        if type_ == Type.SCALAR_LIST:
            kwargs.update(render_type="scalar")
        return fields.List(**kwargs)

    if type_ in [Type.MODEL_DICT, Type.SCALAR_DICT, Type.LITERAL_DICT]:
        if type_ in [Type.SCALAR_DICT, Type.LITERAL_DICT]:
            kwargs.update(render_type="scalar")
        return fields.Dict(**kwargs)

    if type_ == Type.SCALAR and ann in DEFAULT_FIELDS_REPR:
        return DEFAULT_FIELDS_REPR.get(ann, DEFAULT_REPR)(**kwargs)

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

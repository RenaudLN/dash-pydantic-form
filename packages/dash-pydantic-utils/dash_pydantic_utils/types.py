from datetime import date, time
from enum import Enum
from numbers import Number
from types import UnionType
from typing import Annotated, Literal, Union, get_args, get_origin

from pydantic import BaseModel
from pydantic.fields import FieldInfo

from dash_pydantic_utils.common import get_non_null_annotation, is_subclass

SEP = ":"


class Type(Enum):
    """Types of fields."""

    SCALAR = "scalar"
    LITERAL = "literal"
    MODEL = "model"
    UNKNOWN = "unknown"
    DISCRIMINATED_MODEL = "discriminated_model"
    MODEL_LIST = "model_list"
    SCALAR_LIST = "scalar_list"
    LITERAL_LIST = "literal_list"
    UNKOWN_LIST = "unknown_list"
    DISCRIMINATED_MODEL_LIST = "discriminated_model_list"
    MODEL_DICT = "model_dict"
    SCALAR_DICT = "scalar_dict"
    LITERAL_DICT = "literal_dict"
    UNKOWN_DICT = "unkown_dict"
    DISCRIMINATED_MODEL_DICT = "discriminated_model_dict"

    @classmethod
    def classify(cls, annotation: type, discriminator: str | None = None, depth: int = 0) -> bool:  # noqa: PLR0911, PLR0912
        """Classify a value as a field type."""
        annotation = get_non_null_annotation(annotation)

        if get_origin(annotation) is Annotated and get_origin(get_args(annotation)[0]) in [Union, UnionType]:
            if discriminator is None:
                discriminator = next(
                    (f.discriminator for f in get_args(annotation)[1:] if isinstance(f, FieldInfo)), None
                )
            annotation = get_args(annotation)[0]

        if is_subclass(annotation, str | Number | bool | date | time):
            return cls.SCALAR

        if (get_origin(annotation) == Literal) | is_subclass(annotation, Enum):
            return cls.LITERAL

        if is_subclass(annotation, BaseModel):
            return cls.MODEL

        if get_origin(annotation) in [Union, UnionType]:
            if discriminator and all(is_subclass(x, BaseModel) for x in get_args(annotation)):
                return cls.DISCRIMINATED_MODEL
            if all(is_subclass(x, str | Number) for x in get_args(annotation)):
                return cls.SCALAR

        if get_origin(annotation) is list and not depth:
            ann_args = get_args(annotation)
            if not ann_args:
                return cls.UNKOWN_LIST
            args_type = Type.classify(ann_args[0], depth=1)
            if args_type == Type.SCALAR:
                return cls.SCALAR_LIST
            if args_type == Type.LITERAL:
                return cls.LITERAL_LIST
            if args_type == Type.MODEL:
                return cls.MODEL_LIST
            if args_type == Type.DISCRIMINATED_MODEL:
                return cls.DISCRIMINATED_MODEL_LIST
            return cls.UNKOWN_LIST

        if get_origin(annotation) is dict and not depth:
            ann_args = get_args(annotation)
            if not ann_args:
                return cls.UNKOWN_DICT
            args_type = Type.classify(ann_args[1], depth=1)
            if args_type == Type.SCALAR:
                return cls.SCALAR_DICT
            if args_type == Type.LITERAL:
                return cls.LITERAL_DICT
            if args_type == Type.MODEL:
                return cls.MODEL_DICT
            if args_type == Type.DISCRIMINATED_MODEL:
                return cls.DISCRIMINATED_MODEL_DICT
            return cls.UNKOWN_DICT

        return cls.UNKNOWN

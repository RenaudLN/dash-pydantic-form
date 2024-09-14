import logging
import re
from copy import deepcopy
from datetime import date, time
from enum import Enum
from numbers import Number
from types import UnionType
from typing import Any, Literal, Union, get_args, get_origin

from pydantic import BaseModel, ValidationError, create_model
from pydantic_core import PydanticUndefined

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
    MODEL_DICT = "model_dict"
    SCALAR_DICT = "scalar_dict"
    LITERAL_DICT = "literal_dict"
    UNKOWN_DICT = "unkown_dict"

    @classmethod
    def classify(cls, annotation: type, discriminator: str | None = None, depth: int = 0) -> bool:  # noqa: PLR0911, PLR0912
        """Classify a value as a field type."""
        annotation = get_non_null_annotation(annotation)

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

        if get_origin(annotation) == list and not depth:
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
            return cls.UNKOWN_LIST

        if get_origin(annotation) == dict and not depth:
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
            return cls.UNKOWN_DICT

        return cls.UNKNOWN


def deep_merge(dict1: dict, dict2: dict) -> dict:
    """Deep merge two dictionaries, the second input is given priority."""
    dict_final = deepcopy(dict1)
    for key, val in dict2.items():
        if isinstance(val, dict):
            dict_final[key] = deep_merge(dict_final.get(key, {}), val)
        else:
            dict_final[key] = val
    return dict_final


def deep_diff(dict1: dict, dict2: dict) -> dict[str, dict | tuple[Any, Any]]:
    """Compute the deep difference between two dictionaries."""
    diff = {}
    for key in dict1.keys() | dict2.keys():
        if isinstance(dict1.get(key), dict) and isinstance(dict2.get(key), dict):
            sub_diff = deep_diff(dict1[key], dict2[key])
            if sub_diff:
                diff[key] = sub_diff
        elif dict1.get(key) != dict2.get(key):
            diff[key] = (dict1.get(key), dict2.get(key))
    return diff


def get_non_null_annotation(annotation: type[Any]) -> type[Any]:
    """Get a non-null annotation.

    e.g., get_non_null_annotation(Optional[str]) = str
    """
    if get_origin(annotation) in [Union, UnionType]:
        args = tuple(x for x in get_args(annotation) if x != type(None))
        if len(args) == 1:
            return args[0]
        return Union[args]  # noqa: UP007
    return annotation


def get_model_value(item: BaseModel, field: str, parent: str, allow_default: bool = True):  # noqa: PLR0911
    """Get the value of a model (parent, field) pair.

    Parameters
    ----------
    item: BaseModel
        The object to get the value from
    field: str
        The field name
    parent: str
        The parent of the field (for nested fields), in dot notation
    allow_default: bool
        Allow to return the default value, when the object has been created with model_construct.
    """
    try:
        subitem = get_subitem(item, parent)
        if isinstance(subitem, BaseModel):
            return subitem[field]
        if isinstance(subitem, dict) and isinstance(field, int):
            return list(subitem.values())[field]
        return subitem[field]
    except:
        if allow_default:
            subitem_cls = get_subitem_cls(item.__class__, parent, item=item)
            if not is_subclass(subitem_cls, BaseModel):
                return None
            field_info = subitem_cls.model_fields[field]
            if field_info.default is not PydanticUndefined:
                return field_info.default
            if field_info.default_factory:
                return field_info.default_factory()
            return None
        raise


def get_subitem(item: BaseModel | list | dict, parent: str) -> BaseModel:
    """Get the subitem of a model at a given parent.

    e.g., get_subitem(person, "au_metadata") = AUMetadata(param1=True, param2=False)
    """
    if parent == "":
        return item

    path = parent.split(SEP)

    first_part = path[0]
    if isinstance(first_part, str) and first_part.isdigit():
        first_part = int(first_part)

    if isinstance(item, BaseModel):
        next_item = getattr(item, first_part)
    elif isinstance(item, dict) and isinstance(first_part, int):
        next_item = list(item.values())[first_part]
    else:
        next_item = item[first_part]

    if len(path) == 1:
        return next_item

    return get_subitem(next_item, SEP.join(path[1:]))


def is_idx_template(val: str):
    """Check if a string is an index template."""
    return bool(re.findall(r"^\{\{[\w|\{\}]+\}\}$", val))


def get_subitem_cls(model: type[BaseModel], parent: str, item: BaseModel | None = None) -> type[BaseModel]:
    """Get the subitem class of a model at a given parent.

    e.g., get_subitem_cls(Person, "au_metadata") = AUMetadata
    """
    if parent == "":
        return model

    path = parent.split(SEP)

    first_part = path[0]
    second_part = None

    if len(path) == 1:
        ann = get_non_null_annotation(model.model_fields[first_part].annotation)
        return ann

    second_part = path[1]
    if isinstance(second_part, str) and second_part.isdigit():
        second_part = int(second_part)

    field_info = model.model_fields[first_part]
    first_annotation = get_non_null_annotation(field_info.annotation)
    try:
        subitem = get_subitem(item, first_part) if item is not None else None
    except:  # noqa: E722
        subitem = None
    if Type.classify(first_annotation, field_info.discriminator) == Type.DISCRIMINATED_MODEL:
        if not item:
            raise TypeError("Discriminated models with nesting need passing item data to be displayed")
        discriminator_value = None if subitem is None else getattr(subitem, field_info.discriminator, None)
        subitem_cls, _ = handle_discriminated(
            item.__class__, path, first_annotation, field_info.discriminator, discriminator_value
        )
        return get_subitem_cls(subitem_cls, SEP.join(path[1:]), item=subitem)
    if (
        get_origin(first_annotation) is list
        and (isinstance(second_part, int) or is_idx_template(second_part))
        and get_args(first_annotation)
    ):
        return get_subitem_cls(
            get_non_null_annotation(get_args(first_annotation)[0]),
            SEP.join(path[2:]),
            item=subitem,
        )
    if (
        get_origin(first_annotation) is dict
        and (isinstance(second_part, int) or is_idx_template(second_part))
        and get_args(first_annotation)
    ):
        return get_subitem_cls(
            get_non_null_annotation(get_args(first_annotation)[1]),
            SEP.join(path[2:]),
            item=subitem,
        )
    return get_subitem_cls(first_annotation, SEP.join(path[1:]), item=subitem)


def handle_discriminated(model: type[BaseModel], parent: str, annotation: type, disc_field: str, disc_val: Any):
    """Handle a discriminated model."""
    all_vals = set()
    out = None
    for possible in get_args(annotation):
        if not get_origin(possible.model_fields[disc_field].annotation) == Literal:
            raise ValueError("Discriminator must be a Literal")

        vals = get_args(possible.model_fields[disc_field].annotation)
        all_vals = all_vals.union(vals)
        if disc_val is not None and disc_val in vals:
            out = possible

    all_vals = tuple(all_vals)

    if disc_val is None:
        return create_model(
            f"{model.__name__}{parent.replace(SEP, ' ').title().replace(' ', '')}Discriminator",
            **{disc_field: (Literal[tuple(all_vals)], ...)},
        ), all_vals

    if out is None:
        raise ValueError(f"Invalid discriminator value: {disc_val}")

    return out, all_vals


def get_fullpath(*parts, sep: str = SEP):
    """Creates the full path of a field from its name and parent."""
    return sep.join([str(p) for p in parts]).strip(sep)


def get_all_subclasses(cls: type):
    """Get all subclasses of a class."""
    all_subclasses = []

    for subclass in cls.__subclasses__():
        all_subclasses.append(subclass)
        all_subclasses.extend(get_all_subclasses(subclass))

    return all_subclasses


def get_model_cls(str_repr: str) -> type[BaseModel]:
    """Get the model class from a string representation."""
    return next(cls for cls in get_all_subclasses(BaseModel) if str(cls) == str_repr)


def is_subclass(cls: type, base_cls: type) -> bool:
    """Check if a class is a subclass of another class, handling issubclass errors."""
    try:
        return issubclass(cls, base_cls)
    except TypeError:
        return False


def model_construct_recursive(data: dict, data_model: type[BaseModel]):
    """Construct a model recursively."""
    updated = deepcopy(data)
    for key, val in data.items():
        if key not in data_model.model_fields:
            continue

        field_info = data_model.model_fields[key]
        ann = get_non_null_annotation(field_info.annotation)
        type_ = Type.classify(ann, field_info.discriminator)
        if type_ == Type.MODEL:
            updated[key] = model_construct_recursive(val, ann)
        elif type_ == Type.DISCRIMINATED_MODEL and field_info.discriminator in val:
            disc_val = val[field_info.discriminator]
            out = None
            for possible in get_args(ann):
                if not get_origin(possible.model_fields[field_info.discriminator].annotation) == Literal:
                    raise ValueError("Discriminator must be a Literal")

                if disc_val in get_args(possible.model_fields[field_info.discriminator].annotation):
                    out = possible
                    break
            if out is not None:
                updated[key] = model_construct_recursive(val, possible)
        elif type_ == Type.MODEL_LIST and isinstance(val, list):
            updated[key] = [model_construct_recursive(vv, get_args(ann)[0]) for vv in val]

    return data_model.model_construct(**updated)


def from_form_data(data: dict, data_model: type[BaseModel]):
    """Construct a model from form data, allowing to use default values when validation of a field fails."""
    try:
        return data_model.model_validate(data)
    except ValidationError as exc:
        data_with_defaults = deepcopy(data)
        defaulted_fields = []
        for error in exc.errors():
            path_parts = [str(x) for x in error["loc"]]
            for i in range(len(path_parts), 0, -1):
                parts_extract = path_parts[:i]
                path = SEP.join(parts_extract)
                try:
                    failing_model = get_subitem_cls(data_model, SEP.join(parts_extract[:-1]))
                except AttributeError:
                    continue
                if not is_subclass(failing_model, BaseModel):
                    continue
                field = failing_model.model_fields[parts_extract[-1]]
                if field.default != PydanticUndefined:
                    set_at_path(data_with_defaults, path, field.default)
                    defaulted_fields.append(path)
                    break
                if field.default_factory is not None:
                    set_at_path(data_with_defaults, path, field.default_factory())
                    defaulted_fields.append(path)
                    break

        if defaulted_fields:
            logging.info(
                "Could not validate the following fields: %s for %s, using default values instead.",
                defaulted_fields,
                data_model.__name__,
            )
        return data_model.model_validate(data_with_defaults)


def set_at_path(data: dict, path: str, value: Any):
    """Set a value at a path in a dictionary."""
    parts = path.split(SEP)
    pointer = data
    for part in parts[:-1]:
        pointer = pointer.get(part, pointer[int(part)])
    pointer[parts[-1]] = value

import logging
import re
from copy import deepcopy
from types import UnionType
from typing import Annotated, Any, Literal, Union, get_args, get_origin

from pydantic import BaseModel, ValidationError, create_model
from pydantic.fields import FieldInfo
from pydantic_core import PydanticUndefined

from dash_pydantic_utils.common import get_non_null_annotation, is_subclass
from dash_pydantic_utils.types import Type

SEP = ":"


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
        if isinstance(subitem, list) and isinstance(field, int):
            return subitem[field]
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
    elif isinstance(item, list) and isinstance(first_part, int):
        next_item = item[first_part]
    elif is_idx_template(first_part):
        next_item = None
    else:
        next_item = item.get(first_part)

    if len(path) == 1 or next_item is None:
        return next_item

    return get_subitem(next_item, SEP.join(path[1:]))


def is_idx_template(val: str):
    """Check if a string is an index template."""
    return bool(re.findall(r"^\{\{[\w|\{\}]+\}\}$", val))


def get_subitem_cls(  # noqa: PLR0912
    model: type[BaseModel], parent: str, item: BaseModel | None = None
) -> type[BaseModel]:
    """Get the subitem class of a model at a given parent.

    e.g., get_subitem_cls(Person, "au_metadata") = AUMetadata
    """
    if parent == "":
        return model

    path = parent.split(SEP)

    first_part = path[0]
    second_part = None

    if get_origin(model) is Annotated:
        model = get_args(model)[0]
        if get_origin(model) in [Union, UnionType]:
            # NOTE: This might break if several models in the union have the same field name but different definitions
            # or if they have further nesting / unions
            model = next(m for m in get_args(model) if is_subclass(m, BaseModel) and first_part in m.model_fields)

    if len(path) == 1:
        ann = get_non_null_annotation(model.model_fields[first_part].annotation)
        return ann

    second_part = path[1]
    if isinstance(second_part, str) and second_part.isdigit():
        second_part = int(second_part)

    if is_subclass(model, BaseModel):
        field_info = model.model_fields[first_part]
    elif isinstance(item, BaseModel):
        field_info = item.model_fields[first_part]
    else:
        raise TypeError(f"Unsupported model class: {model}")
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
            item.__class__, parent, first_annotation, field_info.discriminator, discriminator_value
        )
        return get_subitem_cls(subitem_cls, SEP.join(path[1:]), item=subitem)
    if (
        get_origin(first_annotation) is list
        and (isinstance(second_part, int) or is_idx_template(second_part))
        and get_args(first_annotation)
    ):
        try:
            subitem = subitem[second_part] if subitem is not None else None
        except:  # noqa: E722
            subitem = None
        return get_subitem_cls(
            get_non_null_annotation(get_args(first_annotation)[0]),
            SEP.join(path[2:]),
            item=subitem,
        )
    if get_origin(first_annotation) is dict and (isinstance(second_part, int | str)) and get_args(first_annotation):
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
    if get_origin(annotation) is Annotated:
        if disc_field is None:
            disc_field = next(
                (f.discriminator for f in get_args(annotation)[1:] if isinstance(f, FieldInfo)),
                None,
            )
        annotation = get_args(annotation)[0]
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


def model_construct_recursive(data: dict, data_model: type[BaseModel]):
    """Construct a model recursively."""
    if not isinstance(data, dict):
        return data_model.model_construct()

    updated = deepcopy(data)
    for key, val in data.items():
        if key not in data_model.model_fields:
            continue
        if val is None:
            updated[key] = None
            continue

        field_info = data_model.model_fields[key]
        ann = get_non_null_annotation(field_info.annotation)
        type_ = Type.classify(ann, field_info.discriminator)
        if type_ == Type.MODEL:
            updated[key] = model_construct_recursive(val, ann)
        elif type_ == Type.DISCRIMINATED_MODEL:
            updated[key] = _construct_handle_discriminated(val, field_info.discriminator, ann)
        elif type_ == Type.MODEL_LIST and isinstance(val, list):
            updated[key] = [model_construct_recursive(vv, get_args(ann)[0]) for vv in val]
        elif type_ == Type.DISCRIMINATED_MODEL_LIST and isinstance(val, list):
            new_val = []
            sub_ann = get_args(ann)[0]
            # Note: since we have a DISCRIMINATED_MODEL_LIST, sub_ann will be an Annotated union with discriminator
            sub_ann2 = get_args(sub_ann)[0]
            discriminator = next((f.discriminator for f in get_args(sub_ann)[1:] if isinstance(f, FieldInfo)), None)
            for vv in val:
                new_val.append(_construct_handle_discriminated(vv, discriminator, sub_ann2))
            updated[key] = new_val
        elif type_ == Type.DISCRIMINATED_MODEL_DICT and isinstance(val, dict):
            new_val = {}
            sub_ann = get_args(ann)[1]
            # Note: since we have a DISCRIMINATED_MODEL_LIST, sub_ann will be an Annotated union with discriminator
            sub_ann2 = get_args(sub_ann)[0]
            discriminator = next((f.discriminator for f in get_args(sub_ann)[1:] if isinstance(f, FieldInfo)), None)
            for kk, vv in val.items():
                new_val[kk] = _construct_handle_discriminated(vv, discriminator, sub_ann2)
            updated[key] = new_val

    return data_model.model_construct(**updated)


def _construct_handle_discriminated(val: dict, discriminator: str | None, ann: type):
    if discriminator is None or discriminator not in val:
        return val

    disc_val = val[discriminator]
    out = None
    for possible in get_args(ann):
        if not get_origin(possible.model_fields[discriminator].annotation) == Literal:
            raise ValueError("Discriminator must be a Literal")

        if disc_val in get_args(possible.model_fields[discriminator].annotation):
            out = possible
            break

    if out is not None:
        return model_construct_recursive(val, out)
    return val


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

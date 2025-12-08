import logging
import re
from copy import deepcopy
from types import UnionType
from typing import Annotated, Any, Literal, Union, get_args, get_origin

from pydantic import BaseModel, Field, RootModel, ValidationError, create_model
from pydantic.fields import FieldInfo
from pydantic_core import PydanticUndefined

from dash_pydantic_utils.common import get_non_null_annotation, is_subclass
from dash_pydantic_utils.types import Type, get_discriminator_from_annotated, get_str_discriminator

SEP = ":"

logger = logging.getLogger(__name__)


def get_model_value(item: BaseModel | None, field: str, parent: str, allow_default: bool = True):  # noqa: PLR0911, PLR0912
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
    if item is None:
        if allow_default:
            return None
        else:
            raise ValueError("item is None")
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
            if not is_subclass(subitem_cls, BaseModel) or field not in subitem_cls.model_fields:
                return None
            field_info = subitem_cls.model_fields[field]
            if field_info.default is not PydanticUndefined:
                return field_info.default
            if field_info.default_factory:
                try:
                    return field_info.default_factory()
                except TypeError:
                    logger.warning("Default factory with validated data not supported in allow_default")
            return None
        raise


def get_subitem(item: BaseModel | list | dict, parent: str) -> BaseModel | list | dict | None:
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
        if first_part in item.__class__.model_fields:
            next_item = getattr(item, first_part, None)
        else:
            raise AttributeError(f"Field {first_part} unavailable in {item}")
    elif isinstance(first_part, str) and is_idx_template(first_part):
        next_item = None
    elif isinstance(item, dict):
        next_item = list(item.values())[first_part] if isinstance(first_part, int) else item.get(first_part)
    elif isinstance(item, list) and isinstance(first_part, int):
        next_item = item[first_part]
    else:
        raise AttributeError(f"{first_part} unavailable in {item}")

    if len(path) == 1 or next_item is None:
        return next_item

    return get_subitem(next_item, SEP.join(path[1:]))


def is_idx_template(val: str):
    """Check if a string is an index template."""
    return bool(re.findall(r"^\{\{[\w|\{\}]+\}\}$", val))


def convert_root_to_base_model(root_model: type[RootModel]) -> type[BaseModel]:
    """Convert a RootModel to a BaseModel."""
    base_model = create_model(
        root_model.__name__,
        rootmodel_root_=(root_model.model_fields["root"].annotation, Field(title="")),
    )

    return base_model


def root_model_converter(func):
    """Decorator to convert a RootModel to a BaseModel."""

    def wrapper(*args, **kwargs):
        out = func(*args, **kwargs)
        if is_subclass(out, RootModel):
            return convert_root_to_base_model(out)
        return out

    return wrapper


@root_model_converter
def get_subitem_cls(  # noqa: PLR0912, PLR0915
    model: type[BaseModel] | type[RootModel], parent: str, item: BaseModel | None = None
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
            if item is not None and type(item) in get_args(model):
                model = type(item)
            else:
                # NOTE: This might break if several models in the union have the same field name
                # but different definitions or if they have further nesting / unions
                model = next(m for m in get_args(model) if is_subclass(m, BaseModel) and first_part in m.model_fields)

    if issubclass(model, RootModel):
        model = convert_root_to_base_model(model)

    if len(path) == 1:
        ann = model.model_fields[first_part].annotation
        if ann is None:
            raise ValueError("Field has no annotation")
        ann = get_non_null_annotation(ann)
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
    if field_info.annotation is None:
        raise ValueError("Field has no annotation")
    first_annotation = get_non_null_annotation(field_info.annotation)
    try:
        subitem = get_subitem(item, first_part) if item is not None else None
        if not isinstance(subitem, BaseModel | list | dict):
            subitem = None
    except:  # noqa: E722
        subitem = None
    discriminator = get_str_discriminator(field_info)
    if Type.classify(first_annotation, discriminator) == Type.DISCRIMINATED_MODEL:
        if item is None:
            raise TypeError("Discriminated models with nesting need passing item data to be displayed")
        if discriminator is None:
            raise ValueError("discriminator should be provided if data_model is a discriminated union")
        discriminator_value = None if subitem is None else getattr(subitem, discriminator, None)
        subitem_cls, _ = handle_discriminated(parent, first_annotation, discriminator, discriminator_value)
        return get_subitem_cls(subitem_cls, SEP.join(path[1:]), item=subitem)
    if (
        get_origin(first_annotation) is list
        and (isinstance(second_part, int) or is_idx_template(second_part))
        and get_args(first_annotation)
    ):
        try:
            subitem = subitem[second_part] if subitem is not None else None
            if not isinstance(subitem, BaseModel):
                subitem = None
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


def handle_discriminated(parent: str, annotation: type, disc_field: str, disc_val: Any | None):
    """Handle a discriminated model."""
    all_vals_set: set[str] = set()
    out = None
    if get_origin(annotation) is Annotated:
        disc_field = disc_field or get_discriminator_from_annotated(annotation, True)
        annotation = get_args(annotation)[0]
    if get_origin(annotation) not in [Union, UnionType]:
        raise ValueError("Should be a union")
    for possible in get_args(annotation):
        if not issubclass(possible, BaseModel):
            raise ValueError("Should be a union of BaseModel")
        if not get_origin(possible.model_fields[disc_field].annotation) == Literal:
            raise ValueError("Discriminator must be a Literal")
        vals = get_args(possible.model_fields[disc_field].annotation)
        if len(vals) != 1:
            raise ValueError("Discriminator field must be a Literal with exactly 1 value")
        if not all(isinstance(x, str) for x in vals):
            raise ValueError("Discriminator field must be a Literal with exactly 1 string value")
        all_vals_set = all_vals_set.union(vals)
        if disc_val is not None and disc_val in vals:
            out = possible

    all_vals = tuple(all_vals_set)

    if disc_val is None:
        programmatic_model = create_model(
            f"M{hash(str(annotation))}{parent.replace(SEP, ' ').title().replace(' ', '')}Discriminator",
            __config__=None,
            __doc__=None,
            __base__=None,
            __module__=__name__,
            __validators__=None,
            __cls_kwargs__=None,
            **{disc_field: (Literal[tuple(all_vals)], ...)},
        )
        return programmatic_model, all_vals

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
        ann = field_info.annotation
        if ann is None:
            raise ValueError("Annotation is None")
        ann = get_non_null_annotation(ann)
        discriminator = get_str_discriminator(field_info)
        type_ = Type.classify(ann, discriminator)
        if type_ == Type.MODEL:
            updated[key] = model_construct_recursive(val, ann)
        elif type_ == Type.DISCRIMINATED_MODEL:
            updated[key] = _construct_handle_discriminated(val, discriminator, ann)
        elif type_ == Type.MODEL_LIST and isinstance(val, list):
            updated[key] = [model_construct_recursive(vv, get_args(ann)[0]) for vv in val]
        elif type_ == Type.DISCRIMINATED_MODEL_LIST and isinstance(val, list):
            new_val = []
            sub_ann = get_args(ann)[0]
            # Note: since we have a DISCRIMINATED_MODEL_LIST, sub_ann will be an Annotated union with discriminator
            sub_ann2 = get_args(sub_ann)[0]
            discriminator = next(
                (get_str_discriminator(f) for f in get_args(sub_ann)[1:] if isinstance(f, FieldInfo)), None
            )
            for vv in val:
                new_val.append(_construct_handle_discriminated(vv, discriminator, sub_ann2))
            updated[key] = new_val
        elif type_ == Type.DISCRIMINATED_MODEL_DICT and isinstance(val, dict):
            new_val = {}
            sub_ann = get_args(ann)[1]
            # Note: since we have a DISCRIMINATED_MODEL_LIST, sub_ann will be an Annotated union with discriminator
            sub_ann2 = get_args(sub_ann)[0]
            discriminator = next(
                (get_str_discriminator(f) for f in get_args(sub_ann)[1:] if isinstance(f, FieldInfo)), None
            )
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
                    try:
                        set_at_path(data_with_defaults, path, field.default_factory())
                        defaulted_fields.append(path)
                        break
                    except TypeError:
                        logger.warning("Default factory with validated data not supported in allow_default")

        if defaulted_fields:
            logger.info(
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

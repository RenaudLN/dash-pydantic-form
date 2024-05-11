from copy import deepcopy
from types import UnionType
from typing import Any, Union, get_args, get_origin

from pydantic import BaseModel
from pydantic_core import PydanticUndefined

SEP = ":"


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
    if (
        get_origin(annotation) in [Union, UnionType]
        and len(non_null_ann := list(set(get_args(annotation)) - {type(None)})) == 1
    ):
        return non_null_ann[0]
    return annotation


def get_model_value(item: BaseModel, field: str, parent: str, allow_default: bool = True):
    """Get the value of a model (parent, field) pair.

    :param item: The object to get the value from
    :param parent: The parent of the field (for nested fields), in dot notation
    :param field: The field name
    :param allow_default: Allow to return the default value, when the object has been created with model_construct.
    """
    try:
        return get_subitem(item, parent)[field]
    except:
        if allow_default:
            field_info = get_subitem_cls(item, parent).model_fields[field]
            if field_info.default is not PydanticUndefined:
                return field_info.default
            if field_info.default_factory:
                return field_info.default_factory()
            return None
        raise


def get_subitem(item: BaseModel, parent: str) -> BaseModel:
    """Get the subitem of a model at a given parent.

    e.g., get_subitem(person, "au_metadata") = AUMetadata(param1=True, param2=False)
    """
    if parent == "":
        return item

    path = parent.split(SEP)

    first_part = path[0]
    if isinstance(first_part, str) and first_part.isdigit():
        first_part = int(first_part)

    if len(path) == 1:
        if isinstance(item, BaseModel):
            return getattr(item, first_part)
        return item[first_part]

    return get_subitem(getattr(item, first_part), SEP.join(path[1:]))


def get_subitem_cls(model: type[BaseModel], parent: str) -> type[BaseModel]:
    """Get the subitem class of a model at a given parent.

    e.g., get_subitem_cls(Person, "au_metadata") = AUMetadata
    """
    if parent == "":
        return model

    path = parent.split(SEP)

    first_part = path[0]
    second_part = None

    if len(path) == 1:
        return get_non_null_annotation(model.model_fields[first_part].annotation)

    second_part = path[1]
    if isinstance(second_part, str) and second_part.isdigit():
        second_part = int(second_part)

    first_annotation = get_non_null_annotation(model.model_fields[first_part].annotation)
    if get_non_null_annotation(get_origin(first_annotation)) == list and isinstance(second_part, int):
        return get_subitem_cls(
            get_non_null_annotation(get_args(first_annotation)[0]),
            SEP.join(path[2:]),
        )
    return get_subitem_cls(first_annotation, SEP.join(path[1:]))


def get_fullpath(*parts):
    """Creates the full path of a field from its name and parent."""
    return SEP.join([str(p) for p in parts]).strip(SEP)


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

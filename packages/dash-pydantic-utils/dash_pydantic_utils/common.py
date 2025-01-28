from copy import deepcopy
from types import UnionType
from typing import Any, Union, get_args, get_origin

from pydantic import BaseModel


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
        args = tuple(x for x in get_args(annotation) if x is not type(None))
        if len(args) == 1:
            return args[0]
        return Union[args]  # noqa: UP007
    return annotation


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

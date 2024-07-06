import json

from dash.development.base_component import Component
from pydantic import BaseModel

from dash_pydantic_form import ids
from dash_pydantic_form.utils import get_non_null_annotation


def find_ids(component: Component, ids: list[str | dict]):
    """Find ids in a component tree."""
    ids_found = []
    ids_not_found = ids
    for elem in component._traverse_ids():
        if elem.id in ids:
            ids_found.append(elem.id)
            ids_not_found.remove(elem.id)
    return ids_found, ids_not_found


def check_ids_exist(component: Component, ids: list[str | dict]):
    """Check if ids exist in a component tree."""
    _, ids_not_found = find_ids(component, ids)
    if ids_not_found:
        raise ValueError(f"Could not find ids: {ids_not_found}")


def check_elem_values(component: Component, expected: dict):
    """Check if elements in a component tree have the expected values."""
    mismatched_values = {}
    for elem in component._traverse_ids():
        str_id = json.dumps(elem.id)
        attribute = "value" if ids.value_field.args[0] in str_id else "checked"
        if str_id in expected and getattr(elem, attribute) != expected[str_id]:
            mismatched_values[str_id] = (getattr(elem, attribute), expected[str_id])
    if mismatched_values:
        raise ValueError(f"Mismatched values: {mismatched_values}")


def get_field_ids(model: type[BaseModel], aio_id: str, form_id: str, fields: list[str] | None = None, **id_kwargs):
    """Get field ids for a model."""
    fields = fields or list(model.model_fields)
    for field_name in fields:
        field_info = model.model_fields[field_name]
        if fields is None or field_name in fields:
            base_id = ids.checked_field if get_non_null_annotation(field_info.annotation) is bool else ids.value_field
            yield base_id(aio_id, form_id, field_name, **id_kwargs)

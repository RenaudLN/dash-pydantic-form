import dataclasses as dc
from functools import partial

from dash.dependencies import _Wildcard


def form_dependent_id(component: str, aio_id: str | _Wildcard, form_id: str | _Wildcard) -> dict:
    """A component id to do callbacks at the document level (e.g. edit/delete)."""
    return {"component": component, "aio_id": aio_id, "form_id": form_id}


def form_base_id(part: str, aio_id: str | _Wildcard, form_id: str | _Wildcard, parent: str | _Wildcard = ""):
    """Form parts id."""
    return {"part": part, "aio_id": aio_id, "form_id": form_id, "parent": parent}


def field_dependent_id(  # noqa: PLR0913
    component: str,
    aio_id: str | _Wildcard,
    form_id: str | _Wildcard,
    field: str | _Wildcard,
    parent: str | _Wildcard = "",
    meta: str | _Wildcard = "",
) -> dict:
    """A component id to do callbacks at the field level (e.g. in the form)."""
    return {
        "component": component,
        "aio_id": aio_id,
        "form_id": form_id,
        "field": field,
        "parent": parent,
        "meta": meta,
    }


value_field = partial(field_dependent_id, "_pydf-value-field")
checked_field = partial(field_dependent_id, "_pydf-checked-field")


class ModelFormIdsFactory:
    """Factory functions for model form ids."""

    form = partial(form_base_id, "_pydf-form")
    main = partial(form_base_id, "_pydf-main")
    restore_wrapper = partial(form_base_id, "_pydf-restore-wrapper")
    restore_btn = partial(form_base_id, "_pydf-restore-btn")
    cancel_restore_btn = partial(form_base_id, "_pydf-cancel-restore-btn")
    wrapper = partial(field_dependent_id, "_pydf-wrapper")
    errors = partial(form_base_id, "_pydf-errors")
    model_store = partial(form_base_id, "_pydf-model-store")
    form_specs_store = partial(form_base_id, "_pydf-form-specs-store")
    change_store = partial(form_base_id, "_pydf-changes-store")
    manage_state = partial(form_base_id, "_pydf-manage-state")


@dc.dataclass(frozen=True)
class ModelFormIds:
    """Model form ids."""

    form: dict[str, str]
    main: dict[str, str]
    restore_wrapper: dict[str, str]
    restore_btn: dict[str, str]
    cancel_restore_btn: dict[str, str]
    errors: dict[str, str]
    model_store: dict[str, str]
    form_specs_store: dict[str, str]
    change_store: dict[str, str]
    manage_state: dict[str, str]

    @classmethod
    def from_basic_ids(cls, aio_id: str, form_id: str) -> "ModelFormIds":
        """Instanciation from aio_id and form_id."""
        return cls(*(getattr(ModelFormIdsFactory, id_field.name)(aio_id, form_id) for id_field in dc.fields(cls)))

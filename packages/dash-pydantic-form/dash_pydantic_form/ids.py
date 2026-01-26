import dataclasses as dc
from functools import partial
from typing import TYPE_CHECKING, Optional, overload

from dash.dependencies import _Wildcard

if TYPE_CHECKING:
    from dash_pydantic_form.model_form import ModelForm


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

    @classmethod
    def from_basic_ids(cls, aio_id: str, form_id: str) -> "ModelFormIds":
        """Instanciation from aio_id and form_id."""
        return cls(*(getattr(ModelFormIdsFactory, id_field.name)(aio_id, form_id) for id_field in dc.fields(cls)))


class IdAccessor:
    """Descriptor for handling access to either instances or the factory of model form ids via ``ModelForm`` class."""

    @overload
    def __get__(self, obj: "ModelForm", objtype=None) -> ModelFormIds: ...
    @overload
    def __get__(self, obj: None, objtype=None) -> type[ModelFormIdsFactory]: ...
    def __get__(self, obj: Optional["ModelForm"], objtype=None):
        """Returns the ``ModelFormIdsFactory`` class if accessed via the ``ModelForm`` class directly (ModelForm.ids)
        or an instance of ``ModelFormIds`` if accessed via an instance of ``ModelForm`` (ModelForm(my_model).ids).
        """
        if obj is None:
            # access via class
            return ModelFormIdsFactory

        if isinstance(obj, ModelForm):
            # access via instance
            return obj._ids

        raise RuntimeError("IdAccessor should only be defined on ModelForm or an instance of ModelForm")

    def __set__(self, obj: "ModelForm", base: ModelFormIds | tuple[str, str]):
        """Sets another set of model form ids to a ``ModelForm`` object."""
        value = ModelFormIds.from_basic_ids(base[0], base[1]) if isinstance(base, tuple) else base

        obj._ids = value

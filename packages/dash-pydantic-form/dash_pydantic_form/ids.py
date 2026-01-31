from functools import partial

from packaging import version

if version.parse(dash.__version__) < version.parse("3.4"):
    from dash.dependencies import _WildCard as WildCard
else:
    from dash.dependencies import WildCard


def form_dependent_id(component: str, aio_id: str | WildCard, form_id: str | WildCard) -> dict:
    """A component id to do callbacks at the document level (e.g. edit/delete)."""
    return {"component": component, "aio_id": aio_id, "form_id": form_id}


def form_base_id(part: str, aio_id: str | WildCard, form_id: str | WildCard, parent: str | WildCard = ""):
    """Form parts id."""
    return {"part": part, "aio_id": aio_id, "form_id": form_id, "parent": parent}


def field_dependent_id(  # noqa: PLR0913
    component: str,
    aio_id: str | WildCard,
    form_id: str | WildCard,
    field: str | WildCard,
    parent: str | WildCard = "",
    meta: str | WildCard = "",
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

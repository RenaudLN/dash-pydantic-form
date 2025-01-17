import warnings
from typing import TYPE_CHECKING, Literal

from dash_iconify import DashIconify
from pydantic import BaseModel

if TYPE_CHECKING:
    from dash_pydantic_form.form_layouts.form_layout import FormLayout

SectionRender = Literal["accordion", "tabs", "steps"]
Position = Literal["top", "bottom", "none"]


class FormSection(BaseModel):
    """Form section model.

    Parameters
    ----------
    name: str
        Section name.
    fields: list[str]
        List of field names from the pydantic model.
    icon: str | DashIconify | None
        Section icon displayed before the section name, optional.
    default_open: bool
        Whether the section is open by default, only used for accordion sections.
    """

    name: str
    fields: list[str]
    icon: str | DashIconify | None = None
    default_open: bool = False

    model_config = {"arbitrary_types_allowed": True}


def Sections(
    sections: list[FormSection],
    remaining_fields_position: Position = "top",
    render: SectionRender = "accordion",
    render_kwargs: dict | None = None,
) -> "FormLayout":
    """Adapter from Sections to FormLayouts for backward compatibility."""
    from dash_pydantic_form.form_layouts import FormLayout

    warnings.warn("Sections is deprecated, use FormLayouts instead.", DeprecationWarning, stacklevel=1)
    return FormLayout.load(
        sections=sections,
        remaining_fields_position=remaining_fields_position,
        layout=render,
        render_kwargs=render_kwargs,
    )

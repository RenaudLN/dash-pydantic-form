from typing import Literal

from dash_iconify import DashIconify
from pydantic import BaseModel

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


class Sections(BaseModel):
    """Form sections model.

    Parameters
    ----------
    sections: list[FormSection]
        List of FormSection.
    remaining_fields_position: Literal["top", "bottom", "none"]
        Position of the fields not listed in the sections. Default "top".
    render: Literal["accordion", "tabs", "steps"]
        how the sections should be rendered. Possible values: "accordion", "tabs", "steps".
        Default "accordion".
    render_kwargs: dict | None
        Additional render kwargs passed to the section render functions, optional.
        See `ModelForm.render_accordion_sections`, `ModelForm.render_tabs_sections` and
        `ModelForm.render_steps_sections`
    """

    sections: list[FormSection]
    remaining_fields_position: Position = "top"
    render: SectionRender = "accordion"
    render_kwargs: dict | None = None

    def model_post_init(self, _context):
        """Model post init."""
        if self.render_kwargs is None:
            self.render_kwargs = {}

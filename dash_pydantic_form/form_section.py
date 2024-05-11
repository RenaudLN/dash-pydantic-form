from typing import Literal, Union

from dash_iconify import DashIconify
from pydantic import BaseModel


SectionRender = Literal["accordion", "tabs", "steps"]
Position = Literal["top", "bottom", "none"]

class FormSection(BaseModel):
    name: str
    fields: list[str]
    icon: Union[str, DashIconify, None] = None
    default_open: bool = False

    model_config = {"arbitrary_types_allowed": True}


class Sections(BaseModel):
    sections: list[FormSection]
    remaining_fields_position: Position = "top"
    render: SectionRender = "accordion"
    excluded_fields: list[str] | None = None
    render_kwargs: dict | None = None

    def model_post_init(self, _context):
        if self.render_kwargs is None:
            self.render_kwargs = {}

        if self.excluded_fields is None:
            self.excluded_fields = []

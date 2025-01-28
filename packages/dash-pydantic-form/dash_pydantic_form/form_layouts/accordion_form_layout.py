import itertools
from copy import deepcopy
from functools import partial
from typing import Literal

import dash_mantine_components as dmc
from dash.development.base_component import Component
from dash_iconify import DashIconify

from dash_pydantic_form.form_section import FormSection
from dash_pydantic_form.ids import form_base_id
from dash_pydantic_utils import deep_merge

from .form_layout import FormLayout, Position


class AccordionFormLayout(FormLayout):
    """Accordion form layout.

    Parameters
    ----------
    render_kwargs: dict | None
        Kwargs to pass to the render method.
    sections: list[FormSection]
        List of form sections.
    remaining_fields_position: Position
        Position of the remaining fields, one of 'top', 'bottom' or 'none'.
    """

    class ids:
        """Accordion form ids."""

        accordion = partial(form_base_id, "_pydf-accordion")

    sections: list[FormSection]
    remaining_fields_position: Position = "top"
    layout: Literal["accordion"] = "accordion"

    def render(  # noqa: PLR0913
        self,
        *,
        field_inputs: dict[str, Component],
        aio_id: str,
        form_id: str,
        path: str,
        **_kwargs,
    ):
        """Render the sections in an accordion."""
        kwargs = deepcopy(self.render_kwargs)
        accordion_styles = deep_merge(
            {
                "control": {"padding": "0.5rem"},
                "label": {"padding": 0},
                "item": {
                    "border": "1px solid color-mix(in srgb, var(--mantine-color-gray-light), transparent 40%)",
                    "background": "color-mix(in srgb, var(--mantine-color-gray-light), transparent 80%)",
                    "marginBottom": "0.5rem",
                    "borderRadius": "0.25rem",
                },
                "content": {
                    "display": "flex",
                    "flexDirection": "column",
                    "gap": "0.375rem",
                    "padding": "0.125rem 0.5rem 0.5rem",
                },
            },
            kwargs.pop("styles", {}),
        )
        multiple = kwargs.pop("multiple", True)
        accordion = dmc.Accordion(
            [
                dmc.AccordionItem(
                    [
                        dmc.AccordionControl(
                            dmc.Text(
                                ([DashIconify(icon=section.icon)] if section.icon else []) + [section.name],
                                style={"display": "flex", "alignItems": "center", "gap": "0.5rem"},
                                fw=600,
                            ),
                        ),
                        dmc.AccordionPanel(
                            self.grid([field_inputs[field] for field in section.fields if field in field_inputs]),
                        ),
                    ],
                    value=section.name,
                )
                for section in self.sections
            ],
            value=[section.name for section in self.sections if section.default_open]
            if multiple
            else next((section.name for section in self.sections if section.default_open), None),
            styles=accordion_styles,
            id=self.ids.accordion(aio_id, form_id, path),
            multiple=multiple,
            **kwargs,
        )

        fields_not_in_sections = set(field_inputs) - set(itertools.chain.from_iterable(s.fields for s in self.sections))

        if self.remaining_fields_position == "none" or not fields_not_in_sections:
            return [accordion]
        if self.remaining_fields_position == "top":
            return [self.grid([v for k, v in field_inputs.items() if k in fields_not_in_sections], mb="sm"), accordion]
        return [accordion, self.grid([v for k, v in field_inputs.items() if k in fields_not_in_sections], mb="sm")]

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


class TabsFormLayout(FormLayout):
    """Tabs form layout.

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
        """Tabs form ids."""

        tabs = partial(form_base_id, "_pydf-tabs")

    sections: list[FormSection]
    remaining_fields_position: Position = "top"
    layout: Literal["tabs"] = "tabs"

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
        kwargs = deepcopy(self.render_kwargs or {})
        value = self.sections[0].name
        for section in self.sections:
            if section.default_open:
                value = section.name
                break

        tabs_styles = deep_merge({"panel": {"padding": "1rem 0.5rem"}}, kwargs.pop("styles", {}))

        tabs = dmc.Tabs(
            [
                dmc.TabsList(
                    [
                        dmc.TabsTab(
                            dmc.Text(
                                ([DashIconify(icon=section.icon)] if section.icon else []) + [section.name],
                                style={"display": "flex", "alignItems": "center", "gap": "0.5rem"},
                            ),
                            value=section.name,
                        )
                        for section in self.sections
                    ]
                ),
                *[
                    dmc.TabsPanel(
                        self.grid([field_inputs[field] for field in section.fields if field in field_inputs]),
                        value=section.name,
                    )
                    for section in self.sections
                ],
            ],
            value=value,
            styles=tabs_styles,
            id=self.ids.tabs(aio_id, form_id, path),
            **kwargs,
        )

        fields_not_in_sections = set(field_inputs) - set(itertools.chain.from_iterable(s.fields for s in self.sections))

        if self.remaining_fields_position == "none" or not fields_not_in_sections:
            return [tabs]
        if self.remaining_fields_position == "top":
            return [self.grid([v for k, v in field_inputs.items() if k in fields_not_in_sections], mb="sm"), tabs]
        return [tabs, self.grid([v for k, v in field_inputs.items() if k in fields_not_in_sections], mb="sm")]

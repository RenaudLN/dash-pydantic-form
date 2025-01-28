import itertools
from copy import deepcopy
from functools import partial
from typing import Literal

import dash_mantine_components as dmc
from dash import MATCH, ClientsideFunction, Input, Output, State, clientside_callback, dcc
from dash.development.base_component import Component
from dash_iconify import DashIconify

from dash_pydantic_form.form_section import FormSection
from dash_pydantic_form.i18n import _
from dash_pydantic_form.ids import form_base_id
from dash_pydantic_utils import deep_merge

from .form_layout import FormLayout, Position


class StepsFormLayout(FormLayout):
    """Steps form layout.

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
        """Steps form ids."""

        steps = partial(form_base_id, "_pydf-steps")
        steps_save = partial(form_base_id, "_pydf-steps-save")
        steps_next = partial(form_base_id, "_pydf-steps-next")
        steps_previous = partial(form_base_id, "_pydf-steps-previous")
        steps_nsteps = partial(form_base_id, "_pydf-steps-nsteps")

    sections: list[FormSection]
    remaining_fields_position: Position = "top"
    layout: Literal["steps"] = "steps"

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
        additional_steps = kwargs.pop("additional_steps", [])
        stepper_styles = deep_merge(
            {
                "root": {"display": "flex", "gap": "1.5rem", "padding": "0.75rem 0 3rem"},
                "content": {"flex": 1, "padding": 0},
                "steps": {"minWidth": 180},
                "step": {"cursor": "pointer"},
                "stepBody": {"padding-top": "0.6875rem"},
                "stepCompletedIcon": {"&>svg": {"width": 12}},
            },
            kwargs.pop("styles", {}),
        )
        stepper = dmc.Stepper(
            id=self.ids.steps(aio_id, form_id, path),
            active=0,
            orientation=kwargs.pop("orientation", "vertical"),
            size=kwargs.pop("size", "sm"),
            styles=stepper_styles,
            children=[
                dmc.StepperStep(
                    label=section.name,
                    icon=DashIconify(icon=section.icon) if section.icon else None,
                    children=self.grid([field_inputs[field] for field in section.fields if field in field_inputs]),
                )
                for section in self.sections
            ]
            + additional_steps,
            **kwargs,
        )

        steps = dmc.Box(
            [
                stepper,
                dmc.Group(
                    [
                        dmc.Button(
                            _("Back"),
                            id=self.ids.steps_previous(aio_id, form_id, path),
                            disabled=True,
                            size="compact-sm",
                            leftSection=DashIconify(icon="carbon:arrow-left", height=16),
                        ),
                        dmc.Button(
                            _("Next"),
                            id=self.ids.steps_next(aio_id, form_id, path),
                            size="compact-sm",
                            rightSection=DashIconify(icon="carbon:arrow-right", height=16),
                        ),
                    ],
                    style={
                        "position": "absolute",
                        "top": f"calc({78 * (len(self.sections) + len(additional_steps))}px + 1rem)",
                    },
                ),
                dcc.Store(data=len(self.sections), id=self.ids.steps_nsteps(aio_id, form_id, path)),
            ],
            pos="relative",
        )

        fields_not_in_sections = set(field_inputs) - set(itertools.chain.from_iterable(s.fields for s in self.sections))

        if self.remaining_fields_position == "none" or not fields_not_in_sections:
            return [steps]
        if self.remaining_fields_position == "top":
            return [self.grid([v for k, v in field_inputs.items() if k in fields_not_in_sections], mb="sm"), steps]
        return [steps, self.grid([v for k, v in field_inputs.items() if k in fields_not_in_sections], mb="sm")]


clientside_callback(
    ClientsideFunction(namespace="pydf", function_name="stepsDisable"),
    Output(StepsFormLayout.ids.steps_previous(MATCH, MATCH, MATCH), "disabled"),
    Output(StepsFormLayout.ids.steps_next(MATCH, MATCH, MATCH), "disabled"),
    Input(StepsFormLayout.ids.steps(MATCH, MATCH, MATCH), "active"),
    State(StepsFormLayout.ids.steps_nsteps(MATCH, MATCH, MATCH), "data"),
)

clientside_callback(
    ClientsideFunction(namespace="pydf", function_name="stepsPreviousNext"),
    Output(StepsFormLayout.ids.steps(MATCH, MATCH, MATCH), "active"),
    Input(StepsFormLayout.ids.steps_previous(MATCH, MATCH, MATCH), "n_clicks"),
    Input(StepsFormLayout.ids.steps_next(MATCH, MATCH, MATCH), "n_clicks"),
    State(StepsFormLayout.ids.steps(MATCH, MATCH, MATCH), "active"),
    State(StepsFormLayout.ids.steps_nsteps(MATCH, MATCH, MATCH), "data"),
    prevent_inital_call=True,
)

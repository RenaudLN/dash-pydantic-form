import contextlib
import itertools
from copy import deepcopy
from functools import partial
from typing import Literal, Union

import dash_mantine_components as dmc
from dash import (
    ALL,
    MATCH,
    ClientsideFunction,
    Input,
    Output,
    State,
    callback,
    clientside_callback,
    ctx,
    dcc,
    html,
)
from dash.development.base_component import Component
from dash_iconify import DashIconify
from pydantic import BaseModel

from . import ids as common_ids
from .fields import BaseField, fields
from .form_section import Sections
from .utils import (
    SEP,
    Type,
    deep_merge,
    get_fullpath,
    get_model_cls,
    get_subitem,
    get_subitem_cls,
    handle_discriminated,
    model_construct_recursive,
)


def form_base_id(part: str, aio_id: str, form_id: str, parent: str = ""):
    """Form parts id."""
    return {"part": part, "aio_id": aio_id, "form_id": form_id, "parent": parent}


Children_ = Component | str | int | float
Children = Children_ | list[Children_]
SectionRender = Literal["accordion", "tabs", "steps"]
Position = Literal["top", "bottom", "none"]


class ModelForm(html.Div):
    """Create a Dash form from a pydantic model.

    Parameters
    ----------
    item: BaseModel | type[BaseModel]
        The model to create the form from, can be the model class or an instance of the class.
        If the class is passed, the form will be empty. If an instance is passed, the form will be pre-filled
        with existing values.
    aio_id: str
        All-in-one component ID
    form_id: str
        Form ID, can be used to create multiple forms on the same page. When working with databases
        this could be the document / record ID.
    fields_repr: dict[str, dict | BaseField] | None
        Mapping between field name and field representation. If not provided, default field
        representations will be used based on the field annotation.
        See :meth:`dash_pydantic_form.fields.get_default_repr`.
    sections: Sections | None
        List of form sections (optional). See :class:`dash_pydantic_form.form_section.Sections`.
    """

    class ids:
        """Model form ids."""

        main = partial(form_base_id, "_pydf-main")
        accordion = partial(form_base_id, "_pydf-accordion")
        tabs = partial(form_base_id, "_pydf-tabs")
        steps = partial(form_base_id, "_pydf-steps")
        steps_save = partial(form_base_id, "_pydf-steps-save")
        steps_next = partial(form_base_id, "_pydf-steps-next")
        steps_previous = partial(form_base_id, "_pydf-steps-previous")
        steps_nsteps = partial(form_base_id, "_pydf-steps-nsteps")
        model_store = partial(form_base_id, "_pydf-model-store")
        form_specs_store = partial(form_base_id, "_pydf-form-specs-store")

    def __init__(  # noqa: PLR0912, PLR0913, PLR0915
        self,
        item: BaseModel | type[BaseModel],
        aio_id: str,
        form_id: str,
        path: str = "",
        fields_repr: dict[str, Union["BaseField", dict]] | None = None,
        sections: Sections | None = None,
        discriminator: str | None = None,
    ) -> None:
        from dash_pydantic_form.fields import get_default_repr

        with contextlib.suppress(Exception):
            if issubclass(item, BaseModel):
                item = item.model_construct()

        fields_repr = fields_repr or {}
        field_inputs = {}
        subitem_cls = get_subitem_cls(item.__class__, path)

        # Handle type unions
        disc_vals = None
        discriminator_value = None
        if Type.classify(subitem_cls, discriminator) == Type.DISCRIMINATED_MODEL:
            subitem = get_subitem(item, path)
            discriminator_value = None if subitem is None else getattr(subitem, discriminator, None)
            subitem_cls, disc_vals = handle_discriminated(
                item.__class__, path, subitem_cls, discriminator, discriminator_value
            )

        more_kwargs = {}
        for field_name, field_info in subitem_cls.model_fields.items():
            if sections and field_name in sections.excluded_fields:
                continue
            # If discriminating field, ensure all discriminator values are shown
            # Also add required metadata for discriminator callback
            if disc_vals and field_name == discriminator:
                field_info = deepcopy(field_info)  # noqa: PLW2901
                field_info.annotation = Literal[disc_vals]
                more_kwargs |= {"n_cols": 4, "field_id_meta": "discriminator"}
            if field_name in fields_repr:
                if isinstance(fields_repr[field_name], dict):
                    field_repr = get_default_repr(field_info, **fields_repr[field_name], **more_kwargs)
                else:
                    field_repr = fields_repr[field_name]
                    for key, val in more_kwargs.items():
                        setattr(field_repr, key, val)
            else:
                field_repr = get_default_repr(field_info, **more_kwargs)

            field_inputs[field_name] = field_repr.render(
                item=item,
                aio_id=aio_id,
                form_id=form_id,
                field=field_name,
                parent=path,
                field_info=field_info,
            )

        if not sections or not any([f for f in field_inputs if f in s.fields] for s in sections.sections if s.fields):
            children = [self.grid(list(field_inputs.values()))]
        else:
            fields_not_in_sections = set(field_inputs) - set(
                itertools.chain.from_iterable(s.fields for s in sections.sections)
            )

            if sections.render == "accordion":
                render_function = self.render_accordion_sections
            elif sections.render == "tabs":
                render_function = self.render_tabs_sections
            elif sections.render == "steps":
                render_function = self.render_steps_sections
            else:
                raise ValueError("Only 'accordion', 'tabs' and 'steps' are supported for `section_render_type`.")

            sections_render = render_function(
                aio_id=aio_id,
                form_id=form_id,
                path=path,
                field_inputs=field_inputs,
                sections=sections,
                **sections.render_kwargs,
            )

            if sections.remaining_fields_position == "none" or not fields_not_in_sections:
                children = sections_render
            elif sections.remaining_fields_position == "top":
                children = [
                    self.grid([v for k, v in field_inputs.items() if k in fields_not_in_sections], mb="sm")
                ] + sections_render
            else:
                children = sections_render + [
                    self.grid([v for k, v in field_inputs.items() if k in fields_not_in_sections], mb="sm")
                ]

        fields_repr_dicts = (
            {
                field_name: (
                    get_default_repr(subitem_cls.model_fields[field_name], **field_repr)
                    if isinstance(field_repr, dict)
                    else field_repr
                ).to_dict()
                for field_name, field_repr in fields_repr.items()
            }
            if fields_repr
            else None
        )
        if not path:
            children.append(dcc.Store(id=self.ids.main(aio_id, form_id)))
            children.append(dcc.Store(data=str(item.__class__), id=self.ids.model_store(aio_id, form_id)))

        if discriminator:
            children.append(
                dcc.Store(
                    data={
                        "sections": sections.model_dump(mode="json") if sections else None,
                        "fields_repr": fields_repr_dicts,
                    },
                    id=self.ids.form_specs_store(aio_id, form_id, path),
                )
            )

        super().__init__(children=children)

    @classmethod
    def grid(cls, children: Children, **kwargs):
        """Create the responsive grid for a field."""
        return dmc.SimpleGrid(children, cols={"base": 1, "sm": 4}, className="pydantic-form-grid", **kwargs)

    @classmethod
    def render_accordion_sections(  # noqa: PLR0913
        cls,
        *,
        aio_id: str,
        form_id: str,
        path: str,
        field_inputs: dict[str, Component],
        sections: Sections,
        **_kwargs,
    ):
        """Render the form sections as accordion."""
        return [
            dmc.Accordion(
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
                                cls.grid([field_inputs[field] for field in section.fields if field in field_inputs]),
                            ),
                        ],
                        value=section.name,
                    )
                    for section in sections.sections
                ],
                value=[section.name for section in sections.sections if section.default_open],
                styles={
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
                id=cls.ids.accordion(aio_id, form_id, path),
                multiple=True,
            )
        ]

    @classmethod
    def render_tabs_sections(  # noqa: PLR0913
        cls,
        *,
        aio_id: str,
        form_id: str,
        path: str,
        field_inputs: dict[str, Component],
        sections: Sections,
        **_kwargs,
    ):
        """Render the form sections as tabs."""
        value = sections.sections[0].name
        for section in sections.sections:
            if section.default_open:
                value = section.name
                break

        return [
            dmc.Tabs(
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
                            for section in sections.sections
                        ]
                    ),
                    *[
                        dmc.TabsPanel(
                            cls.grid([field_inputs[field] for field in section.fields if field in field_inputs]),
                            value=section.name,
                        )
                        for section in sections.sections
                    ],
                ],
                value=value,
                styles={
                    "panel": {"padding": "1rem 0.5rem 0"},
                },
                id=cls.ids.tabs(aio_id, form_id, path),
            )
        ]

    @classmethod
    def render_steps_sections(  # noqa: PLR0913
        cls,
        *,
        aio_id: str,
        form_id: str,
        path: str,
        field_inputs: dict[str, Component],
        sections: Sections,
        additional_steps: list = None,
        **kwargs,
    ):
        """Render the form sections as steps."""
        stepper_styles = deep_merge(
            {
                "root": {"display": "flex", "gap": "1.5rem", "padding": "0.75rem 0 2rem"},
                "content": {"flex": 1, "padding": 0},
                "steps": {"minWidth": 180},
                "step": {"cursor": "pointer"},
                "stepBody": {"padding-top": "0.6875rem"},
                "stepCompletedIcon": {"&>svg": {"width": 12}},
            },
            kwargs.get("styles", {}),
        )
        stepper = dmc.Stepper(
            id=cls.ids.steps(aio_id, form_id, path),
            active=0,
            orientation="vertical",
            size="sm",
            styles=stepper_styles,
            children=[
                dmc.StepperStep(
                    label=section.name,
                    icon=DashIconify(icon=section.icon) if section.icon else None,
                    children=cls.grid([field_inputs[field] for field in section.fields if field in field_inputs]),
                )
                for section in sections.sections
            ]
            + (additional_steps or []),
        )

        return [
            html.Div(
                [
                    stepper,
                    dmc.Group(
                        [
                            dmc.Button(
                                "Back",
                                id=cls.ids.steps_previous(aio_id, form_id, path),
                                disabled=True,
                                size="compact-md",
                                leftSection=DashIconify(icon="carbon:arrow-left", height=16),
                            ),
                            dmc.Button(
                                "Next",
                                id=cls.ids.steps_next(aio_id, form_id, path),
                                size="compact-md",
                                rightSection=DashIconify(icon="carbon:arrow-right", height=16),
                            ),
                        ],
                        style={
                            "position": "absolute",
                            "top": f"calc({70 * (len(sections.sections) + len(additional_steps or []))}px + 1rem)",
                        },
                    ),
                    dcc.Store(data=len(sections.sections), id=cls.ids.steps_nsteps(aio_id, form_id, path)),
                ],
                style={"position": "relative"},
            )
        ]


clientside_callback(
    ClientsideFunction(namespace="pydf", function_name="stepsPreviousNext"),
    Output(ModelForm.ids.steps(MATCH, MATCH, MATCH), "active"),
    Input(ModelForm.ids.steps_previous(MATCH, MATCH, MATCH), "n_clicks"),
    Input(ModelForm.ids.steps_next(MATCH, MATCH, MATCH), "n_clicks"),
    State(ModelForm.ids.steps(MATCH, MATCH, MATCH), "active"),
    State(ModelForm.ids.steps_nsteps(MATCH, MATCH, MATCH), "data"),
    prevent_inital_call=True,
)

clientside_callback(
    ClientsideFunction(namespace="pydf", function_name="stepsDisable"),
    Output(ModelForm.ids.steps_previous(MATCH, MATCH, MATCH), "disabled"),
    Output(ModelForm.ids.steps_next(MATCH, MATCH, MATCH), "disabled"),
    Input(ModelForm.ids.steps(MATCH, MATCH, MATCH), "active"),
    State(ModelForm.ids.steps_nsteps(MATCH, MATCH, MATCH), "data"),
)

clientside_callback(
    ClientsideFunction(namespace="pydf", function_name="stepsClickListener"),
    Output(ModelForm.ids.steps(MATCH, MATCH, MATCH), "id"),
    Input(ModelForm.ids.steps(MATCH, MATCH, MATCH), "id"),
)

clientside_callback(
    ClientsideFunction(namespace="pydf", function_name="getValues"),
    Output(ModelForm.ids.main(MATCH, MATCH), "data"),
    Input(common_ids.value_field(MATCH, MATCH, ALL, ALL, ALL), "value"),
    Input(common_ids.checked_field(MATCH, MATCH, ALL, ALL, ALL), "checked"),
)


@callback(
    Output(fields.Model.ids.form_wrapper(MATCH, MATCH, MATCH, MATCH), "children"),
    Input(common_ids.value_field(MATCH, MATCH, MATCH, MATCH, "discriminator"), "value"),
    State(ModelForm.ids.main(MATCH, MATCH), "data"),
    State(ModelForm.ids.model_store(MATCH, MATCH), "data"),
    State(ModelForm.ids.form_specs_store(MATCH, MATCH, MATCH), "data"),
    prevent_initial_call=True,
)
def update_discriminated(val, form_data: dict, model_name: str, form_specs: dict):
    """Update discriminated form."""
    path: str = get_fullpath(ctx.triggered_id["parent"], ctx.triggered_id["field"])
    parts = path.split(SEP)
    # Update the form data with the new value as it wouldn't have been updated yet
    pointer = form_data
    for i, part in enumerate(parts):
        if i == len(parts) - 1:
            pointer[part] = val
        pointer = pointer[int(part) if part.isdigit() else part]

    # Create an instance of the model sith the form data using model_construct_recursive
    # to build it out as much as possible without failing on validation
    model_cls = get_model_cls(model_name)
    item = model_construct_recursive(form_data, model_cls)

    # Retrieve fields-repr and sections from the stored data
    fields_repr: dict[str, BaseField] = {
        k: BaseField.from_dict(v) for k, v in (form_specs["fields_repr"] or {}).items()
    }
    sections = Sections(**form_specs["sections"]) if form_specs["sections"] else None

    return ModelForm(
        item=item,
        aio_id=ctx.triggered_id["aio_id"],
        form_id=ctx.triggered_id["form_id"],
        path=ctx.triggered_id["parent"],
        discriminator=ctx.triggered_id["field"],
        sections=sections,
        fields_repr=fields_repr,
    )

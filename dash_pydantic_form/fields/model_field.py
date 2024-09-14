from functools import partial
from typing import Literal

import dash_mantine_components as dmc
from dash import (
    MATCH,
    ClientsideFunction,
    Input,
    Output,
    clientside_callback,
    html,
)
from dash.development.base_component import Component
from dash_iconify import DashIconify
from pydantic import BaseModel, Field
from pydantic.fields import FieldInfo

from dash_pydantic_form import ids as common_ids
from dash_pydantic_form.fields.base_fields import BaseField
from dash_pydantic_form.form_section import Sections
from dash_pydantic_form.utils import get_fullpath


class ModelField(BaseField):
    """Model field, used for nested BaseModel.

    Optional attributes:
    * render_type (one of 'accordion', 'modal', default 'accordion')
    * fields_repr, mapping between field name and field representation
    * sections, list of FormSection for the NestedModel form
    """

    render_type: Literal["accordion", "modal"] = Field(
        default="accordion", description="How to render the model field, one of 'accordion', 'modal'."
    )
    fields_repr: dict[str, dict | BaseField] | None = Field(
        default=None,
        description="Fields representation, mapping between field name and field representation for the nested fields.",
    )
    sections: Sections | None = Field(default=None, description="Sub-form sections.")

    full_width = True

    def model_post_init(self, _context):
        """Model post init."""
        super().model_post_init(_context)
        if self.fields_repr is None:
            self.fields_repr = {}

    class ids(BaseField.ids):
        """Model field ids."""

        form_wrapper = partial(common_ids.field_dependent_id, "_pydf-model-form-wrapper")
        edit = partial(common_ids.field_dependent_id, "_pydf-model-field-edit")
        modal = partial(common_ids.field_dependent_id, "_pydf-model-field-modal")
        modal_save = partial(common_ids.field_dependent_id, "_pydf-model-field-modal-save")

    def modal_item(  # noqa: PLR0913
        self,
        item: BaseModel,
        aio_id: str,
        form_id: str,
        field: str,
        parent: str = "",
        field_info: FieldInfo | None = None,
    ) -> Component:
        """Model field modal render."""
        from dash_pydantic_form import ModelForm

        title = self.get_title(field_info, field_name=field)
        new_parent = get_fullpath(parent, field)
        return dmc.Paper(
            dmc.Group(
                [
                    dmc.Text(
                        title,
                        style={
                            "flex": 1,
                            "overflow": "hidden",
                            "textOverflow": "ellipsis",
                            "whiteSpace": "nowrap",
                        },
                    ),
                    dmc.Group(
                        [
                            dmc.ActionIcon(
                                DashIconify(icon="carbon:edit", height=16),
                                variant="light",
                                size="sm",
                                id=self.ids.edit(aio_id, form_id, field, parent=parent),
                            ),
                        ],
                        gap="0.25rem",
                    ),
                    dmc.Modal(
                        [
                            ModelForm(
                                item=item,
                                aio_id=aio_id,
                                form_id=form_id,
                                path=new_parent,
                                fields_repr=self.fields_repr,
                                sections=self.sections,
                                read_only=self.read_only,
                            ),
                            dmc.Group(
                                dmc.Button(
                                    "Save",
                                    leftSection=DashIconify(icon="carbon:save"),
                                    id=self.ids.modal_save(aio_id, form_id, field, parent=parent),
                                ),
                                justify="right",
                                mt="sm",
                            ),
                        ],
                        title=title,
                        id=self.ids.modal(aio_id, form_id, field, parent=parent),
                        style={"--modal-size": "min(calc(100vw - 4rem), 1150px)"},
                    ),
                ],
                gap="sm",
                align="top",
            ),
            withBorder=True,
            radius="sm",
            p="xs",
            className="pydf-model-list-modal-item",
        )

    def accordion_item(  # noqa: PLR0913
        self,
        item: BaseModel,
        aio_id: str,
        form_id: str,
        field: str,
        parent: str = "",
        field_info: FieldInfo | None = None,
    ) -> Component:
        """Model field accordion item render."""
        from dash_pydantic_form import ModelForm

        title = self.get_title(field_info, field_name=field)
        description = self.get_description(field_info)
        return dmc.Accordion(
            dmc.AccordionItem(
                value="item",
                children=[
                    dmc.AccordionControl(dmc.Text(title)),
                    dmc.AccordionPanel(
                        [
                            *([dmc.Text(description, size="xs", c="dimmed")] * bool(title) * bool(description)),
                            html.Div(
                                ModelForm(
                                    item=item,
                                    aio_id=aio_id,
                                    form_id=form_id,
                                    path=get_fullpath(parent, field),
                                    fields_repr=self.fields_repr,
                                    sections=self.sections,
                                    discriminator=field_info.discriminator,
                                    read_only=self.read_only,
                                ),
                                id=self.ids.form_wrapper(
                                    aio_id, form_id, field_info.discriminator or "", parent=get_fullpath(parent, field)
                                ),
                            ),
                        ],
                    ),
                ],
            ),
            value="item",
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
            style={"gridColumn": "span var(--col-4-4)"},
        )

    def _render(  # noqa: PLR0913
        self,
        *,
        item: BaseModel,
        aio_id: str,
        form_id: str,
        field: str,
        parent: str = "",
        field_info: FieldInfo | None = None,
    ) -> Component:
        """Create a form field of type checklist to interact with the model field."""
        if self.render_type == "accordion":
            input_ = self.accordion_item(item, aio_id, form_id, field, parent, field_info)
        elif self.render_type == "modal":
            input_ = self.modal_item(item, aio_id, form_id, field, parent, field_info)
        else:
            raise ValueError("Unknown render type.")
        return input_

    # Open a model modal when editing an item
    clientside_callback(
        ClientsideFunction(namespace="pydf", function_name="syncTrue"),
        Output(ids.modal(MATCH, MATCH, MATCH, MATCH, MATCH), "opened", allow_duplicate=True),
        Input(ids.edit(MATCH, MATCH, MATCH, MATCH, MATCH), "n_clicks"),
        prevent_initial_call=True,
    )

    # Close a model modal when saving an item
    clientside_callback(
        ClientsideFunction(namespace="pydf", function_name="syncFalse"),
        Output(ids.modal(MATCH, MATCH, MATCH, MATCH, MATCH), "opened", allow_duplicate=True),
        Input(ids.modal_save(MATCH, MATCH, MATCH, MATCH, MATCH), "n_clicks"),
        prevent_initial_call=True,
    )

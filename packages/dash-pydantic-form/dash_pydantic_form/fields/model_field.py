from functools import partial
from typing import Literal

import dash_mantine_components as dmc
from dash import (
    MATCH,
    ClientsideFunction,
    Input,
    Output,
    clientside_callback,
)
from dash.development.base_component import Component
from dash_iconify import DashIconify
from pydantic import BaseModel, Field, field_validator
from pydantic.fields import FieldInfo

from dash_pydantic_form import ids as common_ids
from dash_pydantic_form.fields.base_fields import BaseField
from dash_pydantic_form.form_layouts.form_layout import FormLayout
from dash_pydantic_form.i18n import _
from dash_pydantic_utils import get_fullpath


class ModelField(BaseField):
    """Model field, used for nested BaseModel.

    Optional attributes:
    * render_type (one of 'accordion', 'modal', default 'accordion')
    * fields_repr, mapping between field name and field representation
    * form_layout, FormLayout for the NestedModel form
    * form_cols, number of columns in the form
    * excluded_fields, list of field names to exclude from the form altogether
    * fields_order, list of field names in the order they should be rendered
    """

    render_type: Literal["accordion", "modal"] = Field(
        default="accordion", description="How to render the model field, one of 'accordion', 'modal'."
    )
    fields_repr: dict[str, dict | BaseField] | None = Field(
        default=None,
        description="Fields representation, mapping between field name and field representation for the nested fields.",
    )
    form_layout: FormLayout | None = Field(default=None, description="Sub-form layout.")
    form_cols: int = Field(default=4, description="Number of columns in the form.")
    excluded_fields: list[str] | None = Field(default=None, description="Fields excluded from the sub-form")
    fields_order: list[str] | None = Field(default=None, description="Order of fields in the sub-form")

    full_width = True

    @field_validator("form_layout", mode="before")
    @classmethod
    def validate_form_layout(cls, v):
        """Validate form layout."""
        if isinstance(v, FormLayout):
            return v
        if isinstance(v, dict):
            return FormLayout.load(**v)
        raise ValueError("form_layout must be a FormLayout or a dict that can be converted to a FormLayout")

    def model_post_init(self, _context):
        """Model post init."""
        super().model_post_init(_context)
        if self.fields_repr is None:
            self.fields_repr = {}
        if self.form_layout is None and self.model_extra and self.model_extra.get("sections") is not None:
            self.form_layout = self.model_extra["sections"]

    class ids(BaseField.ids):
        """Model field ids."""

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
                                form_layout=self.form_layout,
                                read_only=self.read_only,
                                form_cols=self.form_cols,
                                excluded_fields=self.excluded_fields,
                                fields_order=self.fields_order,
                            ),
                            dmc.Group(
                                dmc.Button(
                                    _("Save"),
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
                        styles={"content": {"containerType": "inline-size"}},
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
                            ModelForm(
                                item=item,
                                aio_id=aio_id,
                                form_id=form_id,
                                path=get_fullpath(parent, field),
                                fields_repr=self.fields_repr,
                                form_layout=self.form_layout,
                                discriminator=field_info.discriminator,
                                read_only=self.read_only,
                                form_cols=self.form_cols,
                                excluded_fields=self.excluded_fields,
                                fields_order=self.fields_order,
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
            style={"--pydf-field-cols": "var(--pydf-form-cols)"},
            className="pydantic-form-field",
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
        try:
            renderer = getattr(self, f"{self.render_type}_item")
        except AttributeError as exc:
            raise ValueError(f"Unknown render type: {self.render_type}") from exc
        return renderer(item, aio_id, form_id, field, parent, field_info)

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

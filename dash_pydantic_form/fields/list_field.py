import uuid
from collections.abc import Callable
from functools import partial
from typing import Literal

import dash_mantine_components as dmc
from dash import (
    ALL,
    MATCH,
    ClientsideFunction,
    Input,
    Output,
    State,
    clientside_callback,
    dcc,
    html,
)
from dash.development.base_component import Component
from dash_iconify import DashIconify
from plotly.io.json import to_json_plotly
from pydantic import BaseModel, Field
from pydantic.fields import FieldInfo

from dash_pydantic_form import ids as common_ids
from dash_pydantic_form.fields.base_fields import BaseField
from dash_pydantic_form.form_section import Sections
from dash_pydantic_form.i18n import _
from dash_pydantic_form.utils import (
    Type,
    get_fullpath,
    get_subitem_cls,
)


class ListField(BaseField):
    """List field, used for list of nested models or scalars.

    Optional attributes:
    * render_type (one of 'accordion', 'modal', 'list', default 'accordion')
        new render types can be defined by extending this class and overriding
        the following methods: _contents_renderer and render_type_item_mapper
    * fields_repr, mapping between field name and field representation
    * sections, list of FormSection for the NestedModel form
    * items_deletable, whether the items can be deleted (bool, default True)
    * items_creatable, whether new items can be created (bool, default True)
    """

    render_type: Literal["accordion", "modal", "list", "scalar"] = Field(
        default="accordion",
        description=(
            "How to render the list of items. One  of 'accordion', 'modal', 'list' for a list of models. "
            "Should be set to 'scalar' for a list of scalars."
        ),
    )
    fields_repr: dict[str, dict | BaseField] | None = Field(
        default=None,
        description="Fields representation, mapping between field name and field representation for the nested fields.",
    )
    sections: Sections | None = Field(default=None, description="Sub-form sections.")
    items_deletable: bool = Field(default=True, description="Whether the items can be deleted.")
    items_creatable: bool = Field(default=True, description="Whether new items can be created.")

    full_width = True

    def model_post_init(self, _context):
        """Model post init."""
        super().model_post_init(_context)
        if self.fields_repr is None:
            self.fields_repr = {}
        if self.read_only:
            self.items_deletable = False
            self.items_creatable = False

    class ids(BaseField.ids):
        """Model list field ids."""

        wrapper = partial(common_ids.field_dependent_id, "_pydf-list-field-wrapper")
        delete = partial(common_ids.field_dependent_id, "_pydf-list-field-delete")
        edit = partial(common_ids.field_dependent_id, "_pydf-list-field-edit")
        modal = partial(common_ids.field_dependent_id, "_pydf-list-field-modal")
        accordion_parent_text = partial(common_ids.field_dependent_id, "_pydf-list-field-accordion-text")
        modal_parent_text = partial(common_ids.field_dependent_id, "_pydf-list-field-modal-text")
        modal_save = partial(common_ids.field_dependent_id, "_pydf-list-field-modal-save")
        add = partial(common_ids.field_dependent_id, "_pydf-list-field-add")
        template_store = partial(common_ids.field_dependent_id, "_pydf-list-field-template-store")

    @classmethod
    def accordion_item(  # noqa: PLR0913
        cls,
        *,
        item: BaseModel,
        aio_id: str,
        form_id: str,
        field: str,
        parent: str,
        index: int,
        value: BaseModel,
        fields_repr: dict[str, dict | BaseField] | None = None,
        sections: Sections | None = None,
        items_deletable: bool = True,
        read_only: bool | None = None,
        **_kwargs,
    ):
        """Create an accordion item for the model list field."""
        from dash_pydantic_form import ModelForm

        new_parent = get_fullpath(parent, field, index)
        return dmc.AccordionItem(
            # Give a random unique value to the item, prepended by uuid: so that the callback
            # to add new items works
            value="uuid:" + uuid.uuid4().hex,
            style={"position": "relative"},
            className="pydf-model-list-accordion-item",
            children=[
                dmc.AccordionControl(
                    [dmc.Text(str(value), id=cls.ids.accordion_parent_text(aio_id, form_id, "", parent=new_parent))]
                    + items_deletable
                    * [
                        dmc.ActionIcon(
                            DashIconify(icon="carbon:trash-can", height=16),
                            color="red",
                            style={
                                "position": "absolute",
                                "top": "50%",
                                "transform": "translateY(-50%)",
                                "right": "2.5rem",
                            },
                            variant="light",
                            size="sm",
                            id=cls.ids.delete(aio_id, form_id, field, parent=parent, meta=index),
                            className="pydf-model-list-accordion-item-delete",
                        ),
                    ],
                    pos="relative",
                ),
                dmc.AccordionPanel(
                    ModelForm(
                        item=item,
                        aio_id=aio_id,
                        form_id=form_id,
                        path=new_parent,
                        fields_repr=fields_repr,
                        sections=sections,
                        read_only=read_only,
                    ),
                ),
            ],
        )

    @classmethod
    def list_item(  # noqa: PLR0913
        cls,
        *,
        item: BaseModel,
        aio_id: str,
        form_id: str,
        field: str,
        parent: str,
        index: int,
        fields_repr: dict[str, dict | BaseField] | None = None,
        sections: Sections | None = None,
        items_deletable: bool = True,
        read_only: bool | None = None,
        **_kwargs,
    ):
        """Create an item with bare forms for the model list field."""
        from dash_pydantic_form import ModelForm

        new_parent = get_fullpath(parent, field, index)
        return dmc.Group(
            [
                ModelForm(
                    item=item,
                    aio_id=aio_id,
                    form_id=form_id,
                    path=new_parent,
                    fields_repr=fields_repr,
                    sections=sections,
                    container_kwargs={"style": {"flex": 1}},
                    read_only=read_only,
                ),
            ]
            + items_deletable
            * [
                dmc.ActionIcon(
                    DashIconify(icon="carbon:trash-can", height=16),
                    color="red",
                    variant="light",
                    size="sm",
                    id=cls.ids.delete(aio_id, form_id, field, parent=parent, meta=index),
                ),
            ],
            gap="sm",
            align="top",
            className="pydf-model-list-list-item",
        )

    @classmethod
    def modal_item(  # noqa: PLR0913
        cls,
        *,
        item: BaseModel,
        aio_id: str,
        form_id: str,
        field: str,
        parent: str,
        index: int,
        value: BaseModel,
        opened: bool = False,
        fields_repr: dict[str, dict | BaseField] | None = None,
        sections: Sections | None = None,
        items_deletable: bool = True,
        read_only: bool | None = None,
        **_kwargs,
    ):
        """Create an item with bare forms for the model list field."""
        from dash_pydantic_form import ModelForm

        new_parent = get_fullpath(parent, field, index)
        return dmc.Paper(
            dmc.Group(
                [
                    dmc.Text(
                        str(value),
                        style={
                            "flex": 1,
                            "overflow": "hidden",
                            "textOverflow": "ellipsis",
                            "whiteSpace": "nowrap",
                        },
                        id=cls.ids.modal_parent_text(aio_id, form_id, "", parent=new_parent),
                    ),
                    dmc.Group(
                        [
                            dmc.ActionIcon(
                                DashIconify(icon="carbon:view" if read_only else "carbon:edit", height=16),
                                variant="light",
                                size="sm",
                                id=cls.ids.edit(aio_id, form_id, "", parent=new_parent),
                                className="pydf-model-list-modal-item-btn",
                            ),
                        ]
                        + items_deletable
                        * [
                            dmc.ActionIcon(
                                DashIconify(icon="carbon:trash-can", height=16),
                                color="red",
                                variant="light",
                                size="sm",
                                id=cls.ids.delete(aio_id, form_id, field, parent=parent, meta=index),
                                className="pydf-model-list-modal-item-btn",
                            ),
                        ],
                        gap="0.5rem",
                    ),
                    dmc.Modal(
                        [
                            ModelForm(
                                item=item,
                                aio_id=aio_id,
                                form_id=form_id,
                                path=new_parent,
                                fields_repr=fields_repr,
                                sections=sections,
                                read_only=read_only,
                            ),
                            dmc.Group(
                                dmc.Button(
                                    _("Save"),
                                    leftSection=DashIconify(icon="carbon:save"),
                                    id=cls.ids.modal_save(aio_id, form_id, "", parent=new_parent),
                                    size="compact-sm",
                                ),
                                justify="right",
                                mt="sm",
                            ),
                        ],
                        title=str(value),
                        id=cls.ids.modal(aio_id, form_id, "", parent=new_parent),
                        style={"--modal-size": "min(calc(100vw - 4rem), 1150px)"},
                        opened=opened,
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

    @classmethod
    def scalar_item(  # noqa: PLR0913
        cls,
        *,
        item: BaseModel,
        aio_id: str,
        form_id: str,
        field: str,
        parent: str,
        index: int,
        items_deletable: bool = True,
        read_only: bool | None = None,
        input_kwargs: dict,
        **kwargs,
    ):
        """Create an item for a scalar list."""
        from dash_pydantic_form.fields import get_default_repr

        scalar_cls = get_subitem_cls(item.__class__, get_fullpath(parent, field, index), item=item)
        field_repr = get_default_repr(
            None, annotation=scalar_cls, read_only=read_only, title="", input_kwargs=input_kwargs, **kwargs
        )
        child = field_repr.render(
            item=item,
            aio_id=aio_id,
            form_id=form_id,
            field=index,
            parent=get_fullpath(parent, field),
            field_info=FieldInfo.from_annotation(scalar_cls),
        )
        if not child.style:
            child.style = {}
        child.style |= {"flex": "1 1 60%"}
        return dmc.Group(
            [child]
            + items_deletable
            * [
                dmc.ActionIcon(
                    DashIconify(icon="carbon:close", height=16),
                    color="red",
                    variant="light",
                    size="sm",
                    mt="0.375rem",
                    id=cls.ids.delete(aio_id, form_id, field, parent=parent, meta=index),
                    className="pydf-model-list-scalar-item-delete",
                ),
            ],
            gap=0,
            align="top",
            className="pydf-model-list-scalar-item",
            wrap="none",
        )

    def _contents_renderer(self, renderer_type: str) -> Callable:
        """Create a renderer for the model list field."""
        raise NotImplementedError(
            "Only the default renderers (accordion, list, modals) are implemented. "
            "Override this method to create custom renderers."
        )

    @classmethod
    def render_type_item_mapper(cls, render_type: str) -> dict[str, Callable]:
        """Mapping between render type and renderer function."""
        return getattr(cls, f"{render_type}_item")

    def _render(  # noqa: PLR0913
        self,
        *,
        item: BaseModel,
        aio_id: str,
        form_id: str,
        field: str,
        parent: str = "",
        field_info: FieldInfo,
    ) -> Component:
        """Create a form field of type checklist to interact with the model field."""
        type_ = Type.classify(field_info.annotation, field_info.discriminator)
        if type_ == Type.MODEL_LIST and self.render_type == "scalar":
            raise ValueError("Cannot render model list as scalar")
        if type_ != Type.MODEL_LIST and self.render_type != "scalar":
            raise ValueError("Cannot render non model list as non scalar")

        value: list = self.get_value(item, field, parent) or []

        class_name = "pydf-model-list-wrapper" + (" required" if self.is_required(field_info) else "")
        if self.render_type == "accordion":
            contents = dmc.Accordion(
                [
                    self.accordion_item(
                        item=item,
                        aio_id=aio_id,
                        form_id=form_id,
                        field=field,
                        parent=parent,
                        index=i,
                        value=val,
                        fields_repr=self.fields_repr,
                        sections=self.sections,
                        items_deletable=self.items_deletable,
                        read_only=self.read_only,
                    )
                    for i, val in enumerate(value)
                ],
                id=self.ids.wrapper(aio_id, form_id, field, parent=parent),
                value=None,
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
                className=class_name,
            )
        elif self.render_type == "list":
            contents = dmc.Stack(
                [
                    self.list_item(
                        item=item,
                        aio_id=aio_id,
                        form_id=form_id,
                        field=field,
                        parent=parent,
                        index=i,
                        fields_repr=self.fields_repr,
                        sections=self.sections,
                        items_deletable=self.items_deletable,
                        read_only=self.read_only,
                    )
                    for i, _ in enumerate(value)
                ],
                id=self.ids.wrapper(aio_id, form_id, field, parent=parent),
                className=class_name,
            )
        elif self.render_type == "scalar":
            contents = html.Div(
                [
                    self.scalar_item(
                        item=item,
                        aio_id=aio_id,
                        form_id=form_id,
                        field=field,
                        parent=parent,
                        index=i,
                        fields_repr=self.fields_repr,
                        sections=self.sections,
                        items_deletable=self.items_deletable,
                        read_only=self.read_only,
                        input_kwargs=self.input_kwargs,
                    )
                    for i, _ in enumerate(value)
                ],
                id=self.ids.wrapper(aio_id, form_id, field, parent=parent),
                className=class_name,
                style={
                    "display": "grid",
                    "gridTemplateColumns": "repeat(auto-fit, minmax(min(100%, 280px), 1fr))",
                    "gap": "0.5rem",
                    "overflow": "hidden",
                    "alignItems": "top",
                },
            )
        elif self.render_type == "modal":
            contents = html.Div(
                [
                    self.modal_item(
                        item=item,
                        aio_id=aio_id,
                        form_id=form_id,
                        field=field,
                        parent=parent,
                        index=i,
                        value=val,
                        fields_repr=self.fields_repr,
                        sections=self.sections,
                        items_deletable=self.items_deletable,
                        read_only=self.read_only,
                    )
                    for i, val in enumerate(value)
                ],
                id=self.ids.wrapper(aio_id, form_id, field, parent=parent),
                style={
                    "display": "grid",
                    "gridTemplateColumns": "repeat(auto-fit, minmax(min(100%, 280px), 1fr))",
                    "gap": "0.5rem",
                    "overflow": "hidden",
                },
                className=class_name,
            )
        else:
            contents = self._contents_renderer(self.render_type)

        # Create a template item to be used clientside when adding new items
        template = self.render_type_item_mapper(self.render_type)(
            item=item.__class__.model_construct(),
            aio_id=aio_id,
            form_id=form_id,
            field=field,
            parent=parent,
            index="{{" + get_fullpath(parent, field).replace(":", "|") + "}}",
            value="-",
            opened=True,
            fields_repr=self.fields_repr,
            sections=self.sections,
            items_deletable=self.items_deletable,
            read_only=self.read_only,
            input_kwargs=self.input_kwargs,
        )
        title = self.get_title(field_info, field_name=field)
        description = self.get_description(field_info)

        return dmc.Stack(
            bool(title)
            * [
                dmc.Stack(
                    bool(title)
                    * [
                        dmc.Text(
                            [title]
                            + [
                                html.Span(
                                    " *", style={"color": "var(--input-asterisk-color, var(--mantine-color-error))"}
                                ),
                            ]
                            * self.is_required(field_info),
                            size="sm",
                            mt=3,
                            fw=500,
                            lh=1.55,
                        )
                    ]
                    + (bool(title) and bool(description)) * [dmc.Text(description, size="xs", c="dimmed", lh=1.2)],
                    gap=0,
                )
            ]
            + [
                contents,
                dcc.Store(
                    data=to_json_plotly(template), id=self.ids.template_store(aio_id, form_id, field, parent=parent)
                ),
            ]
            + self.items_creatable
            * [
                html.Div(
                    [
                        dmc.Button(
                            _("Add"),
                            leftSection=DashIconify(icon="carbon:add", height=16),
                            size="compact-sm",
                            id=self.ids.add(aio_id, form_id, field, parent=parent),
                        ),
                    ],
                ),
            ],
            style={"gridColumn": "span var(--col-4-4)"},
            gap="0.5rem",
            mt="sm",
        )

    clientside_callback(
        ClientsideFunction(namespace="pydf", function_name="addToList"),
        Output(ids.wrapper(MATCH, MATCH, MATCH, MATCH), "children", allow_duplicate=True),
        Input(ids.add(MATCH, MATCH, MATCH, MATCH), "n_clicks"),
        State(ids.wrapper(MATCH, MATCH, MATCH, MATCH), "children"),
        State(ids.template_store(MATCH, MATCH, MATCH, MATCH), "data"),
        prevent_initial_call=True,
    )

    clientside_callback(
        ClientsideFunction(namespace="pydf", function_name="deleteFromList"),
        Output(ids.wrapper(MATCH, MATCH, MATCH, MATCH), "children", allow_duplicate=True),
        Input(ids.delete(MATCH, MATCH, MATCH, MATCH, ALL), "n_clicks"),
        State(ids.wrapper(MATCH, MATCH, MATCH, MATCH), "children"),
        prevent_initial_call=True,
    )

    # Open a model list modal when editing an item
    clientside_callback(
        ClientsideFunction(namespace="pydf", function_name="syncTrue"),
        Output(ids.modal(MATCH, MATCH, MATCH, MATCH, MATCH), "opened", allow_duplicate=True),
        Input(ids.edit(MATCH, MATCH, MATCH, MATCH, MATCH), "n_clicks"),
        prevent_initial_call=True,
    )

    # Close a model list modal when saving an item
    clientside_callback(
        ClientsideFunction(namespace="pydf", function_name="syncFalse"),
        Output(ids.modal(MATCH, MATCH, MATCH, MATCH, MATCH), "opened", allow_duplicate=True),
        Input(ids.modal_save(MATCH, MATCH, MATCH, MATCH, MATCH), "n_clicks"),
        prevent_initial_call=True,
    )

    # Update the modal title and list item to match the name field of the item (if it exists)
    clientside_callback(
        ClientsideFunction(namespace="pydf", function_name="updateModalTitle"),
        Output(ids.modal(MATCH, MATCH, "", MATCH, MATCH), "title"),
        Input(common_ids.value_field(MATCH, MATCH, "name", MATCH, MATCH), "value"),
        State(ids.modal(MATCH, MATCH, "", MATCH, MATCH), "id"),
    )

    # Update the accordion title to match the name field of the item (if it exists)
    clientside_callback(
        ClientsideFunction(namespace="pydf", function_name="updateAccordionTitle"),
        Output(ids.accordion_parent_text(MATCH, MATCH, "", MATCH, MATCH), "children"),
        Input(common_ids.value_field(MATCH, MATCH, "name", MATCH, MATCH), "value"),
    )

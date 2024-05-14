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
    Patch,
    State,
    callback,
    clientside_callback,
    ctx,
    dcc,
    html,
    no_update,
)
from dash.development.base_component import Component
from dash_iconify import DashIconify
from pydantic import BaseModel, Field
from pydantic.fields import FieldInfo

from dash_pydantic_form import ids as common_ids
from dash_pydantic_form.fields.base_fields import BaseField
from dash_pydantic_form.form_section import Sections
from dash_pydantic_form.utils import (
    get_fullpath,
    get_model_cls,
    get_subitem_cls,
)


class ModelListField(BaseField):
    """Model list field, used for list of nested BaseModel.

    Optional attributes:
    * render_type (one of 'accordion', 'modal', 'list', default 'accordion')
        new render types can be defined by extending this class and overriding
        the following methods: _contents_renderer and render_type_item_mapper
    * fields_repr, mapping between field name and field representation
    * sections, list of FormSection for the NestedModel form
    * items_deletable, whether the items can be deleted (bool, default True)
    * items_creatable, whether new items can be created (bool, default True)
    """

    render_type: Literal["accordion", "modal", "list"] = Field(
        default="accordion", description="How to render the list of items, one  of 'accordion', 'modal', 'list'."
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

    class ids(BaseField.ids):
        """Model list field ids."""

        wrapper = partial(common_ids.field_dependent_id, "_pydf-model-list-field-wrapper")
        delete = partial(common_ids.field_dependent_id, "_pydf-model-list-field-delete")
        edit = partial(common_ids.field_dependent_id, "_pydf-model-list-field-edit")
        modal = partial(common_ids.field_dependent_id, "_pydf-model-list-field-modal")
        accordion_parent_text = partial(common_ids.field_dependent_id, "_pydf-model-list-field-accordion-text")
        modal_parent_text = partial(common_ids.field_dependent_id, "_pydf-model-list-field-modal-text")
        modal_save = partial(common_ids.field_dependent_id, "_pydf-model-list-field-modal-save")
        add = partial(common_ids.field_dependent_id, "_pydf-model-list-field-add")
        model_store = partial(common_ids.field_dependent_id, "_pydf-model-list-field-model-store")

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
        **_kwargs,
    ):
        """Create an accordion item for the model list field."""
        from dash_pydantic_form import ModelForm

        new_parent = get_fullpath(parent, field, index)
        return dmc.AccordionItem(
            value=f"{index}",
            style={"position": "relative"},
            className="pydf-model-list-accordion-item",
            children=[
                dmc.AccordionControl(
                    dmc.Text(str(value), id=cls.ids.accordion_parent_text(aio_id, form_id, "", parent=new_parent))
                ),
                dmc.AccordionPanel(
                    ModelForm(
                        item=item,
                        aio_id=aio_id,
                        form_id=form_id,
                        path=new_parent,
                        fields_repr=fields_repr,
                        sections=sections,
                    ),
                ),
            ]
            + items_deletable
            * [
                dmc.ActionIcon(
                    DashIconify(icon="carbon:trash-can", height=16),
                    color="red",
                    style={"position": "absolute", "top": "0.375rem", "right": "2.5rem"},
                    variant="light",
                    size="sm",
                    id=cls.ids.delete(aio_id, form_id, field, parent=parent, meta=index),
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
                                DashIconify(icon="carbon:edit", height=16),
                                variant="light",
                                size="sm",
                                id=cls.ids.edit(aio_id, form_id, "", parent=new_parent),
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
                        gap="0.25rem",
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
                            ),
                            dmc.Group(
                                dmc.Button(
                                    "Save",
                                    leftSection=DashIconify(icon="carbon:save"),
                                    id=cls.ids.modal_save(aio_id, form_id, "", parent=new_parent),
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
            radius="md",
            p="xs",
            className="pydf-model-list-modal-item",
        )

    def _contents_renderer(self, renderer_type: str) -> Callable:
        """Create a renderer for the model list field."""
        raise NotImplementedError(
            "Only the default renderers (accordion, list, modals) are implemented. "
            "Override this method to create custom renderers."
        )

    @classmethod
    def render_type_item_mapper(cls) -> dict[str, Callable]:
        """Mapping between render type and renderer function."""
        return {"accordion": cls.accordion_item, "list": cls.list_item, "modal": cls.modal_item}

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
        from dash_pydantic_form.fields import get_default_repr

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
                    )
                    for i, _ in enumerate(value)
                ],
                id=self.ids.wrapper(aio_id, form_id, field, parent=parent),
                className=class_name,
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
                    )
                    for i, val in enumerate(value)
                ],
                id=self.ids.wrapper(aio_id, form_id, field, parent=parent),
                style={
                    "display": "grid",
                    "gridTemplateColumns": "repeat(auto-fit, minmax(min(100%, 300px), 1fr))",
                    "gap": "0.5rem",
                    "overflow": "hidden",
                },
                className=class_name,
            )
        else:
            contents = self._contents_renderer(self.render_type)

        title = self.get_title(field_info, field_name=field)
        description = self.get_description(field_info)

        subitem_cls = get_subitem_cls(item, get_fullpath(parent, field, "0"))
        fields_repr_dicts = (
            {
                field_name: (
                    get_default_repr(subitem_cls.model_fields[field_name], **field_repr)
                    if isinstance(field_repr, dict)
                    else field_repr
                ).to_dict()
                for field_name, field_repr in self.fields_repr.items()
            }
            if self.fields_repr
            else None
        )
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
                            mb=5,
                            fw=500,
                            lh=1.55,
                        )
                    ]
                    + (bool(title) and bool(description))
                    * [dmc.Text(description, size="xs", c="dimmed", mt=-5, mb=5, lh=1.2)],
                    gap=0,
                )
            ]
            + [
                contents,
                dcc.Store(
                    data={
                        "model": str(item.__class__),
                        "i_list": list(range(1, len(value) + 1)),
                        "sections": self.sections.model_dump(mode="json") if self.sections else None,
                        "fields_repr": fields_repr_dicts,
                        "items_deletable": self.items_deletable,
                        "render_type": self.render_type,
                    },
                    id=self.ids.model_store(aio_id, form_id, field, parent=parent),
                ),
            ]
            + self.items_creatable
            * [
                html.Div(
                    [
                        dmc.Button(
                            "Add",
                            leftSection=DashIconify(icon="carbon:add", height=16),
                            size="compact-md",
                            id=self.ids.add(aio_id, form_id, field, parent=parent),
                        ),
                    ],
                ),
            ],
            style={"gridColumn": "span var(--col-4-4)"},
            gap="sm",
            mt="sm",
        )

    @callback(
        Output(ids.wrapper(MATCH, MATCH, MATCH, MATCH), "children", allow_duplicate=True),
        Output(ids.model_store(MATCH, MATCH, MATCH, MATCH), "data", allow_duplicate=True),
        Input(ids.add(MATCH, MATCH, MATCH, MATCH), "n_clicks"),
        State(ids.model_store(MATCH, MATCH, MATCH, MATCH), "data"),
        prevent_initial_call=True,
    )
    def add_item(n_clicks: int, model_data: tuple[str, int]):
        """Add a new model to the list."""
        if not n_clicks:
            return no_update, no_update

        aio_id = ctx.triggered_id["aio_id"]
        field = ctx.triggered_id["field"]
        form_id = ctx.triggered_id["form_id"]
        parent = ctx.triggered_id["parent"]

        model_name: str = model_data["model"]
        i_list: list[int] = model_data["i_list"]
        fields_repr: dict[str, BaseField] = {
            k: BaseField.from_dict(v) for k, v in (model_data["fields_repr"] or {}).items()
        }
        sections = Sections(**model_data["sections"]) if model_data["sections"] else None
        items_deletable = model_data["items_deletable"]
        render_type = model_data["render_type"]

        i = max(i_list) if i_list else 0
        i_list.append(i + 1)
        model_data["i_list"] = i_list
        item = get_model_cls(model_name).model_construct()

        new_item = ModelListField.render_type_item_mapper()[render_type](
            item=item,
            aio_id=aio_id,
            form_id=form_id,
            field=field,
            parent=parent,
            index=i,
            value=f"# {i + 1}",
            opened=True,
            fields_repr=fields_repr,
            sections=sections,
            items_deletable=items_deletable,
        )
        if i == 0:
            update = [new_item]
        else:
            update = Patch()
            update.append(new_item)
        return update, model_data

    @callback(
        Output(ids.wrapper(MATCH, MATCH, MATCH, MATCH), "children", allow_duplicate=True),
        Output(ids.model_store(MATCH, MATCH, MATCH, MATCH), "data", allow_duplicate=True),
        Input(ids.delete(MATCH, MATCH, MATCH, MATCH, ALL), "n_clicks"),
        State(ids.model_store(MATCH, MATCH, MATCH, MATCH), "data"),
        prevent_initial_call=True,
    )
    def delete_item(n_clicks: int, model_data: tuple[str, int]):
        """Delete a model from the list."""
        if not any(n_clicks):
            return no_update, no_update

        i_list = model_data["i_list"]
        i = ctx.triggered_id["meta"]
        update_items = Patch()
        del update_items[i_list.index(i + 1)]

        update_index = Patch()
        update_index["i_list"].remove(i + 1)

        return update_items, update_index

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
        Output(ids.modal_parent_text(MATCH, MATCH, "", MATCH, MATCH), "children"),
        Output(ids.modal(MATCH, MATCH, "", MATCH, MATCH), "title"),
        Input(common_ids.value_field(MATCH, MATCH, "name", MATCH, MATCH), "value"),
    )

    # Update the accordion title to match the name field of the item (if it exists)
    clientside_callback(
        ClientsideFunction(namespace="pydf", function_name="updateAccordionTitle"),
        Output(ids.accordion_parent_text(MATCH, MATCH, "", MATCH, MATCH), "children"),
        Input(common_ids.value_field(MATCH, MATCH, "name", MATCH, MATCH), "value"),
    )

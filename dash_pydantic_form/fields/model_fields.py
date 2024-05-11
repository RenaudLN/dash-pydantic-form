# pylint: disable = no-self-argument
from functools import partial
from typing import Callable, Literal, Optional, Union

import dash_mantine_components as dmc
from dash import ALL, MATCH, Input, Output, Patch, State, callback, clientside_callback, ctx, dcc, html, no_update
from dash.development.base_component import Component
from dash_iconify import DashIconify
from pydantic import BaseModel
from pydantic.fields import FieldInfo
from typing_extensions import Unpack

from dash_pydantic_form import ids as common_ids
from dash_pydantic_form.fields.base_fields import BaseField, VisibilityFilter
from dash_pydantic_form.form_section import Sections
from dash_pydantic_form.utils import get_fullpath, get_model_value, get_non_null_annotation, get_subitem_cls, get_model_cls


class ModelField(BaseField):
    """Model field, used for nested BaseModel.

    Optional attributes:
    * form_sections, list of FormSection for the NestedModel form

    e.g.
    ```python
    from pydantic import BaseModel
    from firestore_aio import Model
    from firestore_aio.dash import fields

    class Metadata(BaseModel):
        param1: str
        param2: str

    class Person(Model):
        name: str
        metadata: Metadata = fields.Model(title="Metadata")
    ```
    """

    render_type: Literal["accordion", "modal"] = "accordion"
    fields_repr: dict[str, BaseField] | None = None
    sections: Sections = None

    full_width = True

    def model_post_init(self, _context):
        super().model_post_init(_context)
        if self.fields_repr is None:
            self.fields_repr = {}

    class ids(BaseField.ids):  # pylint: disable = invalid-name
        """Model field ids."""

        form_wrapper = partial(common_ids.field_dependent_id, "_pydf-model-form-wrapper")
        edit = partial(common_ids.field_dependent_id, "_pydf-model-field-edit")
        modal = partial(common_ids.field_dependent_id, "_pydf-model-field-modal")
        modal_save = partial(common_ids.field_dependent_id, "_pydf-model-field-modal-save")

    def modal_item(
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
            className="firestore-model-list-modal-item",
        )

    def accordion_item(
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
                                sections=self.sections,
                            ),
                        ],
                        id=self.ids.form_wrapper(aio_id, form_id, field, parent=parent),
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

    def _render(
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
        """nClicks => !!nClicks""",
        Output(ids.modal(MATCH, MATCH, MATCH, MATCH, MATCH), "opened", allow_duplicate=True),
        Input(ids.edit(MATCH, MATCH, MATCH, MATCH, MATCH), "n_clicks"),
        prevent_initial_call=True,
    )

    # Close a model modal when saving an item
    clientside_callback(
        """nClicks => !nClicks""",
        Output(ids.modal(MATCH, MATCH, MATCH, MATCH, MATCH), "opened", allow_duplicate=True),
        Input(ids.modal_save(MATCH, MATCH, MATCH, MATCH, MATCH), "n_clicks"),
        prevent_initial_call=True,
    )


class ModelListField(BaseField):
    """Model list field, used for list of nested BaseModel.

    Optional attributes:
    * render_type (one of 'accordion', 'modal', 'list', default 'accordion')
        new render types can be defined by extending this class and overriding
        the following methods: _contents_renderer and render_type_item_mapper
    * form_sections, list of FormSection for the NestedModel form
    * items_deletable, whether the items can be deleted (bool, default True)
    * items_creatable, whether new items can be created (bool, default True)

    e.g.
    ```python
    from pydantic import BaseModel
    from firestore_aio import Model
    from firestore_aio.dash import fields

    class Pet(BaseModel):
        name: str
        species: str

    class Person(Model):
        name: str
        pets: list[Pet] = fields.ModelList(title="Pets")
    ```
    """
    render_type: Literal["accordion", "modal", "list"] = "accordion"
    fields_repr: dict[str, BaseField] | None = None
    sections: Sections | None = None
    items_deletable: bool = True
    items_creatable: bool = True

    full_width = True

    def model_post_init(self, _context):
        super().model_post_init(_context)
        if self.fields_repr is None:
            self.fields_repr = {}

    class ids(BaseField.ids):  # pylint: disable = invalid-name
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
    def accordion_item(  # pylint: disable=too-many-arguments
        cls,
        *,
        item: BaseModel,
        aio_id: str,
        form_id: str,
        field: str,
        parent: str,
        index: int,
        value: BaseModel,
        fields_repr: dict[str, BaseField] | None = None,
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
            className="firestore-model-list-accordion-item",
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
    def list_item(  # pylint: disable=too-many-arguments
        cls,
        *,
        item: BaseModel,
        aio_id: str,
        form_id: str,
        field: str,
        parent: str,
        index: int,
        fields_repr: dict[str, BaseField] | None = None,
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
            className="firestore-model-list-list-item",
        )

    @classmethod
    def modal_item(  # pylint: disable=too-many-arguments
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
        fields_repr: dict[str, BaseField] | None = None,
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
            className="firestore-model-list-modal-item",
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

    def _render(
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
        return dmc.Stack(
            bool(title)
            * [
                dmc.Stack(
                    bool(title) * [
                        dmc.Text(
                            [title]
                            + [
                                html.Span(" *", style={"color": "var(--input-asterisk-color, var(--mantine-color-error))"}),
                            ] * self.is_required(field_info),
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
                        "fields_repr": {
                            k: v.to_dict() for k, v in self.fields_repr.items()
                        } if self.fields_repr else None,
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
        """nClicks => !!nClicks""",
        Output(ids.modal(MATCH, MATCH, MATCH, MATCH, MATCH), "opened", allow_duplicate=True),
        Input(ids.edit(MATCH, MATCH, MATCH, MATCH, MATCH), "n_clicks"),
        prevent_initial_call=True,
    )

    # Close a model list modal when saving an item
    clientside_callback(
        """nClicks => !nClicks""",
        Output(ids.modal(MATCH, MATCH, MATCH, MATCH, MATCH), "opened", allow_duplicate=True),
        Input(ids.modal_save(MATCH, MATCH, MATCH, MATCH, MATCH), "n_clicks"),
        prevent_initial_call=True,
    )

    # Update the modal title and list item to match the name field of the item (if it exists)
    clientside_callback(
        """val => val != null ? [String(val), String(val)] : [dash_clientside.no_update, dash_clientside.no_update]""",
        Output(ids.modal_parent_text(MATCH, MATCH, "", MATCH, MATCH), "children"),
        Output(ids.modal(MATCH, MATCH, "", MATCH, MATCH), "title"),
        Input(common_ids.value_field(MATCH, MATCH, "name", MATCH, MATCH), "value"),
    )

    # Update the accordion title to match the name field of the item (if it exists)
    clientside_callback(
        """val => val != null ? String(val) : dash_clientside.no_update""",
        Output(ids.accordion_parent_text(MATCH, MATCH, "", MATCH, MATCH), "children"),
        Input(common_ids.value_field(MATCH, MATCH, "name", MATCH, MATCH), "value"),
    )


# class ModelImportField(ModelField):
#     """Model import field."""

#     class ids(ModelField.ids):  # pylint: disable = invalid-name
#         """Model import field ids."""

#         select = partial(field_dependent_id, "_firestore-model-import-select")
#         button = partial(field_dependent_id, "_firestore-model-import-button")
#         model_store = partial(field_dependent_id, "_firestore-model-import-model-store")
#         open_modal = partial(field_dependent_id, "_firestore-model-import-open-modal")
#         modal = partial(field_dependent_id, "_firestore-model-import-modal")

#     def _create_input(self, item: Model, aio_id: str, field: str, parent: str = "") -> Component:
#         """Create a form input to interact with the field."""
#         other_model: type[Model] = get_non_null_annotation(self.annotation)
#         if not issubclass(other_model, Model):
#             raise TypeError(f"Wrong type annotation for field {get_fullpath(parent, field)} to use ModelImport.")

#         import_selector = self.get_import_selector(other_model, aio_id, item.doc_id, field, parent)

#         model_form = super()._create_input(item, aio_id, field, parent)
#         for elem in model_form._traverse_ids():  # pylint: disable = protected-access
#             if elem.id == self.ids.form_wrapper(aio_id, item.doc_id, field, parent):
#                 elem.children = [import_selector] + list(elem.children or [])
#                 break

#         return dmc.Stack(
#             [
#                 model_form,
#                 dcc.Store(
#                     data=[item.__class__.__name__, other_model.__name__],
#                     id=self.ids.model_store(aio_id, item.doc_id, field, parent),
#                 ),
#             ]
#         )

#     @classmethod
#     def get_import_selector(  # pylint: disable = too-many-arguments
#         cls, other_model: type[Model], aio_id: str, doc_id: str, field: str, parent: str = ""
#     ):
#         """Create a modal to select and import an existing item."""
#         other_model_list = other_model.search()
#         return html.Div(
#             [
#                 dmc.Button(
#                     "Import existing",
#                     size="sm",
#                     leftSection=DashIconify(icon="carbon:cloud-download", height=16),
#                     id=cls.ids.open_modal(aio_id, doc_id, field, parent),
#                 ),
#                 dmc.Modal(
#                     dmc.Group(
#                         [
#                             dmc.Select(
#                                 data=[{"label": str(m), "value": m.doc_id} for m in other_model_list],
#                                 placeholder="Select one",
#                                 id=cls.ids.select(aio_id, doc_id, field, parent),
#                                 searchable=True,
#                                 clearable=True,
#                             ),
#                             dmc.Button("Import", id=cls.ids.button(aio_id, doc_id, field, parent)),
#                         ],
#                         gap="xs",
#                     ),
#                     id=cls.ids.modal(aio_id, doc_id, field, parent),
#                     title="Import existing",
#                 ),
#             ],
#             style={"marginBottom": "1.5rem"},
#         )

#     @callback(
#         Output(ids.form_wrapper(MATCH, MATCH, MATCH, parent=MATCH), "children"),
#         Output(ids.select(MATCH, MATCH, MATCH, parent=MATCH), "value"),
#         Input(ids.button(MATCH, MATCH, MATCH, parent=MATCH), "n_clicks"),
#         State(ids.select(MATCH, MATCH, MATCH, parent=MATCH), "value"),
#         State(ids.model_store(MATCH, MATCH, MATCH, parent=MATCH), "data"),
#     )
#     def update_form(trigger, other_doc_id: str, model_names: str):  # pylint: disable = too-many-locals
#         """Update the form with the imported data."""
#         if not ctx.triggered_id or not trigger:
#             return no_update, no_update

#         aio_id = ctx.triggered_id["aio_id"]
#         doc_id = ctx.triggered_id["doc_id"]
#         field = ctx.triggered_id["field"]
#         parent = ctx.triggered_id["parent"]

#         model_name, other_model_name = model_names
#         other_model = MODELS[other_model_name]
#         other_item = other_model.get(other_doc_id)

#         new_form = create_form(aio_id, other_item)

#         # Update all the doc_id and parent to use the one from the current model rather than the one imported
#         new_parent = get_fullpath(parent, field)
#         for base in new_form:
#             for elem in base._traverse_ids():  # pylint: disable = protected-access
#                 if isinstance(elem.id, dict):
#                     if "doc_id" in elem.id:
#                         elem.id["doc_id"] = doc_id
#                     if "parent" in elem.id:
#                         elem.id["parent"] = get_fullpath(new_parent, elem.id["parent"])
#                     # pylint: disable-next = no-member
#                     if elem.id.get("component") == ModelListField.ids.model_store.args[0]:
#                         elem.data[0] = model_name

#         import_selector = ModelImportField.get_import_selector(other_model, aio_id, doc_id, field, parent)
#         return [import_selector] + new_form, None

#     # Open the modal when the button is clicked
#     clientside_callback(
#         """n => !!n""",
#         Output(ids.modal(MATCH, MATCH, MATCH, parent=MATCH), "opened"),
#         Input(ids.open_modal(MATCH, MATCH, MATCH, parent=MATCH), "n_clicks"),
#         prevent_initial_call=True,
#     )

import logging
import uuid
from collections.abc import Callable
from functools import partial
from typing import Any, get_args

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
from dash.dependencies import stringify_id
from dash_iconify import DashIconify
from plotly.io.json import to_json_plotly
from pydantic import BaseModel, Field, SerializeAsAny, field_validator
from pydantic.fields import FieldInfo
from pydantic_core import PydanticUndefined

from dash_pydantic_form import ids as common_ids
from dash_pydantic_form.fields.base_fields import BaseField, FieldsRepr
from dash_pydantic_form.form_layouts.form_layout import FormLayout
from dash_pydantic_form.i18n import _
from dash_pydantic_utils import (
    Type,
    deep_merge,
    get_fullpath,
    get_subitem,
    get_subitem_cls,
    model_construct_recursive,
)

logger = logging.getLogger(__name__)


class ListField(BaseField):
    """List field, used for list of nested models or scalars.

    Optional attributes:
    * render_type (one of 'accordion', 'modal', 'list', default 'accordion')
        new render types can be defined by extending this class and overriding
        the following methods: _contents_renderer and render_type_item_mapper
    * fields_repr, mapping between field name and field representation
    * form_layout, FormLayout, representing how to render the form
    * items_deletable, whether the items can be deleted (bool, default True)
    * items_creatable, whether new items can be created (bool, default True)
    * form_cols, number of columns in the form
    * wrapper_kwargs, kwargs to pass to the <render_type>_items method's wrapper object
    * excluded_fields, list of field names to exclude from the form altogether
    * fields_order, list of field names in the order they should be rendered
    """

    render_type: str = Field(
        default="accordion",
        description=(
            "How to render the list of items. One  of 'accordion', 'modal', 'list' for a list of models. "
            "Should be set to 'scalar' for a list of scalars."
        ),
    )
    fields_repr: FieldsRepr = Field(
        default_factory=dict,
        description="Fields representation, mapping between field name and field representation for the nested fields.",
    )
    form_layout: SerializeAsAny[FormLayout] | None = Field(default=None, description="Sub-form layout.")
    items_deletable: bool = Field(default=True, description="Whether the items can be deleted.")
    items_creatable: bool = Field(default=True, description="Whether new items can be created.")
    form_cols: int = Field(default=4, description="Number of columns in the form.")
    wrapper_kwargs: dict | None = Field(default=None, description="Kwargs to pass to the items wrapper.")
    excluded_fields: list[str] | None = Field(default=None, description="Fields excluded from the sub-form")
    fields_order: list[str] | None = Field(default=None, description="Order of fields in the sub-form")

    full_width = True

    @field_validator("form_layout", mode="before")
    @classmethod
    def validate_form_layout(cls, v):
        """Validate form layout."""
        if isinstance(v, FormLayout) or v is None:
            return v
        if isinstance(v, dict):
            return FormLayout.load(**v)
        raise ValueError("form_layout must be a FormLayout or a dict that can be converted to a FormLayout")

    def model_post_init(self, _context):
        """Model post init."""
        super().model_post_init(_context)
        if self.fields_repr is None:
            self.fields_repr = {}
        if self.read_only:
            self.items_deletable = False
            self.items_creatable = False
        if self.form_layout is None and self.model_extra and self.model_extra.get("sections") is not None:
            self.form_layout = self.model_extra["sections"]
        try:
            self.render_type_item_mapper(self.render_type)
            self.render_type_items_mapper(self.render_type)
        except AttributeError as exc:
            raise ValueError(f"Unknown render type {self.render_type}") from exc
        if self.wrapper_kwargs is None:
            self.wrapper_kwargs = {}

    class ids(BaseField.ids):
        """Model list field ids."""

        wrapper = partial(common_ids.field_dependent_id, "_pydf-list-field-wrapper")
        delete = partial(common_ids.field_dependent_id, "_pydf-list-field-delete")
        edit = partial(common_ids.field_dependent_id, "_pydf-list-field-edit")
        edit_holder = partial(common_ids.field_dependent_id, "_pydf-list-field-edit-holder")
        modal = partial(common_ids.field_dependent_id, "_pydf-list-field-modal")
        accordion_parent_text = partial(common_ids.field_dependent_id, "_pydf-list-field-accordion-text")
        modal_parent_text = partial(common_ids.field_dependent_id, "_pydf-list-field-modal-text")
        modal_save = partial(common_ids.field_dependent_id, "_pydf-list-field-modal-save")
        modal_holder = partial(common_ids.field_dependent_id, "_pydf-list-field-modal-holder")
        modal_item_data = partial(common_ids.field_dependent_id, "_pydf-list-field-modal-item-data")
        add = partial(common_ids.field_dependent_id, "_pydf-list-field-add")
        template_store = partial(common_ids.field_dependent_id, "_pydf-list-field-template-store")

    @staticmethod
    def get_value_str(value: Any):
        """Get value string, using custom __str__ if present."""
        if isinstance(value, BaseModel):
            # Check if __str__ is custom (not BaseModel.__str__)
            if type(value).__str__ is not BaseModel.__str__:
                return str(value)
            # Fallback: use 'name' if present
            if "name" in value.__class__.model_fields and getattr(value, "name", None):
                return str(value.name)
        return str(value)

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
        form_layout: FormLayout | None = None,
        items_deletable: bool = True,
        read_only: bool | None = None,
        discriminator: str | None = None,
        form_cols: int = 4,
        excluded_fields: list[str] | None = None,
        fields_order: list[str] | None = None,
        _value_uid: str | None = None,
        **_kwargs,
    ):
        """Create an accordion item for the model list field."""
        from dash_pydantic_form import ModelForm

        new_parent = get_fullpath(parent, field, index)
        value_str = cls.get_value_str(value)

        return dmc.AccordionItem(
            # Give a random unique value to the item, prepended by uuid: so that the callback
            # to add new items works
            value=_value_uid,
            style={"position": "relative"},
            className="pydf-model-list-accordion-item",
            children=[
                dmc.AccordionControl(
                    [dmc.Text(value_str, id=cls.ids.accordion_parent_text(aio_id, form_id, "", parent=new_parent))]
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
                        form_layout=form_layout,
                        read_only=read_only,
                        discriminator=discriminator,
                        form_cols=form_cols,
                        excluded_fields=excluded_fields,
                        fields_order=fields_order,
                    ),
                ),
            ],
        )

    @classmethod
    def accordion_items(  # noqa: PLR0913
        cls,
        *,
        item: BaseModel,
        aio_id: str,
        form_id: str,
        field: str,
        parent: str,
        value: list[BaseModel],
        fields_repr: dict[str, dict | BaseField] | None = None,
        form_layout: FormLayout | None = None,
        items_deletable: bool = True,
        read_only: bool | None = None,
        discriminator: str | None = None,
        form_cols: int = 4,
        wrapper_class_name: str,
        wrapper_kwargs: dict,
        excluded_fields: list[str] | None = None,
        fields_order: list[str] | None = None,
        input_kwargs: dict,
        **_kwargs,
    ):
        """Create a list of accordion items."""
        wrapper_class_name = wrapper_class_name + " " + wrapper_kwargs.pop("className", "")
        styles = deep_merge(
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
            wrapper_kwargs.pop("styles", {}),
        )

        items = []
        opened_value = [] if wrapper_kwargs.get("multiple", False) else None
        passed_opened_value = wrapper_kwargs.pop("initially_opened_value", None)
        for i, val in enumerate(value):
            value_uid = "uuid:" + uuid.uuid4().hex
            list_item = cls.accordion_item(
                item=item,
                aio_id=aio_id,
                form_id=form_id,
                field=field,
                parent=parent,
                index=i,
                value=val,
                fields_repr=fields_repr,
                form_layout=form_layout,
                items_deletable=items_deletable,
                read_only=read_only,
                discriminator=discriminator,
                form_cols=form_cols,
                excluded_fields=excluded_fields,
                fields_order=fields_order,
                _value_uid=value_uid,
                input_kwargs=input_kwargs,
            )
            items.append(list_item)
            if passed_opened_value is not None:
                if wrapper_kwargs.get("multiple", False):
                    if (isinstance(passed_opened_value, list) and i in passed_opened_value) or passed_opened_value == i:
                        opened_value.append(value_uid)
                elif passed_opened_value == i:
                    opened_value = value_uid

        return dmc.Accordion(
            items,
            id=cls.ids.wrapper(aio_id, form_id, field, parent=parent),
            value=opened_value,
            styles=styles,
            className=wrapper_class_name,
            **wrapper_kwargs,
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
        form_layout: FormLayout | None = None,
        items_deletable: bool = True,
        read_only: bool | None = None,
        discriminator: str | None = None,
        form_cols: int = 4,
        excluded_fields: list[str] | None = None,
        fields_order: list[str] | None = None,
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
                    form_layout=form_layout,
                    container_kwargs={"style": {"flex": 1}},
                    read_only=read_only,
                    discriminator=discriminator,
                    form_cols=form_cols,
                    excluded_fields=excluded_fields,
                    fields_order=fields_order,
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
    def list_items(  # noqa: PLR0913
        cls,
        *,
        item: BaseModel,
        aio_id: str,
        form_id: str,
        field: str,
        parent: str,
        value: list[BaseModel],
        fields_repr: dict[str, dict | BaseField] | None = None,
        form_layout: FormLayout | None = None,
        items_deletable: bool = True,
        read_only: bool | None = None,
        discriminator: str | None = None,
        form_cols: int = 4,
        wrapper_class_name: str,
        wrapper_kwargs: dict,
        excluded_fields: list[str] | None = None,
        fields_order: list[str] | None = None,
        input_kwargs: dict,
        **_kwargs,
    ):
        """Create a list of list items."""
        wrapper_class_name = wrapper_class_name + " " + wrapper_kwargs.pop("className", "")
        return dmc.Stack(
            [
                cls.list_item(
                    item=item,
                    aio_id=aio_id,
                    form_id=form_id,
                    field=field,
                    parent=parent,
                    index=i,
                    fields_repr=fields_repr,
                    form_layout=form_layout,
                    items_deletable=items_deletable,
                    read_only=read_only,
                    discriminator=discriminator,
                    form_cols=form_cols,
                    excluded_fields=excluded_fields,
                    fields_order=fields_order,
                    input_kwargs=input_kwargs,
                )
                for i, _ in enumerate(value)
            ],
            id=cls.ids.wrapper(aio_id, form_id, field, parent=parent),
            className=wrapper_class_name,
            **wrapper_kwargs,
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
        form_layout: FormLayout | None = None,
        items_deletable: bool = True,
        read_only: bool | None = None,
        discriminator: str | None = None,
        form_cols: int = 4,
        excluded_fields: list[str] | None = None,
        fields_order: list[str] | None = None,
        **_kwargs,
    ):
        """Create an item with bare forms for the model list field."""
        from dash_pydantic_form import ModelForm

        new_parent = get_fullpath(parent, field, index)
        value_str = cls.get_value_str(value)

        item_data = ModelForm(
            item=item,
            aio_id=aio_id,
            form_id=form_id,
            path=new_parent,
            fields_repr=fields_repr,
            form_layout=form_layout,
            read_only=read_only,
            discriminator=discriminator,
            form_cols=form_cols,
            excluded_fields=excluded_fields,
            fields_order=fields_order,
        )

        return dmc.Paper(

                dmc.Group(
                    [
                            html.Div(dmc.Text(
                                value_str,
                                style={
                                    "flex": 1,
                                    "overflow": "hidden",
                                    "textOverflow": "ellipsis",
                                    "whiteSpace": "nowrap",
                                },
                                id=cls.ids.modal_parent_text(aio_id, form_id, "", parent=new_parent),
                            ),
                            style={'cursor': 'pointer', 'flex': 1},
                            id=cls.ids.edit_holder(aio_id, form_id, "", parent=new_parent),
                            title="view" if read_only else "edit"
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
                                dcc.Store(id=cls.ids.modal_item_data(aio_id, form_id, "", parent=new_parent),
                                          data=to_json_plotly(item_data)),
                                dcc.Loading(
                                    [
                                        html.Div(id=cls.ids.modal_holder(aio_id, form_id, "", parent=new_parent),
                                                 style={"minHeight": "200px"}),
                                    ],
                                    custom_spinner=dmc.Skeleton(h='100%', visible=True),
                                    target_components={stringify_id(cls.ids.modal_holder(aio_id, form_id, "", parent=new_parent)): 'children'},
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
                            title=value_str,
                            id=cls.ids.modal(aio_id, form_id, "", parent=new_parent),
                            style={"--modal-size": "min(calc(100vw - 4rem), 1150px)"},
                            styles={"content": {"containerType": "inline-size"}},
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
    def modal_items(  # noqa: PLR0913
        cls,
        *,
        item: BaseModel,
        aio_id: str,
        form_id: str,
        field: str,
        parent: str,
        value: list[BaseModel],
        fields_repr: dict[str, dict | BaseField] | None = None,
        form_layout: FormLayout | None = None,
        items_deletable: bool = True,
        read_only: bool | None = None,
        discriminator: str | None = None,
        form_cols: int = 4,
        wrapper_class_name: str,
        wrapper_kwargs: dict,
        excluded_fields: list[str] | None = None,
        fields_order: list[str] | None = None,
        input_kwargs: dict,
        **_kwargs,
    ):
        """Create a list of modal items."""
        wrapper_class_name = wrapper_class_name + " " + wrapper_kwargs.pop("className", "")
        style = deep_merge(
            {
                "display": "grid",
                "gridTemplateColumns": "repeat(auto-fit, minmax(min(100%, 280px), 1fr))",
                "gap": "0.5rem",
                "overflow": "hidden",
            },
            wrapper_kwargs.pop("style", {}),
        )
        return html.Div(
            [
                cls.modal_item(
                    item=item,
                    aio_id=aio_id,
                    form_id=form_id,
                    field=field,
                    parent=parent,
                    index=i,
                    value=val,
                    fields_repr=fields_repr,
                    form_layout=form_layout,
                    items_deletable=items_deletable,
                    read_only=read_only,
                    discriminator=discriminator,
                    form_cols=form_cols,
                    excluded_fields=excluded_fields,
                    fields_order=fields_order,
                    input_kwargs=input_kwargs,
                )
                for i, val in enumerate(value)
            ],
            id=cls.ids.wrapper(aio_id, form_id, field, parent=parent),
            style=style,
            className=wrapper_class_name,
            **wrapper_kwargs,
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
        value: Any,  # noqa: ARG003
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

    @classmethod
    def scalar_items(  # noqa: PLR0913
        cls,
        *,
        item: BaseModel,
        aio_id: str,
        form_id: str,
        field: str,
        parent: str,
        value: list[BaseModel],
        fields_repr: dict[str, dict | BaseField] | None = None,
        form_layout: FormLayout | None = None,
        items_deletable: bool = True,
        read_only: bool | None = None,
        input_kwargs: dict,
        wrapper_class_name: str,
        wrapper_kwargs: dict,
        **_kwargs,
    ):
        """Create a list of scalar items."""
        wrapper_class_name = wrapper_class_name + " " + wrapper_kwargs.pop("className", "")
        style = deep_merge(
            {
                "display": "grid",
                "gridTemplateColumns": "repeat(auto-fit, minmax(min(100%, 280px), 1fr))",
                "gap": "0.5rem",
                "overflow": "hidden",
                "alignItems": "top",
            },
            wrapper_kwargs.pop("style", {}),
        )
        return html.Div(
            [
                cls.scalar_item(
                    item=item,
                    aio_id=aio_id,
                    form_id=form_id,
                    field=field,
                    parent=parent,
                    index=i,
                    value=val,
                    fields_repr=fields_repr,
                    form_layout=form_layout,
                    items_deletable=items_deletable,
                    read_only=read_only,
                    input_kwargs=input_kwargs,
                )
                for i, val in enumerate(value)
            ],
            id=cls.ids.wrapper(aio_id, form_id, field, parent=parent),
            className=wrapper_class_name,
            style=style,
            **wrapper_kwargs,
        )

    @classmethod
    def render_type_item_mapper(cls, render_type: str) -> Callable:
        """Mapping between render type and renderer function."""
        return getattr(cls, f"{render_type}_item")

    @classmethod
    def render_type_items_mapper(cls, render_type: str) -> Callable:
        """Mapping between render type and renderer function."""
        return getattr(cls, f"{render_type}_items")

    @staticmethod
    def make_template_item(item: BaseModel, parent: str, field: str):
        """Make a template item."""
        template_item = model_construct_recursive(item.model_dump(), item.__class__)
        if isinstance(subitem := get_subitem(item, parent), BaseModel):
            pointer = get_subitem(template_item, parent)
            default_val = None
            field_info = subitem.__class__.model_fields[field]
            if field_info.default is not PydanticUndefined:
                default_val = field_info.default
            if field_info.default_factory is not None:
                try:
                    default_val = field_info.default_factory()
                except TypeError:
                    logger.warning("Default factory with validated data not supported in allow_default")
            if isinstance(pointer, dict):
                pointer[field] = default_val
            else:
                setattr(pointer, field, default_val)

        return template_item

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
        if type_ in [Type.MODEL_LIST, Type.DISCRIMINATED_MODEL_LIST] and self.render_type == "scalar":
            raise ValueError("Cannot render model list as scalar")
        if type_ not in [Type.MODEL_LIST, Type.DISCRIMINATED_MODEL_LIST] and self.render_type != "scalar":
            raise ValueError("Cannot render non model list as non scalar")

        discriminator = (
            get_args(get_args(field_info.annotation)[0])[1].discriminator
            if type_ == Type.DISCRIMINATED_MODEL_LIST
            else None
        )

        value: list = self.get_value(item, field, parent) or []

        wrapper_class_name = "pydf-model-list-wrapper" + (" required" if self.is_required(field_info) else "")
        contents = self.render_type_items_mapper(self.render_type)(
            item=item,
            aio_id=aio_id,
            form_id=form_id,
            field=field,
            parent=parent,
            value=value,
            fields_repr=self.fields_repr,
            form_layout=self.form_layout,
            items_deletable=self.items_deletable,
            read_only=self.read_only,
            input_kwargs=self.input_kwargs,
            discriminator=discriminator,
            form_cols=self.form_cols,
            wrapper_class_name=wrapper_class_name,
            wrapper_kwargs=self.wrapper_kwargs,
            excluded_fields=self.excluded_fields,
            fields_order=self.fields_order,
        )

        template_item = self.make_template_item(item, parent, field)

        # Create a template item to be used clientside when adding new items
        template = self.render_type_item_mapper(self.render_type)(
            item=template_item,
            aio_id=aio_id,
            form_id=form_id,
            field=field,
            parent=parent,
            index="{{" + get_fullpath(parent, field).replace(":", "|") + "}}",
            value="-",
            opened=True,
            fields_repr=self.fields_repr,
            form_layout=self.form_layout,
            # The template items (used when adding new ones) should always be deletable
            items_deletable=True,
            read_only=self.read_only,
            input_kwargs=self.input_kwargs,
            discriminator=discriminator,
            form_cols=self.form_cols,
            excluded_fields=self.excluded_fields,
            fields_order=self.fields_order,
        )

        title = self.get_title(field_info, field_name=field)
        description = self.get_description(field_info)

        title_children: list = [title] + [
            html.Span(" *", style={"color": "var(--input-asterisk-color, var(--mantine-color-error))"})
        ] * self.is_required(field_info)

        return dmc.Stack(
            bool(title)
            * [
                dmc.Stack(
                    bool(title)
                    * [
                        dmc.Text(
                            title_children,
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
            className="pydantic-form-field",
            style={"--pydf-field-cols": "var(--pydf-form-cols)"},
            gap="0.5rem",
        )


clientside_callback(
    ClientsideFunction(namespace="pydf", function_name="addToList"),
    Output(ListField.ids.wrapper(MATCH, MATCH, MATCH, MATCH), "children", allow_duplicate=True),
    Input(ListField.ids.add(MATCH, MATCH, MATCH, MATCH), "n_clicks"),
    State(ListField.ids.wrapper(MATCH, MATCH, MATCH, MATCH), "children"),
    State(ListField.ids.template_store(MATCH, MATCH, MATCH, MATCH), "data"),
    prevent_initial_call=True,
)

clientside_callback(
    ClientsideFunction(namespace="pydf", function_name="deleteFromList"),
    Output(ListField.ids.wrapper(MATCH, MATCH, MATCH, MATCH), "children", allow_duplicate=True),
    Input(ListField.ids.delete(MATCH, MATCH, MATCH, MATCH, ALL), "n_clicks"),
    State(ListField.ids.wrapper(MATCH, MATCH, MATCH, MATCH), "children"),
    prevent_initial_call=True,
)

# Open a model list modal when editing an item
clientside_callback(
    ClientsideFunction(namespace="pydf", function_name="syncTrue"),
    Output(ListField.ids.modal(MATCH, MATCH, MATCH, MATCH, MATCH), "opened", allow_duplicate=True),
    Input(ListField.ids.edit(MATCH, MATCH, MATCH, MATCH, MATCH), "n_clicks"),
    prevent_initial_call=True,
)

clientside_callback(
    ClientsideFunction(namespace="pydf", function_name="syncTrue"),
    Output(ListField.ids.modal(MATCH, MATCH, MATCH, MATCH, MATCH), "opened", allow_duplicate=True),
    Input(ListField.ids.edit_holder(MATCH, MATCH, MATCH, MATCH, MATCH), "n_clicks"),
    prevent_initial_call=True,
)

# Close a model list modal when saving an item
clientside_callback(
    ClientsideFunction(namespace="pydf", function_name="syncFalse"),
    Output(ListField.ids.modal(MATCH, MATCH, MATCH, MATCH, MATCH), "opened", allow_duplicate=True),
    Input(ListField.ids.modal_save(MATCH, MATCH, MATCH, MATCH, MATCH), "n_clicks"),
    prevent_initial_call=True,
)

# Update the modal title and list item to match the name field of the item (if it exists)
clientside_callback(
    ClientsideFunction(namespace="pydf", function_name="updateModalTitle"),
    Output(ListField.ids.modal(MATCH, MATCH, "", MATCH, MATCH), "title"),
    Input(common_ids.value_field(MATCH, MATCH, "name", MATCH, MATCH), "value"),
    State(ListField.ids.modal(MATCH, MATCH, "", MATCH, MATCH), "id"),
    prevent_initial_call=True,
)

# Update the accordion title to match the name field of the item (if it exists)
clientside_callback(
    ClientsideFunction(namespace="pydf", function_name="updateAccordionTitle"),
    Output(ListField.ids.accordion_parent_text(MATCH, MATCH, "", MATCH, MATCH), "children"),
    Input(common_ids.value_field(MATCH, MATCH, "name", MATCH, MATCH), "value"),
    prevent_initial_call=True,
)

clientside_callback(
    """
        async (opened, data, currentForm, id) => {
            if (opened || dash_clientside.callback_context.triggered_id === null) {
                var elem = await waitForElem(dash_component_api.stringifyId(id));
                elem = elem.parentNode.nextElementSibling; // Get the loading spinner div
                await new Promise(resolve => {
                    (async function poll() {
                        while (true) {
                            const rect = elem.getBoundingClientRect();
                            const style = getComputedStyle(elem);
                            await new Promise(r => setTimeout(r, 100));
                            const isVisible =
                                rect.height > 0 &&
                                style.visibility !== 'hidden' &&
                                style.opacity !== '0';
                            if (isVisible) break;
                        }
                        resolve();
                    })();
                }); // Wait for element to be visible and have non-zero height
                return [
                    JSON.parse(data),
                    dash_clientside.no_update
                ];
            } else if (currentForm) {
                return [[], JSON.stringify(currentForm)];
            }
            return [[], dash_clientside.no_update];
        }
    """,
    Output(ListField.ids.modal_holder(MATCH, MATCH, MATCH, MATCH, MATCH), "children"),
    Output(ListField.ids.modal_item_data(MATCH, MATCH, MATCH, MATCH, MATCH), "data"),
    Input(ListField.ids.modal(MATCH, MATCH, MATCH, MATCH, MATCH), "opened"),
    State(ListField.ids.modal_item_data(MATCH, MATCH, MATCH, MATCH, MATCH), "data"),
    State(ListField.ids.modal_holder(MATCH, MATCH, MATCH, MATCH, MATCH), "children"),
    State(ListField.ids.modal_holder(MATCH, MATCH, MATCH, MATCH, MATCH), "id"),
)
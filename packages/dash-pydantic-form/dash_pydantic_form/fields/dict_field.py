from functools import partial
from typing import Literal, get_args

import dash_mantine_components as dmc
from dash import dcc, html
from dash.development.base_component import Component
from dash_iconify import DashIconify
from plotly.io.json import to_json_plotly
from pydantic import BaseModel
from pydantic.fields import FieldInfo

from dash_pydantic_form import ids as common_ids
from dash_pydantic_form.fields.base_fields import BaseField
from dash_pydantic_form.fields.list_field import ListField
from dash_pydantic_form.form_layouts.form_layout import FormLayout
from dash_pydantic_form.i18n import _
from dash_pydantic_utils import Type, get_fullpath


class DictField(ListField):
    """Dict field for dict of models or scalars."""

    render_type: Literal["accordion", "modal", "scalar"] = "accordion"

    class ids(ListField.ids):
        """Dict field ids."""

        item_key = partial(common_ids.field_dependent_id, "_pydf-dict-field-item-key")

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
        fields_repr: dict[str, dict | BaseField] | None = None,
        form_layout: FormLayout | None = None,
        items_deletable: bool = True,
        read_only: bool | None = None,
        value: str | None = None,
        **kwargs,
    ):
        """Create an item with bare forms for the model dict field."""
        contents = super().accordion_item(
            item=item,
            aio_id=aio_id,
            form_id=form_id,
            field=field,
            parent=parent,
            index=index,
            value=kwargs.pop("value", None),
            fields_repr=fields_repr,
            form_layout=form_layout,
            items_deletable=items_deletable,
            read_only=read_only,
            **kwargs,
        )
        contents.children[0].children[0] = cls.key_input(
            aio_id, form_id, field, parent, index, key=value, read_only=read_only, w="calc(100% - 3.5rem)"
        )
        return contents

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
        value: str | None = None,
        opened: bool = False,
        fields_repr: dict[str, dict | BaseField] | None = None,
        form_layout: FormLayout | None = None,
        items_deletable: bool = True,
        read_only: bool | None = None,
        **kwargs,
    ):
        """Create an item with bare forms for the model dict field."""
        contents = super().modal_item(
            item=item,
            aio_id=aio_id,
            form_id=form_id,
            field=field,
            parent=parent,
            index=index,
            value=kwargs.pop("value", None),
            opened=opened,
            fields_repr=fields_repr,
            form_layout=form_layout,
            items_deletable=items_deletable,
            read_only=read_only,
            **kwargs,
        )
        contents.children.children[0] = cls.key_input(
            aio_id, form_id, field, parent, index, key=value, read_only=read_only, style={"flex": 1}
        )
        return contents

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
        value: str | None = None,
        items_deletable: bool = True,
        read_only: bool | None = None,
        input_kwargs: dict,
        **kwargs,
    ):
        """Create an item for a scalar dict."""
        contents = super().scalar_item(
            item=item,
            aio_id=aio_id,
            form_id=form_id,
            field=field,
            parent=parent,
            index=index,
            items_deletable=items_deletable,
            read_only=read_only,
            input_kwargs=input_kwargs,
            value="",
            **kwargs,
        )
        contents.children = [
            cls.key_input(
                aio_id, form_id, field, parent, index, key=value, read_only=read_only, style={"flex": "0 0 30%"}
            ),
            dmc.Text(":", pl="0.25rem", pr="0.5rem", fw=500, lh=2),
        ] + contents.children
        return contents

    @classmethod
    def key_input(  # noqa: PLR0913
        cls,
        aio_id: str,
        form_id: str,
        field: str,
        parent: str,
        index: int,
        key: str | None = None,
        read_only: bool | None = None,
        **input_kwargs,
    ):
        """Create an input for the key of a dict item."""
        return dmc.TextInput(
            placeholder="Key",
            id=cls.ids.item_key(aio_id, form_id, field, parent=parent, meta=index),
            leftSection=DashIconify(icon="fe:key"),
            value=key,
            readOnly=read_only,
            **input_kwargs,
        )

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
        if type_ in [Type.MODEL_LIST, Type.MODEL_DICT] and self.render_type == "scalar":
            raise ValueError("Cannot render model list as scalar")
        if (
            type_
            not in [Type.MODEL_LIST, Type.MODEL_DICT, Type.DISCRIMINATED_MODEL_LIST, Type.DISCRIMINATED_MODEL_DICT]
            and self.render_type != "scalar"
        ):
            raise ValueError("Cannot render non model list as non scalar")

        discriminator = (
            get_args(get_args(field_info.annotation)[1])[1].discriminator
            if type_ in [Type.DISCRIMINATED_MODEL_LIST, Type.DISCRIMINATED_MODEL_DICT]
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
        )

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
            form_layout=self.form_layout,
            items_deletable=self.items_deletable,
            read_only=self.read_only,
            input_kwargs=self.input_kwargs,
            discriminator=discriminator,
            form_cols=self.form_cols,
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
            className="pydantic-form-field",
            style={"--pydf-field-cols": "var(--pydf-form-cols)"},
            gap="0.5rem",
        )

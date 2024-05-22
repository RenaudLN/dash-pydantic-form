from functools import partial
from typing import Any

import dash_mantine_components as dmc
from dash import MATCH, ClientsideFunction, Input, Output, clientside_callback, dcc, html
from dash.development.base_component import Component
from pydantic import BaseModel
from pydantic.fields import FieldInfo

from dash_pydantic_form import ids as common_ids
from dash_pydantic_form.fields.base_fields import BaseField


class MarkdownField(BaseField):
    """Markdown field."""

    full_width = True

    class ids(BaseField.ids):
        """Model list field ids."""

        preview = partial(common_ids.field_dependent_id, "_pydf-markdown-field-preview")

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
        """Render the markdown field."""
        value = self.get_value(item, field, parent)
        if self.read_only:
            return self._render_read_only(value, field, field_info)

        return html.Div(
            [
                dmc.Textarea(
                    value=value,
                    label=self.get_title(field_info, field_name=field),
                    description=self.get_description(field_info),
                    id=common_ids.value_field(aio_id, form_id, field, parent=parent),
                    autosize=True,
                    minRows=3,
                    **self.input_kwargs,
                ),
                dcc.Markdown(
                    value,
                    id=self.ids.preview(aio_id, form_id, field, parent=parent),
                    className="pydf-markdown-preview",
                ),
            ],
            style={"display": "grid", "gap": "1rem", "gridTemplateColumns": "1fr 1fr"},
        )

    @staticmethod
    def _get_value_repr(value: Any, _field_info: FieldInfo):
        if value is None:
            return "-"
        return dcc.Markdown(value)


clientside_callback(
    ClientsideFunction(namespace="pydf", function_name="sync"),
    Output(MarkdownField.ids.preview(MATCH, MATCH, MATCH, parent=MATCH), "children"),
    Input(common_ids.value_field(MATCH, MATCH, MATCH, parent=MATCH), "value"),
)

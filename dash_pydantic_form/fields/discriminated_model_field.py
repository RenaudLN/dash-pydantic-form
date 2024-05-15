from dash.development.base_component import Component
from pydantic import BaseModel
from pydantic.fields import FieldInfo

from .model_field import ModelField


class DiscriminatedModelField(ModelField):
    """Discriminated model field, used for nested BaseModel."""

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
        return super()._render(
            item=item,
            aio_id=aio_id,
            form_id=form_id,
            field=field,
            parent=parent,
            field_info=field_info,
        )

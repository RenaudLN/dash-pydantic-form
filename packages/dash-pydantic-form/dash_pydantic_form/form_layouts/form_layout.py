import json
from abc import ABC, abstractmethod
from typing import Annotated, Literal, Union

import dash_mantine_components as dmc
from dash.development.base_component import Component
from plotly.io.json import to_json_plotly
from pydantic import BaseModel, Discriminator, Field, TypeAdapter, field_serializer

from dash_pydantic_utils import get_all_subclasses

Children_ = Component | str | int | float
Children = Children_ | list[Children_]
Position = Literal["top", "bottom", "none"]


class FormLayout(BaseModel, ABC):
    """Abstract form layout class, base for all form layouts.

    Parameters
    ----------
    render_kwargs: dict | None
        Kwargs to pass to the render method.
    """

    render_kwargs: dict = Field(default_factory=dict)
    layout: str

    @abstractmethod
    def render(  # noqa: PLR0913
        self,
        *,
        field_inputs: dict[str, Component],
        aio_id: str,
        form_id: str,
        path: str,
        read_only: bool | None,
        form_cols: int,
    ):
        """Render the form layout."""
        raise NotImplementedError

    def model_post_init(self, _context):
        """Model post init."""
        if self.render_kwargs is None:
            self.render_kwargs = {}

    @field_serializer("render_kwargs")
    def serialize_render_kwargs(self, value):
        """Serialize render kwargs, allowing Dash object values."""
        jsonified = to_json_plotly(value)
        if not isinstance(jsonified, str):
            raise ValueError("Expected string after serialisation")
        return json.loads(jsonified)

    @classmethod
    def grid(cls, children: Children, **kwargs):
        """Create the responsive grid for a field."""
        return dmc.SimpleGrid(children, className="pydantic-form-grid " + kwargs.pop("className", ""), **kwargs)

    @classmethod
    def load(cls, **data) -> "FormLayout":
        """Load the form layout or a subclass."""
        adapter = TypeAdapter(Annotated[Union[tuple(get_all_subclasses(cls))], Discriminator("layout")])  # noqa: UP007
        return adapter.validate_python(data)

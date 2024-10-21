from collections.abc import Mapping
from functools import partial
from typing import ClassVar

import dash_mantine_components as dmc
from dash import MATCH, ClientsideFunction, Input, Output, State, clientside_callback, dcc
from dash.development.base_component import Component
from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic.fields import FieldInfo

from dash_pydantic_form import ids as common_ids
from dash_pydantic_form.fields.base_fields import BaseField
from dash_pydantic_form.quantity import Quantity
from dash_pydantic_form.utils import (
    get_fullpath,
    get_non_null_annotation,
)


class QuantityField(BaseField):
    """Quantity field."""

    unit_options: list[str] | Mapping[str, str] = Field(
        title="Unit options",
        description="List of units to show in the dropdown, if a Mapping, will use the values as unit labels",
    )
    auto_convert: bool | None = Field(
        title="Auto-convert between units when switching.",
        description="If None, checks whether auto-conversion is possible but falls back to False if impossible",
        default=None,
    )
    unit_select_width: str = Field(
        title="Width of the unit select",
        default="5rem",
    )

    kwargs_for_both: ClassVar[list[str]] = ("size",)

    class ids:
        """Quantity field ids."""

        conversion_store = partial(common_ids.field_dependent_id, "_pydf-quantity-conversions")

    @field_validator("unit_options")
    @classmethod
    def check_unit_options(cls, unit_options: list[str]):
        """Ensure unit_options has at least one value."""
        if len(unit_options) == 0:
            raise ValueError("At least one unit option must be defined.")
        return unit_options

    @model_validator(mode="after")
    def check_field(self):
        """Check auto convert field based on unit options."""
        if self.auto_convert is False:
            return self

        if len(self.unit_options) == 1:
            self.auto_convert = False
        else:
            try:
                units_info = [Quantity.get_unit_info(unit)[0] for unit in self.unit_options]
                if len(set(units_info)) != 1:
                    raise ValueError("Incompatible units found")
                self.auto_convert = True
            except ValueError:
                if self.auto_convert is True:
                    raise
                self.auto_convert = False

        return self

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
        """Render the quantity field."""
        ann = get_non_null_annotation(field_info.annotation)
        if not issubclass(ann, BaseModel) or set(ann.model_fields) != {"unit", "value"}:
            raise TypeError("Quantity field should be used with a field that has value and unit sub-fields.")

        value: Quantity | None = self.get_value(item, field, parent)

        # Convert to Quantity if dict
        if isinstance(value, dict) and set(value) == {"unit", "value"}:
            value = Quantity(**value)

        # Try converting if the given uit does not match any of the input units
        if value and value.unit not in self.unit_options:
            value = Quantity(value.value, value.unit).to(next(iter(self.unit_options)))

        meta = "auto-convert" if self.auto_convert else "default"
        new_parent = get_fullpath(parent, field)
        value_id = common_ids.value_field(aio_id, form_id, "value", parent=new_parent, meta=meta)
        unit_id = common_ids.value_field(aio_id, form_id, "unit", parent=new_parent, meta=meta)

        current_unit = value.unit if value else next(iter(self.unit_options))
        with_select = len(self.unit_options) > 1 and not self.read_only
        input_kwargs = self.input_kwargs

        # Add unit suffix and placeholder if not already user-defined
        if not with_select:
            current_unit_label = (
                current_unit if isinstance(self.unit_options, list) else self.unit_options[current_unit]
            )
            if "suffix" not in input_kwargs and "prefix" not in input_kwargs:
                input_kwargs["suffix"] = f" {current_unit_label}"
            if "placeholder" not in input_kwargs:
                input_kwargs["placeholder"] = current_unit_label

        select_kwargs = {k: v for k, v in input_kwargs.items() if k in self.kwargs_for_both}

        return dmc.Group(
            [
                dmc.NumberInput(
                    label=self.get_title(field_info=field_info, field_name=field),
                    description=self.get_description(field_info),
                    value=value.value if value else None,
                    required=self.is_required(field_info),
                    readOnly=self.read_only,
                    id=value_id,
                    hideControls=True,
                    flex="1 1 10rem",
                    styles={"input": {"borderRadius": "var(--input-radius) 0 0 var(--input-radius)"}}
                    if with_select
                    else None,
                    **input_kwargs,
                    **{"data-currentunit": current_unit},
                ),
                dmc.Select(
                    value=current_unit,
                    id=unit_id,
                    data=self.unit_options
                    if isinstance(self.unit_options, list)
                    else [{"value": unit, "label": label} for unit, label in self.unit_options.items()],
                    ml=-1,
                    checkIconPosition="right",
                    readOnly=self.read_only,
                    flex=f"0 1 {self.unit_select_width}",
                    styles={"input": {"borderRadius": "0 var(--input-radius) var(--input-radius) 0"}},
                    display=None if with_select else "none",
                    **select_kwargs,
                ),
                dcc.Store(
                    id=self.ids.conversion_store(aio_id, form_id, "", new_parent, meta),
                    data={unit: list(Quantity.get_unit_info(unit)[1]) for unit in self.unit_options}
                    if self.auto_convert
                    else None,
                ),
            ],
            align="end",
            wrap="nowrap",
            gap=0,
        )


clientside_callback(
    ClientsideFunction(namespace="pydf", function_name="convertQuantityUnit"),
    Output(common_ids.value_field(MATCH, MATCH, "value", MATCH, "auto-convert"), "value", allow_duplicate=True),
    Output(common_ids.value_field(MATCH, MATCH, "value", MATCH, "auto-convert"), "data-currentunit"),
    Input(common_ids.value_field(MATCH, MATCH, "unit", MATCH, "auto-convert"), "value"),
    State(common_ids.value_field(MATCH, MATCH, "value", MATCH, "auto-convert"), "value"),
    State(common_ids.value_field(MATCH, MATCH, "value", MATCH, "auto-convert"), "data-currentunit"),
    State(QuantityField.ids.conversion_store(MATCH, MATCH, "", MATCH, "auto-convert"), "data"),
    prevent_initial_call=True,
)

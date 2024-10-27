import json
import logging
from collections.abc import Callable
from functools import partial
from typing import ClassVar, Literal

import dash_mantine_components as dmc
from dash import (
    ALL,
    MATCH,
    Input,
    Output,
    State,
    callback,
    clientside_callback,
    ctx,
    dcc,
    no_update,
)
from dash.development.base_component import Component
from dash_iconify import DashIconify
from pydantic import BaseModel, Field
from pydantic.fields import FieldInfo

from dash_pydantic_form import ids as common_ids
from dash_pydantic_form.fields.base_fields import BaseField
from dash_pydantic_form.i18n import _


def side_id(  # noqa: PLR0913
    component: str,
    aio_id: str,
    form_id: str,
    field: str,
    parent: str,
    meta: str,
    side: Literal["left", "right"],
):
    """TransferListField side id."""
    return common_ids.field_dependent_id(component, aio_id, form_id, field, parent, meta) | {"side": side}


class TransferListField(BaseField):
    """TransferListField."""

    base_component = None
    full_width = True

    titles: tuple[str, str] | None = Field(default=None, description="List titles.")
    search_placeholder: str | None = Field(default=None, description="Search placeholder.")
    show_transfer_all: bool = Field(default=True, description="Show transfer all button.")
    list_height: int = Field(default=200, description="List rows height in pixels.")
    max_items: int = Field(default=0, description="Max number of items to display.")
    radius: int | str | None = Field(default=None, description="List border-radius.")
    placeholder: str | None = Field(default=None, description="Placeholder text when no item is available.")
    nothing_found: str | None = Field(default=None, description="Text to display when no item is available.")
    transfer_all_matching_filters: bool = Field(default=True, description="Transfer all when filters match.")
    options_labels: dict | None = Field(default=None, description="Label for the options list.")
    data_getter: str = Field(description="Data getter name, needs to have been registered with register_data_getter.")

    getters: ClassVar[dict[str, Callable[[str | None, int | None], list[str]]]] = {}

    class ids:
        """TransferListField ids."""

        search = partial(side_id, "__trl-search-input")
        transfer = partial(side_id, "__trl-transfer-button")
        transfer_tooltip = partial(side_id, "__trl-transfer-tooltip")
        transfer_all = partial(side_id, "__trl-transfer-all-button")
        transfer_all_tooltip = partial(side_id, "__trl-transfer-all-tooltip")
        checklist = partial(side_id, "__trl-checklist")

    @classmethod
    def register_data_getter(
        cls,
        data_getter: Callable[[str | None, int | None], list[str]],
        name: str | None = None,
    ):
        """Register a data_getter."""
        name = name or str(data_getter)
        if name in cls.getters:
            logging.warning("Data getter %s already registered for TransferList field.", name)
        cls.getters[name] = data_getter

    @classmethod
    def get_data(cls, data_getter: str, value: list, search: str | None = None, max_items: int | None = None) -> dict:
        """Retrieve data from Literal annotation if data is not present in input_kwargs."""
        try:
            getter = cls.getters[data_getter]
        except KeyError as exc:
            logging.error(
                "Data getter %s could not be found, make sure you register it at the root level.", data_getter
            )
            raise exc
        search_data = getter(search, max_items + len(value) if max_items else max_items)
        data = [x for x in search_data if x not in value]
        if max_items:
            data = data[:max_items]

        return data

    def _render(  # noqa: PLR0913
        self,
        *,
        item: BaseModel,
        aio_id: str,
        form_id: str,
        field: str,
        parent: str = "",
        field_info: FieldInfo | None = None,  # noqa: ARG002
    ) -> Component:
        value = self.get_value(item, field, parent) or []
        data_left = self.get_data(self.data_getter, value, search=None, max_items=self.max_items)
        id_data = {"aio_id": aio_id, "form_id": form_id, "field": field, "parent": parent, "meta": ""}
        return dmc.SimpleGrid(
            [
                # First list
                dmc.Stack(
                    [
                        *([dmc.Text(self.titles[0], fw=600)] if self.titles else []),
                        dmc.Paper(
                            [
                                dmc.Group(
                                    [
                                        self.search_input(id_data, "left", placeholder=self.search_placeholder),
                                        self.transfer(id_data, "left", self.show_transfer_all),
                                        *([self.transfer_all(id_data, "left")] if self.show_transfer_all else []),
                                    ],
                                    style={"alignItems": "initial"},
                                    gap=0,
                                ),
                                self.checklist(
                                    id_data, "left", data_left, self.list_height, self.max_items, self.options_labels
                                ),
                            ],
                            radius=self.radius,
                            withBorder=True,
                            style={"overflow": "hidden"},
                        ),
                    ],
                    gap="0.375rem",
                    style={"gridColumn": "span var(--col-2-4)"},
                ),
                # Second list
                dmc.Stack(
                    [
                        *([dmc.Text(self.titles[1], fw=600)] if self.titles else []),
                        dmc.Paper(
                            [
                                dmc.Group(
                                    [
                                        *([self.transfer_all(id_data, "right")] if self.show_transfer_all else []),
                                        self.transfer(id_data, "right", self.show_transfer_all),
                                        self.search_input(id_data, "right", placeholder=self.search_placeholder),
                                    ],
                                    style={"alignItems": "initial"},
                                    gap=0,
                                ),
                                self.checklist(id_data, "right", value, self.list_height, None, self.options_labels),
                            ],
                            radius=self.radius,
                            withBorder=True,
                            style={"overflow": "hidden"},
                        ),
                    ],
                    gap="0.375rem",
                    style={"gridColumn": "span var(--col-2-4)"},
                ),
                # This input holds the actual value as well as some metadata to pass to callbacks
                dmc.JsonInput(
                    id=common_ids.value_field(**(id_data | {"meta": "transferlist"})),
                    style={"display": "none"},
                    value=value,
                    **{
                        "data-placeholder": json.dumps(self.placeholder),
                        "data-nothingfound": json.dumps(self.nothing_found),
                        "data-getter": self.data_getter,
                        "data-maxitems": self.max_items,
                        "data-transferallmatchingfilters": json.dumps(self.transfer_all_matching_filters),
                    },
                ),
            ],
            className="pydantic-form-grid",
            spacing="md",
            **self.input_kwargs,
        )

    @classmethod
    def checkbox(cls, value: dict | str, options_labels: dict | None = None):
        """Checkbox for the checklist.

        :param value: value of the checkbox, dict with keys label and value
        """
        options_labels = options_labels or {}
        if isinstance(value, str):
            value = {"label": options_labels.get(value, value), "value": value}

        return dmc.Checkbox(
            label=value["label"],
            value=value["value"],
            px="0.5rem",
            styles={
                "labelWrapper": {"flex": 1},
                "label": {"cursor": "pointer", "padding": "0.5rem 0"},
                "body": {"alignItems": "center", "gap": "0.5rem"},
            },
            className="transferlist-checkbox",
        )

    @classmethod
    def checklist(  # noqa: PLR0913
        cls,
        id_data: dict,
        side: Literal["left", "right"],
        value: list[dict],
        list_height: int,
        max_items: int | None = None,
        options_labels: dict | None = None,
    ):
        """Checklist in a scrollarea for each list of the transfer.

        :param id_data: dict to put in the id
        :param side: list side
        :param value: list value, list of dicts with keys label and value
        :param list_height: height of the checklist
        :param max_items: the max number of items displayed in the checklist
        """
        if max_items:
            value = value[:max_items]
        return dcc.Loading(
            dmc.ScrollArea(
                dmc.CheckboxGroup(
                    [cls.checkbox(val, options_labels) for val in value] + cls.more_text(max_items, len(value)),
                    py="0.25rem",
                    id=cls.ids.checklist(**id_data, side=side),
                ),
                style={"height": list_height},
                px="0.25rem",
            ),
            custom_spinner=dmc.Loader(),
            delay_show=500,
        )

    @classmethod
    def search_input(cls, id_data: dict, side: Literal["left", "right"], **kwargs):
        """List search input.

        :param id_data: dict to put in the id
        :param side: list side
        :param **kwargs: kwargs to pass to the TextInput
        """
        return dmc.TextInput(
            styles={
                "root": {"flex": 1},
                "input": {
                    "borderTop": "none",
                    "borderLeft": "none",
                    "borderRight": "none",
                },
            },
            radius=0,
            id=cls.ids.search(**id_data, side=side),
            debounce=250,
            **kwargs,
        )

    @classmethod
    def transfer_all(cls, id_data: dict, side: Literal["left", "right"]):
        """Transfer all button.

        :param id_data: dict to put in the id
        :param side: list side
        """
        icon_side = "left" if side == "right" else "right"
        return dmc.Tooltip(
            dmc.Paper(
                dmc.UnstyledButton(
                    DashIconify(icon=f"uiw:d-arrow-{icon_side}", height=12),
                    style={"height": 34, "width": 34, "display": "grid", "placeContent": "center"},
                    id=cls.ids.transfer_all(**id_data, side=side),
                ),
                withBorder=True,
                radius=0,
                h="100%",
                style={
                    "borderTop": "none",
                    "borderLeft": "none",
                    "borderRight": "none",
                },
            ),
            label="Transfer all",
            id=cls.ids.transfer_all_tooltip(**id_data, side=side),
        )

    @classmethod
    def transfer(cls, id_data: dict, side: Literal["left", "right"], show_transfer_all: bool):
        """Transfer button.

        :param id_data: dict to put in the id
        :param side: list side
        :param show_transfer_all: whether the transfer all button is visible (impacts border style)
        """
        icon_side = "left" if side == "right" else "right"
        return dmc.Tooltip(
            dmc.Paper(
                dmc.UnstyledButton(
                    DashIconify(icon=f"uiw:{icon_side}", height=12),
                    style={"height": 34, "width": 34, "display": "grid", "placeContent": "center"},
                    id=cls.ids.transfer(**id_data, side=side),
                ),
                withBorder=True,
                radius=0,
                h="100%",
                style={"borderTop": "none"}
                | ({"borderRight": "none"} if not show_transfer_all and side == "right" else {})
                | ({"borderLeft": "none"} if not show_transfer_all and side == "left" else {}),
            ),
            label="Transfer selected",
            id=cls.ids.transfer_tooltip(**id_data, side=side),
        )

    @classmethod
    def more_text(cls, max_items: int, data_length: int):
        """Text to display when there are more items than max_items."""
        if not max_items or data_length < max_items:
            return []

        return [
            dmc.Text(
                _("Showing first {max_items} items, refine your search for more...").format(max_items=max_items),
                size="xs",
                c="dimmed",
                p="0.25rem 0.5rem",
                pos="sticky",
                bottom=0,
                bg="var(--mantine-color-body)",
            ),
        ]


@callback(
    Output(TransferListField.ids.checklist(MATCH, MATCH, MATCH, MATCH, "", MATCH), "children"),
    Output(TransferListField.ids.checklist(MATCH, MATCH, MATCH, MATCH, "", MATCH), "value"),
    Input(TransferListField.ids.search(MATCH, MATCH, MATCH, MATCH, "", MATCH), "value"),
    State(common_ids.value_field(MATCH, MATCH, MATCH, MATCH, "transferlist"), "value"),
    State(common_ids.value_field(MATCH, MATCH, MATCH, MATCH, "transferlist"), "data-nothingfound"),
    State(common_ids.value_field(MATCH, MATCH, MATCH, MATCH, "transferlist"), "data-placeholder"),
    State(common_ids.value_field(MATCH, MATCH, MATCH, MATCH, "transferlist"), "data-getter"),
    State(common_ids.value_field(MATCH, MATCH, MATCH, MATCH, "transferlist"), "data-maxitems"),
    State(TransferListField.ids.checklist(MATCH, MATCH, MATCH, MATCH, "", MATCH), "value"),
    prevent_initial_call=True,
)
def filter_checklist(  # noqa: PLR0913
    search: str,
    value: list,
    nothing_found: str,
    placeholder: str,
    data_getter: str,
    max_items: int,
    selection: list[str],
):
    """Filter the list on search."""
    if not ctx.triggered_id:
        return no_update, no_update

    if ctx.triggered_id["side"] == "left":
        filtered = TransferListField.get_data(data_getter, value, search=search, max_items=max_items)
    else:
        filtered = [x for x in value if not search or search.lower() in x.lower()]
    children = None
    updated_selection = [s for s in (selection or []) if s in filtered]
    if filtered:
        children = [TransferListField.checkbox(val) for val in filtered]
        children += TransferListField.more_text(max_items, len(filtered))
    elif search and nothing_found:
        children = dmc.Text(json.loads(nothing_found), p="0.5rem", c="dimmed")
    elif not search and placeholder:
        children = dmc.Text(json.loads(placeholder), p="0.5rem", c="dimmed")
    return children, updated_selection


@callback(
    Output(common_ids.value_field(MATCH, MATCH, MATCH, MATCH, "transferlist"), "value"),
    Output(TransferListField.ids.checklist(MATCH, MATCH, MATCH, MATCH, "", ALL), "children", allow_duplicate=True),
    Output(TransferListField.ids.checklist(MATCH, MATCH, MATCH, MATCH, "", ALL), "value", allow_duplicate=True),
    Output(TransferListField.ids.search(MATCH, MATCH, MATCH, MATCH, "", ALL), "value", allow_duplicate=True),
    Input(TransferListField.ids.transfer(MATCH, MATCH, MATCH, MATCH, "", ALL), "n_clicks"),
    Input(TransferListField.ids.transfer_all(MATCH, MATCH, MATCH, MATCH, "", ALL), "n_clicks"),
    State(TransferListField.ids.checklist(MATCH, MATCH, MATCH, MATCH, "", ALL), "value"),
    State(TransferListField.ids.search(MATCH, MATCH, MATCH, MATCH, "", ALL), "value"),
    State(common_ids.value_field(MATCH, MATCH, MATCH, MATCH, "transferlist"), "value"),
    State(common_ids.value_field(MATCH, MATCH, MATCH, MATCH, "transferlist"), "data-placeholder"),
    State(common_ids.value_field(MATCH, MATCH, MATCH, MATCH, "transferlist"), "data-transferallmatchingfilters"),
    State(common_ids.value_field(MATCH, MATCH, MATCH, MATCH, "transferlist"), "data-getter"),
    State(common_ids.value_field(MATCH, MATCH, MATCH, MATCH, "transferlist"), "data-maxitems"),
    prevent_initial_call=True,
)
def transfer_values(  # noqa: PLR0913
    trigger1: tuple[int, int],
    trigger2: tuple[int, int],
    selection: tuple[list[str], list[str]],
    search: tuple[str, str],
    current_value: list[str],
    placeholder: str,
    transfer_matching: str,
    data_getter: str,
    max_items: int,
):
    """Transfer items from one list to the other."""
    if not (ctx.triggered_id and (any(trigger1) or any(trigger2))):
        return no_update

    side = ctx.triggered_id["side"]
    search_ = search[0] if side == "left" else search[1]
    # Transfer selected items when clicking the transfer button
    if ctx.triggered_id["component"] == TransferListField.ids.transfer("", "", "", "", "", "")["component"]:
        transferred = selection[0] if side == "left" else selection[1]
    # Transfer all items when clicking the transfer all button
    elif search_ and json.loads(transfer_matching):
        # Filter out items that don't match the search if transfer_matching is set
        if side == "left":
            transferred = TransferListField.get_data(data_getter, current_value, search=search_, max_items=0)
        else:
            transferred = [x for x in current_value if search_.lower() in x.lower()]
    else:
        transferred = (
            current_value
            if side == "right"
            else TransferListField.get_data(data_getter, current_value, search=None, max_items=max_items)
        )

    if not transferred:
        return no_update

    # Update the value
    new_value = current_value + transferred if side == "left" else [v for v in current_value if v not in transferred]

    data_left = TransferListField.get_data(data_getter, new_value, search=search[0], max_items=max_items)

    # Create the new checkboxes or placeholder texts
    placeholder = json.loads(placeholder)
    new_children = [
        ([TransferListField.checkbox(v) for v in data_left] + TransferListField.more_text(max_items, len(data_left)))
        if data_left
        else dmc.Text(placeholder, p="0.5rem", c="dimmed"),
        [TransferListField.checkbox(v) for v in new_value if not search[1] or search[1].lower() in v.lower()]
        if new_value
        else dmc.Text(placeholder, p="0.5rem", c="dimmed"),
    ]

    return new_value, new_children, [[]] * 2, [no_update] * 2


# Gray out the transfer button when nothing is selected
clientside_callback(
    """(selection, style) => {
        return [{
            ...style,
            color: !!selection.length ? null : "gray",
            cursor: !!selection.length ? "pointer" : "default",
        }, !selection.length]
    }""",
    Output(TransferListField.ids.transfer(MATCH, MATCH, MATCH, MATCH, "", MATCH), "style"),
    Output(TransferListField.ids.transfer_tooltip(MATCH, MATCH, MATCH, MATCH, "", MATCH), "disabled"),
    Input(TransferListField.ids.checklist(MATCH, MATCH, MATCH, MATCH, "", MATCH), "value"),
    State(TransferListField.ids.transfer(MATCH, MATCH, MATCH, MATCH, "", MATCH), "style"),
)


# Gray out the transfer all button when nothing can be transferred
clientside_callback(
    """(filtered, style) => {
        const disabled = !filtered || !filtered.length
        return [{
            ...style,
            color: !disabled ? null : "gray",
            cursor: !disabled ? "pointer" : "default",
        }, disabled]
    }""",
    Output(TransferListField.ids.transfer_all(MATCH, MATCH, MATCH, MATCH, "", MATCH), "style"),
    Output(TransferListField.ids.transfer_all_tooltip(MATCH, MATCH, MATCH, MATCH, "", MATCH), "disabled"),
    Input(TransferListField.ids.checklist(MATCH, MATCH, MATCH, MATCH, "", MATCH), "children"),
    State(TransferListField.ids.transfer_all(MATCH, MATCH, MATCH, MATCH, "", MATCH), "style"),
)

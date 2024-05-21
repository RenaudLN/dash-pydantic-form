import json
from functools import partial
from typing import Literal

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
    no_update,
)
from dash.development.base_component import Component
from dash_iconify import DashIconify
from pydantic import BaseModel, Field
from pydantic.fields import FieldInfo

from dash_pydantic_form import ids as common_ids
from dash_pydantic_form.fields.base_fields import BaseField


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

    full_width = True

    titles: tuple[str, str] | None = Field(default=None, description="List titles.")
    search_placeholder: str | None = Field(default=None, description="Search placeholder.")
    show_transfer_all: bool = Field(default=True, description="Show transfer all button.")
    list_height: int = Field(default=200, description="List rows height in pixels.")
    limit: int | None = Field(default=None, description="Max number of items to display.")
    radius: int | str | None = Field(default=None, description="List border-radius.")
    placeholder: str | None = Field(default=None, description="Placeholder text when no item is available.")
    nothing_found: str | None = Field(default=None, description="Text to display when no item is available.")
    transfer_all_matching_filters: bool = Field(default=True, description="Transfer all when filters match.")
    options_labels: dict | None = Field(default=None, description="Label for the options list.")

    class ids:
        """TransferListField ids."""

        search = partial(side_id, "__trl-search-input")
        transfer = partial(side_id, "__trl-transfer-input")
        transfer_all = partial(side_id, "__trl-transfer-all-input")
        checklist = partial(side_id, "__trl-checklist-input")

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
        value = self.get_value(item, field, parent) or [[], []]
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
                                    id_data, "left", value[0], self.list_height, self.limit, self.options_labels
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
                                self.checklist(
                                    id_data, "right", value[1], self.list_height, self.limit, self.options_labels
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
                # This input holds the actual value as well as some metadata to pass to callbacks
                dmc.JsonInput(
                    id=common_ids.value_field(**(id_data | {"meta": "transferlist"})),
                    style={"display": "none"},
                    value=value,
                    **{
                        "data-placeholder": json.dumps(self.placeholder),
                        "data-nothingfound": json.dumps(self.nothing_found),
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
        limit: int = None,
        options_labels: dict | None = None,
    ):
        """Checklist in a scrollarea for each list of the transfer.

        :param id_data: dict to put in the id
        :param side: list side
        :param value: list value, list of dicts with keys label and value
        :param list_height: height of the checklist
        :param limit: limit the number of items displayed in the checklist
        """
        if limit:
            value = value[:limit]
        return dmc.ScrollArea(
            dmc.CheckboxGroup(
                [cls.checkbox(val, options_labels) for val in value],
                py="0.25rem",
                id=cls.ids.checklist(**id_data, side=side),
            ),
            style={"height": list_height},
            px="0.25rem",
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
        return dmc.Paper(
            dmc.UnstyledButton(
                DashIconify(icon=f"uiw:d-arrow-{icon_side}", height=12),
                style={"height": 34, "width": 34, "display": "grid", "placeContent": "center"},
                id=cls.ids.transfer_all(**id_data, side=side),
            ),
            withBorder=True,
            radius=0,
            style={
                "borderTop": "none",
                "borderLeft": "none",
                "borderRight": "none",
            },
        )

    @classmethod
    def transfer(cls, id_data: dict, side: Literal["left", "right"], show_transfer_all: bool):
        """Transfer button.

        :param id_data: dict to put in the id
        :param side: list side
        :param show_transfer_all: whether the transfer all button is visible (impacts border style)
        """
        icon_side = "left" if side == "right" else "right"
        return dmc.Paper(
            dmc.UnstyledButton(
                DashIconify(icon=f"uiw:{icon_side}", height=12),
                style={"height": 34, "width": 34, "display": "grid", "placeContent": "center"},
                id=cls.ids.transfer(**id_data, side=side),
            ),
            withBorder=True,
            radius=0,
            style={"borderTop": "none"}
            | ({"borderRight": "none"} if not show_transfer_all and side == "right" else {})
            | ({"borderLeft": "none"} if not show_transfer_all and side == "left" else {}),
        )


@callback(
    Output(TransferListField.ids.checklist(MATCH, MATCH, MATCH, MATCH, "", MATCH), "children"),
    Output(TransferListField.ids.checklist(MATCH, MATCH, MATCH, MATCH, "", MATCH), "value"),
    Input(TransferListField.ids.search(MATCH, MATCH, MATCH, MATCH, "", MATCH), "value"),
    State(common_ids.value_field(MATCH, MATCH, MATCH, MATCH, "transferlist"), "value"),
    State(common_ids.value_field(MATCH, MATCH, MATCH, MATCH, "transferlist"), "data-nothingfound"),
    State(common_ids.value_field(MATCH, MATCH, MATCH, MATCH, "transferlist"), "data-placeholder"),
    State(TransferListField.ids.checklist(MATCH, MATCH, MATCH, MATCH, "", MATCH), "value"),
    prevent_initial_call=True,
)
def filter_checklist(
    search: str,
    values: list[list[dict]],
    nothing_found: str,
    placeholder: str,
    selection: list[str],
):
    """Filter the list on search."""
    if not ctx.triggered_id:
        return no_update, no_update

    value = values[0] if ctx.triggered_id["side"] == "left" else values[1]
    filtered = [v for v in value if not search or search.lower() in v["label"].lower()]
    children = None
    filtered_values = [f["value"] for f in filtered]
    updated_selection = [s for s in (selection or []) if s in filtered_values]
    if filtered:
        children = [TransferListField.checkbox(val) for val in filtered]
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
    prevent_initial_call=True,
)
def transfer_values(  # noqa: PLR0913
    trigger1: list[int],
    trigger2: list[int],
    selection: list[list[str]],
    search: list[str],
    current_value: list[list[dict]],
    placeholder: str,
    transfer_matching: str,
):
    """Transfer items from one list to the other."""
    if not (ctx.triggered_id and (any(trigger1) or any(trigger2))):
        return no_update, no_update, no_update, no_update

    side = ctx.triggered_id["side"]
    # Transfer selected items when clicking the transfer button
    if ctx.triggered_id["component"] == TransferListField.ids.transfer("", "", "", "", "", "")["component"]:
        transferred = selection[0] if side == "left" else selection[1]
    # Transfer all items when clicking the transfer all button
    elif json.loads(transfer_matching):
        # Filter out items that don't match the search if transfer_matching is set
        search_ = search[0 if side == "left" else 1]
        transferred = [
            v["value"]
            for v in current_value[0 if side == "left" else 1]
            if not search_ or search_.lower() in v["label"].lower()
        ]
    else:
        transferred = [v["value"] for v in current_value[0 if side == "left" else 1]]

    if not transferred:
        return no_update, [no_update] * 2, [no_update] * 2, [no_update] * 2

    # Update the value
    if side == "left":
        new_value = [
            [v for v in current_value[0] if v["value"] not in transferred],
            current_value[1] + [v for v in current_value[0] if v["value"] in transferred],
        ]
    else:
        new_value = [
            current_value[0] + [v for v in current_value[1] if v["value"] in transferred],
            [v for v in current_value[1] if v["value"] not in transferred],
        ]

    # Create the new checkboxes or placeholder texts
    placeholder = json.loads(placeholder)
    new_children = [
        [TransferListField.checkbox(v) for v in new_value[0]]
        if new_value[0]
        else dmc.Text(placeholder, p="0.5rem", c="dimmed"),
        [TransferListField.checkbox(v) for v in new_value[1]]
        if new_value[1]
        else dmc.Text(placeholder, p="0.5rem", c="dimmed"),
    ]

    return new_value, new_children, [[]] * 2, [""] * 2


# Gray out the transfer button when nothing is selected
clientside_callback(
    """(selection, style) => {
        return {
            ...style,
            color: !!selection.length ? null : "gray",
            cursor: !!selection.length ? "pointer" : "default",
        }
    }""",
    Output(TransferListField.ids.transfer(MATCH, MATCH, MATCH, MATCH, "", MATCH), "style"),
    Input(TransferListField.ids.checklist(MATCH, MATCH, MATCH, MATCH, "", MATCH), "value"),
    State(TransferListField.ids.transfer(MATCH, MATCH, MATCH, MATCH, "", MATCH), "style"),
)


# Gray out the transfer all button when nothing can be transferred
clientside_callback(
    """(filtered, style) => {
        const disabled = !filtered || !filtered.length
        return {
            ...style,
            color: !disabled ? null : "gray",
            cursor: !disabled ? "pointer" : "default",
        }
    }""",
    Output(TransferListField.ids.transfer_all(MATCH, MATCH, MATCH, MATCH, "", MATCH), "style"),
    Input(TransferListField.ids.checklist(MATCH, MATCH, MATCH, MATCH, "", MATCH), "children"),
    State(TransferListField.ids.transfer_all(MATCH, MATCH, MATCH, MATCH, "", MATCH), "style"),
)

from __future__ import annotations

import json
from datetime import date
from typing import Literal

import dash_mantine_components as dmc
from dash import Dash, Input, Output, State, _dash_renderer, callback, clientside_callback, html
from dash.development.base_component import Component
from dash_iconify import DashIconify
from pydantic import BaseModel, Field, ValidationError

from dash_pydantic_form import FormLayout, ModelForm, fields, ids
from dash_pydantic_form.utils import SEP, get_model_cls

_dash_renderer._set_react_version("18.2.0")

NODE_WIDTH = 64
NODE_HEIGHT = 32
LINK_WIDTH = 24
LINK_RADIUS = 6
LINK_COLOR = "color-mix(in srgb, var(--mantine-color-body), var(--mantine-color-text) 40%)"
NODE_COLOR = "color-mix(in srgb, var(--mantine-color-body), var(--mantine-color-text) 15%)"


class TreeFormLayout(FormLayout):
    """Tree form layout."""

    layout: Literal["tree"] = "tree"

    def render(  # noqa: PLR0913
        self,
        *,
        field_inputs: dict[str, Component],
        aio_id: str,
        form_id: str,
        path: str,
        read_only: bool,
        **_kwargs,
    ) -> list[Component]:  # noqa: ARG002
        """Render the form layout."""
        parts = path.split(":")
        if len(parts) < 2:  # noqa: PLR2004
            base = self.grid(list(field_inputs.values()))
            if "children" in field_inputs:
                return [
                    base,
                    dmc.ActionIcon(
                        DashIconify(icon="carbon:add"),
                        ml=-13,
                        mt="-0.5rem",
                        id=fields.List.ids.add(aio_id, form_id, "children", parent=path),
                    ),
                ]
            return [base]
        parent = ":".join(parts[:-2])
        field = parts[-2]
        index = parts[-1]
        popover = dmc.Menu(
            [
                dmc.MenuTarget(
                    dmc.Group(
                        [
                            dmc.Text(
                                "-",
                                id=fields.List.ids.accordion_parent_text(aio_id, form_id, "", parent=path),
                                size="xs",
                                style={"whiteSpace": "nowrap", "overflow": "hidden", "textOverflow": "ellipsis"},
                                maw="calc(100% - 0.25rem)",
                            ),
                            *(
                                [
                                    html.Div(
                                        DashIconify(icon="carbon:close", height=16, color="#fff"),
                                        id=fields.List.ids.delete(aio_id, form_id, field, parent=parent, meta=index),
                                        className="hover-visible",
                                        style={
                                            "borderRadius": "50%",
                                            "position": "absolute",
                                            "height": "1rem",
                                            "width": "1rem",
                                            "top": "-0.2875rem",
                                            "right": "-0.375rem",
                                            "backgroundColor": "var(--mantine-color-red-filled)",
                                            "cursor": "pointer",
                                            "display": "grid",
                                            "placeContent": "center",
                                        },
                                    ),
                                ]
                                if not read_only
                                else []
                            ),
                        ],
                        h=NODE_HEIGHT,
                        w=NODE_WIDTH,
                        px="0.25rem",
                        justify="center",
                        bg=NODE_COLOR,
                        style={"borderRadius": "0.375rem", "cursor": "pointer"},
                        pos="relative",
                    ),
                ),
                dmc.MenuDropdown(
                    dmc.Stack([inp for f, inp in field_inputs.items() if f != "children"], gap="0.5rem"),
                    p="0.375rem 1rem 0.75rem",
                ),
            ],
            position="bottom",
            shadow="md",
            withArrow=True,
            offset=4,
        )
        content = [
            dmc.Group(
                [
                    dmc.Box(
                        h=LINK_RADIUS,
                        w=LINK_WIDTH,
                        style={
                            "borderLeft": f"2px solid {LINK_COLOR}",
                            "borderBottom": f"2px solid {LINK_COLOR}",
                            "borderRadius": f"0 0 0 {LINK_RADIUS}px",
                            "translate": f"0 -{LINK_RADIUS / 2:.0f}px",
                        },
                    ),
                    popover,
                ],
                ml=-LINK_WIDTH - 2,
                mr=-2,
                gap=0,
            )
        ]
        if "children" in field_inputs:
            content[0].children.append(
                dmc.Box(
                    h=LINK_RADIUS,
                    w=LINK_WIDTH,
                    style={
                        "borderRight": f"2px solid {LINK_COLOR}",
                        "borderTop": f"2px solid {LINK_COLOR}",
                        "borderRadius": f"0 {LINK_RADIUS}px 0 0",
                        "translate": f"0 {LINK_RADIUS / 2:.0f}px",
                    },
                ),
            )
            content.append(
                dmc.Group(
                    field_inputs["children"],
                    mt=LINK_RADIUS + max(LINK_RADIUS, NODE_HEIGHT // 2),
                ),
            )
            content.append(
                dmc.ActionIcon(
                    DashIconify(icon="carbon:add"),
                    pos="absolute",
                    left=NODE_HEIGHT + LINK_WIDTH + 15,
                    bottom=0,
                    id=fields.List.ids.add(aio_id, form_id, "children", parent=path),
                )
            )

        return [
            dmc.Group(
                content,
                gap=0,
                align="start",
                pos="relative",
                pb="1.5rem" if "children" in field_inputs else 0,
            )
        ]


node_repr_kwargs = {
    "form_layout": TreeFormLayout(),
    "render_type": "list",
    "items_deletable": False,
    "items_creatable": False,
    "wrapper_kwargs": {
        "gap": "0.5rem",
        "style": {"borderLeft": f"2px solid {LINK_COLOR}"},
        "pl": LINK_WIDTH,
        "mih": "2rem",
        "className": "node-wrapper",
    },
}


class Node(BaseModel):  # noqa: D101
    name: str = None
    field_a: date = None
    children: list[Node1] = Field(
        title="",
        default_factory=list,
        repr_kwargs=node_repr_kwargs,
    )


class Node1(BaseModel):  # noqa: D101
    name: str = None
    meta_1: str = None
    meta_2: float = None
    children: list[Node2] = Field(
        title="",
        default_factory=list,
        repr_kwargs=node_repr_kwargs,
    )


class Node2(BaseModel):  # noqa: D101
    name: str = None


class Tree(BaseModel):  # noqa: D101
    name: str
    children: list[Node] = Field(
        title="Components",
        default_factory=list,
        repr_kwargs=node_repr_kwargs,
    )


app = Dash(__name__, external_stylesheets=dmc.styles.ALL)
server = app.server

AIO_ID = "aio"
FORM_ID = "form"

form = ModelForm(
    Tree,
    aio_id=AIO_ID,
    form_id=FORM_ID,
    store_progress="session",
    restore_behavior="auto",
    form_layout=TreeFormLayout(),
    # read_only=True,
    container_kwargs={"style": {"paddingInline": "2rem"}},
)

app.layout = app.layout = dmc.MantineProvider(
    id="mantine-provider",
    defaultColorScheme="auto",
    children=dmc.AppShell(
        [
            dmc.NotificationProvider(),
            dmc.AppShellMain(
                dmc.Container(
                    [
                        dmc.Group(
                            [
                                dmc.Title("Tree form", order=3),
                                dmc.Switch(
                                    offLabel=DashIconify(icon="radix-icons:moon", height=18),
                                    onLabel=DashIconify(icon="radix-icons:sun", height=18),
                                    size="md",
                                    color="yellow",
                                    persistence=True,
                                    checked=True,
                                    id="scheme-switch",
                                ),
                            ],
                            align="center",
                            justify="space-between",
                            mb="1rem",
                        ),
                        form,
                    ],
                    pt="1rem",
                ),
            ),
            dmc.AppShellAside(
                dmc.ScrollArea(
                    dmc.Text(
                        id=ids.form_dependent_id("output", AIO_ID, FORM_ID),
                        style={"whiteSpace": "pre-wrap"},
                        p="1rem 0.5rem",
                    ),
                ),
            ),
        ],
        aside={"width": 350},
    ),
)


@callback(
    Output(ids.form_dependent_id("output", AIO_ID, FORM_ID), "children"),
    Output(form.ids.errors, "data"),
    Input(form.ids.main, "data"),
    State(form.ids.model_store, "data"),
    prevent_initial_call=True,
)
def display(form_data, model_name):
    """Display form data."""
    children = dmc.Stack(
        [
            dmc.Text("Form data", mb="-0.5rem", fw=600),
            dmc.Code(
                json.dumps(form_data, indent=2),
            ),
        ]
    )
    errors = None
    try:
        model_cls = get_model_cls(model_name)
        item = model_cls.model_validate(form_data)
        children.children[1].children = item.model_dump_json(indent=2)
    except ValidationError as e:
        children.children.extend(
            [
                dmc.Text("Validation errors", mb="-0.5rem", fw=500, c="red"),
                dmc.List(
                    [
                        dmc.ListItem(
                            [SEP.join([str(x) for x in error["loc"]]), f" : {error['msg']}, got {error['input']}"],
                        )
                        for error in e.errors()
                    ],
                    size="sm",
                    c="red",
                ),
            ]
        )
        errors = None
        errors = {SEP.join([str(x) for x in error["loc"]]): error["msg"] for error in e.errors()}

    return children, errors


clientside_callback(
    """(isLightMode) => isLightMode ? 'light' : 'dark'""",
    Output("mantine-provider", "forceColorScheme"),
    Input("scheme-switch", "checked"),
    prevent_initial_callback=True,
)

if __name__ == "__main__":
    app.run_server(debug=True)

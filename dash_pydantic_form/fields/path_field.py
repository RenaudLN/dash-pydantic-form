import math
import re
from functools import partial
from typing import Literal

import dash_mantine_components as dmc
import fsspec
from dash import ALL, MATCH, ClientsideFunction, Input, Output, State, callback, clientside_callback, ctx, dcc, html
from dash.development.base_component import Component
from dash_iconify import DashIconify
from pydantic import BaseModel
from pydantic.fields import FieldInfo

from dash_pydantic_form.fields.base_fields import BaseField
from dash_pydantic_form.ids import field_dependent_id, value_field

PathType = Literal["file", "directory", "glob"]


class PathField(BaseField):
    """Path field."""

    path_type: PathType = "file"
    backend: str
    prefix: str = ""
    with_copy_button: bool = True
    modal_max_width: int = 800
    value_includes_prefix: bool = False
    page_size: int = 20

    class ids(BaseField.ids):  # pylint: disable = invalid-name
        """Model list field ids."""

        modal = partial(field_dependent_id, "_firestore-path-field-modal")
        modal_btn = partial(field_dependent_id, "_firestore-path-field-modal-btn")
        filetree = partial(field_dependent_id, "_firestore-path-field-filetree")
        config = partial(field_dependent_id, "_firestore-path-field-config")
        prefix = partial(field_dependent_id, "_firestore-path-field-prefix")
        glob = partial(field_dependent_id, "_firestore-path-field-glob")
        pagination = partial(field_dependent_id, "_firestore-path-field-pagination")
        pagination_store = partial(field_dependent_id, "_firestore-path-field-pagination-store")
        nav = lambda aio_id, form_id, field, parent, meta, path: field_dependent_id(  # noqa: E731
            "_firestore-path-field-nav", aio_id, form_id, field, parent, meta
        ) | {"path": path}
        checkbox = lambda aio_id, form_id, field, parent, meta, path: field_dependent_id(  # noqa: E731
            "_firestore-path-field-checkbox", aio_id, form_id, field, parent, meta
        ) | {"path": path}

    def fs(self) -> fsspec.AbstractFileSystem:
        """Get the filesystem."""
        return fsspec.filesystem(self.backend)

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
        """Create a form field of type image to interact with the model field."""
        value = self.get_value(item, field, parent)

        inputs = [
            dmc.Button(
                value or dmc.Text(f"Click to select a {self.path_type}", size="xs", fs="italic"),
                size="sm",
                id=self.ids.modal_btn(aio_id, form_id, field, parent),
                variant="outline",
                color="dimmed",
                styles={
                    "inner": {"justifyContent": "start"},
                    "label": {"fontWeight": "normal"},
                    "root": {
                        "borderRadius": "0 0.25rem 0.25rem 0",
                        "border": "1px solid var(--mantine-color-default-border)",
                    },
                },
                px="0.5rem",
                flex=1,
            ),
        ]
        if self.path_type == "glob":
            if value:
                base_path_match = re.findall("^([^*]*)\/.*\*", value)
                if not base_path_match:
                    raise ValueError("Invalid glob pattern.")

                base_path = base_path_match[0]
                glob = value[len(base_path) :]
            else:
                base_path = None
                glob = ""

            if not value:
                inputs[0].children.children = "Click to select a directory"
            inputs[0].styles["root"]["borderRadius"] = 0

            inputs += [
                dmc.TextInput(
                    value=glob,
                    size="sm",
                    id=self.ids.glob(aio_id, form_id, field, parent),
                    styles={"input": {"borderRadius": "0 0.25rem 0.25rem 0"}},
                    debounce=350,
                    placeholder="Enter glob pattern",
                    flex=1,
                    ml=-1,
                ),
            ]

        title = self.get_title(field_info, field_name=field)
        description = self.get_description(field_info)

        return dmc.Stack(
            (title is not None)
            * [
                dmc.Text(
                    [title]
                    + [
                        html.Span(" *", style={"color": "var(--input-asterisk-color, var(--mantine-color-error))"}),
                    ]
                    * self.is_required(field_info),
                    size="sm",
                    mt=3,
                    mb=5,
                    fw=500,
                    lh=1.55,
                )
            ]
            + (title is not None and description is not None)
            * [dmc.Text(description, size="xs", c="dimmed", mt=-5, mb=5, lh=1.2)]
            + [self._base_group(value, inputs, (aio_id, form_id, field, parent))],
            gap=0,
        )

    def _base_group(self, value, inputs: list, id_args: tuple) -> Component:
        prefix = self.prefix.rstrip("/") + "/"
        return dmc.Group(
            [
                dmc.Menu(
                    [
                        dmc.MenuTarget(
                            dmc.Paper(
                                prefix,
                                fz="sm",
                                h="2.25rem",
                                lh="2rem",
                                bg="var(--mantine-color-default)",
                                withBorder=True,
                                style={
                                    "borderRadius": "0.25rem 0 0 0.25rem",
                                    "borderRight": "none",
                                    "maxWidth": "10rem",
                                    "overflow": "hidden",
                                    "textOverflow": "ellipsis",
                                    "whiteSpace": "nowrap",
                                },
                                px="0.75rem",
                            ),
                            boxWrapperProps={"h": "100%"},
                        ),
                        dmc.MenuDropdown(dmc.Text(self.prefix + "/", size="sm", p="0.25rem 0.5rem")),
                    ],
                    trigger="hover",
                    position="bottom-start",
                    shadow="md",
                ),
                *inputs,
                dmc.Text(
                    dcc.Clipboard(target_id=value_field(*id_args), className="hover-clipboard"),
                    ml="0.5rem",
                    display=None if self.with_copy_button else "none",
                    flex=0,
                ),
                dmc.TextInput(
                    id=value_field(*id_args),
                    display="none",
                    value=value,
                ),
                dmc.Modal(
                    id=self.ids.modal(*id_args),
                    title=f"Select a {self.path_type if self.path_type != 'glob' else 'directory'}",
                    size=f"min({self.modal_max_width}px, 100vw - 4rem)",
                ),
                dcc.Store(
                    id=self.ids.config(*id_args),
                    data={
                        "path_type": self.path_type,
                        "backend": self.backend,
                        "prefix": prefix,
                        "value_includes_prefix": self.value_includes_prefix,
                        "page_size": self.page_size,
                    },
                ),
            ],
            # TODO
            style={"&>div:first-child": {"flex": "0 0 100px"}, "&>*": {"flex": "1 1 37%"}},
            gap=0,
            wrap="nowrap",
        )

    @staticmethod
    def _get_subpath(prefix: str, value: str | None, val, rm_value: bool = False, safe: bool = False):
        subpath = val[len(prefix.split("://")[-1]) :]
        if rm_value and value:
            subpath = subpath.removeprefix(value).lstrip("/")
        if safe:
            subpath = subpath.replace(".", "||")

        return subpath

    @staticmethod
    def _base_button(children, icon: DashIconify = None, **kwargs):
        return dmc.Button(
            children,
            size="compact-sm",
            color="gray",
            variant="subtle",
            leftSection=icon,
            styles={"inner": {"justifyContent": "start"}, "label": {"fontWeight": "normal"}},
            **kwargs,
        )

    @staticmethod
    def _file_group(val):
        return dmc.Group(
            [DashIconify(icon="flat-color-icons:file", height=16), dmc.Text(val, size="sm")],
            gap="xs",
        )

    @staticmethod
    def _selectable_group(checkbox_id: dict, button: dmc.Button = None, label=None):
        return dmc.Group(
            [
                dmc.Checkbox(
                    id=checkbox_id,
                    label=label,
                    size="sm",
                    style={"--checkbox-size": "1rem"},
                    pl=6.333,
                    styles={
                        "body": {"alignItems": "center"},
                        "label": {"paddingLeft": "0.625rem", "cursor": "pointer"},
                    },
                )
            ]
            + ([button] if button is not None else []),
            gap="0.625rem",
        )


# dmc.Skeleton
clientside_callback(
    ClientsideFunction(namespace="pydf", function_name="showPathFieldSkeletons"),
    Output(PathField.ids.modal(MATCH, MATCH, MATCH, MATCH, MATCH), "opened"),
    Output(PathField.ids.modal(MATCH, MATCH, MATCH, MATCH, MATCH), "children"),
    Input(PathField.ids.modal_btn(MATCH, MATCH, MATCH, MATCH, MATCH), "n_clicks"),
)


@callback(
    Output(PathField.ids.filetree(MATCH, MATCH, MATCH, MATCH, MATCH), "children"),
    Input(PathField.ids.filetree(MATCH, MATCH, MATCH, MATCH, MATCH), "id"),
    Input(PathField.ids.nav(MATCH, MATCH, MATCH, MATCH, MATCH, ALL), "n_clicks"),
    Input(PathField.ids.pagination(MATCH, MATCH, MATCH, MATCH, ALL), "value"),
    State(value_field(MATCH, MATCH, MATCH, MATCH, MATCH), "value"),
    State(PathField.ids.config(MATCH, MATCH, MATCH, MATCH, MATCH), "data"),
    State(PathField.ids.pagination_store(MATCH, MATCH, MATCH, MATCH, ALL), "data"),
)
def update_filetree(  # noqa: PLR0913
    id_, _navs, page, value, config, pagination_value
):
    """Update the file tree."""
    fs = fsspec.filesystem(config["backend"])
    path_type = config["path_type"]
    prefix = config["prefix"]
    id_parts = (id_["aio_id"], id_["form_id"], id_["field"], id_["parent"], id_["meta"])
    value = (value or "").removeprefix(prefix)
    page = page[0] if page else 1
    pagination_value = pagination_value[0] if pagination_value else value

    if ctx.triggered_id and isinstance(ctx.triggered_id, dict):
        if "nav" in ctx.triggered_id["component"]:
            value = ctx.triggered_id["path"].replace("||", ".")
            page = 1
        else:
            value = pagination_value
    elif path_type == "glob":
        base_path_match = re.findall("^([^*]*)\/.*\*", value)
        value = "" if not base_path_match else base_path_match[0]

    # This happens when the modal first opens after clicking on the button
    # in this case, we want to show the content one level up.
    if not ctx.triggered_id:
        value = value.rsplit("/", maxsplit=1)[0]

    if path_type == "glob":
        path_type = "directory"

    vals = fs.ls(f"{prefix.rstrip('/')}/{(value or '').lstrip('/')}", detail=True)

    filtered_vals = [
        v
        for v in vals
        if ((path_type == "file") or (v["type"] != "file"))
        and PathField._get_subpath(prefix, value, v["name"]) != value
    ]
    parts = value.split("/")
    page_size = config.get("page_size", 20)
    return (
        [
            dmc.Group(
                [
                    dmc.Breadcrumbs(
                        [
                            PathField._base_button(
                                DashIconify(icon="flat-color-icons:opened-folder", height=16),
                                id=PathField.ids.nav(*id_parts, ""),
                            )
                        ]
                        + (
                            [
                                PathField._base_button(
                                    part,
                                    id=PathField.ids.nav(*id_parts, "/".join(parts[: i + 1]).replace(".", "||")),
                                )
                                for i, part in enumerate(parts)
                            ]
                            if value
                            else []
                        ),
                        separator="/",
                        separatorMargin="0.125rem",
                        ml=-3,
                    ),
                    dmc.Text("/", c="dimmed", lh=1),
                ],
                gap="0.125rem",
                pb="0.5rem",
                mb="0.5rem",
                pos="sticky",
                top="3.75rem",
                bg="var(--mantine-color-body)",
                style={
                    "zIndex": 1,
                    "borderBottom": "1px solid color-mix(in srgb, var(--mantine-color-default-border), #0000 50%)",
                },
                w="100%",
            ),
        ]
        + [
            PathField._base_button(
                PathField._get_subpath(prefix, value, v["name"], rm_value=True),
                icon=DashIconify(icon="flat-color-icons:folder", height=16),
                id=PathField.ids.nav(*id_parts, PathField._get_subpath(prefix, value, v["name"], safe=True)),
            )
            if v["type"] != path_type
            else PathField._selectable_group(
                PathField.ids.checkbox(*id_parts, PathField._get_subpath(prefix, value, v["name"], safe=True)),
                **{
                    "button": PathField._base_button(
                        PathField._get_subpath(prefix, value, v["name"], True),
                        icon=DashIconify(icon="flat-color-icons:folder", height=16),
                        id=PathField.ids.nav(*id_parts, PathField._get_subpath(prefix, value, v["name"], safe=True)),
                    )
                    if v["type"] == "directory"
                    else None,
                    "label": None
                    if v["type"] == "directory"
                    else PathField._file_group(PathField._get_subpath(prefix, value, v["name"], True)),
                },
            )
            for v in filtered_vals[page_size * (page - 1) : page_size * page]
        ]
        + (
            [
                dmc.Pagination(
                    total=math.ceil(len(filtered_vals) / page_size),
                    value=page,
                    id=PathField.ids.pagination(*id_parts),
                    mt="1rem",
                    size="sm",
                    boundaries=2,
                    siblings=2,
                ),
                dcc.Store(data=value, id=PathField.ids.pagination_store(*id_parts)),
            ]
            if len(filtered_vals) > page_size
            else []
        )
        + (
            [
                dmc.Checkbox(
                    id=PathField.ids.checkbox(*id_parts, value.replace(".", "||")),
                    label=f"Select {path_type}",
                )
            ]
            if len(filtered_vals) == 0
            else []
        )
    )


clientside_callback(
    ClientsideFunction(namespace="pydf", function_name="updatePathFieldValue"),
    Output(PathField.ids.modal(MATCH, MATCH, MATCH, MATCH, MATCH), "opened", allow_duplicate=True),
    Output(value_field(MATCH, MATCH, MATCH, MATCH, MATCH), "value", allow_duplicate=True),
    Output(PathField.ids.modal_btn(MATCH, MATCH, MATCH, MATCH, MATCH), "children"),
    Input(PathField.ids.checkbox(MATCH, MATCH, MATCH, MATCH, MATCH, ALL), "checked"),
    Input(PathField.ids.glob(MATCH, MATCH, MATCH, MATCH, ALL), "value"),
    State(PathField.ids.config(MATCH, MATCH, MATCH, MATCH, MATCH), "data"),
    State(PathField.ids.modal_btn(MATCH, MATCH, MATCH, MATCH, MATCH), "children"),
    prevent_initial_call=True,
)

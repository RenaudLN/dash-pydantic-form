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
from dash_pydantic_form.i18n import _
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

        modal = partial(field_dependent_id, "_pydf-path-field-modal")
        modal_btn = partial(field_dependent_id, "_pydf-path-field-modal-btn")
        modal_btn_text = partial(field_dependent_id, "_pydf-path-field-modal-btn-text")
        filetree = partial(field_dependent_id, "_pydf-path-field-filetree")
        config = partial(field_dependent_id, "_pydf-path-field-config")
        prefix = partial(field_dependent_id, "_pydf-path-field-prefix")
        glob = partial(field_dependent_id, "_pydf-path-field-glob")
        pagination = partial(field_dependent_id, "_pydf-path-field-pagination")
        pagination_store = partial(field_dependent_id, "_pydf-path-field-pagination-store")
        filter = partial(field_dependent_id, "_pydf-path-field-filter")
        nav = lambda aio_id, form_id, field, parent, meta, path: field_dependent_id(  # noqa: E731
            "_pydf-path-field-nav", aio_id, form_id, field, parent, meta
        ) | {"path": path}
        checkbox = lambda aio_id, form_id, field, parent, meta, path: field_dependent_id(  # noqa: E731
            "_pydf-path-field-checkbox", aio_id, form_id, field, parent, meta
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
        if self.read_only:
            return self._render_read_only(value, field, field_info)

        inputs = [
            dmc.Button(
                dmc.ScrollArea(
                    value
                    or dmc.Text(
                        _("Click to select a {path_type}").format(path_type=_(self.path_type)),
                        size="xs",
                        fs="italic",
                    ),
                    id=self.ids.modal_btn_text(aio_id, form_id, field, parent),
                    offsetScrollbars=True,
                    scrollbars="x",
                    scrollbarSize="0.25rem",
                    mb="-0.125rem",
                ),
                size="sm",
                id=self.ids.modal_btn(aio_id, form_id, field, parent),
                variant="outline",
                color="dimmed",
                styles={
                    "inner": {"justifyContent": "start"},
                    "label": {"fontWeight": "normal"},
                    "root": {
                        "borderRadius": "0.25rem",
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
                inputs[0].children.children = _("Click to select a directory")
            inputs[0].styles["root"]["borderRadius"] = "0.25rem 0 0 0.25rem"

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
                    title=_("Select a {path_type}").format(
                        path_type=_(self.path_type if self.path_type != "glob" else "directory")
                    ),
                    size=f"min({self.modal_max_width}px, 100vw - 4rem)",
                    styles={"header": {"paddingTop": "0.75rem", "paddingBottom": "0.25rem", "minHeight": "2.75rem"}},
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
            gap=0,
            wrap="nowrap",
        )

    @staticmethod
    def _get_subpath(prefix: str, value: str | None, val: str, rm_value: bool = False, safe: bool = False):
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

    @classmethod
    def _breadcrumbs_group(  # noqa: PLR0913
        cls, prefix: str, value: str, id_parts: list[str], parts: list[str], current_filter: str | None
    ):
        return dmc.Group(
            [
                dmc.Breadcrumbs(
                    [
                        dmc.Tooltip(
                            cls._base_button(
                                DashIconify(icon="flat-color-icons:opened-folder", height=16),
                                id=cls.ids.nav(*id_parts[:-1], path="", meta="breadcrumbs"),
                            ),
                            label=prefix.rstrip("/"),
                        ),
                    ]
                    + (
                        [
                            cls._base_button(
                                part,
                                id=cls.ids.nav(
                                    *id_parts[:-1], path="/".join(parts[: i + 1]).replace(".", "||"), meta="breadcrumbs"
                                ),
                            )
                            for i, part in enumerate(parts)
                        ]
                        if value
                        else []
                    )
                    + [
                        dmc.TextInput(
                            size="xs",
                            placeholder=_("Filter with prefix"),
                            variant="unstyled",
                            id=cls.ids.filter(*id_parts),
                            classNames={"input": "path-field-filter-input"},
                            leftSection=DashIconify(icon="carbon:filter", height=14),
                            debounce=350,
                            value=current_filter,
                        )
                    ],
                    separator="/",
                    separatorMargin="0.125rem",
                    ml=-3,
                ),
            ],
            gap="0.125rem",
            pb="0.5rem",
            mb="0.5rem",
            pos="sticky",
            top="2.75rem",
            bg="var(--mantine-color-body)",
            style={
                "zIndex": 1,
                "borderBottom": "1px solid color-mix(in srgb, var(--mantine-color-default-border), #0000 50%)",
            },
            w="100%",
        )

    @classmethod
    def filetree(  # noqa: PLR0913
        cls,
        *,
        prefix: str,
        value: str,
        id_parts: list[str],
        parts: list[str],
        path_type: PathType,
        filtered_vals: list[dict],
        page_size: int,
        page: int,
        current_filter: str | None = None,
    ):
        """File tree."""
        return [
            cls._breadcrumbs_group(prefix, value, id_parts, parts, current_filter),
            *[
                cls._base_button(
                    cls._get_subpath(prefix, value, v["name"], rm_value=True),
                    icon=DashIconify(icon="flat-color-icons:folder", height=16),
                    id=cls.ids.nav(*id_parts, cls._get_subpath(prefix, value, v["name"], safe=True)),
                )
                if v["type"] != path_type
                else cls._selectable_group(
                    cls.ids.checkbox(*id_parts, cls._get_subpath(prefix, value, v["name"], safe=True)),
                    **{
                        "button": cls._base_button(
                            cls._get_subpath(prefix, value, v["name"], True),
                            icon=DashIconify(icon="flat-color-icons:folder", height=16),
                            id=cls.ids.nav(*id_parts, cls._get_subpath(prefix, value, v["name"], safe=True)),
                        )
                        if v["type"] == "directory"
                        else None,
                        "label": None
                        if v["type"] == "directory"
                        else cls._file_group(cls._get_subpath(prefix, value, v["name"], True)),
                    },
                )
                for v in filtered_vals[page_size * (page - 1) : page_size * page]
            ],
            *(
                [
                    dmc.Pagination(
                        total=math.ceil(len(filtered_vals) / page_size),
                        value=page,
                        id=cls.ids.pagination(*id_parts),
                        mt="0.5rem",
                        size="sm",
                        boundaries=2,
                        siblings=2,
                    ),
                    dcc.Store(data=value, id=cls.ids.pagination_store(*id_parts)),
                ]
                if len(filtered_vals) > page_size
                else []
            ),
            *(
                [
                    dmc.Checkbox(
                        id=PathField.ids.checkbox(*id_parts, value.replace(".", "||")),
                        label=_("Select {path_type}").format(path_type=_(path_type)),
                    )
                ]
                if len(filtered_vals) == 0 and not current_filter
                else []
            ),
            *(
                [dmc.Text(_("No match"), size="sm", c="dimmed", fs="italic", px="0.5rem")]
                if len(filtered_vals) == 0 and current_filter
                else []
            ),
        ]


# dmc.Skeleton
clientside_callback(
    ClientsideFunction(namespace="pydf", function_name="showPathFieldSkeletons"),
    Output(PathField.ids.modal(MATCH, MATCH, MATCH, MATCH, MATCH), "opened"),
    Output(PathField.ids.modal(MATCH, MATCH, MATCH, MATCH, MATCH), "children"),
    Input(PathField.ids.modal_btn(MATCH, MATCH, MATCH, MATCH, MATCH), "n_clicks"),
)


@callback(
    Output(PathField.ids.filetree(MATCH, MATCH, MATCH, MATCH), "children"),
    Input(PathField.ids.filetree(MATCH, MATCH, MATCH, MATCH), "id"),
    Input(PathField.ids.nav(MATCH, MATCH, MATCH, MATCH, ALL, ALL), "n_clicks"),
    Input(PathField.ids.pagination(MATCH, MATCH, MATCH, MATCH, ALL), "value"),
    Input(PathField.ids.filter(MATCH, MATCH, MATCH, MATCH, ALL), "value"),
    State(value_field(MATCH, MATCH, MATCH, MATCH), "value"),
    State(PathField.ids.config(MATCH, MATCH, MATCH, MATCH), "data"),
    State(PathField.ids.pagination_store(MATCH, MATCH, MATCH, MATCH, ALL), "data"),
)
def update_filetree(  # noqa: PLR0913
    id_, _navs, page, filter_str, value, config, pagination_value
):
    """Update the file tree."""
    fs = fsspec.filesystem(config["backend"])
    path_type = config["path_type"]
    prefix = config["prefix"]
    id_parts = (id_["aio_id"], id_["form_id"], id_["field"], id_["parent"], id_["meta"])
    value = (value or "").removeprefix(prefix)
    page = page[0] if page else 1
    pagination_value = pagination_value[0] if pagination_value else value

    from_filter = False
    if ctx.triggered_id and isinstance(ctx.triggered_id, dict):
        if "nav" in ctx.triggered_id["component"]:
            value = ctx.triggered_id["path"].replace("||", ".")
            page = 1
        elif "filter" in ctx.triggered_id["component"]:
            value = next(
                inp["id"]["path"].replace("||", ".")
                for inp in ctx.inputs_list[1][::-1]
                if inp["id"]["meta"] == "breadcrumbs"
            )
            from_filter = True
            page = 1
        else:
            value = pagination_value
    elif path_type == "glob":
        base_path_match = re.findall("^([^*]*)\/.*\*", value)
        value = value if not base_path_match else base_path_match[0]

    # This happens when the modal first opens after clicking on the button
    # in this case, we want to show the content one level up.
    if not ctx.triggered_id:
        val_split = value.rsplit("/", maxsplit=1)
        value = val_split[0]
        if len(val_split) > 1:
            from_filter = True
            filter_str = [val_split[1]]

    if path_type == "glob":
        path_type = "directory"

    vals: list[dict] = fs.ls(f"{prefix.rstrip('/')}/{(value or '').lstrip('/')}", detail=True)

    filtered_vals = []
    for val in vals:
        subpath = PathField._get_subpath(prefix, value, val["name"])
        subpath2 = PathField._get_subpath(prefix, value, val["name"], rm_value=True)
        if (
            ((path_type == "file") or (val["type"] != "file"))
            and subpath != value
            and (not from_filter or not filter_str or not filter_str[0] or subpath2.startswith(filter_str[0]))
        ):
            filtered_vals.append(val)

    parts = value.split("/")
    page_size = config.get("page_size", 20)

    return PathField.filetree(
        prefix=prefix,
        value=value,
        id_parts=id_parts,
        parts=parts,
        path_type=path_type,
        filtered_vals=filtered_vals,
        page_size=page_size,
        page=page,
        current_filter=(filter_str or [""])[0] if from_filter else "",
    )


clientside_callback(
    ClientsideFunction(namespace="pydf", function_name="updatePathFieldValue"),
    Output(PathField.ids.modal(MATCH, MATCH, MATCH, MATCH, MATCH), "opened", allow_duplicate=True),
    Output(value_field(MATCH, MATCH, MATCH, MATCH, MATCH), "value", allow_duplicate=True),
    Output(PathField.ids.modal_btn_text(MATCH, MATCH, MATCH, MATCH, MATCH), "children"),
    Input(PathField.ids.checkbox(MATCH, MATCH, MATCH, MATCH, MATCH, ALL), "checked"),
    Input(PathField.ids.glob(MATCH, MATCH, MATCH, MATCH, ALL), "value"),
    State(PathField.ids.config(MATCH, MATCH, MATCH, MATCH, MATCH), "data"),
    State(PathField.ids.modal_btn_text(MATCH, MATCH, MATCH, MATCH, MATCH), "children"),
    prevent_initial_call=True,
)

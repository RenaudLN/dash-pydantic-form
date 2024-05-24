import base64
import io
import uuid
from datetime import date
from functools import partial
from typing import get_args

import dash_ag_grid as dag
import dash_mantine_components as dmc
import pandas as pd
from dash import MATCH, ClientsideFunction, Input, Output, State, callback, clientside_callback, dcc, html, no_update
from dash.development.base_component import Component
from pydantic import BaseModel, Field
from pydantic.fields import FieldInfo
from pydantic_core import PydanticUndefined

from dash_pydantic_form import ids as common_ids
from dash_pydantic_form.fields.base_fields import (
    BaseField,
    CheckboxField,
    RadioItemsField,
    SegmentedControlField,
    SelectField,
    TextareaField,
    TextField,
)
from dash_pydantic_form.fields.markdown_field import MarkdownField
from dash_pydantic_form.ids import field_dependent_id
from dash_pydantic_form.utils import get_fullpath, get_non_null_annotation


class EditableTableField(BaseField):
    """Editable table input field attributes and rendering."""

    fields_repr: dict[str, dict | BaseField] | None = Field(
        default=None,
        description="Fields representation, mapping between field name and field representation for the nested fields.",
    )
    with_upload: bool = Field(default=True, description="Whether to allow uploading a CSV file.")
    rows_editable: bool = Field(default=True, description="Whether to allow adding/removing rows.")
    table_height: int = Field(default=300, description="Table rows height in pixels.")
    column_defs_overrides: dict[str, dict] | None = Field(default=None, description="Ag-grid column_defs overrides.")

    full_width = True

    def model_post_init(self, _context):
        """Model post init."""
        super().model_post_init(_context)
        if self.fields_repr is None:
            self.fields_repr = {}
        if self.column_defs_overrides is None:
            self.column_defs_overrides = {}
        if self.read_only:
            self.rows_editable = False
            self.with_upload = False

    class ids(BaseField.ids):
        """Model list field ids."""

        editable_table = partial(field_dependent_id, "_pydf-editable-table-table")
        upload_csv = partial(field_dependent_id, "_pydf-editable-table-upload")
        add_row = partial(field_dependent_id, "_pydf-editable-table-add-row")
        notification_wrapper = partial(field_dependent_id, "_pydf-editable-table-notification-wrapper")

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
        """Create a form field of type Editable Table input to interact with the model."""
        value = self.get_value(item, field, parent) or []
        template: type[BaseModel] = get_args(get_non_null_annotation(field_info.annotation))[0]
        if not issubclass(template, BaseModel):
            raise TypeError(f"Wrong type annotation for field {get_fullpath(parent, field)} to use EditableTable.")

        required_fields = [f for f, f_info in template.model_fields.items() if f_info.is_required()]
        optional_fields = [f for f in template.model_fields if f not in required_fields]

        upload = []
        if self.with_upload:
            upload_ = dcc.Upload(
                id=self.ids.upload_csv(aio_id, form_id, field, parent=parent),
                children=dmc.Stack(
                    [
                        html.Div(
                            [
                                "Drag & drop a csv file or ",
                                dmc.Anchor("select it", href="#"),
                            ]
                        ),
                        dmc.Stack(
                            [
                                dmc.Text("CSV columns", size="sm"),
                                dmc.Group(
                                    [
                                        dmc.Text("REQUIRED", size="sm", style={"flexShrink": 0}),
                                        dmc.Group(
                                            [
                                                dmc.Badge(
                                                    f,
                                                    color="dark",
                                                    style={
                                                        "textTransform": "none",
                                                        "padding": "0 0.25rem",
                                                        "fontWeight": "normal",
                                                    },
                                                    radius="sm",
                                                )
                                                for f in required_fields
                                            ],
                                            gap="0.25rem",
                                        ),
                                    ],
                                    gap="0.5rem",
                                    wrap=False,
                                    align="start",
                                ),
                            ]
                            * bool(required_fields)
                            + [
                                dmc.Group(
                                    [
                                        dmc.Text("OPTIONAL", size="sm", style={"flexShrink": 0}),
                                        dmc.Group(
                                            [
                                                dmc.Badge(
                                                    f,
                                                    color="dark",
                                                    style={
                                                        "textTransform": "none",
                                                        "padding": "0 0.25rem",
                                                        "fontWeight": "normal",
                                                    },
                                                    radius="sm",
                                                )
                                                for f in optional_fields
                                            ],
                                            gap="0.25rem",
                                        ),
                                    ],
                                    gap="0.5rem",
                                    wrap=False,
                                    align="start",
                                ),
                            ]
                            * bool(optional_fields),
                            gap="0.375rem",
                            mt="1rem",
                        ),
                    ],
                    gap=6,
                    align="start",
                    style={"margin": "0 auto", "width": "fit-content"},
                ),
                style={
                    "width": "100%",
                    "borderWidth": "1px",
                    "borderStyle": "dashed",
                    "borderRadius": "5px",
                    "padding": "1rem 1.5rem",
                },
            )
            upload = [
                dmc.Menu(
                    [
                        dmc.MenuTarget(dmc.Button("Upload CSV", size="compact-sm")),
                        dmc.MenuDropdown(upload_),
                    ],
                    shadow="xl",
                    position="top-start",
                    styles={"dropdown": {"maxWidth": "min(90vw, 500px)"}},
                ),
            ]

        add_row = []
        if self.rows_editable:
            add_row = [
                dmc.Button(
                    "Add row",
                    id=self.ids.add_row(aio_id, form_id, field, parent=parent),
                    size="compact-sm",
                ),
            ]

        def get_field_repr(field: str) -> BaseField | dict:
            from dash_pydantic_form.fields import get_default_repr

            if field in self.fields_repr:
                return self.fields_repr[field]
            return get_default_repr(template.model_fields[field])

        title = self.get_title(field_info, field_name=field)
        description = self.get_description(field_info)
        return html.Div(
            [
                html.Div(
                    (title is not None)
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
                            mb=5,
                            fw=500,
                            lh=1.55,
                        )
                    ]
                    + (title is not None and description is not None)
                    * [dmc.Text(description, size="xs", c="dimmed", mt=-5, mb=5, lh=1.2)],
                ),
                dag.AgGrid(
                    id=self.ids.editable_table(aio_id, form_id, field, parent=parent),
                    columnDefs=(
                        [
                            {
                                "headerName": "",
                                "cellRenderer": "PydfDeleteButton",
                                "lockPosition": "left",
                                "maxWidth": 35,
                                "filter": False,
                                "cellStyle": {
                                    "padding": 0,
                                    "display": "grid",
                                    "placeContent": "center",
                                },
                                "editable": False,
                            }
                        ]
                        # removes the delete button if add button is removed
                        if self.rows_editable
                        else []
                    )
                    + [  # Generate a column def depending on the field type
                        self._generate_field_column(
                            field_name=field_name,
                            field_repr=get_field_repr(field_name),
                            field_info=template.model_fields[field_name],
                            required_field=field_name in required_fields,
                            editable=not self.read_only,
                        )
                        for field_name in template.model_fields
                    ],
                    defaultColDef={"editable": not self.read_only, "resizable": True, "sortable": True, "filter": True},
                    rowData=value,
                    columnSize="responsiveSizeToFit",
                    style={"height": self.table_height},
                    dashGridOptions={
                        "singleClickEdit": True,
                        "rowSelection": "multiple",
                        "stopEditingWhenCellsLoseFocus": True,
                        "suppressRowHoverHighlight": self.read_only,
                        "suppressRowClickSelection": self.read_only,
                    },
                    className="ag-theme-alpine ag-themed overflowing-ag-grid",
                ),
            ]
            + ([dmc.Group(add_row + upload)] if (self.rows_editable or self.with_upload) else [])
            + [
                dmc.JsonInput(
                    id=common_ids.value_field(aio_id, form_id, field, parent=parent),
                    value=value,
                    style={"display": "none"},
                ),
                html.Div(id=self.ids.notification_wrapper(aio_id, form_id, field, parent=parent)),
            ]
            * (not self.read_only),
            style={"display": "grid", "gap": "0.5rem", "gridTemplateColumns": "1fr"},
        )

    def _generate_field_column(  # noqa: PLR0913
        self,
        *,
        field_name: str,
        field_repr: BaseField | dict,
        field_info: FieldInfo,
        required_field: bool,
        editable: bool = True,
    ):
        """Takes a field and generates the 'columnDefs' dictionary for said field based on its type."""
        from dash_pydantic_form.fields import get_default_repr

        if isinstance(field_repr, dict):
            field_repr = get_default_repr(field_info, **field_repr)
        # Column_def no matter the type
        column_def = {
            "editable": editable,
            "field": field_name,
            "headerName": field_repr.get_title(field_info, field_name=field_name),
            "required": required_field,
            "cellClass": {
                "function": "(params.value == null || params.value == '') ? 'required_cell' : ''",
            }
            if required_field
            else None,
        }

        if description := field_repr.get_description(field_info):
            column_def.update({"headerTooltip": description})

        if field_info.default != PydanticUndefined:
            column_def["default_value"] = field_info.default
        if field_info.default_factory is not None:
            column_def["default_value"] = field_info.default_factory()

        # if select field, generate column of dropdowns
        if isinstance(field_repr, SelectField | SegmentedControlField | RadioItemsField):
            data = (
                field_repr.data_getter()
                if field_repr.data_getter
                else field_repr.input_kwargs.get("data", field_repr._get_data(field_info=field_info))
            )
            options = [
                {
                    "value": x
                    if isinstance(x, str | int | float)
                    else (x["value"] if isinstance(x, dict) else x.value),
                    "label": x
                    if isinstance(x, str | int | float)
                    else (x["label"] if isinstance(x, dict) else x.label),
                }
                for x in data
            ]
            params = {k: v for k, v in field_repr.input_kwargs.items() if k not in ["data"]}
            column_def.update(
                {
                    "cellEditor": {"function": "PydfDropdown"},
                    "cellEditorPopup": False,
                    "cellEditorParams": {"options": options, **params},
                    "cellRenderer": "PydfOptionsRenderer",
                    "cellClass": {
                        "function": "selectRequiredCell(params)",
                    }
                    if required_field
                    else None,
                }
            )

        if isinstance(field_info, TextareaField | MarkdownField):
            column_def.update(
                {
                    "cellEditor": "agLargeTextCellEditor",
                    "cellEditorPopup": True,
                    "cellEditorParams": {"maxLength": 100, "rows": 10, "cols": 50},
                }
            )

        if isinstance(field_info, TextField | TextareaField | MarkdownField):
            column_def.update({"dtype": "str"})

        if isinstance(field_info, CheckboxField):
            column_def.update({"cellRenderer": "PydfCheckbox", "editable": False})

        if get_non_null_annotation(field_info.annotation) == date:
            column_def.update(
                {
                    "cellEditor": {"function": "PydfDatePicker"},
                    "cellEditorPopup": False,
                    "cellEditorParams": field_repr.input_kwargs,
                },
            )

        # update with custom defs
        column_def.update(self.column_defs_overrides.get(field_name, {}))

        # default return base definition (text field)
        return column_def

    # Sync the JsonInput from the table data
    clientside_callback(
        ClientsideFunction(namespace="pydf", function_name="syncTableJson"),
        Output(common_ids.value_field(MATCH, MATCH, MATCH, parent=MATCH), "value", allow_duplicate=True),
        Input(ids.editable_table(MATCH, MATCH, MATCH, parent=MATCH), "rowData"),
        Input(ids.editable_table(MATCH, MATCH, MATCH, parent=MATCH), "virtualRowData"),
        Input(ids.editable_table(MATCH, MATCH, MATCH, parent=MATCH), "cellValueChanged"),
        prevent_initial_call=True,
    )

    @callback(
        Output(ids.editable_table(MATCH, MATCH, MATCH, parent=MATCH), "rowData", allow_duplicate=True),
        Output(ids.notification_wrapper(MATCH, MATCH, MATCH, parent=MATCH), "children", allow_duplicate=True),
        Input(ids.upload_csv(MATCH, MATCH, MATCH, parent=MATCH), "contents"),
        State(ids.editable_table(MATCH, MATCH, MATCH, parent=MATCH), "columnDefs"),
        prevent_initial_call=True,
    )
    def csv_to_table(contents, column_defs):
        """Output uploaded csv file to the editable table."""
        if contents is not None:
            _, content_string = contents.split(",")

            decoded = base64.b64decode(content_string)
            data = pd.read_csv(
                io.StringIO(decoded.decode("utf-8")),
                dtype={f["field"]: f["dtype"] for f in column_defs if "field" in f and "dtype" in f},
            )
            required_columns = [col["field"] for col in column_defs if col.get("required")]
            if set(required_columns).issubset(data.columns):
                for col in column_defs:
                    if not (field := col.get("field")):
                        continue
                    if options := col.get("cellEditorParams", {}).get("options"):
                        values = [x["value"] for x in options]
                        options_dict = {x["label"]: x["value"] for x in options}
                        data[field] = data[field].where(data[field].isin(values), data[field].map(options_dict))

                return data.to_dict("records"), None

            return no_update, dmc.Notification(
                color="red",
                title="Wrong column names",
                message="CSV upload failed, the file should contain the following columns: "
                f"{', '.join(required_columns)}",
                id=uuid.uuid4().hex,
                action="show",
            )
        return no_update, None

    @callback(
        Output(ids.editable_table(MATCH, MATCH, MATCH, parent=MATCH), "rowTransaction", allow_duplicate=True),
        Input(ids.add_row(MATCH, MATCH, MATCH, parent=MATCH), "n_clicks"),
        State(ids.editable_table(MATCH, MATCH, MATCH, parent=MATCH), "columnDefs"),
        prevent_initial_call=True,
    )
    def add_row(n_clicks, column_defs):
        """Add new row in editable table on user click."""
        if n_clicks is not None:
            return {"add": [{col["field"]: col.get("default_value") for col in column_defs if "field" in col}]}
        return no_update

import contextlib
import dataclasses as dc
import uuid
import warnings
from copy import deepcopy
from functools import partial
from types import UnionType
from typing import Annotated, Literal, Union, get_args, get_origin, overload

import dash_mantine_components as dmc
from dash import (
    ALL,
    MATCH,
    ClientsideFunction,
    Input,
    Output,
    State,
    callback,
    clientside_callback,
    ctx,
    dcc,
    html,
    no_update,
)
from dash.development.base_component import Component, rd
from pydantic import BaseModel
from pydantic.fields import FieldInfo

from dash_pydantic_utils import (
    SEP,
    Type,
    get_fullpath,
    get_model_cls,
    get_subitem,
    get_subitem_cls,
    handle_discriminated,
    is_subclass,
    model_construct_recursive,
)

from . import ids as common_ids
from .fields import BaseField, fields
from .form_layouts import FormLayout
from .i18n import _, language_context
from .ids import form_base_id

Children_ = Component | str | int | float
Children = Children_ | list[Children_]
SectionRender = Literal["accordion", "tabs", "steps"]
Position = Literal["top", "bottom", "none"]


class ModelFormIdsFactory:
    """Factory functions for model form ids."""

    form = partial(form_base_id, "_pydf-form")
    main = partial(form_base_id, "_pydf-main")
    restore_wrapper = partial(form_base_id, "_pydf-restore-wrapper")
    restore_btn = partial(form_base_id, "_pydf-restore-btn")
    cancel_restore_btn = partial(form_base_id, "_pydf-cancel-restore-btn")
    wrapper = partial(common_ids.field_dependent_id, "_pydf-wrapper")
    errors = partial(form_base_id, "_pydf-errors")
    model_store = partial(form_base_id, "_pydf-model-store")
    form_specs_store = partial(form_base_id, "_pydf-form-specs-store")


@dc.dataclass(frozen=True)
class ModelFormIds:
    """Model form ids."""

    form: dict[str, str]
    main: dict[str, str]
    restore_wrapper: dict[str, str]
    restore_btn: dict[str, str]
    cancel_restore_btn: dict[str, str]
    errors: dict[str, str]
    model_store: dict[str, str]
    form_specs_store: dict[str, str]

    @classmethod
    def from_basic_ids(cls, aio_id: str, form_id: str) -> "ModelFormIds":
        """Instanciation from aio_id and form_id."""
        return cls(*(getattr(ModelFormIdsFactory, id_field.name)(aio_id, form_id) for id_field in dc.fields(cls)))


class IdAccessor:
    """Descriptor for handling access to either instances or the factory of model form ids via ``ModelForm`` class."""

    @overload
    def __get__(self, obj: "ModelForm", objtype=None) -> ModelFormIds: ...
    @overload
    def __get__(self, obj: None, objtype=None) -> type[ModelFormIdsFactory]: ...
    def __get__(self, obj, objtype=None):
        """Returns the ``ModelFormIdsFactory`` class if accessed via the ``ModelForm`` class directly (ModelForm.ids)
        or an instance of ``ModelFormIds`` if accessed via an instance of ``ModelForm`` (ModelForm(my_model).ids).
        """
        if obj is None:
            # access via class
            return ModelFormIdsFactory

        if isinstance(obj, ModelForm):
            # access via instance
            return obj._ids

        raise RuntimeError("IdAccessor should only be defined on ModelForm or an instance of ModelForm")

    def __set__(self, obj: "ModelForm", value: ModelFormIds | tuple[str, str]):
        """Sets another set of model form ids to a ``ModelForm`` object."""
        if isinstance(value, tuple):
            value = ModelFormIds.from_basic_ids(*value)

        obj._ids = value


class ModelForm(html.Div):
    """Create a Dash form from a pydantic model.

    Parameters
    ----------
    item: BaseModel | type[BaseModel]
        The model to create the form from, can be the model class or an instance of the class.
        If the class is passed, the form will be empty. If an instance is passed, the form will be pre-filled
        with existing values.
    aio_id: str | None
        All-in-one component ID. A pseudo-random string will be auto-generated if not provided.
    form_id: str | None
        Form ID, can be used to create multiple forms on the same page. When working with databases
        this could be the document / record ID. A pseudo-random string will be auto-generated if not provided.
    form_cols: int
        Number of columns in the form, defaults to 4.
    fields_repr: dict[str, dict | BaseField] | None
        Mapping between field name and field representation. If not provided, default field
        representations will be used based on the field annotation.
        See `fields.get_default_repr`.
    sections: FormLayout | None
        DEPRECATED: Use form_layout.
    form_layout: FormLayout | None
        Defines how to render the form layout, built-in layouts are `accordion`, `tabs` and `steps`.
        If not provided, default to rendering the fields in a grid.
    submit_on_enter: bool
        Whether to submit the form on enter. Default False.
        Note: this may break the behaviour of some fields (e.g. editable table), use with caution.
    excluded_fields: list[str] | None
        List of field names to exclude from the form altogether, optional.
    container_kwargs: dict | None
        Additional kwargs to pass to the containing div.
    read_only: bool | None
        Whether the form should be read only.
        True/False set all the fields to read only or not. None keeps the field setting.
    debounce_inputs: int | None
        Debounce inputs in milliseconds. Only works with DMC components that can be debounced.
    locale: str | None
        Locale to render the buttons and helpers in, currently English and French are supported.
        If left to None, will default to system locale, and fallback to English.
    cols: int
        Deprecated, use `form_cols` instead.
    data_model: type[BaseModel] | Annotated[UnionType, FieldInfo] | None
        The data model or union of models to create the form from, this is mostly used for discriminated unions.
    fields_order: list[str] | None
        List of field names to order the fields in the form. The fields will be displayed in the order provided.
        All fields not in the list will be displayed in ther model order, after the ones defined here.
    store_progress: bool | Literal["local", "session"]
        Whether to store the progress of the form in the local store, to allow picking up where the user left off.
        If set to True or "local" will store to local storage, if set to "session" will store to session storage.
    """

    ids = IdAccessor()
    _ids: ModelFormIds

    def __init__(  # noqa: PLR0912, PLR0913, PLR0915
        self,
        item: BaseModel | type[BaseModel] | Annotated[UnionType, FieldInfo],
        aio_id: str | None = None,
        form_id: str | None = None,
        path: str = "",
        form_cols: int = 4,
        fields_repr: dict[str, Union["BaseField", dict]] | None = None,
        sections: FormLayout | None = None,
        form_layout: FormLayout | None = None,
        submit_on_enter: bool = False,
        discriminator: str | None = None,
        excluded_fields: list[str] | None = None,
        container_kwargs: dict | None = None,
        read_only: bool | None = None,
        debounce_inputs: int | None = None,
        locale: str = None,
        cols: int = None,
        data_model: type[BaseModel] | Annotated[UnionType, FieldInfo] | None = None,
        fields_order: list[str] | None = None,
        store_progress: bool | Literal["local", "session"] = False,
        restore_behavior: Literal["auto", "notify"] = "notify",
    ) -> None:
        if data_model is None:
            data_model = type(item) if isinstance(item, BaseModel) else item
        if is_subclass(item, BaseModel):
            item = item.model_construct()
        if not isinstance(item, BaseModel):
            item = None
        if get_origin(data_model) is Annotated:
            if discriminator is None:
                discriminator = next((f.discriminator for f in get_args(data_model) if isinstance(f, FieldInfo)), None)
            data_model = get_args(data_model)[0]

        aio_id = aio_id or str(uuid.UUID(int=rd.randint(0, 2**128)))
        form_id = form_id or str(uuid.UUID(int=rd.randint(0, 2**128)))
        self.ids = ModelFormIds.from_basic_ids(aio_id, form_id)

        if cols is not None:
            warnings.warn("cols is deprecated, use form_cols instead", DeprecationWarning, stacklevel=1)
            form_cols = cols
        if sections is not None:
            warnings.warn("sections is deprecated, use form_layout instead", DeprecationWarning, stacklevel=1)
            if form_layout is None:
                form_layout = sections

        fields_repr = fields_repr or {}

        subitem_cls, disc_vals = self.get_discriminated_subitem_cls(
            item=item, path=path, discriminator=discriminator, data_model=data_model
        )
        with language_context(locale):
            field_inputs = self.render_fields(
                item=item,
                aio_id=aio_id,
                form_id=form_id,
                path=path,
                subitem_cls=subitem_cls,
                disc_vals=disc_vals,
                fields_repr=fields_repr,
                excluded_fields=excluded_fields,
                discriminator=discriminator,
                read_only=read_only,
                debounce_inputs=debounce_inputs,
                form_cols=form_cols,
            )
            # Re-order fields as per fields_order
            if fields_order:
                field_inputs = {f: field_inputs[f] for f in fields_order if f in field_inputs} | {
                    f: r for f, r in field_inputs.items() if f not in fields_order
                }

            if not form_layout:
                children = [FormLayout.grid(list(field_inputs.values()))]
            else:
                children = form_layout.render(
                    field_inputs=field_inputs,
                    aio_id=aio_id,
                    form_id=form_id,
                    path=path,
                    read_only=read_only,
                    form_cols=form_cols,
                )

            children.extend(
                self._get_meta_children(
                    fields_repr=fields_repr,
                    form_layout=form_layout,
                    aio_id=aio_id,
                    form_id=form_id,
                    path=path,
                    form_cols=form_cols,
                    data_model=data_model,
                    restore_behavior=restore_behavior,
                )
            )

        container_kwargs = container_kwargs or {}
        style = {"--pydf-form-cols": f"{form_cols}"} | container_kwargs.pop("style", {}) | {"position": "relative"}
        if not path:
            style |= {"containerType": "inline-size"}

        super().__init__(
            children=html.Div(children, id=ModelFormIdsFactory.wrapper(aio_id, form_id, discriminator or "", path)),
            style=style,
            **(
                {
                    "id": ModelFormIdsFactory.form(aio_id, form_id, path),
                    "data-submitonenter": submit_on_enter,
                    "data-storeprogress": store_progress,
                    "data-getvalues": None,
                    "data-restored": None,
                    "data-update": None,
                }
                if not path
                else {}
            ),
            **container_kwargs,
        )

    @staticmethod
    def get_discriminated_subitem_cls(
        *,
        item: BaseModel | None,
        path: str,
        discriminator: str | None,
        data_model: type[BaseModel] | UnionType,
    ) -> tuple[type[BaseModel], tuple]:
        """Get the subitem of a model at a given parent, handling type unions."""
        subitem_cls = (
            get_subitem_cls(item.__class__, path, item=item) if is_subclass(data_model, BaseModel) else data_model
        )

        # Handle type unions
        disc_vals = None
        discriminator_value = None
        if Type.classify(subitem_cls, discriminator) == Type.DISCRIMINATED_MODEL:
            subitem = get_subitem(item, path) if item is not None else None
            discriminator_value = None if subitem is None else getattr(subitem, discriminator, None)
            subitem_cls, disc_vals = handle_discriminated(
                item.__class__, path, subitem_cls, discriminator, discriminator_value
            )

        return subitem_cls, disc_vals

    @staticmethod
    def render_fields(  # noqa: PLR0913
        *,
        item: BaseModel,
        aio_id: str,
        form_id: str,
        path: str,
        subitem_cls: type[BaseModel],
        disc_vals: list[str],
        fields_repr: dict[str, dict | BaseField],
        excluded_fields: list[str],
        discriminator: str | None,
        read_only: bool | None,
        debounce_inputs: int | None,
        form_cols: int,
    ) -> dict[str, Component]:
        """Render each field in the form."""
        from dash_pydantic_form.fields import get_default_repr

        excluded_fields = (excluded_fields or []) + subitem_cls.model_config.get("private_fields", [])

        field_inputs = {}
        for field_name, field_info in subitem_cls.model_fields.items():
            if field_name in (excluded_fields or []):
                continue
            more_kwargs = {"form_cols": form_cols}
            if read_only:
                more_kwargs["read_only"] = read_only
            if debounce_inputs:
                more_kwargs["debounce"] = debounce_inputs
            # If discriminating field, ensure all discriminator values are shown
            # Also add required metadata for discriminator callback
            if disc_vals and field_name == discriminator:
                field_info = deepcopy(field_info)  # noqa: PLW2901
                field_info.annotation = Literal[disc_vals]
                more_kwargs |= {"n_cols": "var(--pydf-form-cols)", "field_id_meta": "discriminator"}
            if field_name in fields_repr:
                if isinstance(fields_repr[field_name], dict):
                    field_repr = get_default_repr(field_info, **(fields_repr[field_name] | more_kwargs))
                else:
                    field_repr = fields_repr[field_name]
                    if more_kwargs:
                        field_repr = field_repr.__class__(**(field_repr.model_dump() | more_kwargs))
            else:
                field_repr = get_default_repr(field_info, **more_kwargs)

            field_inputs[field_name] = field_repr.render(
                item=item,
                aio_id=aio_id,
                form_id=form_id,
                field=field_name,
                parent=path,
                field_info=field_info,
            )

        return field_inputs

    @classmethod
    def _get_meta_children(  # noqa: PLR0913
        cls,
        *,
        fields_repr: dict[str, dict | BaseField],
        form_layout: FormLayout | None,
        aio_id: str,
        form_id: str,
        path: str,
        form_cols: int,
        data_model: type[BaseModel] | UnionType,
        restore_behavior: Literal["auto", "notify"],
    ):
        """Get 'meta' form children used for passing data to callbacks."""
        children = []
        if not path:
            children.append(
                html.Div(
                    cls.get_restore_data_overlay(aio_id, form_id),
                    id=cls.ids.restore_wrapper(aio_id, form_id),
                    style={"display": "none"},
                    **{"data-behavior": restore_behavior},
                )
            )
            children.append(dcc.Store(id=cls.ids.main(aio_id, form_id)))
            children.append(dcc.Store(id=cls.ids.errors(aio_id, form_id)))
            if is_subclass(data_model, BaseModel):
                model_name = str(data_model)
            elif get_origin(data_model) in [Union, UnionType]:
                model_name = [str(x) for x in get_args(data_model)]
            else:
                raise ValueError("data_model must be a pydantic BaseModel or Union of models")
            children.append(dcc.Store(data=model_name, id=cls.ids.model_store(aio_id, form_id)))

        fields_repr_dicts = (
            {
                field_name: field_repr if isinstance(field_repr, dict) else field_repr.to_dict()
                for field_name, field_repr in fields_repr.items()
            }
            if fields_repr
            else None
        )

        children.append(
            dcc.Store(
                data={
                    "form_layout": form_layout.model_dump(mode="json") if form_layout else None,
                    "fields_repr": fields_repr_dicts,
                    "form_cols": form_cols,
                },
                id=cls.ids.form_specs_store(aio_id, form_id, path),
            )
        )

        return children

    @classmethod
    def get_restore_data_overlay(cls, aio_id: str, form_id: str):
        """Get the overlay for restoring data."""
        return dmc.Stack(
            dmc.Card(
                [
                    dmc.Text(_("Found previous form data. Do you want to restore it?"), size="sm", mb="1.25rem"),
                    dmc.Group(
                        [
                            dmc.Button(
                                _("Restore"),
                                size="compact-sm",
                                id=cls.ids.restore_btn(aio_id, form_id),
                            ),
                            dmc.Button(
                                _("Cancel"),
                                size="compact-sm",
                                variant="outline",
                                id=cls.ids.cancel_restore_btn(aio_id, form_id),
                            ),
                        ],
                        justify="center",
                    ),
                ],
                shadow="lg",
                withBorder=True,
            ),
            pos="absolute",
            style={"inset": 0, "backdropFilter": "blur(3px)", "zIndex": 1},
            bg="color-mix(in srgb, var(--mantine-color-body), #0000 25%)",
            p="2rem",
            align="center",
        )


clientside_callback(
    ClientsideFunction(namespace="pydf", function_name="getValues"),
    Output(ModelForm.ids.main(MATCH, MATCH), "data"),
    Input(common_ids.value_field(MATCH, MATCH, ALL, ALL, ALL), "value"),
    Input(common_ids.checked_field(MATCH, MATCH, ALL, ALL, ALL), "checked"),
    Input(fields.Dict.ids.item_key(MATCH, MATCH, ALL, ALL, ALL), "value"),
    Input(BaseField.ids.visibility_wrapper(MATCH, MATCH, ALL, ALL, ALL), "style"),
    Input(ModelForm.ids.form(MATCH, MATCH), "data-getvalues"),
    State(ModelForm.ids.form(MATCH, MATCH), "id"),
    State(ModelForm.ids.form(MATCH, MATCH), "data-storeprogress"),
    State(ModelForm.ids.main(MATCH, MATCH), "data"),
    State(ModelForm.ids.restore_wrapper(MATCH, MATCH), "id"),
    State(ModelForm.ids.restore_wrapper(MATCH, MATCH), "data-behavior"),
)

clientside_callback(
    ClientsideFunction(namespace="pydf", function_name="restoreData"),
    Output(ModelForm.ids.form(MATCH, MATCH), "data-update", allow_duplicate=True),
    Output(ModelForm.ids.restore_wrapper(MATCH, MATCH), "style", allow_duplicate=True),
    Output(ModelForm.ids.form(MATCH, MATCH), "data-restored", allow_duplicate=True),
    Input(ModelForm.ids.restore_btn(MATCH, MATCH), "n_clicks"),
    State(ModelForm.ids.form(MATCH, MATCH), "data-restored"),
    prevent_initial_call=True,
)

clientside_callback(
    ClientsideFunction(namespace="pydf", function_name="cancelRestoreData"),
    Output(ModelForm.ids.restore_wrapper(MATCH, MATCH), "style", allow_duplicate=True),
    Output(ModelForm.ids.form(MATCH, MATCH), "data-restored", allow_duplicate=True),
    Output(ModelForm.ids.form(MATCH, MATCH), "data-getvalues", allow_duplicate=True),
    Input(ModelForm.ids.cancel_restore_btn(MATCH, MATCH), "n_clicks"),
    prevent_initial_call=True,
)

clientside_callback(
    ClientsideFunction(namespace="pydf", function_name="listenToSubmit"),
    Output(ModelForm.ids.form(MATCH, MATCH), "id"),
    Input(ModelForm.ids.form(MATCH, MATCH), "id"),
    State(ModelForm.ids.form(MATCH, MATCH), "data-submitonenter"),
)

clientside_callback(
    ClientsideFunction(namespace="pydf", function_name="displayErrors"),
    Output(common_ids.value_field(MATCH, MATCH, ALL, ALL, ALL), "error"),
    Input(ModelForm.ids.errors(MATCH, MATCH), "data"),
    State(common_ids.value_field(MATCH, MATCH, ALL, ALL, ALL), "id"),
)


@callback(
    Output(ModelForm.ids.wrapper(MATCH, MATCH, MATCH, MATCH), "children", allow_duplicate=True),
    Input(ModelForm.ids.form(MATCH, MATCH, MATCH), "data-update"),
    State(ModelForm.ids.model_store(MATCH, MATCH, MATCH), "data"),
    State(ModelForm.ids.form_specs_store(MATCH, MATCH, MATCH), "data"),
    prevent_initial_call=True,
)
def update_data(form_data: dict, model_name: str | list[str], form_specs: dict):
    """Update contents with ids.form data-update."""
    if not form_data:
        return no_update
    return update_form_wrapper_contents(form_data, None, model_name, form_specs)


@callback(
    Output(ModelForm.ids.wrapper(MATCH, MATCH, MATCH, MATCH), "children", allow_duplicate=True),
    Input(common_ids.value_field(MATCH, MATCH, MATCH, MATCH, "discriminator"), "value"),
    State(ModelForm.ids.main(MATCH, MATCH), "data"),
    State(ModelForm.ids.model_store(MATCH, MATCH), "data"),
    State(ModelForm.ids.form_specs_store(MATCH, MATCH, MATCH), "data"),
    prevent_initial_call=True,
)
def update_discriminated(val, form_data: dict, model_name: str | list[str], form_specs: dict):
    """Update contents when discriminator input changes."""
    path: str = get_fullpath(ctx.triggered_id["parent"], ctx.triggered_id["field"])
    discriminator = ctx.triggered_id["field"]
    parts = path.split(SEP)
    # Update the form data with the new value as it wouldn't have been updated yet
    pointer = form_data
    for i, part in enumerate(parts):
        if i == len(parts) - 1:
            pointer[part] = val
        if part.isdigit():
            pointer = list(pointer.values())[int(part)] if isinstance(pointer, dict) else pointer[int(part)]
        else:
            pointer = pointer[part]
    return update_form_wrapper_contents(form_data, discriminator, model_name, form_specs)


def update_form_wrapper_contents(
    form_data: dict,
    discriminator: str | None,
    model_name: str | list[str],
    form_specs: dict,
):
    """Update the form wrapper contents."""
    # Create an instance of the model with the form data using model_construct_recursive
    # to build it out as much as possible without failing on validation
    if isinstance(model_name, str):
        model_cls = get_model_cls(model_name)
    else:
        if not (disc_val := form_data.get(discriminator)):
            return no_update
        model_union = [get_model_cls(x) for x in model_name]
        model_cls = next(
            (x for x in model_union if x.model_fields[discriminator].default == disc_val),
            None,
        )
        if model_cls is None:
            return no_update

    item = model_construct_recursive(form_data, model_cls)

    # Retrieve fields-repr and form_layout from the stored data
    fields_repr: dict[str, BaseField] = form_specs["fields_repr"] or {}
    for k, v in fields_repr.items():
        with contextlib.suppress(KeyError):
            fields_repr[k] = BaseField.from_dict(v)
    form_layout = FormLayout.load(**form_specs["form_layout"]) if form_specs["form_layout"] else None

    form = ModelForm(
        item=item,
        aio_id=ctx.triggered_id["aio_id"],
        form_id=ctx.triggered_id["form_id"],
        path=ctx.triggered_id["parent"],
        discriminator=discriminator,
        form_layout=form_layout,
        fields_repr=fields_repr,
        form_cols=form_specs["form_cols"],
        data_model=None if isinstance(model_name, str) else Union[tuple(model_union)],  # noqa: UP007
    )

    return form.children.children

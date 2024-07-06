import json
from datetime import date
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field

from dash_pydantic_form import ModelForm
from tests.utils import check_elem_values, check_ids_exist, get_field_ids


def test_0001_basic_form():
    """Test a basic form."""

    class E(Enum):
        A = "a"
        B = "b"

    class M(BaseModel):
        a: int = Field(title="Field A")
        b: str = Field(title="Field A")
        c: Literal["a", "b"] = Field(title="Field C")
        d: bool = Field(title="Field D")
        e: E = Field(title="Field E")
        f: date = Field(title="Field F")

    aio_id = "basic"
    form_id = "form"
    form = ModelForm(M, aio_id=aio_id, form_id=form_id)
    check_ids_exist(form, list(get_field_ids(M, aio_id, form_id)))
    check_elem_values(form, {json.dumps(fid): None for fid in get_field_ids(M, aio_id, form_id)})

    data = {"a": 1, "b": "foo", "c": "a", "d": True, "e": "b", "f": "2022-01-01"}
    assert list(data) == list(M.model_fields)
    item = M(**data)
    form_filled = ModelForm(item, aio_id=aio_id, form_id=form_id)
    check_ids_exist(form_filled, list(get_field_ids(M, aio_id, form_id)))
    check_elem_values(
        form_filled,
        {
            json.dumps(fid): val
            for fid, val in zip(get_field_ids(M, aio_id, form_id), item.model_dump().values(), strict=True)
        },
    )

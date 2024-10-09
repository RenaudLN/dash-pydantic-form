from typing import get_args, get_origin

import pytest
from pydantic import BaseModel, Field

from dash_pydantic_form import utils


def test_ut0001_get_subitem():
    """Test get_subitem."""

    class Nested2(BaseModel):
        a: int

    class Nested(BaseModel):
        li: list[Nested2] = Field(default_factory=list)
        di: dict[str, Nested2] = Field(default_factory=dict)

    class Base(BaseModel):
        name: str
        x: Nested
        y: list[Nested] = Field(default_factory=list)
        z: dict[str, Nested] = Field(default_factory=dict)

    item = Base(
        name="test",
        x=Nested(li=[Nested2(a=1), Nested2(a=2)], di={"d0": Nested2(a=3)}),
        y=[
            Nested(li=[Nested2(a=4), Nested2(a=5)], di={"d1": Nested2(a=6)}),
            Nested(li=[Nested2(a=7), Nested2(a=8)], di={"d2": Nested2(a=9)}),
        ],
        z={
            "z0": Nested(li=[Nested2(a=10), Nested2(a=11)], di={"d3": Nested2(a=12)}),
            "z1": Nested(li=[Nested2(a=13), Nested2(a=14)], di={"d4": Nested2(a=15)}),
        },
    )

    assert utils.get_subitem(item, "name") == "test"
    assert utils.get_subitem(item, "x") == Nested(li=[Nested2(a=1), Nested2(a=2)], di={"d0": Nested2(a=3)})
    assert utils.get_subitem(item, "x:li") == [Nested2(a=1), Nested2(a=2)]
    assert utils.get_subitem(item, "x:li:1") == Nested2(a=2)
    assert utils.get_subitem(item, "x:di:d0:a") == 3  # noqa: PLR2004
    assert utils.get_subitem(item, "y:0:li:0:a") == 4  # noqa: PLR2004
    assert utils.get_subitem(item, "y:1:di:d2:a") == 9  # noqa: PLR2004
    assert utils.get_subitem(item, "z:z0:li:0:a") == 10  # noqa: PLR2004
    assert utils.get_subitem(item, "z:z1:di:d4:a") == 15  # noqa: PLR2004
    assert utils.get_subitem(item, "z:1:di:0:a") == 15  # noqa: PLR2004
    assert utils.get_subitem(item, "z:z2") is None

    with pytest.raises(AttributeError):
        utils.get_subitem(item, "u")
    with pytest.raises(AttributeError):
        utils.get_subitem(item, "z:z1:k")
    with pytest.raises(IndexError):
        utils.get_subitem(item, "z:3")
    with pytest.raises(IndexError):
        utils.get_subitem(item, "y:3")


def test_u0002_get_subitem_cls():
    """Test get_subitem_cls."""

    class Nested2(BaseModel):
        a: int

    class Nested(BaseModel):
        li: list[Nested2] = Field(default_factory=list)
        di: dict[str, Nested2] = Field(default_factory=dict)

    class Base(BaseModel):
        name: str
        x: Nested
        y: list[Nested] = Field(default_factory=list)
        z: dict[str, Nested] = Field(default_factory=dict)

    assert utils.get_subitem_cls(Base, "name") is str
    assert utils.get_subitem_cls(Base, "x") is Nested
    tmp = utils.get_subitem_cls(Base, "x:li")
    assert get_origin(tmp) is list
    assert get_args(tmp)[0] is Nested2
    assert utils.get_subitem_cls(Base, "x:li:0") is Nested2
    tmp = utils.get_subitem_cls(Base, "x:di")
    assert get_origin(tmp) is dict
    assert utils.get_subitem_cls(Base, "x:di:0") is Nested2
    assert utils.get_subitem_cls(Base, "x:di:d0") is Nested2
    assert utils.get_subitem_cls(Base, "z:somekey") is Nested
    assert utils.get_subitem_cls(Base, "z:somekey:di:otherkey") is Nested2
    assert utils.get_subitem_cls(Base, "z:0:di:1") is Nested2
    assert utils.get_subitem_cls(Base, "y:9") is Nested
    assert utils.get_subitem_cls(Base, "y:9:li:7") is Nested2

    with pytest.raises(AttributeError):
        utils.get_subitem(Base, "u")
    with pytest.raises(AttributeError):
        utils.get_subitem(Base, "x:u")
    with pytest.raises(AttributeError):
        utils.get_subitem(Base, "x:li:key")


def test_ut0003_get_model_value():
    """Test get_model_value."""

    class Nested2(BaseModel):
        a: int

    class Nested(BaseModel):
        li: list[Nested2] = Field(default_factory=list)
        di: dict[str, Nested2] = Field(default_factory=dict)

    class Base(BaseModel):
        name: str
        x: Nested
        y: list[Nested] = Field(default_factory=list)
        z: dict[str, Nested] = Field(default_factory=dict)

    item = Base(
        name="test",
        x=Nested(li=[Nested2(a=1), Nested2(a=2)], di={"d0": Nested2(a=3)}),
        y=[
            Nested(li=[Nested2(a=4), Nested2(a=5)], di={"d1": Nested2(a=6)}),
            Nested(li=[Nested2(a=7), Nested2(a=8)], di={"d2": Nested2(a=9)}),
        ],
        z={
            "z0": Nested(li=[Nested2(a=10), Nested2(a=11)], di={"d3": Nested2(a=12)}),
            "z1": Nested(li=[Nested2(a=13), Nested2(a=14)], di={"d4": Nested2(a=15)}),
        },
    )

    assert utils.get_model_value(item, "name", "") == "test"
    assert utils.get_model_value(item, "a", "x:li:0") == 1  # noqa: PLR2004
    assert utils.get_model_value(item, "a", "x:di:d0") == 3  # noqa: PLR2004
    assert utils.get_model_value(item, "a", "z:0:li:1") == 11  # noqa: PLR2004
    assert utils.get_model_value(item, "a", "x:li:3", True) is None
    assert utils.get_model_value(item, "a", "x:di:3", True) is None

    with pytest.raises(IndexError):
        assert utils.get_model_value(item, "a", "x:li:3", False)
    with pytest.raises(IndexError):
        assert utils.get_model_value(item, "a", "x:di:3", False)

import pandas as pd
import pytest

from dash_pydantic_utils import Quantity, QuantityDtype


@pytest.mark.parametrize(
    "value, unit, prefix, expected",
    [
        (1.0, "m", "k", 1e3),
        (1.0, "m", "M", 1e6),
        (1.0, "m", "u", 1e-6),
        (1.0, "s", "G", 1e9),
    ],
)
def test_qt0001_prefix(value: float, unit: str, prefix: str, expected: float):
    """Test prefix conversion."""
    assert Quantity(value, f"{prefix}{unit}") == Quantity(expected, unit)


@pytest.mark.parametrize(
    "value1, unit1, value2, unit2",
    [
        (1.0, "m", 1.0, "m"),
        (1.0, "h", 60.0, "min"),
        (1.0, "h", 3600.0, "s"),
        (0.0, "C", 273.15, "K"),
    ],
)
def test_qt0002_unit_conversion(value1: float, unit1: str, value2: float, unit2: str):
    """Test unit conversion."""
    assert Quantity(value1, unit1) == Quantity(value2, unit2)


def test_qt0003_operations():
    """Test operations."""
    assert Quantity(1, "m") + Quantity(2, "m") == Quantity(3, "m")
    assert Quantity(1, "m") - Quantity(2, "m") == Quantity(-1, "m")
    assert Quantity(1, "m") * Quantity(2, "m") == Quantity(2, "m^2")
    assert Quantity(1, "km") / Quantity(30, "min") == Quantity(2, "km/h")
    assert Quantity(1, "m") ** 2 == Quantity(1, "m^2")
    assert Quantity(1, "km") ** 2 == Quantity(1, "km^2")
    assert Quantity(1, "km") ** 2 == Quantity(1e6, "m^2")
    assert Quantity(150, "USD/MWh") * Quantity(1, "MW") * Quantity(0.5, "h") == Quantity(75, "USD")
    with pytest.raises(ValueError):
        Quantity(1, "m").to("s")


def test_qt0004_pandas_series():
    """Test pandas series."""
    series = pd.Series([1, 2, 3], dtype=QuantityDtype(unit="m"))
    assert series.dtype == QuantityDtype(unit="m")
    assert series[0] == Quantity(1, "m")
    assert series.at[1] == Quantity(2, "m")
    assert series.loc[2] == Quantity(3, "m")
    assert series.qt.to("km").equals(pd.Series([1, 2, 3], dtype=QuantityDtype(unit="km")) / 1e3)
    with pytest.raises(ValueError):
        series.qt.to("s")
    with pytest.raises(ValueError):
        series.qt.to("kg")


def test_qt0005_pandas_series_operations():
    """Test pandas series operations."""
    series = pd.Series([1, 2, 3], dtype=QuantityDtype(unit="m"))
    assert (series + series).equals(pd.Series([2, 4, 6], dtype=QuantityDtype(unit="m")))
    assert (series * 2).equals(pd.Series([2, 4, 6], dtype=QuantityDtype(unit="m")))
    assert (2 * series).equals(pd.Series([2, 4, 6], dtype=QuantityDtype(unit="m")))
    assert (series - series).equals(pd.Series([0, 0, 0], dtype=QuantityDtype(unit="m")))
    assert (series * series).qt.to("m^2").equals(pd.Series([1, 4, 9], dtype=QuantityDtype(unit="m^2")))
    assert (series / series).qt.to("%").equals(pd.Series([100, 100, 100], dtype=QuantityDtype(unit="%")))
    assert (Quantity(50, "%") * series).equals(pd.Series([0.5, 1, 1.5], dtype=QuantityDtype(unit="m")))
    assert (series * Quantity(50, "%")).equals(pd.Series([0.5, 1, 1.5], dtype=QuantityDtype(unit="m")))

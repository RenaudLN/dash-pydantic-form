from __future__ import annotations

import re
from copy import deepcopy
from functools import lru_cache
from itertools import permutations
from types import SimpleNamespace
from typing import TYPE_CHECKING, ClassVar, TypedDict, TypeVar, overload

from pydantic import BaseModel, ConfigDict, field_validator
from typing_extensions import Self

if TYPE_CHECKING:
    import numpy as np
    import numpy.typing as npt
    import pandas as pd

    float_array = npt.NDArray[np.floating]
else:
    try:
        import numpy as np
        import numpy.typing as npt
        import pandas as pd

        float_array = npt.NDArray[np.floating]
    except ModuleNotFoundError:

        def raise_not_found():
            """Raise ModuleNotFoundError."""
            raise ModuleNotFoundError("numpy not found")

        float_array = float
        np = SimpleNamespace(ndarray=float, array=raise_not_found)
        pd = SimpleNamespace(Series=None, DataFrame=None)

T = TypeVar("T")


PREFIX_MULTIPLIERS = {
    "n": 1e-9,
    "u": 1e-6,
    "m": 1e-3,
    "c": 1e-2,
    "d": 1e-1,
    "D": 1e1,
    "h": 1e2,
    "k": 1e3,
    "M": 1e6,
    "G": 1e9,
    "T": 1e12,
}


class ISUnits(BaseModel):
    """International system units + money unit."""

    kg: int = 0
    m: int = 0
    s: int = 0
    A: int = 0
    K: int = 0
    mol: int = 0
    cd: int = 0
    """Extend IS units to money quantities."""
    USD: int = 0

    model_config = ConfigDict(extra="forbid")

    def is_empty(self) -> bool:
        """Check if the model is empty."""
        return all(getattr(self, field) == 0 for field in self.model_fields)

    def __hash__(self):
        """The hash function."""
        return hash(frozenset(self.model_dump().items()))

    def __mul__(self, other: ISUnits) -> ISUnits:
        """Multiply two IS units."""
        return self.__class__(**{field: getattr(self, field) + getattr(other, field) for field in self.model_fields})

    def __truediv__(self, other: ISUnits) -> ISUnits:
        """Divide two IS units."""
        return self.__class__(**{field: getattr(self, field) - getattr(other, field) for field in self.model_fields})

    def __pow__(self, other: int) -> ISUnits:
        """Raise to power."""
        return self.__class__(**{field: getattr(self, field) * other for field in self.model_fields})

    def __repr__(self) -> str:
        """Representation."""
        return f"ISUnits({self})"

    def __str__(self) -> str:
        """String representation."""
        return "*".join([unit + (f"^{pow}" if pow != 1 else "") for unit, pow in self.model_dump().items() if pow])

    @classmethod
    def from_str(cls, unit_str: str) -> ISUnits:
        """Create from string."""
        return cls(
            **{
                unit: int(pow) if pow else 1
                for unit, pow in re.findall(r"(kg|m|s|K|A|mol|cd|USD)(?:\^(\-*\d+))*(?:\*|$)", unit_str)
            }
        )


class NameData(TypedDict):
    """Name data."""

    unit: str
    category: str


class Quantity(BaseModel):
    """Quantity model."""

    value: float | float_array
    """Value or array of values quantified by the unit."""
    unit: str
    """Unit of the quantity."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    conversion: ClassVar[dict[ISUnits, dict[str, int | float | tuple[int | float, int | float]]]] = {
        # Unitless
        ISUnits(): {
            "": 1,
            "%": 0.01,
            "‰": 0.001,
        },
        # Money
        ISUnits(USD=1): {
            "USD": 1,
            "EUR": 1.07,
            "GBP": 1.30,
            "AUD": 0.67,
            "JPY": 0.0067,
            "CAD": 0.73,
            "CHF": 1.16,
            "CNY": 0.14,
            "NZD": 0.61,
            "ZAR": 0.057,
            "INR": 0.012,
        },
        # Length
        ISUnits(m=1): {
            "m": 1,
            "mi": 1609.344,
            "NM": 1852,
            "ft": 0.3048,
            "in": 0.0254,
        },
        # Mass
        ISUnits(kg=1): {
            "kg": 1,
            "g": 0.001,
            "lb": 0.453592,
            "oz": 0.0283495,
        },
        # Time
        ISUnits(s=1): {
            "s": 1,
            "min": 60,
            "h": 3600,
            "d": 86400,
        },
        # Force
        ISUnits(kg=1, m=1, s=-2): {
            "N": 1,
        },
        # Pressure
        ISUnits(kg=1, m=-1, s=-2): {
            "Pa": 1,
            "atm": 101325,
            "psi": 6894.76,
        },
        # Energy
        ISUnits(kg=1, m=2, s=-2): {
            "J": 1,
            "Wh": 3600,
            "cal": 4.184,
        },
        # Frequency
        ISUnits(s=-1): {
            "Hz": 1,
        },
        # Temperature
        ISUnits(K=1): {
            "K": 1,
            "C": (1, 273.15),
            "F": (5 / 9, 273.15 - 5 / 9 * 32),
        },
        # Power
        ISUnits(kg=1, m=2, s=-3): {
            "W": 1,
            "hp": 745.7,
        },
        # Area
        ISUnits(m=2): {
            "m^2": 1,
            "ha": 10000,
            "acre": 4046.86,
            "in^2": 0.00064516,
            "ft^2": 0.092903,
            "mi^2": 2589988.1,
        },
        # Volume
        ISUnits(m=3): {
            "m^3": 1,
            "L": 0.001,
            "gal": 0.00378541,
        },
        # Speed
        ISUnits(m=1, s=-1): {
            "m/s": 1,
            "mph": 0.44704,
            "kph": 1 / 3.6,
        },
        # Acceleration
        ISUnits(m=1, s=-2): {
            "m/s^2": 1,
        },
    }
    """Conversion factors from unit to IS unit."""

    names: ClassVar[dict[ISUnits, NameData]] = {
        ISUnits(): {"category": "Unitless", "unit": ""},
        ISUnits(USD=1): {"category": "Money", "unit": "USD"},
        ISUnits(m=1): {"category": "Length", "unit": "m"},
        ISUnits(kg=1): {"category": "Mass", "unit": "kg"},
        ISUnits(s=1): {"category": "Time", "unit": "s"},
        ISUnits(K=1): {"category": "Temperature", "unit": "K"},
        ISUnits(s=-1): {"category": "Frequency", "unit": "Hz"},
        ISUnits(kg=1, m=1, s=-2): {"category": "Force", "unit": "N"},
        ISUnits(kg=1, m=-1, s=-2): {"category": "Pressure", "unit": "Pa"},
        ISUnits(kg=1, m=2, s=-2): {"category": "Energy", "unit": "J"},
        ISUnits(kg=1, m=2, s=-3): {"category": "Power", "unit": "W"},
        ISUnits(m=2): {"category": "Area", "unit": "m^2"},
        ISUnits(m=3): {"category": "Volume", "unit": "m^3"},
        ISUnits(m=1, s=-1): {"category": "Speed", "unit": "m/s"},
        ISUnits(m=1, s=-2): {"category": "Acceleration", "unit": "m/s^2"},
    }
    """Category names and default units for each IS unit."""

    def __init__(self, value: float | float_array, unit: str):
        if isinstance(value, list):
            value = np.array(value)
        super().__init__(value=value, unit=unit)

    @property
    def unit_multiplier(self) -> tuple[float, float]:
        """Get multiplier."""
        return self.get_unit_info(self.unit)[1]

    @property
    def i_s_units(self) -> ISUnits:
        """Get IS units."""
        return self.get_unit_info(self.unit)[0]

    @property
    def category(self) -> str:
        """Get category."""
        return self.get_unit_info(self.unit)[2]

    @classmethod
    @lru_cache
    def get_unit_info(cls, unit: str) -> tuple[ISUnits, tuple[float, float], str]:
        """Get information about a given unit."""
        i_s_pattern = re.compile("^((kg|m|s|K|USD|A|mol|cd)(?:\^(\-*\d+))*(?:\*|$))+$")
        # IS units repr
        if re.match(i_s_pattern, unit):
            i_s_units = ISUnits.from_str(unit)
            return i_s_units, (1, 0), cls.names.get(i_s_units, {}).get("category", "Quantity")

        all_units = sum([list(units) for units in cls.conversion.values()], [])

        def trim_prefixes(unit: str) -> tuple[str, str | None]:
            if unit in all_units:
                return unit, None
            for prefix in PREFIX_MULTIPLIERS:
                if unit.startswith(prefix):
                    base_unit = unit.removeprefix(prefix)
                    if base_unit in all_units:
                        return base_unit, prefix
            raise ValueError(f"Unsupported unit: {unit}")

        i_s_units = ISUnits()
        factor, base = 1.0, 0.0
        for i, unit_ in enumerate(unit.split("/")):
            base_unit, prefix = trim_prefixes(unit_)
            i_s_units_, conversion_ = next(
                (i_s_units, group[base_unit]) for i_s_units, group in cls.conversion.items() if base_unit in group
            )
            if isinstance(conversion_, tuple):
                factor_, base_ = conversion_
                if i > 0 and base_ != 0:
                    raise NotImplementedError("Not supported: unit with non-zero base in denominator")
            else:
                factor_, base_ = conversion_, 0

            if prefix:
                prefix_multiplier = PREFIX_MULTIPLIERS[prefix]
                # Handle cases where prefix multiplier is brought to a power (e.g area, volume)
                if (
                    re.match(i_s_pattern, base_unit)
                    and sum(v != 0 for v in i_s_units_.model_dump().values()) == 1
                    and abs(pow := next(v for v in i_s_units_.model_dump().values() if v != 0)) > 1
                ):
                    prefix_multiplier = prefix_multiplier**pow

                factor_ *= prefix_multiplier

            if i == 0:
                i_s_units = i_s_units_
                factor = factor_
                base = base_
            else:
                i_s_units /= i_s_units_
                factor /= factor_

        return i_s_units, (factor, base), cls.names.get(i_s_units, {}).get("category", "Quantity")

    @property
    def unit_parts(self) -> dict[ISUnits, str]:
        """Get unit parts."""
        return {self.get_unit_info(part)[0]: part for part in self.unit.split("/")}

    @field_validator("unit")
    def validate_unit(cls, unit: str) -> str:
        """Validate unit."""
        _ = cls.get_unit_info(unit)
        return unit

    def _to_default_unit(self) -> float | float_array:
        """Convert to default unit."""
        factor, base = self.unit_multiplier
        return self.value * factor + base

    def _from_default_unit(self, value) -> float:
        """Convert from default unit."""
        factor, base = self.unit_multiplier
        return (value - base) / factor

    def to(self, unit: str) -> Self:
        """Convert to another unit."""
        if self.get_unit_info(unit)[0] != self.i_s_units:
            self_repr = self.category if self.category != "Quantity" else str(self.unit)
            other_info = self.get_unit_info(unit)
            other_repr = other_info[2] if other_info[2] != "Quantity" else str(unit)
            raise ValueError(f"Cannot convert between different types: {self_repr} <-/-> {other_repr}.")
        default_unit_value = self._to_default_unit()
        factor, base = self.get_unit_info(unit)[1]
        return self.__class__(unit=unit, value=(default_unit_value - base) / factor)

    @overload
    def __add__(self, other: pd.DataFrame) -> pd.DataFrame: ...
    @overload
    def __add__(self, other: pd.Series) -> pd.Series: ...
    @overload
    def __add__(self, other: Self | float | int | float_array) -> Self: ...
    def __add__(
        self, other: Self | float | int | float_array | pd.Series | pd.DataFrame
    ) -> Self | pd.Series | pd.DataFrame:
        """Add two quantities, they need to be of the same category."""
        if pd.DataFrame and isinstance(other, pd.DataFrame):
            return other.assign(**{col: self + other[col] for col in other.columns})

        if pd.Series and isinstance(other, pd.Series):
            from .pandas_engine import QuantityDtype

            other_unit = getattr(other.dtype, "unit", "")
            val = self + Quantity(other.to_numpy(), other_unit)
            return pd.Series(val.value, index=other.index, dtype=QuantityDtype(unit=val.unit))

        if isinstance(other, float | int | np.ndarray):
            return self.__class__(self.value + other, self.unit)

        if isinstance(other, Quantity):
            if other.i_s_units != self.i_s_units:
                raise ValueError("Cannot add quantities of different types.")

            return self.__class__(
                self._from_default_unit(self._to_default_unit() + other._to_default_unit()), self.unit
            )

        raise NotImplementedError

    @overload
    def __sub__(self, other: pd.DataFrame) -> pd.DataFrame: ...
    @overload
    def __sub__(self, other: pd.Series) -> pd.Series: ...
    @overload
    def __sub__(self, other: Self | float | int | float_array) -> Self: ...
    def __sub__(
        self, other: Self | float | int | float_array | pd.Series | pd.DataFrame
    ) -> Self | pd.Series | pd.DataFrame:
        """Add two quantities, they need to be of the same category."""
        if pd.DataFrame and isinstance(other, pd.DataFrame):
            return other.assign(**{col: self - other[col] for col in other.columns})

        if pd.Series and isinstance(other, pd.Series):
            from .pandas_engine import QuantityDtype

            other_unit = getattr(other.dtype, "unit", "")
            val = self - Quantity(other.to_numpy(), other_unit)
            return pd.Series(val.value, index=other.index, dtype=QuantityDtype(unit=val.unit))

        if isinstance(other, float | int | np.ndarray):
            return self.__class__(unit=self.unit, value=self.value + other)

        if isinstance(other, Quantity):
            if self.i_s_units != other.i_s_units:
                raise ValueError("Cannot subtract quantities of different types.")

            return self.__class__(
                unit=self.unit,
                value=self._from_default_unit(self._to_default_unit() - other._to_default_unit()),
            )

        raise NotImplementedError

    def _get_output_unit(self, other: Self | float | int | float_array, out_i_s_units: ISUnits) -> str | None:
        all_parts = deepcopy(self.unit_parts)
        if isinstance(other, Quantity):
            all_parts = deepcopy(other.unit_parts) | all_parts

        if out_i_s_units in all_parts:
            return all_parts[out_i_s_units]

        unit_parts = next(
            (
                (all_parts.get(i1) or v1["unit"], all_parts.get(i2) or v2["unit"])
                for (i1, v1), (i2, v2) in permutations(self.names.items(), 2)
                if i1 / i2 == out_i_s_units and (i1 in all_parts or i2 in all_parts)
            ),
            None,
        )

        if unit_parts:
            return "/".join(unit_parts)

        return None

    @overload
    def __mul__(self, other: pd.DataFrame) -> pd.DataFrame: ...
    @overload
    def __mul__(self, other: pd.Series) -> pd.Series: ...
    @overload
    def __mul__(self, other: Self | float | int | float_array) -> Self: ...
    def __mul__(
        self, other: Self | float | int | float_array | pd.Series | pd.DataFrame
    ) -> Self | pd.Series | pd.DataFrame:
        """Multiply a quantity with a number."""
        if pd.DataFrame and isinstance(other, pd.DataFrame):
            return other.assign(**{col: self * other[col] for col in other.columns})

        if pd.Series and isinstance(other, pd.Series):
            from .pandas_engine import QuantityDtype

            other_unit = getattr(other.dtype, "unit", "")
            val = self * Quantity(other.to_numpy(), other_unit)
            return pd.Series(val.value, index=other.index, dtype=QuantityDtype(unit=val.unit))

        if isinstance(other, float | int | np.ndarray):
            return self.__class__(unit=self.unit, value=self.value * other)

        if isinstance(other, Quantity):
            i_s_units = self.i_s_units * other.i_s_units
            out = self.__class__(
                value=self._to_default_unit() * other._to_default_unit(),
                unit=self.names.get(i_s_units, {}).get("unit", str(i_s_units)),
            )
            output_unit = self._get_output_unit(other, i_s_units)
            if output_unit is not None:
                out = out.to(output_unit)
            return out

        raise NotImplementedError

    def __rmul__(self, other: float | int | float_array | pd.Series | pd.DataFrame) -> Self | pd.Series | pd.DataFrame:
        """Multiply a quantity with a number.
        NOTE: No pandas support for __rmul__.
        """
        if not isinstance(other, float | int | np.ndarray | pd.Series | pd.DataFrame):
            raise TypeError("Can only multiply numbers by quantities")
        return self.__mul__(other)

    @overload
    def __truediv__(self, other: pd.DataFrame) -> pd.DataFrame: ...
    @overload
    def __truediv__(self, other: pd.Series) -> pd.Series: ...
    @overload
    def __truediv__(self, other: Self | float | int | float_array) -> Self: ...
    def __truediv__(
        self, other: Self | float | int | float_array | pd.Series | pd.DataFrame
    ) -> Self | pd.Series | pd.DataFrame:
        """Divide a quantity with a number or another quantity."""
        if pd.DataFrame and isinstance(other, pd.DataFrame):
            return other.assign(**{col: self / other[col] for col in other.columns})

        if pd.Series and isinstance(other, pd.Series):
            from .pandas_engine import QuantityDtype

            other_unit = getattr(other.dtype, "unit", "")
            val = self / Quantity(other.to_numpy(), other_unit)
            return pd.Series(val.value, index=other.index, dtype=QuantityDtype(unit=val.unit))

        if isinstance(other, float | int | np.ndarray):
            return self.__class__(unit=self.unit, value=self.value / other)

        if isinstance(other, Quantity):
            i_s_units = self.i_s_units / other.i_s_units
            out = self.__class__(
                value=self._to_default_unit() / other._to_default_unit(),
                unit=self.names.get(i_s_units, {}).get("unit", str(i_s_units)),
            )
            output_unit = self._get_output_unit(other, i_s_units)
            if output_unit is not None:
                out = out.to(output_unit)
            return out

        raise NotImplementedError

    def __rtruediv__(self, other: float | int | float_array) -> Self:
        """Divide a number by a quantity.
        NOTE: No pandas support for __rtruediv__.
        """
        if not isinstance(other, float | int | np.ndarray):
            raise TypeError("Can only divide numbers by quantities")

        i_s_units = self.i_s_units**-1
        return self.__class__(
            value=other / self._to_default_unit(),
            unit=self.names.get(i_s_units, {}).get("unit", str(i_s_units)),
        )

    def __pow__(self, other: int) -> Self:
        """Raise a quantity to a power."""
        if not isinstance(other, int):
            raise TypeError("Can only raise a quantity to an integer power")

        i_s_units = self.i_s_units**other
        return self.__class__(
            value=self._to_default_unit() ** other,
            unit=self.names.get(i_s_units, {}).get("unit", str(i_s_units)),
        )

    def __eq__(self, other) -> bool:
        """Equality."""
        if not isinstance(other, Quantity) or self.i_s_units != other.i_s_units:
            return False
        self_default = self._to_default_unit()
        other_default = other._to_default_unit()
        if isinstance(self_default, float | int):
            return self_default == other_default
        return bool((self_default == other_default).all())

    def __neg__(self) -> Self:
        """Negate."""
        return self.__class__(unit=self.unit, value=-self.value)

    def __repr__(self) -> str:
        """Representation."""
        return f"{self.category}({self})"

    def __str__(self) -> str:
        """String representation."""
        if not isinstance(self.value, float):
            return f"{self.value}, {self.unit}"
        base = f"{self.value:.3f}" if abs(self.value) >= 1e-2 or self.value == 0 else f"{self.value:.2e}"  # noqa: PLR2004
        if "." in base:
            base = base.rstrip("0").rstrip(".")
        return f"{base} {self.unit}" if self.unit else base

    def __len__(self) -> int | None:
        """Length."""
        return None if isinstance(self.value, float | int) else len(self.value)

    def __iter__(self):
        """Iterator."""
        if isinstance(self.value, float | int):
            yield self
        else:
            for value in self.value:
                yield self.__class__(unit=self.unit, value=value)

    @property
    def dtype(self):
        """Pandas dtype associated with this value."""
        from .pandas_engine import QuantityDtype

        return QuantityDtype(unit=self.unit)

    @classmethod
    def register_unit_rates(
        cls,
        i_s_units: ISUnits | str,
        unit_name: str,
        rate: float = 1.0,
        category: str | None = None,
    ) -> None:
        """Set currency rates."""
        if isinstance(i_s_units, str):
            i_s_units = ISUnits.from_str(i_s_units)

        if i_s_units not in cls.conversion:
            cls.conversion[i_s_units] = {}
        cls.conversion[i_s_units][unit_name] = rate
        if i_s_units not in cls.names:
            if category is None:
                raise ValueError("Category must be specified for new units")
            cls.names[i_s_units] = {"category": category, "unit": unit_name}

        cls.get_unit_info.cache_clear()

import re
from collections.abc import Mapping
from functools import lru_cache
from typing import ClassVar, TypedDict, Union

from pydantic import BaseModel, ConfigDict, field_validator

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

    def __mul__(self, other: "ISUnits") -> "ISUnits":
        """Multiply two IS units."""
        return self.__class__(**{field: getattr(self, field) + getattr(other, field) for field in self.model_fields})

    def __truediv__(self, other: "ISUnits") -> "ISUnits":
        """Divide two IS units."""
        return self.__class__(**{field: getattr(self, field) - getattr(other, field) for field in self.model_fields})

    def __pow__(self, other: int) -> "ISUnits":
        """Raise to power."""
        return self.__class__(**{field: getattr(self, field) * other for field in self.model_fields})

    def __repr__(self) -> str:
        """Representation."""
        return f"ISUnits({self})"

    def __str__(self) -> str:
        """String representation."""
        return "*".join([unit + (f"^{pow}" if pow != 1 else "") for unit, pow in self.model_dump().items() if pow])

    @classmethod
    def from_str(cls, unit_str: str) -> "ISUnits":
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

    value: float
    unit: str | None

    """Conversion factors from unit to IS unit."""
    conversion: ClassVar[dict[ISUnits, Mapping[str, float]]] = {
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
    }
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
    }

    def __init__(self, value: float, unit: str):
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
            return i_s_units, (1, 0), cls.names.get(i_s_units, {}).get("category", "Generic")

        all_units = sum([list(units) for units in cls.conversion.values()], [])

        def trim_prefixes(unit: str) -> str:
            if unit in all_units:
                return unit, None
            for prefix in PREFIX_MULTIPLIERS:
                if unit.startswith(prefix):
                    base_unit = unit.removeprefix(prefix)
                    if base_unit in all_units:
                        return base_unit, prefix
            raise ValueError(f"Unsupported unit: {unit}")

        base_unit, prefix = trim_prefixes(unit)

        i_s_units, conversion = next(
            (i_s_units, group[base_unit]) for i_s_units, group in cls.conversion.items() if base_unit in group
        )

        if isinstance(conversion, tuple):
            factor, base = conversion
        else:
            factor, base = conversion, 0

        if prefix:
            prefix_multiplier = PREFIX_MULTIPLIERS[prefix]
            # Handle cases where prefix multiplier is brought to a power (e.g area, volume)
            if (
                re.match(i_s_pattern, base_unit)
                and sum(v != 0 for v in i_s_units.model_dump().values()) == 1
                and abs(pow := next(v for v in i_s_units.model_dump().values() if v != 0)) > 1
            ):
                prefix_multiplier = prefix_multiplier**pow

            factor *= prefix_multiplier

        return i_s_units, (factor, base), cls.names.get(i_s_units, {}).get("category", "Generic")

    @field_validator("unit")
    def validate_unit(cls, unit: str) -> str:
        """Validate unit."""
        _ = cls.get_unit_info(unit)
        return unit

    def _to_default_unit(self) -> float:
        """Convert to default unit."""
        factor, base = self.unit_multiplier
        return self.value * factor + base

    def _from_default_unit(self, value) -> float:
        """Convert from default unit."""
        factor, base = self.unit_multiplier
        return (value - base) / factor

    def to(self, unit: str) -> "Quantity":
        """Convert to another unit."""
        default_unit_value = self._to_default_unit()
        factor, base = self.get_unit_info(unit)[1]
        return self.__class__(unit=unit, value=(default_unit_value - base) / factor)

    def __add__(self, other: Union["Quantity", float, int]) -> "Quantity":
        """Add two quantities, they need to be of the same category."""
        if isinstance(other, float | int):
            return self.__class__(unit=self.unit, value=self.value + other)

        if other.i_s_units != self.i_s_units:
            raise ValueError("Cannot add quantities of different types.")

        return self.__class__(
            unit=self.unit,
            value=self._from_default_unit(self._to_default_unit() + other._to_default_unit()),
        )

    def __sub__(self, other: Union["Quantity", float, int]) -> "Quantity":
        """Add two quantities, they need to be of the same category."""
        if isinstance(other, float | int):
            return self.__class__(unit=self.unit, value=self.value + other)

        if self.i_s_units != other.i_s_units:
            raise ValueError("Cannot subtract quantities of different types.")

        return self.__class__(
            unit=self.unit,
            value=self._from_default_unit(self._to_default_unit() - other._to_default_unit()),
        )

    def __mul__(self, other: Union["Quantity", float, int]) -> "Quantity":
        """Multiply a quantity with a number."""
        if isinstance(other, float | int):
            return self.__class__(unit=self.unit, value=self.value * other)

        i_s_units = self.i_s_units * other.i_s_units
        if i_s_units.is_empty():
            return self._to_default_unit() / other._to_default_unit()

        return self.__class__(
            value=self._to_default_unit() * other._to_default_unit(),
            unit=self.names.get(i_s_units, {}).get("unit", str(i_s_units)),
        )

    def __rmul__(self, other: float | int) -> "Quantity":
        """Multiply a quantity with a number."""
        return self.__mul__(other)

    def __truediv__(self, other: Union["Quantity", float, int]) -> Union["Quantity", float]:
        """Divide a quantity with a number or another quantity."""
        if isinstance(other, float | int):
            return self.__class__(unit=self.unit, value=self.value / other)

        i_s_units = self.i_s_units / other.i_s_units
        if i_s_units.is_empty():
            return self._to_default_unit() / other._to_default_unit()

        return self.__class__(
            value=self._to_default_unit() / other._to_default_unit(),
            unit=self.names.get(i_s_units, {}).get("unit", str(i_s_units)),
        )

    def __rtruediv__(self, other: float | int):
        """Divide a number by a quantity."""
        if not isinstance(other, float | int):
            raise TypeError("Can only divide numbers by quantities")

        i_s_units = self.i_s_units**-1
        return self.__class__(
            value=other / self._to_default_unit(),
            unit=self.names.get(i_s_units, {}).get("unit", str(i_s_units)),
        )

    def __pow__(self, other: int) -> "Quantity":
        """Raise a quantity to a power."""
        if not isinstance(other, int):
            raise TypeError("Can only raise a quantity to an integer power")

        i_s_units = self.i_s_units**other
        return self.__class__(
            value=self._to_default_unit() ** other,
            unit=self.names.get(i_s_units, {}).get("unit", str(i_s_units)),
        )

    def __eq__(self, other: "Quantity") -> bool:
        """Equality."""
        if not isinstance(other, Quantity) or self.i_s_units != other.i_s_units:
            return False
        return self._to_default_unit() == other._to_default_unit()

    def __neg__(self) -> "Quantity":
        """Negate."""
        return self.__class__(unit=self.unit, value=-self.value)

    def __repr__(self) -> str:
        """Representation."""
        return f"{self.category}({self})"

    def __str__(self) -> str:
        """String representation."""
        base = f"{self.value:.3f}" if abs(self.value) >= 1e-2 or self.value == 0 else f"{self.value:.2e}"  # noqa: PLR2004
        if "." in base:
            base = base.rstrip("0").rstrip(".")
        return f"{base} {self.unit}" if self.unit else base

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
            cls.names[i_s_units] = {"category": category, "unit": unit_name}

        cls.get_unit_info.cache_clear()

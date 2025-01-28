# ruff: noqa
# TODO: ^
from __future__ import annotations

import re
from typing import ClassVar

import numpy as np
import numpy.typing as npt
import pandas as pd
from pandas.core import ops
from pandas.core.algorithms import take
from pandas.core.arrays.numeric import NumericArray, NumericDtype
from pandas.core.dtypes.base import register_extension_dtype
from pandas.core.dtypes.common import is_bool, is_float_dtype, pandas_dtype
from pandas.core.dtypes.missing import isna, notna
from pandas.core.indexers import check_array_indexer
from pandas.util._decorators import cache_readonly

from .quantity import ISUnits
from .quantity import Quantity as Quantity_


class Quantity(Quantity_):
    value: float | np.ndarray
    model_config = {"arbitrary_types_allowed": True}

    def __str__(self) -> str:
        if isinstance(self.value, np.ndarray):
            return f"{self.value}, {self.unit}"
        return super().__str__()

    @property
    def dtype(self):
        return QuantityDtype(unit=self.unit)


@register_extension_dtype
class QuantityDtype(NumericDtype):
    type = np.float64
    name: ClassVar[str] = "Quantity"
    _metadata = ("unit",)
    _default_np_dtype = np.dtype(np.float64)
    _checker = is_float_dtype

    @property
    def name(self) -> str:
        return f"Quantity[{self.unit}]"

    def __init__(self, unit: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.unit = unit

    def __repr__(self):
        return f"QuantityDtype({self.unit})"

    @classmethod
    def construct_array_type(cls) -> type[QuantityArray]:
        """
        Return the array type associated with this dtype.

        Returns
        -------
        type
        """
        return QuantityArray

    @classmethod
    def construct_from_string(cls, string: str):
        try:
            unit = re.findall(r"^Quantity\[(.*)\]$", string)[0]
            return cls(unit=unit)
        except Exception as exc:
            raise TypeError(f"Cannot construct QuantityDtype from {string}") from exc

    @classmethod
    def _safe_cast(cls, values: np.ndarray, dtype: np.dtype, copy: bool) -> np.ndarray:
        """
        Safely cast the values to the given dtype.

        "safe" in this context means the casting is lossless.
        """
        # This is really only here for compatibility with IntegerDtype
        # Here for compat with IntegerDtype
        return values.astype(dtype, copy=copy)

    def __from_arrow__(self, array, **kwargs):
        import pyarrow
        from pandas.core.arrays.arrow._arrow_utils import pyarrow_array_to_numpy_and_mask

        array_class = self.construct_array_type()

        pyarrow_type = pyarrow.from_numpy_dtype(self.type)
        if not array.type.equals(pyarrow_type) and not pyarrow.types.is_null(array.type):
            # test_from_arrow_type_error raise for string, but allow
            #  through itemsize conversion GH#31896
            rt_dtype = pandas_dtype(array.type.to_pandas_dtype())
            if rt_dtype.kind not in "iuf":
                # Could allow "c" or potentially disallow float<->int conversion,
                #  but at the moment we specifically test that uint<->int works
                raise TypeError(f"Expected array of {self} type, got {array.type} instead")

            array = array.cast(pyarrow_type)

        if isinstance(array, pyarrow.ChunkedArray):
            # TODO this "if" can be removed when requiring pyarrow >= 10.0, which fixed
            # combine_chunks for empty arrays https://github.com/apache/arrow/pull/13757
            array = pyarrow.array([], type=array.type) if array.num_chunks == 0 else array.combine_chunks()

        data, mask = pyarrow_array_to_numpy_and_mask(array, dtype=self.numpy_dtype)
        return array_class(self.unit, data.copy(), ~mask, copy=False)

    def _get_common_dtype(self, dtypes: list):
        if not all(isinstance(dtype, QuantityDtype) for dtype in dtypes):
            raise ValueError("No common dtype between Quantity and non-Quantity types")
        raise ValueError("No common dtype between Quantity with different units")

    def __eq__(self, other):
        return isinstance(other, QuantityDtype) and self.unit == other.unit

    def __hash__(self):
        return hash(str(self))


class QuantityArray(NumericArray):
    _dtype_cls = QuantityDtype
    _internal_fill_value = np.nan

    @cache_readonly
    def dtype(self) -> NumericDtype:
        return QuantityDtype(unit=self.unit)

    def __init__(self, unit: str, values: np.ndarray, mask: npt.NDArray[np.bool_], copy: bool = False):
        self.unit = unit
        super().__init__(values, mask, copy=copy)

    @classmethod
    def _from_sequence(cls, scalars, *, dtype=None, copy: bool = False):
        values, mask = cls._coerce_to_array(scalars, dtype=dtype, copy=copy)
        return cls(unit=dtype.unit, values=values, mask=mask)

    def _arith_method(self, other, op):
        pd_op = ops.get_array_op(op)
        self_q = Quantity(value=self._data, unit=self.dtype.unit)
        mask = self._mask
        if isinstance(other, QuantityArray):
            other_q = Quantity(value=other._data, unit=other.dtype.unit)
            mask |= other._mask
        elif isinstance(other, Quantity | float | int):
            other_q = other
        result = pd_op(self_q, other_q)
        if not isinstance(result, Quantity):
            result = Quantity(value=result, unit="")
        return self._maybe_mask_result(result, mask)

    def _maybe_mask_result(self, result: Quantity, mask: np.ndarray):
        if not isinstance(result, Quantity):
            result = Quantity(value=result, unit=self.unit)
        return QuantityArray(result.unit, result.value, mask, copy=False)

    def copy(self):
        data = self._data.copy()
        mask = self._mask.copy()
        return self.__class__(unit=self.unit, values=data, mask=mask)

    def to(self, other_unit: str):
        new_value = Quantity(value=self._data, unit=self.unit).to(other_unit).value
        return self.__class__(value=new_value, unit=other_unit)

    def __repr__(self):
        return repr(Quantity(value=self._data, unit=self.unit))

    def __getitem__(self, item):
        item = check_array_indexer(self, item)

        newmask = self._mask[item]
        if is_bool(newmask):
            # This is a scalar indexing
            if newmask:
                return self.dtype.na_value
            return Quantity(value=self._data[item], unit=self.unit)

        return self.__class__(self.unit, self._data[item], newmask)

    def take(
        self,
        indexer,
        *,
        allow_fill: bool = False,
        fill_value=None,
        axis=0,
    ):
        # we always fill with 1 internally
        # to avoid upcasting
        data_fill_value = self._internal_fill_value if isna(fill_value) else fill_value
        result = take(
            self._data,
            indexer,
            fill_value=data_fill_value,
            allow_fill=allow_fill,
            axis=axis,
        )

        mask = take(self._mask, indexer, fill_value=True, allow_fill=allow_fill, axis=axis)

        # if we are filling
        # we only fill where the indexer is null
        # not existing missing values
        # TODO(jreback) what if we have a non-na float as a fill value?
        if allow_fill and notna(fill_value):
            fill_mask = np.asarray(indexer) == -1
            result[fill_mask] = fill_value
            mask = mask ^ fill_mask

        return self.__class__(self.unit, result, mask)

    @classmethod
    def _concat_same_type(
        cls,
        to_concat,
        axis=0,
    ):
        unit = to_concat[0].unit
        if not all(x.unit == unit for x in to_concat):
            raise ValueError("Can only concatenate Quantity with the same unit")
        data = np.concatenate([x._data for x in to_concat], axis=axis)
        mask = np.concatenate([x._mask for x in to_concat], axis=axis)
        return cls(unit, data, mask)


@pd.api.extensions.register_series_accessor("qt")
class QuantityAccessor:
    def __init__(self, pandas_obj: pd.Series):
        self._obj = pandas_obj

    def to(self, other_unit: str):
        new_value = Quantity(value=self._obj.to_numpy(), unit=self._obj.dtype.unit).to(other_unit).value
        return pd.Series(new_value, index=self._obj.index, dtype=QuantityDtype(unit=other_unit))


@pd.api.extensions.register_dataframe_accessor("qt")
class QuantityAccessor:
    def __init__(self, pandas_obj: pd.DataFrame):
        self._obj = pandas_obj

    def to(self, other_unit: str):
        if not all(isinstance(dtype, QuantityDtype) for dtype in self._obj.dtypes.values):
            raise ValueError("Can only convert a DataFrame of Quantity")
        if len(set(self._obj.dtypes.values)) != 1:
            raise ValueError("Can only convert a DataFrame of Quantity with the same unit")

        unit = self._obj.dtypes.values[0].unit
        new_value = Quantity(value=self._obj.to_numpy(), unit=unit).to(other_unit).value
        return pd.DataFrame(
            new_value, index=self._obj.index, columns=self._obj.columns, dtype=QuantityDtype(unit=other_unit)
        )

    def find(self, unit: str | None = None, category: str | None = None, i_s_units: ISUnits | str | None = None):
        if not any([unit, category, i_s_units]):
            return self._obj[[col for col, dtype in self._obj.dtypes.items() if isinstance(dtype, QuantityDtype)]]

        if unit:
            return self._obj[self._obj.dtypes[self._obj.dtypes == QuantityDtype(unit)].index]
        if isinstance(i_s_units, str):
            i_s_units = ISUnits.from_str(i_s_units)
        cols = []
        for col, dtype in self._obj.dtypes.items():
            if isinstance(dtype, QuantityDtype):
                col_i_s_units, _, col_category = Quantity.get_unit_info(dtype.unit)
                if (category and col_category == category) or (i_s_units and col_i_s_units == i_s_units):
                    cols.append(col)
        return self._obj[cols]

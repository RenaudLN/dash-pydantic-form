from pydantic import BaseModel

from .quantity import Quantity

try:
    from .pandas_engine import QuantityDtype
except ModuleNotFoundError:
    QuantityDtype = None

BaseModel.__getitem__ = lambda self, key: self.__dict__.get(key)

__all__ = ["Quantity", "QuantityDtype"]

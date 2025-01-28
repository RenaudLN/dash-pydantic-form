from pydantic import BaseModel

try:
    from .pandas import Quantity, QuantityDtype
except ModuleNotFoundError:
    from .quantity import Quantity

    QuantityDtype = None

BaseModel.__getitem__ = lambda self, key: self.__dict__.get(key)

__all__ = ["Quantity", "QuantityDtype"]

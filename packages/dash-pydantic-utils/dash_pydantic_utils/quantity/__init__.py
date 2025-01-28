try:
    from .pandas import Quantity
except ModuleNotFoundError:
    from .quantity import Quantity

__all__ = ["Quantity"]

import logging

from .base_fields import CheckboxField as Checkbox
from .base_fields import ChecklistField as Checklist
from .base_fields import ColorField as Color
from .base_fields import DateField as Date
from .base_fields import DatetimeField as Datetime
from .base_fields import JsonField as Json
from .base_fields import MultiSelectField as MultiSelect
from .base_fields import NumberField as Number
from .base_fields import PasswordField as Password
from .base_fields import RadioItemsField as RadioItems
from .base_fields import RangeField as Range
from .base_fields import SegmentedControlField as SegmentedControl
from .base_fields import SelectField as Select
from .base_fields import SliderField as Slider
from .base_fields import SwitchField as Switch
from .base_fields import TextareaField as Textarea
from .base_fields import TextField as Text
from .base_fields import TimeField as Time
from .dict_field import DictField as Dict
from .list_field import ListField as List
from .markdown_field import MarkdownField as Markdown
from .model_field import ModelField as Model
from .table_field import TableField as Table
from .transferlist_field import TransferListField as TransferList


def deprecated_field_factory(name: str, base_class: type):
    """Create a field class with a deprecation warning message."""
    old_post_init = getattr(base_class, "model_post_init", None)

    def post_init(self, _context):
        logging.warning(f"{name} is deprecated, use {base_class.__name__.removesuffix('Field')} instead.")
        if old_post_init is not None:
            old_post_init(self, _context)

    newclass = type(name, (base_class,), {"model_post_init": post_init})
    return newclass


# Backwards compatibility
ModelList = deprecated_field_factory("ModelList", List)
EditableTable = deprecated_field_factory("EditableTable", Table)

__all__ = [
    "Checkbox",
    "Checklist",
    "Color",
    "Date",
    "Datetime",
    "Dict",
    "EditableTable",
    "Json",
    "List",
    "Markdown",
    "Model",
    "ModelList",
    "MultiSelect",
    "Number",
    "Password",
    "RadioItems",
    "Range",
    "SegmentedControl",
    "Select",
    "Slider",
    "Switch",
    "Table",
    "Textarea",
    "Text",
    "Time",
    "TransferList",
]

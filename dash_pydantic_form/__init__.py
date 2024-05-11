from pydantic import BaseModel

from dash_pydantic_form.form_section import FormSection, Sections
from dash_pydantic_form.model_form import ModelForm
from dash_pydantic_form.fields import fields

BaseModel.__getitem__ = lambda self, key: self.__dict__.get(key)
BaseModel.to_plotly_json = lambda self: self.model_dump(mode="json")

_css_dist = [
    {
        "relative_package_path": "pydantic_form_styles.css",
        "namespace": "dash_pydantic_form",
    },
]
_js_dist = [
    {
        "relative_package_path": "pydantic_form_scripts.js",
        "namespace": "dash_pydantic_form",
    },
]
__version__ = "0.1.0"

__all__ = ["FormSection", "ModelForm", "Sections", "fields"]

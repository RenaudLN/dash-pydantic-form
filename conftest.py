import pytest
from dash import _dash_renderer


@pytest.fixture(scope="session", autouse=True)
def set_react_18():
    """Set react version to 18.2.0 to work with DMC."""
    _dash_renderer._set_react_version("18.2.0")

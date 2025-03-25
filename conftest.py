from copy import deepcopy

import dash
import dash._callback
import pytest

PYDF_CALLBACK_LIST = []
PYDF_CALLBACK_MAP = {}


@pytest.fixture(scope="session", autouse=True)
def init_test_session():
    """Set react version to 18.2.0 to work with DMC."""
    if dash.__version__ < "3":
        from dash import _dash_renderer

        _dash_renderer._set_react_version("18.2.0")

    global PYDF_CALLBACK_LIST, PYDF_CALLBACK_MAP  # noqa: PLW0603
    PYDF_CALLBACK_LIST = deepcopy(dash._callback.GLOBAL_CALLBACK_LIST)
    PYDF_CALLBACK_MAP = deepcopy(dash._callback.GLOBAL_CALLBACK_MAP)


@pytest.fixture(scope="function", autouse=True)
def reset_callbacks():
    """Reload dash pydantic form to add the callbacks."""
    dash._callback.GLOBAL_CALLBACK_LIST = deepcopy(PYDF_CALLBACK_LIST)
    dash._callback.GLOBAL_CALLBACK_MAP = deepcopy(PYDF_CALLBACK_MAP)

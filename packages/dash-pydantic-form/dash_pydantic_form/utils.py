from typing_extensions import TypedDict


class JSFunction(TypedDict):
    """JS function on a dash_clientside namespace."""

    namespace: str
    function_name: str

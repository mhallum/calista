"""Domain layer utilities."""

from dataclasses import fields, is_dataclass
from typing import Any, TypeVar, cast

D = TypeVar("D")


def dict_to_dataclass(dc_type: type[D], values: dict[str, Any]) -> D:
    """Recursively build a dataclass instance from a nested dict.

    Args:
        dc_type: The dataclass type to build.
        values: The dict containing the data.

    Returns:
        An instance of dc_type populated with data from values.
    """

    if not is_dataclass(dc_type):
        raise TypeError(f"{dc_type} is not a dataclass type")
    kwargs = {}
    for field in fields(dc_type):
        inner = values.get(field.name)
        if is_dataclass(field.type) and isinstance(inner, dict):
            kwargs[field.name] = dict_to_dataclass(cast(type[Any], field.type), inner)
        else:
            kwargs[field.name] = inner
    return cast(D, dc_type(**kwargs))

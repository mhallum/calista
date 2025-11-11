"""Domain layer utilities."""

from collections.abc import Callable
from dataclasses import MISSING, fields, is_dataclass
from types import NoneType
from typing import Any, TypeVar, cast, get_args, get_origin, get_type_hints

D = TypeVar("D")


def dict_to_dataclass(dc_type: type[D], values: dict[str, Any]) -> D:
    """Recursively build a dataclass instance from a nested dict.

    Args:
        dc_type: The dataclass type to build.
        values: The dict containing the data.

    Returns:
        An instance of dc_type populated with data from values.

    Note:
        - Fields in values that are not in dc_type are ignored.
        - All fields without defaults must be present in values.
        - This does not handle complex types like lists of dataclasses
          or unions beyond SomeDataclass | None.
    """

    if not is_dataclass(dc_type):
        raise TypeError(f"{dc_type} is not a dataclass type")
    type_hints = get_type_hints(dc_type)
    kwargs = {}
    for field in fields(dc_type):
        has_default = (
            field.default is not MISSING or field.default_factory is not MISSING
        )
        field_type = type_hints.get(field.name, field.type)
        if field.name in values:
            inner = values[field.name]
            target_dc = _resolve_dataclass_type(field_type)
            if target_dc and isinstance(inner, dict):
                kwargs[field.name] = dict_to_dataclass(cast(type[Any], target_dc), inner)  # pragma: no mutate # fmt: skip # pylint: disable=line-too-long
            else:
                kwargs[field.name] = inner
        else:
            if not has_default and field.init:
                raise KeyError(f"Missing required field '{field.name}'")
            if not field.init:
                continue
            if field.default is not MISSING:
                kwargs[field.name] = field.default
            elif field.default_factory is not MISSING:
                factory = cast(Callable[[], Any], field.default_factory)  # pragma: no mutate # fmt: skip
                kwargs[field.name] = factory()
            else:
                # this should be unreachable, but just in case ...
                msg = f"Field '{field.name}' has unexpected state: no default or default_factory found"  # pragma: no mutate # pragma: no cover # pylint: disable=line-too-long
                raise RuntimeError(msg)  # pragma: no mutate  # pragma: no cover # fmt: skip # pylint: disable=line-too-long
    return cast(D, dc_type(**kwargs))  # pragma: no mutate


def _resolve_dataclass_type(field_type: Any) -> type[Any] | None:
    origin = get_origin(field_type)
    if origin is None:
        return cast(type[Any], field_type) if is_dataclass(field_type) else None  # pragma: no mutate # fmt: skip # pylint: disable=line-too-long
    args = [arg for arg in get_args(field_type) if arg is not NoneType]
    if len(args) == 1 and is_dataclass(args[0]):
        return cast(type[Any], args[0])
    return None

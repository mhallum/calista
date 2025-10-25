"""Tri-state handling for catalog patch fields.

This module defines the ``UNSET`` sentinel, the `Unsettable` type alias,
and the `resolve` helper for applying partial updates to catalog entries.

A field of type ``Unsettable[T]`` can take three states:

* ``UNSET`` — the field is intentionally left unchanged in a patch.
* ``None`` — the field is explicitly cleared (only if allowed).
* concrete ``T`` — the field is explicitly updated to a new value.

Using this tri-state convention lets patches distinguish between omission,
explicit clearing, and explicit setting of a value.
"""

from dataclasses import dataclass
from typing import Literal, TypeVar, overload

from .errors import InvalidRevisionError

# pylint: disable=too-many-arguments


def _get_unset() -> "_UnsetType":
    # Factory used by pickle to retrieve the one true instance.
    return UNSET


@dataclass(frozen=True)
class _UnsetType:
    """Sentinel to mark fields intentionally left unset in patches.

    This is distinct from `None`, which indicates an explicit clearing of a value.
    """

    def __bool__(self) -> bool:  # falsy to simplify conditionals
        return False

    def __repr__(self) -> str:
        return "UNSET"

    def __reduce__(self):  # keep singleton on pickle
        return (_get_unset, ())


# Singleton instance
UNSET = _UnsetType()

T = TypeVar("T")
type Unsettable[T] = T | _UnsetType | None


@overload
def resolve(
    value: T | None | _UnsetType,
    current: T,
    *,
    clearable: Literal[False],
    field: str,
    kind: str,
    key: str,
) -> T: ...
@overload
def resolve(
    value: T | None | _UnsetType,
    current: T,
    *,
    clearable: Literal[True],
    field: str,
    kind: str,
    key: str,
) -> T | None: ...
def resolve(
    value: T | None | _UnsetType,
    current: T,
    *,
    clearable: bool,
    field: str,
    kind: str,
    key: str,
) -> T | None:
    """Resolve a tri-state value against the current value.

    Args:
        value: The new value from the patch (may be UNSET, None, or a concrete value).
        current: The current value from the existing snapshot.
        clearable: Whether this field is allowed to be cleared (set to None).
        field: The name of the field (for error messages).
        kind: The kind of entity being patched (for error messages).
        key: The unique key of the entity being patched (for error messages).

    Returns:
        The resolved value according to these rules:
        If value is a concrete value, return it.
        If value is UNSET, return the current value.
        If value is None and clearable=True, return None.
        If value is None and clearable=False, raise InvalidRevisionError.

    Raises:
        InvalidRevisionError: If attempting to clear a non-clearable field.
    """
    if isinstance(value, _UnsetType):
        return current
    if value is None and not clearable:
        raise InvalidRevisionError(kind, key, f"{field} cannot be cleared")
    return value  # may be None only when clearable=True

"""Unit tests for calista.interfaces.catalog.unsettable module."""

import pickle
import re

import pytest

from calista.interfaces.catalog.errors import InvalidRevisionError
from calista.interfaces.catalog.unsettable import UNSET, resolve

# --- Tests for _UnsetType singleton ---


def test_unset_is_falsy():
    """UNSET evaluates to False in boolean contexts."""
    assert not UNSET


def test_unset_repr():
    """UNSET has the expected repr string."""
    assert repr(UNSET) == "UNSET"


def test_unset_is_singleton():
    """UNSET remains identical after pickling and unpickling."""
    serialized = pickle.dumps(UNSET)
    deserialized = pickle.loads(serialized)
    assert deserialized is UNSET


# --- Tests for resolve function in unsettable.py ---


def test_resolve_unset_returns_current():
    """resolve(UNSET, ...) returns the current value."""
    current_value = "Discovery Channel Telescope"
    result = resolve(
        UNSET,
        current_value,
        clearable=False,
        field="name",
        kind="site",
        key="LDT",
    )
    assert result == current_value


def test_resolve_none_clears_value_when_clearable():
    """resolve(None, ...) returns None when clearable=True."""
    result = resolve(
        None,
        "XXX",
        clearable=True,
        field="mpc_code",
        kind="site",
        key="LDT",
    )
    assert result is None


def test_resolve_none_raises_when_not_clearable():
    """resolve(None, ...) raises InvalidRevisionError when clearable=False."""
    with pytest.raises(
        InvalidRevisionError,
        match=re.escape("Invalid site (LDT) revision: name cannot be cleared"),
    ):
        resolve(
            None,
            "Lowell Discovery Telescope",
            clearable=False,
            field="name",
            kind="site",
            key="LDT",
        )


def test_resolve_concrete_value_returns_value():
    """resolve(concrete_value, ...) returns the concrete value."""
    current_value = "Discovery Channel Telescope"
    new_value = "Lowell Discovery Telescope"
    result = resolve(
        new_value,
        current_value,
        clearable=False,
        field="name",
        kind="site",
        key="LDT",
    )
    assert result == new_value

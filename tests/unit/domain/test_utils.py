""" "Unit tests for calista.domain.utils module."""

import re
from dataclasses import asdict, dataclass

import pytest

from calista.domain.utils import dict_to_dataclass


def test_dict_to_dataclass_round_trip():
    """Test that dict_to_dataclass correctly rebuilds a dataclass from its dict representation."""

    @dataclass(frozen=True, slots=True)
    class Inner:
        """Inner dataclass for testing."""

        a: int
        b: str

    @dataclass(frozen=True, slots=True)
    class Outer:
        """Outer dataclass for testing."""

        x: float
        y: Inner
        z: dict[str, int]

    original = Outer(x=3.14, y=Inner(a=42, b="hello"), z={"key": 1})
    as_dict = asdict(original)
    rebuilt = dict_to_dataclass(Outer, as_dict)

    assert rebuilt == original


def test_dict_to_dataclass_type_error():
    """Test that dict_to_dataclass raises TypeError when given a non-dataclass type."""

    with pytest.raises(
        TypeError, match=re.escape("<class 'int'> is not a dataclass type")
    ):
        dict_to_dataclass(int, {"a": 1})

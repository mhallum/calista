""" "Unit tests for calista.domain.utils module."""

import re
from dataclasses import asdict, dataclass, field

import pytest

from calista.domain.utils import dict_to_dataclass

# pylint: disable=missing-class-docstring, magic-value-comparison


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


@pytest.mark.parametrize(
    "data, missing", [({"a": 1, "c": None}, "b"), ({"a": 1, "b": "test"}, "c")]
)
def test_dict_to_dataclass_missing_field(data, missing):
    """Test that dict_to_dataclass raises TypeError when a required field is missing."""

    @dataclass(frozen=True, slots=True)
    class Foo:
        a: int
        b: str
        c: float | None

    with pytest.raises(KeyError, match=f"Missing required field '{missing}'"):
        dict_to_dataclass(Foo, data)


def test_dict_to_dataclass_union_none_field_is_required():
    """Test that a field with type float | None is still required if not provided."""

    @dataclass(frozen=True, slots=True)
    class Foo:
        a: int
        b: str
        c: float | None

    # 'c' is omitted entirely, should raise KeyError
    data = {"a": 1, "b": "test"}
    with pytest.raises(KeyError, match="Missing required field 'c'"):
        dict_to_dataclass(Foo, data)


def test_dict_to_dataclass_extra_field():
    """Test that dict_to_dataclass ignores extra fields in the input dict."""

    @dataclass(frozen=True, slots=True)
    class Foo:
        a: int

    data = {"a": 1, "b": 2}
    result = dict_to_dataclass(Foo, data)
    assert result == Foo(a=1)


def test_dict_to_dataclass_none_value():
    """Test that dict_to_dataclass handles None values."""

    @dataclass(frozen=True, slots=True)
    class Foo:
        a: int | None

    data = {"a": None}
    result = dict_to_dataclass(Foo, data)
    assert result == Foo(a=None)


def test_dict_to_dataclass_default_fields():
    """Test that dict_to_dataclass correctly handles fields with default values."""

    @dataclass(frozen=True, slots=True)
    class Foo:
        a: int
        b: str = "default"
        c: float | None = 3.14
        d: list[int] = field(default_factory=lambda: [1, 2, 3])

    data = {"a": 10}
    result = dict_to_dataclass(Foo, data)
    assert result == Foo(a=10, b="default", c=3.14, d=[1, 2, 3])


def test_dict_to_dataclass_default_fields_nested():
    """Test that dict_to_dataclass correctly handles nested dataclasses with default values."""

    @dataclass(frozen=True, slots=True)
    class Inner:
        a: int
        b: str = "inner_default"

    @dataclass(frozen=True, slots=True)
    class Outer:
        x: float
        y: Inner = field(default_factory=lambda: Inner(a=0))

    data = {"x": 2.71}
    result = dict_to_dataclass(Outer, data)
    assert result == Outer(x=2.71, y=Inner(a=0, b="inner_default"))


def test_dict_to_dataclass_deeply_nested():
    """Test dict_to_dataclass with multiple levels of nested dataclasses."""

    @dataclass(frozen=True, slots=True)
    class Level3:
        a: int
        b: int | None = None
        c: int = 3

    @dataclass(frozen=True, slots=True)
    class Level2:
        level3: Level3

    @dataclass(frozen=True, slots=True)
    class Level1:
        level2: Level2

    data = {"level2": {"level3": {"a": 99}}}
    result = dict_to_dataclass(Level1, data)
    assert result == Level1(level2=Level2(level3=Level3(a=99)))


def test_dict_to_dataclass_overrides_can_be_set_after_defaults():
    """Ensure defaults don't prevent later overrides from being applied."""

    @dataclass(frozen=True, slots=True)
    class Foo:
        required: int
        use_default: str = "default"
        override_me: str = "original"
        override_me_too: str = field(default_factory=lambda: "also original")

    data = {
        "required": 7,
        "override_me": "mutated",
        "override_me_too": "mutated too",
    }
    result = dict_to_dataclass(Foo, data)

    assert result.use_default == "default"
    assert result.override_me == "mutated"
    assert result.override_me_too == "mutated too"


def test_dict_to_dataclass_default_factory_does_not_abort_loop():
    """Test that default_factory fields are handled correctly."""

    @dataclass(frozen=True, slots=True)
    class Foo:
        required: int
        generated: list[int] = field(default_factory=lambda: [1])
        label: str = "default"

    data = {"required": 10, "label": "custom"}
    result = dict_to_dataclass(Foo, data)

    assert result.generated == [1]
    assert result.label == "custom"


def test_dict_to_dataclass_nested_optional_dc_field():
    """Test that optional nested dataclass fields are handled correctly."""

    @dataclass(frozen=True, slots=True)
    class Inner:
        a: int
        b: str

    @dataclass(frozen=True, slots=True)
    class Outer:
        x: float
        y: Inner | None = None

    data_with_inner = {"x": 1.23, "y": {"a": 42, "b": "hello"}}
    result_with_inner = dict_to_dataclass(Outer, data_with_inner)
    assert result_with_inner == Outer(x=1.23, y=Inner(a=42, b="hello"))
    data_without_inner = {"x": 4.56}
    result_without_inner = dict_to_dataclass(Outer, data_without_inner)
    assert result_without_inner == Outer(x=4.56, y=None)
    data_with_explicit_none = {"x": 4.56, "y": None}
    result_with_explicit_none = dict_to_dataclass(Outer, data_with_explicit_none)
    assert result_with_explicit_none == Outer(x=4.56, y=None)

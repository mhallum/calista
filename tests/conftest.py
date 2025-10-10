"""Global pytest fixtures for CALISTA."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from sqlalchemy.engine import Engine


pytest_plugins = [
    "tests.fixtures.sqlite",
    "tests.fixtures.postgres",
    "tests.fixtures.datagen",
]


# Helper to route to an existing engine fixture by name
@pytest.fixture
def engine(request: pytest.FixtureRequest) -> Engine:
    """Indirection fixture to parametrize over engine-providing fixtures.

    Example:
        ```py
        @pytest.mark.parametrize("engine", ["postgres_engine", "sqlite_engine_file"], indirect=True)
        def test_something(engine): ...
        ```
    """
    return request.getfixturevalue(request.param)

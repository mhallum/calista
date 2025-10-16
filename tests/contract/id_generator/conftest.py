"""Fixtures for id_generator contract tests."""

from collections.abc import Iterable

import pytest

from calista.adapters.id_generators import (
    SimpleIdGenerator,
    ULIDGenerator,
    UUIDv4Generator,
)
from calista.interfaces.id_generator import IdGenerator


@pytest.fixture(params=["ulid", "uuid4", "simple"])
def id_generator(
    request: pytest.FixtureRequest,
) -> Iterable[IdGenerator]:
    """Return a fresh IdGenerator instance for the requested backend.

    Supported params:
      - `"ulid"` → ULIDGenerator
      - `"uuid4"` → UUIDv4Generator
      - `"simple"` → SimpleIdGenerator

    Extend by adding new identifiers to `params` and branching below to
    construct the corresponding backend. Each invocation yields a brand-new
    IdGenerator instance for isolation.
    """

    match request.param:
        case "ulid":
            yield ULIDGenerator()
        case "uuid4":
            yield UUIDv4Generator()
        case "simple":
            yield SimpleIdGenerator()
        case _:
            raise ValueError(f"unknown id generator type: {request.param}")


@pytest.fixture(params=["ulid"])
def monotonic_id_generators(request: pytest.FixtureRequest) -> Iterable[IdGenerator]:
    """Yield instances of IdGenerators that promise monotonic ID order."""
    match request.param:
        case "ulid":
            yield ULIDGenerator()
        case _:
            raise ValueError(f"unknown monotonic id generator type: {request.param}")

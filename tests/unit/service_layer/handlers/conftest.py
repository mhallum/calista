"""Pytest fixtures for service layer handler unit tests."""

from __future__ import annotations
from collections.abc import Callable
from typing import TYPE_CHECKING

import pytest

from .fakes import bootstrap_test_bus

if TYPE_CHECKING:
    from calista.service_layer.messagebus import MessageBus


@pytest.fixture
def make_test_bus() -> Callable[..., MessageBus]:
    """Factory to create a message bus with in-memory catalogs and UoW for testing."""
    return bootstrap_test_bus

"""Pytest fixtures for service layer handler unit tests."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

import pytest

from .fakes import bootstrap_test_bus

if TYPE_CHECKING:
    from calista.service_layer.messagebus import MessageBus

# pylint: disable=redefined-outer-name


@pytest.fixture
def bus_params():
    """Default bus parameters. Classes can override this fixture"""
    return {}


@pytest.fixture
def make_test_bus(bus_params) -> Callable[..., MessageBus]:
    """Factory to create a message bus with in-memory catalogs and UoW for testing."""

    def _make():
        return bootstrap_test_bus(**bus_params)

    return _make

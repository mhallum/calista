"""Base class for handler tests."""

from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from calista.service_layer.messagebus import MessageBus


class HandlerTestBase:
    """Base class for handler tests providing common setup and utilities."""

    bus: MessageBus

    # declare what fixtures seeding needs (subclasses can override)
    seed_uses: tuple[str, ...] = ()
    fx: SimpleNamespace

    @pytest.fixture(autouse=True)
    def _attach_bus(self, request, make_test_bus):
        """Fresh bus per test; seed using any fixtures declared in seed_uses."""
        self.bus = make_test_bus()

        # Make a handy namespace of requested fixtures available as self.fx
        fx = {name: request.getfixturevalue(name) for name in self.seed_uses}
        self.fx = SimpleNamespace(**fx)

        self._seed_bus(request)  # generic: can pull *any* fixture by name
        self.reset_committed()

    def _seed_bus(self, request) -> None:
        """Override to preload the bus. Use request.getfixturevalue(...) as needed."""

    def assert_committed(self) -> None:
        """Assert that the unit of work was committed."""
        assert hasattr(self.bus.uow, "committed")
        assert self.bus.uow.committed is True

    def assert_not_committed(self) -> None:
        """Assert that the unit of work was not committed."""
        assert hasattr(self.bus.uow, "committed")
        assert self.bus.uow.committed is False

    def reset_committed(self) -> None:
        """Reset the committed flag on the unit of work."""
        if hasattr(self.bus.uow, "committed"):
            self.bus.uow.committed = False

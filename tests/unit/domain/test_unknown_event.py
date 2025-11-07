"""Module for testing unknown event handling for each aggregate.

Whenever an aggregate is added, it should be added to the parameterized test below.
This saves having to include a separate test for each aggregate.
"""

from dataclasses import dataclass

import pytest

from calista.domain import aggregates, events

# pylint: disable=redefined-outer-name,protected-access


@dataclass(frozen=True)
class UnknownEvent(events.DomainEvent):
    """A fake event for testing purposes."""

    fake_aggregate_id: str

    @property
    def aggregate_id(self) -> str:
        return self.fake_aggregate_id


@pytest.fixture
def unknown_event():
    """Fixture for an unknown event."""
    return UnknownEvent(fake_aggregate_id="test-aggregate")


@pytest.mark.parametrize(
    "aggregate",
    [
        aggregates.ObservationSession(aggregate_id="test-aggregate"),
    ],
    ids=["ObservationSession"],
)
def test_apply_unknown_event(aggregate):
    """Test that applying an unknown event raises a ValueError."""
    event = UnknownEvent(fake_aggregate_id=aggregate.aggregate_id)
    with pytest.raises(ValueError, match="Unhandled event type: UnknownEvent"):
        aggregate._apply(event)

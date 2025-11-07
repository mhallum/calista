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


@pytest.mark.parametrize(
    "aggregate",
    [
        aggregates.ObservationSession(aggregate_id="test-aggregate"),
        aggregates.RawFitsFile(aggregate_id="test-aggregate"),
    ],
    ids=["ObservationSession", "RawFitsFile"],
)
def test_aggregate_raises_error_on_unknown_event_application(aggregate):
    """Test that applying an unknown event raises a ValueError for each aggregate."""
    event = UnknownEvent(fake_aggregate_id=aggregate.aggregate_id)
    with pytest.raises(ValueError, match="Unhandled event type: UnknownEvent"):
        aggregate._apply(event)

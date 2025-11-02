"""Unit tests for the ObservationSession aggregate."""

from dataclasses import dataclass

import pytest

from calista.domain import events
from calista.domain.aggregates.observation_session import ObservationSession

# pylint: disable=magic-value-comparison,too-few-public-methods,protected-access


class TestObservationSessionInitialization:
    """Tests for the ObservationSession aggregate initialization."""

    @staticmethod
    def test_initialization_sets_defaults():
        """Test that the aggregate initializes with correct default values."""

        session = ObservationSession(aggregate_id="session-123")

        assert session.aggregate_id == "session-123"
        assert session.natural_key is None
        assert session.facility_code is None
        assert session.night_id is None
        assert session.segment_number == 0


class TestObservationSessionRegistration:
    """Tests for the register construction path."""

    @staticmethod
    def test_register_session_sets_attributes():
        """Test that registering a session sets the correct attributes."""

        session = ObservationSession.register(
            aggregate_id="session-123",
            natural_key="OBS-20240601-001",
            facility_code="FAC001",
            night_id="20240601",
            segment_number=1,
        )

        assert session.aggregate_id == "session-123"
        assert session.natural_key == "OBS-20240601-001"
        assert session.facility_code == "FAC001"
        assert session.night_id == "20240601"
        assert session.segment_number == 1

    @staticmethod
    def test_register_session_adds_event_to_pending_events():
        """Test that registering a session enqueues the correct event."""

        session = ObservationSession.register(
            aggregate_id="session-456",
            natural_key="OBS-20240602-002",
            facility_code="FAC002",
            night_id="20240602",
            segment_number=2,
        )

        assert len(session._pending_events) == 1
        event = session._pending_events[0]
        assert isinstance(event, events.ObservationSessionRegistered)
        assert event.session_id == "session-456"
        assert event.natural_key == "OBS-20240602-002"
        assert event.facility_code == "FAC002"
        assert event.night_id == "20240602"
        assert event.segment_number == 2

    @staticmethod
    def test_register_session_does_not_bump_version():
        """Test that registering a session does not increment the version."""

        session = ObservationSession.register(
            aggregate_id="session-789",
            natural_key="OBS-20240603-003",
            facility_code="FAC003",
            night_id="20240603",
            segment_number=3,
        )

        assert session._version == 0


class TestObservationSessionApply:
    """Tests for the _apply method of ObservationSession."""

    @staticmethod
    def test_apply_observation_session_registered_event():
        """Test that applying an ObservationSessionRegistered event sets attributes correctly."""

        # Define a fake event class for testing
        @dataclass(frozen=True)
        class FakeEvent(events.DomainEvent):
            """A fake event for testing purposes."""

            fake_aggregate_id: str

            @property
            def aggregate_id(self) -> str:
                return self.fake_aggregate_id

        # Make an observation session
        session = ObservationSession.register(
            aggregate_id="session-001",
            natural_key="OBS-20240604-004",
            facility_code="FAC004",
            night_id="20240604",
            segment_number=4,
        )

        # Attempt to apply the event
        event = FakeEvent(fake_aggregate_id="session-001")
        with pytest.raises(
            ValueError,
            match="Unhandled event type: FakeEvent",
        ):
            session._apply(event)

"""Observation Session Aggregate"""

from calista.domain import events

from .base import Aggregate

# pylint: disable=too-many-arguments,
# pylint: disable=too-many-positional-arguments


class ObservationSession(Aggregate):
    """Aggregate root representing an observation session."""

    STREAM_TYPE = "ObservationSession"

    def __init__(self, aggregate_id: str) -> None:
        super().__init__(aggregate_id)
        self.natural_key: str | None = None
        self.facility_code: str | None = None
        self.night_id: str | None = None
        self.segment_number: int = 0

    # --- Construction Paths ---

    @classmethod
    def register(
        cls,
        aggregate_id: str,
        natural_key: str,
        facility_code: str,
        night_id: str,
        segment_number: int = 1,
    ) -> "ObservationSession":
        """Register a new observation session."""
        session = cls(aggregate_id)
        event = events.ObservationSessionRegistered(
            session_id=aggregate_id,
            natural_key=natural_key,
            facility_code=facility_code,
            night_id=night_id,
            segment_number=segment_number,
        )
        session._enqueue(event)
        return session

    # --- Event Application ---

    def _apply(self, event: events.DomainEvent) -> None:
        match event:
            case events.ObservationSessionRegistered():
                self.natural_key = event.natural_key
                self.facility_code = event.facility_code
                self.night_id = event.night_id
                self.segment_number = event.segment_number
            case _:
                raise ValueError(f"Unhandled event type: {type(event).__name__}")

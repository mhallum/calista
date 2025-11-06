"""Tests for the register_observation_session handler via the message bus."""

from calista.interfaces.stream_index import NaturalKey
from calista.service_layer import commands
from tests.unit.service_layer.handlers.base import HandlerTestBase

# pylint: disable=magic-value-comparison


class TestRegisterObservationSession(HandlerTestBase):
    """Tests for the register_observation_session handler via the message bus."""

    # --- Setup ---

    # Used by HandlerTestBase to seed the bus
    def _seed_bus(self, request):
        """Seed the message bus with a facility."""
        make_site_params = request.getfixturevalue("make_site_params")
        make_telescope_params = request.getfixturevalue("make_telescope_params")
        make_instrument_params = request.getfixturevalue("make_instrument_params")
        self.bus.handle(
            commands.PublishSiteRevision(**make_site_params("S1", "Test Site 1"))
        )
        self.bus.handle(
            commands.PublishTelescopeRevision(
                **make_telescope_params("T1", "Test Telescope 1")
            )
        )
        self.bus.handle(
            commands.PublishInstrumentRevision(
                **make_instrument_params("I1", "Test Instrument 1")
            )
        )
        self.bus.handle(
            commands.RegisterFacility(
                facility_code="FAC1",
                site_code="S1",
                telescope_code="T1",
                instrument_code="I1",
            )
        )

    # --- Tests ---

    def test_registers_observation_session(self):
        """Registering an observation session creates the aggregate."""

        cmd = commands.RegisterObservationSession(
            facility_code="FAC1",
            night_id="20240601",
            segment_number=2,
        )
        self.bus.handle(cmd=cmd)

        # Check that the stream index has an entry for the new session
        index_entry = self.bus.uow.stream_index.lookup(
            NaturalKey("ObservationSession", "FAC1-20240601-0002")
        )
        assert index_entry is not None
        stream_id = index_entry.stream_id

        # Check that the event store has the ObservationSessionRegistered event
        events = list(self.bus.uow.eventstore.read_stream(stream_id))
        assert len(events) == 1  # One event: ObservationSessionRegistered
        event = events[0]
        payload = event.payload
        assert event.event_type == "ObservationSessionRegistered"
        assert payload["natural_key"] == "FAC1-20240601-0002"
        assert payload["facility_code"] == "FAC1"
        assert payload["night_id"] == "20240601"
        assert payload["segment_number"] == 2

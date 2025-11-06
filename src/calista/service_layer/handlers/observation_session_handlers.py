"""Handlers relation to observation session aggregate."""

from collections.abc import Callable

from calista.domain.aggregates.observation_session import ObservationSession
from calista.interfaces.id_generator import IdGenerator
from calista.interfaces.stream_index import NaturalKey
from calista.interfaces.unit_of_work import AbstractUnitOfWork
from calista.service_layer import commands
from calista.service_layer import repositories as repos


def register_observation_session(
    cmd: commands.RegisterObservationSession,
    uow: AbstractUnitOfWork,
    event_id_generator: IdGenerator,
    aggregate_id_generator: IdGenerator,
) -> None:
    """Register a new observation session."""

    natural_key = f"{cmd.facility_code}-{cmd.night_id}-{cmd.segment_number:04d}"

    session = ObservationSession.register(
        aggregate_id=aggregate_id_generator.new_id(),
        natural_key=natural_key,
        facility_code=cmd.facility_code,
        night_id=cmd.night_id,
        segment_number=cmd.segment_number,
    )

    with uow:
        session_repo = repos.ObservationSessionRepository(
            event_store=uow.eventstore,
            event_id_generator=event_id_generator,
        )
        session_repo.store_events(session)

        uow.stream_index.reserve(
            natural_key=NaturalKey(kind="ObservationSession", key=natural_key),
            stream_id=session.aggregate_id,
        )

        uow.commit()


COMMAND_HANDLERS: dict[type, Callable[..., None]] = {
    commands.RegisterObservationSession: register_observation_session
}

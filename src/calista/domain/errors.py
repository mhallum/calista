"""Domain-layer error definitions."""


class DomainError(Exception):
    """Base class for domain-layer errors."""


class AggregateIdMismatchError(DomainError):
    """Raised when an event targets a different aggregate_id than the receiver."""

    def __init__(self, aggregate_id: str, event_aggregate_id: str) -> None:
        super().__init__(
            f"Event aggregate ID '{event_aggregate_id}' does not match "
            f"aggregate ID '{aggregate_id}'."
        )
        self.aggregate_id = aggregate_id
        self.event_aggregate_id = event_aggregate_id

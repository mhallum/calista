"""Domain-layer error definitions."""

# ============================================================================
#                           General domain errors
# ============================================================================


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


class InvalidTransitionError(DomainError):
    """Raised when an aggregate is in an invalid state for the attempted action."""


# ============================================================================
#                   RawFitsFile related errors
# ============================================================================


class DuplicateClassificationError(InvalidTransitionError):
    """Raised when a file is reclassified with a different frame type."""

    def __init__(self, aggregate_id: str, frame_type: str) -> None:
        super().__init__(
            f"File {aggregate_id} has already been classified as {frame_type}."
        )
        self.aggregate_id = aggregate_id
        self.frame_type = frame_type


class UnstoredFileClassificationError(InvalidTransitionError):
    """Raised when attempting to classify a file that has not been stored yet."""

    def __init__(self, aggregate_id: str) -> None:
        super().__init__(f"File {aggregate_id} must be stored before classification.")
        self.aggregate_id = aggregate_id

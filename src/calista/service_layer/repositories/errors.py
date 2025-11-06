"""Repository-related error definitions."""


class RepositoryError(Exception):
    """Base class for repository-related errors."""


class AggregateNotFoundError(RepositoryError):
    """Raised when an aggregate cannot be found in its repository."""

    aggregate_id: str
    aggregate_type_name: str

    def __init__(self, aggregate_type_name: str, aggregate_id: str):
        super().__init__(f"{aggregate_type_name} with ID {aggregate_id} not found.")
        self.aggregate_type_name = aggregate_type_name
        self.aggregate_id = aggregate_id

"""Exceptions for stream index operations."""


class StreamIndexError(Exception):
    """Base class for stream index errors."""


class NaturalKeyAlreadyBound(StreamIndexError):
    """Conflict: natural key already points to a different stream.

    Attributes:
        natural_key (str): The natural key that is already bound.
        stream_id (str): The stream ID that the natural key is bound to.
        kind (str): The stream type (e.g. "ObservationSession").
    """

    def __init__(self, natural_key: str, stream_id: str, kind: str):
        super().__init__(
            f"Natural key '{natural_key}' is already bound to stream ID '{stream_id}' for kind '{kind}'."
        )
        self.natural_key = natural_key
        self.stream_id = stream_id
        self.kind = kind


class StreamIdAlreadyBound(StreamIndexError):
    """Conflict: stream ID already bound to a different natural key.

    Attributes:
        stream_id (str): The stream ID that is already bound.
        natural_key (str): The natural key that the stream ID is bound to.
        kind (str): The stream type (e.g. "ObservationSession").
    """

    def __init__(self, stream_id: str, natural_key: str, kind: str):
        super().__init__(
            f"Stream ID '{stream_id}' is already bound to natural key '{natural_key}' for kind '{kind}'."
        )
        self.stream_id = stream_id
        self.natural_key = natural_key
        self.kind = kind

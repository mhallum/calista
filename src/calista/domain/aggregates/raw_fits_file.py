"""Aggregate representing a raw FITS file."""

from datetime import datetime
from enum import Enum
from typing import ClassVar

from calista.domain import errors, events
from calista.domain.value_objects import FrameType, StoredFileMetadata

from .base import Aggregate

# pylint: disable=too-many-arguments


class Status(Enum):
    """Enumeration of possible RawFitsFile statuses."""

    NEW = "new"
    STORED = "stored"
    CATEGORIZED = "categorized"


class RawFitsFile(Aggregate):
    """Aggregate representing a raw FITS file."""

    STREAM_TYPE: ClassVar[str] = "RawFitsFile"

    def __init__(self, aggregate_id: str):
        super().__init__(aggregate_id)
        self.session_id: str | None = None
        self.metadata: StoredFileMetadata | None = None
        self.frame_type: FrameType | None = None
        self.status: Status = Status.NEW

    # --- Construction Paths ---

    @classmethod
    def register_ingested_file(
        cls,
        aggregate_id: str,
        session_id: str,
        *,
        sha256: str,
        cas_key: str,
        size_bytes: int,
        ingested_at: datetime,
    ) -> "RawFitsFile":
        """Ingest a new raw FITS file.

        Args:
            aggregate_id (str): The unique identifier for the aggregate.
            session_id (str): The observation session ID the file belongs to.
            sha256 (str): The SHA-256 hash of the file.
            cas_key (str): The content-addressable storage key for the file.
            size_bytes (int): The size of the file in bytes.
            ingested_at (datetime): The timestamp when the file was stored.

        Returns:
            RawFitsFile: The newly created RawFitsFile aggregate.
        """

        raw_fits_file = cls(aggregate_id)
        event = events.RawFitsFileIngested(
            file_id=aggregate_id,
            session_id=session_id,
            sha256=sha256,
            cas_key=cas_key,
            size_bytes=size_bytes,
            ingested_at=ingested_at.isoformat(),
        )
        raw_fits_file._enqueue(event)
        return raw_fits_file

    # --- State Transitions ---

    def classify_frame(self, frame_type: FrameType) -> None:
        """Classify the frame type of the raw FITS file.

        Args:
            frame_type (FrameType): The type of frame (e.g., FrameType.BIAS).

        Raises:
            UnstoredFileClassificationError: If the file is not in a state to be classified.
            DuplicateClassificationError: If the file has already been classified with
                a different frame type.
        """

        if self.status == Status.NEW:
            raise errors.UnstoredFileClassificationError(self.aggregate_id)
        if self.status == Status.CATEGORIZED:
            if self.frame_type == frame_type:
                return  # Idempotent
            raise errors.DuplicateClassificationError(
                self.aggregate_id, str(self.frame_type)
            )

        event = events.RawFitsFileClassified(
            file_id=self.aggregate_id, frame_type=frame_type.value
        )
        self._enqueue(event)

    # --- Event Application ---

    def _apply(self, event: events.DomainEvent) -> None:
        match event:
            case events.RawFitsFileIngested():
                self.session_id = event.session_id
                self.metadata = StoredFileMetadata(
                    sha256=event.sha256,
                    cas_key=event.cas_key,
                    size_bytes=event.size_bytes,
                    stored_at=datetime.fromisoformat(event.ingested_at),
                )
                self._set_status(Status.STORED)
            case events.RawFitsFileClassified():
                self.frame_type = FrameType(event.frame_type)
                self._set_status(Status.CATEGORIZED)
            case _:
                raise ValueError(f"Unhandled event type: {type(event).__name__}")

    # --- Internal Helpers ---
    def _set_status(self, status: Status) -> None:
        self.status = status

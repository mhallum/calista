"""Custom SQLAlchemy types for CALISTA.

These types encapsulate small, backend-aware behaviors while preserving clear
Python-side types for tooling and auto-generated API docs.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, BigInteger, Integer
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import DateTime, TypeDecorator

from calista.adapters.db.dialects import DialectName

if TYPE_CHECKING:
    from sqlalchemy.engine.interfaces import Dialect

__all__ = ["BIGINT_PK", "UTCDateTime", "PORTABLE_JSON"]


BIGINT_PK = BigInteger().with_variant(Integer(), "sqlite")

PORTABLE_JSON = JSON(none_as_null=True).with_variant(
    JSONB(none_as_null=True), "postgresql"
)


class UTCDateTime(TypeDecorator[datetime]):  # pylint: disable=too-many-ancestors
    """Timezone-aware UTC datetime.

    Ensures values are stored and returned as aware ``datetime`` objects in UTC.
    Naive datetimes are treated as UTC.
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> Any:
        if value is None:
            return None
        # Treat naïve as UTC; always normalize to UTC
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        value = value.astimezone(timezone.utc)
        # SQLite: store naïve UTC so it won't be reinterpreted as local
        return (
            value.replace(tzinfo=None)
            if dialect.name == DialectName.SQLITE.value
            else value
        )

    def process_result_value(self, value: Any, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            # SQLite returns naïve — declare it as UTC
            if value.tzinfo is None:
                return value.replace(tzinfo=timezone.utc)
            return value.astimezone(timezone.utc)
        return value

    # make pylint happy

    def process_literal_param(self, value: datetime | None, dialect: Dialect) -> Any:
        # just reuse bind logic for literal rendering
        return self.process_bind_param(value, dialect)

    @property
    def python_type(self) -> type[datetime]:
        return datetime

"""SQLAlchemy-backed Unit of Work for Calista.

Provides a context-managed UnitOfWork using a SQLAlchemy Connection
and the SqlAlchemyEventStore.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from calista.adapters.eventstore.sqlalchemy_adapters import SqlAlchemyEventStore
from calista.interfaces.unit_of_work import AbstractUnitOfWork

if TYPE_CHECKING:
    from sqlalchemy.engine import Connection, Engine


class SqlAlchemyUnitOfWork(AbstractUnitOfWork):
    """SQLAlchemy-backed Unit of Work."""

    def __init__(self, engine: Engine):
        self.engine = engine
        self.connection: Connection

    def __enter__(self):
        self.connection = self.engine.connect()
        self.eventstore = SqlAlchemyEventStore(self.connection)
        return super().__enter__()

    def __exit__(self, *args):
        super().__exit__(*args)
        self.connection.close()

    def commit(self):
        self.connection.commit()

    def rollback(self):
        self.connection.rollback()

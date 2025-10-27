from calista.adapters.catalog.memory_store import InMemoryCatalogData
from calista.adapters.catalog.site_catalog.memory import InMemorySiteCatalog
from calista.adapters.eventstore.memory import MemoryEventStore
from calista.bootstrap.bootstrap import build_message_bus
from calista.interfaces.unit_of_work import AbstractUnitOfWork, CatalogBundle
from calista.service_layer.handlers import COMMAND_HANDLERS

# pylint: disable=consider-using-assignment-expr


class FakeUoW(AbstractUnitOfWork):
    """A fake unit of work for testing purposes."""

    def __init__(self):
        catalog_data = InMemoryCatalogData(
            sites={}, telescopes={}, instruments={}, facilities={}
        )
        self.eventstore = MemoryEventStore()
        self.catalogs = CatalogBundle(sites=InMemorySiteCatalog(catalog_data))
        self.committed = False

    def commit(self):
        self.committed = True

    def rollback(self):
        pass


def bootstrap_test_bus():
    """Bootstrap a message bus for testing purposes."""
    uow = FakeUoW()
    return build_message_bus(uow=uow, command_handlers=COMMAND_HANDLERS)

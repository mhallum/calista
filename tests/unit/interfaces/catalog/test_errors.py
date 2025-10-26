"""Unit tests for calista.interfaces.catalog.errors."""

from calista.interfaces.catalog.errors import CatalogError

# pylint: disable=magic-value-comparison


def test_catalog_error_message_default():
    """CatalogError uses a default message if none is provided."""
    error = CatalogError(kind="site", key="LDT")
    assert str(error) == "site (LDT) catalog error"

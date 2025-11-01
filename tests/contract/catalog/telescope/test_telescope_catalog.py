"""Contract tests for TelescopeCatalog adapters.

These tests ensure adapters can publish revisions and retrieve snapshots, maintain
deterministic telescope versions, accept case-insensitive codes, raise the expected catalog
errors, and persist recorded_at timestamps as timezone-aware UTC datetimes.
"""

# ruff: noqa: F403
# pylint: disable=wildcard-import, unused-wildcard-import
from tests.contract.catalog.shared.versioned_catalog_base import *

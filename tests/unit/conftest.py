"""Default marks for tests under `tests/unit/`."""

from pathlib import Path

import pytest

# pylint: disable=unused-argument

UNIT_ROOT = Path(__file__).parent.resolve()
MARKER_NAME = "unit"


@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    """Add default `unit` marks to items in `tests/unit/`."""
    for item in items:
        path = item.path.resolve()  # pytest>=8: pathlib.Path
        if UNIT_ROOT in path.parents:
            if not any(marker.name == MARKER_NAME for marker in item.iter_markers()):
                item.add_marker(pytest.mark.unit)

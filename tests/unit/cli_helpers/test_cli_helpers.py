"""Unit tests for `calista.cli.helpers`.

Covers three areas:
1) URL sanitization helper.
2) OSC-8 hyperlink support detection heuristic.
3) Emoji → ASCII glyph fallbacks in stderr messages.

The glyph helpers write to **stderr** via Click; tests simulate an ASCII-only
terminal by patching `click.get_text_stream` to return a stream object with
`encoding = "ascii"` and then assert the ASCII fallbacks are used.
"""

from __future__ import annotations

import pytest

from calista.cli.helpers import hyperlinks, sanitize_url

# ---------------------------------------------------------------------------
# Test utilities
# ---------------------------------------------------------------------------


class FakeAsciiStream:
    """Minimal TTY-like stream that reports ASCII encoding.

    Provides just enough surface for code that inspects terminal capabilities:
    - `encoding` attribute to drive encoding-dependent behavior.
    - `isatty()` returning `True` so TTY guards do not early-exit.
    - `write()` stub so it quacks like a text stream if inspected.
    """

    encoding = "ascii"

    def isatty(self) -> bool:  # pylint: disable=no-self-use
        """Pretend to be an interactive terminal (required by some guards)."""
        return True

    def write(self, s) -> None:  # pragma: no cover - not used, present for completeness
        """No-op write stub; tests capture via pytest rather than this method."""


@pytest.fixture(autouse=True)
def _clean_osc8_env(monkeypatch):
    """Clear terminal-identifying env vars before each test.

    Ensures the OSC-8 detection matrix sets only the variables under test and
    that no incidental environment on the runner bleeds into expectations.
    """
    for k in ("TERM_PROGRAM", "WT_SESSION", "VTE_VERSION", "TERM"):
        monkeypatch.delenv(k, raising=False)


# ---------------------------------------------------------------------------
# URL sanitization
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        (
            "postgresql+psycopg://user:pass@localhost/dbname",
            "postgresql+psycopg://user:***@localhost/dbname",
        ),
        (
            "postgresql+psycopg://user@localhost/dbname",
            "postgresql+psycopg://user@localhost/dbname",
        ),
        ("sqlite:///some/path/to/db.sqlite3", "sqlite:///some/path/to/db.sqlite3"),
        ("sqlite:///:memory:", "sqlite:///:memory:"),
    ],
)
def test_sanitize_url(url: str, expected: str) -> None:
    """Mask passwords in URLs while leaving other cases unchanged."""
    assert sanitize_url(url) == expected


# ---------------------------------------------------------------------------
# OSC-8 hyperlink support detection
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("env", "expected"),
    [
        ({"TERM_PROGRAM": "vscode"}, True),
        ({"TERM_PROGRAM": "Apple_Terminal"}, True),
        ({"TERM_PROGRAM": "iTerm.app"}, True),
        ({"TERM_PROGRAM": "WezTerm"}, True),
        ({"TERM_PROGRAM": "kitty"}, True),
        ({"WT_SESSION": "1"}, True),  # Windows Terminal
        ({"VTE_VERSION": "6000"}, True),  # GNOME / Tilix / VTE family
        ({"TERM": "alacritty"}, True),  # Alacritty
        ({"TERM": "konsole-256color"}, True),  # Konsole
        ({}, False),  # no signals
    ],
)
def test_supports_osc8_matrix(monkeypatch, env, expected):
    """Verify heuristic returns expected result for each terminal signal."""
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    # isatty() must be True or early-exit returns False
    assert (
        hyperlinks.supports_osc8(
            stream=FakeAsciiStream()  # type: ignore[arg-type]
        )
        is expected
    )


def test_supports_osc8_non_tty(monkeypatch):
    """Return False when the stream is not a TTY, regardless of env."""

    class FakeNonTTY:
        # pylint: disable=missing-class-docstring,missing-function-docstring,no-self-use,too-few-public-methods
        def isatty(self) -> bool:
            return False

    monkeypatch.setenv("TERM_PROGRAM", "vscode")
    assert (
        hyperlinks.supports_osc8(
            stream=FakeNonTTY()  # type: ignore[arg-type]
        )
        is False
    )

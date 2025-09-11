"""Unit tests for :mod:`calista.cli.helpers.messages`.

This suite verifies three behaviors:

1) Emoji/ASCII glyph selection respects the *current* stderr encoding
   reported by ``click.get_text_stream("stderr")``.
2) ``_supports_character`` **re-queries** Click's text stream on every call
   (guards against implementations that cache or ignore the stream).
3) ``warn``/``success`` emit **styled** (ANSI yellow/green + bold + reset)
   lines to **stderr** (and not stdout).
"""

import io
import sys

import click
import pytest

from calista.entrypoints.cli.helpers.messages import (
    _supports_character,
    caution_glyph,
    error,
    error_glyph,
    success,
    success_glyph,
    warn,
)

SET_YELLOW = "\x1b[33m"
SET_GREEN = "\x1b[32m"
SET_RED = "\x1b[31m"
SET_BOLD = "\x1b[1m"
RESET = "\x1b[0m"


class FakeTTY(io.StringIO):
    """A text stream that mimics a TTY and exposes a controllable encoding.

    Click consults the stream's ``.encoding`` and ``.isatty()`` to decide if
    color should be emitted and whether Unicode glyphs are encodable. This
    helper lets tests deterministically drive those decisions.
    """

    def __init__(self, encoding: str):
        super().__init__()
        self._encoding = encoding

    @property
    def encoding(self) -> str:
        """Declared character encoding (e.g., ``'ascii'`` or ``'utf-8'``)."""
        return self._encoding

    @encoding.setter
    def encoding(self, value: str) -> None:
        self._encoding = value

    def isatty(self) -> bool:
        """Report that this stream is a TTY (prevents Click from stripping ANSI)."""
        return True


@pytest.mark.parametrize(
    ("encoding", "expected_caution", "expected_success", "expected_error"),
    [
        ("ascii", "[!]", "[OK]", "[X]"),
        ("utf-8", "⚠️", "✅", "❌"),
    ],
)
def test_glyphs_respect_stream_encoding(
    monkeypatch, encoding, expected_caution, expected_success, expected_error
):
    """caution_glyph/success_glyph/error_glyph choose emoji vs ASCII according to stderr encoding.

    Patches ``click.get_text_stream("stderr")`` to a FakeTTY with the requested
    encoding so the glyph decision is deterministic.
    """
    stream = FakeTTY(encoding)

    # Force _supports_character() to inspect our fake stderr
    monkeypatch.setattr(click, "get_text_stream", lambda name: stream)

    assert caution_glyph() == expected_caution
    assert success_glyph() == expected_success
    assert error_glyph() == expected_error


def test_supports_character_requeries_stream_each_call(monkeypatch):
    """_supports_character must consult Click's stream on every call (no caching).

    We alternate encodings between calls (ascii → utf-8) and expect the first
    probe to fail and the second to succeed, proving re-querying behavior.
    """
    calls: list[str] = []

    def stream_factory(name: str):  # pylint: disable=unused-argument
        # Alternate encodings on each call
        enc = "ascii" if len(calls) == 0 else "utf-8"
        calls.append(enc)
        return FakeTTY(enc)

    monkeypatch.setattr(click, "get_text_stream", stream_factory)

    # First call should report False for ascii (emoji not encodable)
    assert _supports_character("⚠️") is False
    # Second call should re-fetch and succeed for utf-8
    assert _supports_character("⚠️") is True

    assert calls == ["ascii", "utf-8"]  # sanity


@pytest.mark.parametrize(
    ("encoding", "glyph", "color_code", "func"),
    [
        ("ascii", "[!]", SET_YELLOW, warn),
        ("utf-8", "⚠️", SET_YELLOW, warn),
        ("ascii", "[OK]", SET_GREEN, success),
        ("utf-8", "✅", SET_GREEN, success),
        ("ascii", "[X]", SET_RED, error),
        ("utf-8", "❌", SET_RED, error),
    ],
)
def test_messages_emit_styled_stderr(monkeypatch, encoding, glyph, color_code, func):
    """warn/success/error write bold, colored lines to stderr with the right glyph.

    We point both the *probe* (Click's text stream) and the *writer* (sys.stderr)
    to the same FakeTTY so that glyph choice and actual output are consistent.
    """
    stream = FakeTTY(encoding)

    # Same object for probe and writer
    monkeypatch.setattr(click, "get_text_stream", lambda name: stream)
    monkeypatch.setattr(sys, "stderr", stream, raising=False)

    # Ensure color is not globally disabled in CI
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setenv("CLICOLOR", "1")

    func("danger!")

    out = stream.getvalue()
    assert glyph in out
    assert SET_BOLD in out
    assert color_code in out
    assert RESET in out


def test_warn_writes_to_stderr_only(monkeypatch, capsys):
    """warn should write to stderr and leave stdout untouched (for machine output)."""
    stream = FakeTTY("utf-8")
    monkeypatch.setattr(click, "get_text_stream", lambda name: stream)
    # Let Click write to real sys.stderr so capsys can see it
    msg = "danger!"
    warn(msg)
    captured = capsys.readouterr()
    assert msg in captured.err
    assert captured.out == ""

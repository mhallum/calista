"""Terminal message helpers for the Calista CLI.

Small helpers for rendering user-visible lines with sensible emoji→ASCII fallbacks.
Messages write to stderr by default so stdout can remain machine-readable.
"""

from typing import TextIO

import click


def _supports_character(character: str, stream: TextIO | None = None) -> bool:
    """Return True if *character* can be encoded on the target stream.

    Uses the stream's declared encoding (defaults to Click's stderr stream).
    This is a lightweight guard to decide whether to emit emojis or fall back
    to ASCII so terminals without UTF-8 don't raise `UnicodeEncodeError`.

    Args:
        character: A single Unicode character to probe (e.g., "⚠️", "✅").
        stream: A file-like object with an ``encoding`` attribute; if omitted,
            ``click.get_text_stream("stderr")`` is used.

    Returns:
        bool: True if encoding succeeds; False on `UnicodeEncodeError`.
    """

    stream = stream or click.get_text_stream("stderr")
    encoding = getattr(stream, "encoding", None) or "utf-8"
    try:
        character.encode(encoding)
    except UnicodeEncodeError:
        return False
    return True


def caution_glyph(stream: TextIO | None = None) -> str:
    """Warning marker suitable for terminals with/without emoji support.

    Returns:
        str: "⚠️" when the stream supports it; otherwise the ASCII fallback "[!]".
    """
    return "⚠️" if _supports_character("⚠️", stream) else "[!]"


def success_glyph(stream: TextIO | None = None) -> str:
    """Success marker with graceful fallbacks.

    Tries a green check emoji first, then the Unicode check mark, then ASCII.

    Returns:
        str: One of "✅", "✓", or "[OK]" depending on stream support.
    """
    if _supports_character("✅", stream):
        return "✅"
    if _supports_character("✓", stream):
        return "✓"
    return "[OK]"


def warn(msg: str) -> None:
    """Emit a yellow, bold warning line to **stderr** with a caution glyph.

    Args:
        msg: The message to display.

    Note:
        Warnings go to **stderr** so they won't interfere with data piped from
        stdout (e.g., when using ``--json``).

    Example:
        ``⚠️  This will modify your database.``

    """
    g = caution_glyph()
    click.secho(f"{g}  {msg}", fg="yellow", bold=True, err=True)


def success(msg: str) -> None:
    """Emit a green, bold success line to **stderr** with a success glyph.

    Args:
        msg: The message to display.

    Note:
        Success messages go to **stderr** to keep stdout clean for machine-
        readable output when needed. Change this if your UX prefers stdout.

    Example:
        ``✅  Database is up-to-date at head.``
    """
    g = success_glyph()
    click.secho(f"{g}  {msg}", fg="green", bold=True, err=True)

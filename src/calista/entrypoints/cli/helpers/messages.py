"""Terminal message helpers for the Calista CLI.

Small helpers for rendering user-visible lines with sensible emoji→ASCII fallbacks.
Messages write to stderr by default so stdout can remain machine-readable.
"""

import click


def _supports_character(character: str) -> bool:
    """Return True if *character* can be encoded on stderr.

    This is a lightweight guard to decide whether to emit emojis or fall back
    to ASCII so terminals without UTF-8 don't raise `UnicodeEncodeError`.

    Args:
        character: A single Unicode character to probe (e.g., "⚠️", "✅").

    Returns:
        bool: True if encoding succeeds; False on `UnicodeEncodeError`.
    """

    stream = click.get_text_stream("stderr")  # pragma: no mutate
    encoding = getattr(stream, "encoding")
    try:
        character.encode(encoding)
    except UnicodeEncodeError:
        return False
    return True


def caution_glyph() -> str:
    """Warning marker suitable for terminals with/without emoji support.

    Returns:
        str: "⚠️" when the stream supports it; otherwise the ASCII fallback "[!]".
    """
    emoji, fallback = ("⚠️", "[!]")  # pragma: no mutate
    if _supports_character(emoji):
        return emoji
    return fallback


def success_glyph() -> str:
    """Success marker with graceful fallbacks.

    Tries a green check emoji first, then ASCII.

    Returns:
        str: "✅" or "[OK]" depending on stream support.
    """
    emoji, fallback = ("✅", "[OK]")  # pragma: no mutate
    if _supports_character(emoji):
        return emoji
    return fallback


def error_glyph() -> str:
    """Error marker with graceful fallbacks.

    Tries a red cross emoji first, then ASCII.

    Returns:
        str: "❌" or "[X]" depending on stream support.
    """
    emoji, fallback = ("❌", "[X]")  # pragma: no mutate
    if _supports_character(emoji):
        return emoji
    return fallback


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


def error(msg: str) -> None:
    """Emit a red, bold error line to **stderr** with a caution glyph.

    Args:
        msg: The message to display.

    Note:
        Error messages go to **stderr** so they won't interfere with data piped from
        stdout (e.g., when using ``--json``).

    Example:
        ``❌  Cannot connect to database.``

    """
    g = error_glyph()
    click.secho(f"{g}  {msg}", fg="red", bold=True, err=True)

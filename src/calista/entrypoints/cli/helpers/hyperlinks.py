"""OSC-8 hyperlink utilities for the Calista CLI.

Provides a small heuristic to detect whether the active text stream supports
OSC-8 terminal hyperlinks and a helper to render a URL as a clickable link,
falling back to plain text when unsupported. Pure formatting only.
"""

import os
import sys
from typing import TextIO


def supports_osc8(stream: TextIO | None = None) -> bool:
    """Heuristically detect whether the target stream supports OSC-8 hyperlinks.

    Args:
        stream: File-like text stream to probe; defaults to ``sys.stdout``.

    Returns:
        bool: ``True`` if hyperlinks should be emitted; ``False`` otherwise.

    Notes:
        - Returns ``False`` when the stream is not a TTY (e.g., piped or redirected).
        - Uses a conservative allowlist based on terminal identifiers
          (e.g., VS Code, iTerm2, WezTerm, Kitty, Windows Terminal).
        - This is a best-effort check; some pagers or settings may still strip escapes.
    """
    stream = stream or sys.stdout
    if not getattr(stream, "isatty", lambda: False)():
        return False
    terminal_program = (os.getenv("TERM_PROGRAM") or "").lower()
    return bool(
        terminal_program
        in {"apple_terminal", "vscode", "iterm.app", "wezterm", "kitty"}
        or os.getenv("WT_SESSION")  # Windows Terminal
        or os.getenv("VTE_VERSION")  # GNOME Terminal, Tilix, etc.
        or os.getenv("TERM", "").startswith(("alacritty", "konsole"))
    )


def hyperlink(url: str) -> str:
    """Return an OSC-8 hyperlink with a graceful fallback for unsupported terminals.

    Args:
        url: Target URL.


    Returns:
        str: The URL wrapped in OSC-8 sequences when supported, otherwise a
        plain URL string.

    Notes:
        - Uses BEL (``\\x07``) as the OSC-8 terminator for broad terminal support.
    """
    if not supports_osc8():
        return url
    return f"\x1b]8;;{url}\x07{url}\x1b]8;;\x07"  # OSC 8 ; ; URL BEL

"""CLI helpers for CALISTA.

Utilities used by the command-line interface: URL sanitization for safe display,
OSC-8 terminal hyperlinks when supported, and message emitters that write to
stderr with emoji→ASCII fallbacks.
"""

from .db_url import sanitize_url
from .hyperlinks import hyperlink
from .messages import success, warn

__all__ = ["sanitize_url", "warn", "success", "hyperlink"]

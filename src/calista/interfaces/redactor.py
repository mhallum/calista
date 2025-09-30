"""Interfaces for redacting sensitive values.

This module defines the Redactor interface and the RedactorMode enumeration
used by adapters to sanitize secrets (passwords, tokens, API keys, etc.)
from strings such as database URLs, HTTP authorization headers, and free-form
key/value fragments. Implementations should provide sanitize_db_url that
returns a display-safe string with sensitive values redacted.
"""

import abc
from enum import Enum

# pylint: disable=too-few-public-methods


class RedactorMode(Enum):
    """Enumeration for redactor modes.

    Modes:
    - LENIENT: redact passwords/tokens but keep usernames/ids visible.
    - STRICT: redact passwords/tokens and also usernames/ids.
    """

    LENIENT = "lenient"
    STRICT = "strict"


class Redactor(abc.ABC):
    """Interface for sanitizing sensitive information from strings."""

    _mode: RedactorMode

    @abc.abstractmethod
    def sanitize_db_url(self, raw_url: str) -> str:
        """Return a display-safe DB URL.

        Args:
            raw_url: Raw database connection URL.

        Returns:
            A sanitized database URL with sensitive information redacted.
        """

    @property
    def mode(self) -> RedactorMode:
        """Return the redaction mode."""
        return self._mode

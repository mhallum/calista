"""Regex-based redactor for sanitizing secrets from strings.

This module provides a Redactor implementation that masks sensitive values
(passwords, tokens, API keys, etc.) found in database URLs, ODBC/DSN-style
strings, HTTP Authorization headers, and free-form "key: value" fragments.
It supports lenient and strict modes (strict also redacts usernames/ids).
"""

import re

from calista.interfaces import redactor
from calista.interfaces.redactor import RedactorMode

# pylint: disable=too-few-public-methods

PLACEHOLDER = "***"
SECRET_KEYWORDS = [
    "password",
    "passwd",
    "pwd",
    "secret",
    "token",
    "api_key",
    "apikey",
    "access_token",
    "refresh_token",
    "id_token",
    "authorization",
    "sig",
    "signature",
]
STRICT_MODE_ADDITIONAL_KEYWORDS = ["user", "username", "uid"]
BEARER_PATTERN = re.compile(r"(?i)Bearer\s[0-9a-zA-Z\.]*")
PWD_PATTERN = re.compile(r"\bpwd=\S+", re.IGNORECASE)
UID_PATTERN = re.compile(r"\buid=[^;]+", re.IGNORECASE)


class Redactor(redactor.Redactor):
    """Redactor implementation using regex-based sanitization."""

    def __init__(self, mode: RedactorMode = RedactorMode.LENIENT) -> None:
        self._mode = mode

    def sanitize_db_url(self, raw_url: str) -> str:
        sanitized = str(raw_url)

        # 1) user:pass@  → user:***@
        sanitized = re.sub(
            r"(?<=://)([^:@/]+):([^@/]+)@",
            r"\1:***@",
            sanitized,
        )

        # 2) Strict: redact visible username before '@' (but only if one exists)
        if self._mode == RedactorMode.STRICT:
            sanitized = re.sub(
                r"(?<=://)([^:@/]+)(?=:(?:\*\*\*|[^@/]*)@)",
                PLACEHOLDER,
                sanitized,
            )

        # 3) Bearer tokens: Bearer <token>
        sanitized = BEARER_PATTERN.sub(PLACEHOLDER, sanitized)

        # 4) Query-string secrets: build regex from SECRET_KEYWORDS

        keywords_pattern = "|".join(
            kw.replace("_", "[-_]?")
            for kw in (
                SECRET_KEYWORDS + STRICT_MODE_ADDITIONAL_KEYWORDS
                if self._mode == RedactorMode.STRICT
                else SECRET_KEYWORDS
            )
        )
        sanitized = re.sub(
            rf"(?i)([?&](?:{keywords_pattern})=)[^&#\s;]*",
            rf"\1{PLACEHOLDER}",
            sanitized,
        )

        # 5) ODBC-ish pairs: Pwd=... (leave Uid alone unless strict)
        sanitized = re.sub(PWD_PATTERN, f"Pwd={PLACEHOLDER}", sanitized)
        if self._mode == RedactorMode.STRICT:
            sanitized = re.sub(
                UID_PATTERN,
                f"Uid={PLACEHOLDER}",
                sanitized,
            )

        # 6) Key:Value secrets (non-URL accidental forms)
        sanitized = re.sub(
            rf"(?i)(\b(?:{keywords_pattern})\s*:\s*)\S+",
            rf"\1{PLACEHOLDER}",
            sanitized,
        )

        return sanitized

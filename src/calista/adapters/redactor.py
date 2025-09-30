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
STRICT_MODE_SECRET_KEYWORDS = SECRET_KEYWORDS + STRICT_MODE_ADDITIONAL_KEYWORDS
SECRET_KEYWORDS_PATTERN = "|".join(kw.replace("_", "[-_]?") for kw in (SECRET_KEYWORDS))
STRICT_MODE_SECRET_KEYWORDS_PATTERN = "|".join(
    kw.replace("_", "[-_]?") for kw in (STRICT_MODE_SECRET_KEYWORDS)
)
QUERY_STRING_PATTERN = re.compile(
    rf"([?&](?:{SECRET_KEYWORDS_PATTERN})=)[^&#\s;]*", re.IGNORECASE
)
STRICT_MODE_QUERY_STRING_PATTERN = re.compile(
    rf"([?&](?:{STRICT_MODE_SECRET_KEYWORDS_PATTERN})=)[^&#\s;]*", re.IGNORECASE
)
KEY_VALUE_SECRET_PATTERN = re.compile(
    rf"(\b(?:{SECRET_KEYWORDS_PATTERN})\s*:\s*)\S+", re.IGNORECASE
)
STRICT_MODE_KEY_VALUE_SECRET_PATTERN = re.compile(
    rf"(\b(?:{STRICT_MODE_SECRET_KEYWORDS_PATTERN})\s*:\s*)\S+", re.IGNORECASE
)
BEARER_PATTERN = re.compile(r"Bearer\s[0-9a-zA-Z\.]*", re.IGNORECASE)
PWD_PATTERN = re.compile(r"\bpwd=\S+", re.IGNORECASE)
UID_PATTERN = re.compile(r"\buid=[^;]+", re.IGNORECASE)
URL_PASSWORD_PATTERN = re.compile(r"(?<=://)([^:@/]+):([^@/]+)@")
URL_USER_PATTERN = re.compile(r"(?<=://)([^:@/]+)(?=:(?:\*\*\*|[^@/]*)@)")


class Redactor(redactor.Redactor):
    """Redactor implementation using regex-based sanitization."""

    def __init__(self, mode: RedactorMode = RedactorMode.LENIENT) -> None:
        self._mode = mode

    def sanitize_db_url(self, raw_url: str) -> str:
        sanitized = str(raw_url)

        # 1) user:pass@  → user:***@
        sanitized = re.sub(
            URL_PASSWORD_PATTERN,
            # Mutation testing somehow messes with this line without actually mutating anything.
            # This leads to "survived" mutants that don't actually change the code.
            # Hence the pragma to ignore mutation for this line.
            r"\1:***@",  # pragma: no mutate
            sanitized,
        )

        # 2) Strict: redact visible username before '@' (but only if one exists)
        if self._mode == RedactorMode.STRICT:
            sanitized = re.sub(
                URL_USER_PATTERN,
                PLACEHOLDER,
                sanitized,
            )

        # 3) Bearer tokens: Bearer <token>
        sanitized = BEARER_PATTERN.sub(PLACEHOLDER, sanitized)

        # 4) Query-string secrets: build regex from SECRET_KEYWORDS

        query_pattern = (
            STRICT_MODE_QUERY_STRING_PATTERN
            if self._mode == RedactorMode.STRICT
            else QUERY_STRING_PATTERN
        )

        sanitized = re.sub(
            query_pattern,
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

        key_value_pattern = (
            STRICT_MODE_KEY_VALUE_SECRET_PATTERN
            if self._mode == RedactorMode.STRICT
            else KEY_VALUE_SECRET_PATTERN
        )

        sanitized = re.sub(
            key_value_pattern,
            rf"\1{PLACEHOLDER}",
            sanitized,
        )

        return sanitized

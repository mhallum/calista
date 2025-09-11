"""Database URL helpers for CLI output.

This module provides `sanitize_url`, which renders a database URL with any
password redacted (as ``***``) so it's safe to show in prompts, logs, or errors.
It uses SQLAlchemy's URL parser and performs no I/O or connectivity checks.

Examples:
    ```bash
    >>> sanitize_url("postgresql+psycopg://calista:s3cr3t@localhost:5432/calista")
    'postgresql+psycopg://calista:***@localhost:5432/calista'
    ```
    ```bash
    >>> sanitize_url("sqlite+pysqlite:///tmp/test.db")
    'sqlite+pysqlite:///tmp/test.db'
    ```

Caveats:
    - Only the URL password field is redacted. If you embed secrets in query
      parameters (e.g., ``?password=...``), they are not scrubbed by this helper.
"""

from sqlalchemy.engine import make_url


def sanitize_url(url: str) -> str:
    """Sanitize a database URL for display by redacting the password, if any.

    Args:
        url (str): The database URL to sanitize.

    Returns:
        str: The sanitized database URL.
    """
    parsed = make_url(url)
    return parsed.render_as_string(hide_password=True)

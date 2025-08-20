"""CALISTA config system"""

import os
from pathlib import Path


def get_postgres_uri() -> str:
    """Get the PostgreSQL URI from environment variables or defaults."""
    host = os.environ.get("CALISTA_DB_HOST", "localhost")
    port = 54321 if host == "localhost" else 5432  # pylint: disable=magic-value-comparison
    password = os.environ.get("CALISTA_DB_PASSWORD", "abc123")
    user = os.environ.get("CALISTA_DB_USER", "calista")
    db_name = "allocation"
    return f"postgresql://{user}:{password}@{host}:{port}/{db_name}"


def get_file_store_path() -> Path:
    """Get the file store path from environment variables or defaults."""
    return Path(os.environ.get("CALISTA_FILE_STORE_PATH", Path.home() / "calista-data"))

# Database Setup

CALISTA uses **PostgreSQL** by default.

## Quick start (PostgreSQL)

1. Point CALISTA at your database:

    ```bash
    export CALISTA_DB_URL=postgresql+psycopg://calista:changeme@localhost:5432/calista
    ```

    _Optional (omit the password if your system supplies it via `~/.pgpass` or a Postgres service):_

    ```bash
    export CALISTA_DB_URL=postgresql+psycopg://calista@localhost:5432/calista
    ```

2. Check database status:

    Before applying migrations, verify CALISTA can reach your database:

    ```bash
    calista db status
    ```

    **Typical output**

    _Uninitialized (fresh database):_

    ```bash
    ✅  Database reachable
    Backend : postgresql
    URL     : postgresql+psycopg://USER:***@localhost:5432/calista
    Schema  : uninitialized
    ```

    If you see " Cannot connect to database", double-check `CALISTA_DB_URL` and that your DB is running.

3. Initialize the schema:

    ```bash
    calista db upgrade
    ```

4. (Optional) Verify the current revision:

    ```bash
    calista db current
    ```

    or

    ```bash
    calista db status
    ```

## If you don’t already have a PostgreSQL database

- **macOS (Homebrew)**

   ```bash
   brew install postgresql@17
   brew services start postgresql@17
   ```

   _Note: you may need to update your PATH per Homebrew’s post-install message._

- **Ubuntu/Debian**

   ```bash
   sudo apt-get update && sudo apt-get install -y postgresql
   sudo systemctl enable --now postgresql
   ```

- **Docker (quick local database)**

   ```bash
   docker run --name calista-pg \
     -e POSTGRES_USER=calista \
     -e POSTGRES_PASSWORD=changeme \
     -e POSTGRES_DB=calista \
     -p 5432:5432 -d postgres:17
   ```

Create a role and database (example, your setup may differ):

```bash
psql -U postgres -h localhost -c "CREATE ROLE calista LOGIN PASSWORD 'changeme';"
psql -U postgres -h localhost -c "CREATE DATABASE calista OWNER calista;"
```

Verify connectivity:

```bash
psql "postgresql://calista:changeme@localhost:5432/calista" -c "SELECT 1;"
```

## Alternate engine (SQLite, limited features)

```bash
export CALISTA_DB_URL=sqlite:///./calista.db
calista db upgrade
```

SQLite is supported for quick local runs and CI, but it lacks some PostgreSQL features (e.g., JSONB indexes, certain CHECK constraints).

For more advanced database commands, see the [CLI reference](../cli/db.md).

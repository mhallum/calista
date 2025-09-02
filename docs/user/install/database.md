# Database Setup

> Note: In source installs, run `alembic upgrade head`. A packaged `calista-db upgrade`
> command will be provided in the next release.

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
2. Initialize the schema:
   ```bash
   alembic upgrade head
   ```
3. Check status:
   ```bash
   alembic current
   ```

## If you don’t already have a PostgreSQL database

- macOS (Homebrew)
  ```bash
  brew install postgresql@17
  brew services start postgresql@17
  ```
  _Note that you may need to update your PATH. Follow homebrew's instructions._
- Ubuntu/Debian
  ```bash
  sudo apt-get update && sudo apt-get install -y postgresql
  sudo systemctl enable --now postgresql
  ```
- Docker (quick local database)
  ```bash
  docker run --name calista-pg -e POSTGRES_USER=calista -e POSTGRES_PASSWORD=changeme \
    -e POSTGRES_DB=calista -p 5432:5432 -d postgres:17
  ```

Create a database and user (example, your setup may be different):

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
alembic upgrade head
alembic current
```

SQLite is supported for quick local runs and CI, but it lacks some PostgreSQL features (e.g., JSONB indexes, certain CHECK expressions).

## Troubleshooting

- Permission errors: ensure the database and user exist and can create schema.
- Connection refused: check host/port, container networking, or service name.
- Schema already present (from an older dev DB):
  - Align Alembic without changing the DB: `alembic stamp head`
  - Or reset: `alembic downgrade base && alembic upgrade head`

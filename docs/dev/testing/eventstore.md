# Testing the Event Store Schema

How CALISTA tests the event-store schema and migrations across SQLite and PostgreSQL.

## What’s covered

- **Types (unit-ish)**
  - PortableJSON round-trip (SQLite JSON / Postgres JSONB)
  - UTCDateTime timezone/nullable behavior
- **Schema shape (integration)**
  - Columns + nullability
  - PK / UQ: `pk_event_store`, `uq_event_store_event_id`, `uq_event_store_stream_id_version`
  - CHECKs: `version >= 1`, `length(event_id) = 26`
  - Server default for `recorded_at`
- **Append-only invariants (integration)**
  - `UPDATE` is rejected
  - `DELETE` is rejected
    (Enforced by triggers: PL/pgSQL on Postgres; `RAISE(ABORT)` on SQLite when DB is created via Alembic)
- **Migrations smoke**
  - `alembic upgrade head` creates `event_store`
  - `alembic downgrade base` drops it
  - Verified on SQLite (file DB) and Postgres (Testcontainers)
- **Postgres extras**
  - JSONB GIN indexes on `payload`, `metadata` (PG-only)

## Fixtures (tests/conftest.py)

- `sqlite_engine_memory` — In-memory SQLite; tables via `metadata.create_all()` (no Alembic, thus **no triggers**).
- `sqlite_engine_file` — File-backed SQLite; **migrated via Alembic** to head (triggers available).
- `pg_url` — Session-scoped Postgres 17 (Testcontainers); migrated to head once.
- `postgres_engine` — Per-test engine using `pg_url`; truncates `event_store` after each test.
- `engine` — Indirection to parametrize tests over the above engines.
- `make_event()` — Factory that returns a valid `event_store` row dict.

## Test modules

- `tests/integration/test_event_store_schema.py`
  Inspects table/columns and asserts nullability, checks, PK/UQ names, server defaults, and type/dialect expectations.

- `tests/integration/test_event_store_append_only.py`
  Verifies append-only behavior (parametrized over `postgres_engine` and `sqlite_engine_file`):

  - Seed a row, assert `UPDATE`/`DELETE` raise, and the row remains unchanged/present.

- `tests/integration/test_migrations_roundtrip_sqlite.py`
  File-backed SQLite:

  - `upgrade head` ⇒ `event_store` exists (via `sqlite_master`)
  - `downgrade base` ⇒ `event_store` absent

- `tests/integration/test_migrations_roundtrip_pg.py`
  Postgres 17 via Testcontainers:
  - Creates a scratch DB (AUTOCOMMIT on `postgres`)
  - `upgrade head` ⇒ `event_store` exists; typed insert via SA `event_store` table
  - `downgrade base` ⇒ `event_store` absent
  - Drops the scratch DB

## Which backend for which test?

| Area                      | SQLite (memory) | SQLite (file, Alembic) | Postgres 17 |
| ------------------------- | --------------- | ---------------------- | ----------- |
| Types / simple DDL checks | ✅              | ✅                     | ✅          |
| Triggers (append-only)    | ❌ (no Alembic) | ✅                     | ✅          |
| JSONB + GIN               | ❌              | ❌                     | ✅          |
| Upgrade/Downgrade smoke   | ❌              | ✅                     | ✅          |

## Running

All tests:

```bash
poetry run pytest
```

Only migrations smoke:

```bash
poetry run pytest tests/integration/test_migrations_roundtrip_pg.py
poetry run pytest tests/integration/test_migrations_roundtrip_sqlite.py
```

Only append-only:

```bash
poetry run pytest tests/integration/test_event_store_append_only.py
```

Single test:

```bash
poetry run pytest tests/integration/test_event_store_append_only.py::test_update_is_blocked
```

## Notes / gotchas

- Triggers exist only when the DB is created via **Alembic**. The in-memory SQLite fixture uses `create_all()` and therefore does **not** have triggers.
- Postgres JSONB GIN indexes are **PG-only** and are guarded in the migration; SQLite will not have them.
- Round-trip tests rely on `env.py` resolving the URL via `-x url=...`/config/env so migrations run against the ephemeral databases created by the tests.

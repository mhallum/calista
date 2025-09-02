# Migrations Policy (Alembic)

## Defaults

- `compare_type = True`
- SQLite runs with `render_as_batch = True`
- URL comes from `CALISTA_DB_URL` (or `-x url=...`), not hardcoded in `alembic.ini`
- Baseline is **pinned/immutable**; introduce a new baseline only with a clear migration path

## Authoring rules

- Guard Postgres-specific features:
  ```py
  bind = op.get_bind()
  if bind.dialect.name == "postgresql":
  ...
  ```
- Provide SQLite parity where feasible (e.g., triggers using `RAISE(ABORT)`), or explicitly document/skip if not supported
- Use stable, explicit names:
  - Constraints: `pk_event_store`, `uq_event_store_stream_id_version`, …
  - Indexes: ` ix_event_store_event_store_event_type`, …
  - Triggers: `event_store_forbid_mod`, …
- Avoid destructive changes; if unavoidable, add a data-migration step and document rollback behavior
- Keep DDL and data migrations in **separate revisions**; make data steps idempotent

## Review checklist

- [ ] **Upgrade + downgrade** succeed on **SQLite and Postgres**
- [ ] **Round-trip tests** pass (PG + SQLite): upgrade → assert → downgrade → assert
- [ ] **Append-only** behavior enforced (UPDATE/DELETE blocked) where promised
- [ ] Postgres-only code is guarded by `if dialect == "postgresql":`
- [ ] Names of **constraints/indexes/triggers** follow conventions and match tests/docs
- [ ] Reversible (or rationale + safe fallback if not)
- [ ] No unintended table recreations on SQLite (batch mode changes minimized)
- [ ] No data loss without explicit, reviewed data migration
- [ ] Autogenerate diff reviewed; manual edits applied where needed
- [ ] Baseline/revision dependencies correct; no rewrites of published revisions

## Testing checklist

- [ ] `tests/integration/test_migrations_roundtrip_pg.py` passes
- [ ] `tests/integration/test_migrations_roundtrip_sqlite.py` passes
- [ ] `tests/integration/test_event_store_append_only.py` passes (PG and Alembic-backed SQLite if supported)
- [ ] Local `alembic downgrade base && alembic upgrade head` succeeds on both backends

# ADR-0004: Schema Migrations

**Status**: Accepted <br>
**Related**: ADR-0003 Database, ADR-0005 Event Store

## Context

CALISTA must evolve schemas predictably across upgrades. Manual SQL patches are brittle. Users may run Postgres or SQLite, so migrations must be portable.

## Decision

- **Tooling**: Use **Alembic** for migrations.
- **When**:

  - Migrations are explicit by default and run via `calista db upgrade`.
  - On bootstrap of any command that requires the database, CALISTA checks the Alembic revision. If it’s behind, the command fails fast with an instruction to run `calista db upgrade`.
  - Users may opt-in to automatic upgrades via `--auto-upgrade`, `CALISTA_AUTO_UPGRADE=1`, or `[db] auto_upgrade = true` in `calista.toml`. When enabled, CALISTA applies `upgrade head` during bootstrap before command execution.
  - Non-DB commands (help, version, config-only) bypass the check.

- **Direction**:
  - Runtime: Schema migrations are **forward-only**. Once applied, a migration is never rolled back. If a mistake is discovered, it is corrected by writing a new migration that moves the schema forward again. This avoids destructive downgrades and ensures user data is never lost.
  - Development / CI: Migrations may be run both forward and backward. Downgrades are allowed to simplify testing, resetting databases, and iterating on schema design during development. Because test data is disposable, destructive operations are acceptable in this context.
- **Safety**:
  - Pre-upgrade backups are taken only when an upgrade runs (explicit or opt-in auto-upgrade).
  - Dev/CI workflows may skip backups for speed.
- **Versioning**: Alembic tracks the current schema revision in an `alembic_version` table inside the `calista` schema. This table stores the revision identifier of the last applied migration.
- **Dialect Guards**: CALISTA supports Postgres (runtime) and SQLite (dev/CI). Migrations must remain portable across both. Backend-specific implementation details (e.g., JSONB vs TEXT) are documented in developer guides.
- Migration files are named as:<br>
  `YYYYMMDD_HHMM_<short-summary>.py` (UTC timestamp + short description).<br>
  Example: `20250826_1030_create_event_store.py`. <br>
  This ensures chronological ordering and human-readable intent.

## Consequences

- Predictable schema evolution.
- Runtime safety via backups.
- Dev agility via reversible migrations.
- Slight upfront complexity, but avoids chaos later.

# ADR-0003: Database

**Status**: Accepted

**Related**: ADR-0004 Schema Migrations, ADR-0005 Event Store

## Context

CALISTA Requires a persistent relational store for:

- Event store (append-only domain events)
- Metadata (project configs (maybe), migration state)
- Projections

## Decision

- **Primary Runtime Database**: PostgreSQL
- **Development & CI**: SQLite
- **Isolation**: Use dedicated schema (`calista`) in Postgres.
- **Search Path**: Explicitly set (`SET search_path = calista, public`)
- **Connections**:
  - Local intalls for power users.
  - Dockerized Postgres optional, not required
- **User Ownership**: Database is **user-hosted**; CALISTA never provides central hosting.

## Consequences

- Postgres provides strong guarantees for provenance and scale.
- SQLite offers speed/simplicity for dev/CI, but fewer features.
- Schema migration must handle dialect differences.
- Users must configure their own Postgres instances for production.

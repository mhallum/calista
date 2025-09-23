# ADR-0022: Logging & Flight Recorder

**Status:** Accepted

## Context

CALISTA needs reliable, uniform runtime logging for both application and third-party libraries, plus a lightweight way to capture debug context when something goes wrong. We want clean console output, consistent formatting across libraries, and a “last run” artifact we can attach to bug reports—without introducing a durable audit stream.

## Decision

### Scope

- Use **runtime/console logging** + a **flight recorder** for the last run.

### Where logging is configured

- **Entrypoints (CLI/worker)** are responsible for **invoking** logging setup.
- The setup logic resides in a **dedicated module** (e.g., `calista/logging.py`) that defines the console formatter, library baselines, flight recorder wiring, and redaction filters.
- `bootstrap/` and adapters **use** loggers but **do not** attach handlers or mutate global logging.

### Console formatting (runtime)

- Single, unified formatter for CALISTA and libraries (same look).
- Include a top-level channel tag, e.g., `[calista]`, `[alembic]`, `[sqlalchemy]`.

### Verbosity & levels

- Click-Extra defaults: **WARNING** by default; `-v → INFO`; `-vv → DEBUG`.
- `-v/-vv` affect **`calista.*` only**; third-party loggers remain at baselines unless explicitly changed.

### Third-party console controls

- **`--log-level NAME=LEVEL` / `-L NAME=LEVEL`** (repeatable): set **console** minimum levels per third-party prefix (e.g., `-L sqlalchemy=INFO`).
    - Default: `sqlalchemy=WARNING`, `alembic=WARNING`.

### Flight recorder (runtime “last-run” file)

- **Enabled by default.** In-memory ring buffer.
- **Flushes automatically on WARNING/ERROR**; a **manual dump flag** may also be provided to force a write even if no warnings or errors occur.
- Default capacity **2000** records; tunable via `CALISTA_FLIGHT_RECORDER_CAPACITY` envar.
- **Truncate at process start** so only the most recent run is preserved.
- Captures CALISTA **and** third-party runtime logs (console filters do not affect capture).
- **Disable entirely with `--no-flight-recorder`.**

### Log locations

- OS user logs/state directory (defaults):
    - macOS: `~/Library/Logs/CALISTA/last-run.log`
    - Linux: `$XDG_STATE_HOME/calista/logs/last-run.log` (fallback `~/.local/state/calista/logs/last-run.log`)
    - Windows: `%LOCALAPPDATA%\CALISTA\Logs\last-run.log`
- **Override path:** `--log-path PATH` or env `CALISTA_LOG_PATH`.

### Redaction

- Apply a central redaction filter across runtime + flight recorder (mask DSN passwords, tokens, and other secrets).

### Multiprocess readiness (future)

- If workers arrive, switch file sinks to `QueueHandler/QueueListener` to avoid concurrent write issues.

### Namespace reservation

- Reserve the logger name **`calista.audit`** to avoid future collisions if an audit logger is introduced later.

## Alternatives Considered

- **Structured audit logger (`calista.audit`)**: **not necessary now**—single-user workflow, and runtime logs + flight recorder cover current needs. We may revisit later **if** project scope or requirements change.

## Consequences

- Clean, consistent console output with simple controls for third-party verbosity.
- A reliable **last-run** artifact exists when failures occur, without accumulating history on disk.
- Minimal surface area today; room to evolve later without conflicting names.

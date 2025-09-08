# Tooling Guide

This page describes how development tools are configured for CALISTA.

## Configuration Conventions

Tool configuration is centralized in `pyproject.toml` whenever possible, so settings are Git-tracked and colocated with build metadata.

- **In `pyproject.toml`**
    - `ruff` (linting + formatting)
    - `mypy` (static typing)
    - `pytest`
    - `pyright` (used by Pylance)
    - `mutmut` (mutation testing)

- **Separate files**
    - `.pylintrc` → Pylint rules

Editor-only preferences (e.g. VS Code’s `settings.json`) are kept local and not committed.

## Python Versions & Environments

- Python version is declared in `pyproject.toml`.
- Local installs managed with Poetry.
- Virtual environments (`.venv/`, `venv/`) and dotenv files are not committed.

## Pre-commit Hooks

- `pre-commit` runs fast checks before commits (ruff, mypy, pytest).
- Hooks are defined in `.pre-commit-config.yaml` and kept up to date with `pre-commit autoupdate`.

## Testing

- Pytest is the primary test runner.
- Hypothesis is used for property-based testing and integrates directly with pytest.
- Default discovery runs under `tests/`. Non-test folders like `scratch/` are ignored.
- Mutation testing is performed with Mutmut.

## Static Typing

- Type checking is handled by Pyright (via Pylance in VS Code).
- Configuration is kept in `pyproject.toml`.

## CI Alignment

- CI runs the same tooling (ruff, mypy, pytest, mutmut) using `pyproject.toml`.
- Python version matrix matches the version declared locally.

### Configuration Conventions

We centralize tool configuration in `pyproject.toml` whenever possible, so settings are Git-tracked and colocated with other build metadata.

- **In `pyproject.toml`**

  - `ruff` (linting + formatting)
  - `mypy` (static typing)
  - `pytest` (under `[tool.pytest.ini_options]`)

- **Separate files (tool does not support `pyproject.toml`)**
  - `.pylintrc` → Pylint rules
  - `.editorconfig` → basic editor formatting hints (optional)

Other editor-only preferences (e.g. VS Code’s `settings.json`) are kept local and not committed.

This split ensures reproducible tooling while respecting each tool’s supported config format.

### Pytest Configuration

All pytest options are defined in `pyproject.toml` under the `[tool.pytest.ini_options]` section.
We deliberately avoid `pytest.ini`, `tox.ini`, or `setup.cfg`, since their presence takes precedence and would cause pytest to ignore the `pyproject.toml` block.
Keeping all configuration in `pyproject.toml` ensures tool settings are centralized, Git-tracked, and consistent with the rest of the project (ruff, mypy, etc.).

"""Helpers for parsing logger-level CLI options.

This module provides utilities used by the CLI to parse options of the
form NAME=LEVEL (repeatable or comma/space-separated). It normalizes input
values into individual items and converts/validates textual log level names
into the corresponding numeric logging levels.
"""

import logging
import re

import click

# Parser for NAME=LEVEL pairs
DEFAULT_LIB_LEVELS = {"sqlalchemy": logging.WARNING, "alembic": logging.WARNING}


def _normalize_items(value: str | list[str] | tuple[str, ...]) -> list[str]:
    """Normalize an input value into a flat list of items.

    Splits the input on commas and whitespace and removes empty fragments.
    Accepts either a single string (which may contain multiple comma/space-
    separated items) or a sequence of strings (as provided by repeatable Click
    options).

    Args:
        value (str | list[str] | tuple[str, ...]): The option value from Click.

    Returns:
        list[str]: A flat list of non-empty item strings.
    """
    items: list[str] = []
    if isinstance(value, (tuple, list)):
        for v in value:
            items.extend([s for s in re.split(r"[,\s]+", v) if s])
    else:  # plain string
        items.extend([s for s in re.split(r"[,\s]+", value) if s])
    return items


def parse_log_level(
    ctx: click.Context,  # pylint: disable=unused-argument
    param: click.Parameter | None,  # pylint: disable=unused-argument
    value: str | list[str] | tuple[str, ...],
) -> dict[str, int]:
    """Click callback that parses NAME=LEVEL pairs into a name->level dict.

    Combines DEFAULT_LIB_LEVELS with any overrides supplied via the CLI. Each
    item must be of the form NAME=LEVEL where LEVEL is a standard logging level
    name (e.g. DEBUG, INFO, WARNING).

    Args:
        ctx (click.Context): Click context (passed by Click, not used here).
        param (click.Parameter | None): Click parameter (passed by Click, not used here).
        value (str | list[str] | tuple[str, ...]): The raw option value(s).

    Returns:
        dict[str, int]: Mapping of logger names to numeric logging levels.

    Raises:
        click.BadParameter: If an item is malformed (not NAME=LEVEL) or LEVEL is invalid.
    """

    items = _normalize_items(value)
    levels = dict(DEFAULT_LIB_LEVELS)
    for item in items:
        try:
            name, level_str = item.split("=", 1)
        except ValueError as e:
            raise click.BadParameter(f"Expected NAME=LEVEL, got {item!r}") from e
        if (lvl := getattr(logging, level_str.strip().upper(), None)) is None:
            raise click.BadParameter(f"Invalid log level: {level_str}")
        levels[name.strip()] = lvl
    return levels

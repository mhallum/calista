"""docs_cmds.py — import this module ONLY from mkdocs-click.

It disables Click/color styling so mkdocs-click renders plain text.
"""

from __future__ import annotations

from typing import IO, Any

import click

# pylint: disable=unused-argument,too-many-arguments,too-many-positional-arguments


# --- hard-disable styling before importing CLI objects -----------------


def _noop_style(
    text: str,
    fg: str | None = None,
    bg: str | None = None,
    bold: bool | None = None,
    dim: bool | None = None,
    underline: bool | None = None,
    overline: bool | None = None,
    italic: bool | None = None,
    blink: bool | None = None,
    reverse: bool | None = None,
    strikethrough: bool | None = None,
    reset: bool = True,
) -> str:
    # ignore all styling; return text unchanged
    return text


def _noop_secho(
    message: str | None = None,
    file: IO[str] | None = None,
    nl: bool = True,
    err: bool = False,
    color: bool | None = None,
    **styles: Any,
) -> None:
    # forward to echo but force no color; preserve file/nl/err
    click.echo(message, file=file, nl=nl, err=err, color=False)


# Turn off color globally for any Context created during help rendering.
click.core.Context.color = False
# Replace the styling helpers used by Click (and most wrappers).
click.style = _noop_style
click.secho = _noop_secho

# Neutralize click-extra styling too.
try:
    # pylint: disable=import-outside-toplevel
    import click_extra as _cx
except Exception:  # pylint: disable=broad-except
    _cx = None  # pylint: disable=invalid-name

if _cx is not None:
    _cx.style = _noop_style
    _cx.secho = _noop_secho


# --- now import and re-export real CLI objects -------------------------
# pylint: disable=wrong-import-position,import-outside-toplevel
from .db import db  # "calista db" subgroup  # noqa: E402
from .main import calista  # top-level group  # noqa: E402

__all__ = ["calista", "db"]

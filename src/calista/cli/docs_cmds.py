"""docs_cmds.py — import this module ONLY from mkdocs-click.

It disables Click/color styling so mkdocs-click renders plain text.
"""

from __future__ import annotations

import importlib
from collections.abc import Callable
from types import ModuleType
from typing import IO, Any, AnyStr, TypeAlias, cast

import click

# pylint: disable=unused-argument,too-many-arguments,too-many-positional-arguments


# --- hard-disable styling before importing CLI objects -----------------

Color: TypeAlias = int | tuple[int, int, int] | str


def _noop_style(
    text: Any,
    fg: Color | None = None,
    bg: Color | None = None,
    bold: bool | None = None,
    dim: bool | None = None,
    underline: bool | None = None,
    overline: bool | None = None,
    italic: bool | None = None,
    blink: bool | None = None,
    reverse: bool | None = None,
    strikethrough: bool | None = None,
    reset: bool = True,
) -> Any:
    return text


def _noop_secho(
    message: Any | None = None,
    file: IO[AnyStr] | None = None,
    nl: bool = True,
    err: bool = False,
    color: bool | None = None,
    **styles: Any,
) -> None:
    click.echo(message, file=file, nl=nl, err=err, color=False)


# Turn off color globally for any Context created during help rendering.
click.core.Context.color = False
# Replace the styling helpers used by Click (and most wrappers).
click.style = _noop_style
click.secho = _noop_secho

# Neutralize click-extra styling too.
_cx: ModuleType | None
try:
    _cx = importlib.import_module("click_extra")
except Exception:  # pylint: disable=broad-except
    _cx = None  # pylint: disable=invalid-name

if _cx is not None:
    style_attr = getattr(_cx, "style", None)
    if callable(style_attr):
        setattr(_cx, "style", cast(Callable[..., Any], _noop_style))

    secho_attr = getattr(_cx, "secho", None)
    if callable(secho_attr):
        setattr(_cx, "secho", cast(Callable[..., None], _noop_secho))

# --- now import and re-export real CLI objects -------------------------
# pylint: disable=wrong-import-position,import-outside-toplevel
from .db import db  # "calista db" subgroup  # noqa: E402
from .main import calista  # top-level group  # noqa: E402

__all__ = ["calista", "db"]

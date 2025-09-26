"""Unit tests for the CLI log level parser.

These tests exercise calista.entrypoints.cli.helpers.log_level_parser.parse_log_level,
covering default behavior, override semantics, input normalization (commas/spaces),
case-insensitivity, and error handling for malformed input.
"""

import logging
import types

import click
import pytest

from calista.entrypoints.cli.helpers.log_level_parser import parse_log_level


def make_ctx():
    """Create a minimal Click context stub.

    The parser callback expects a Click context argument but does not use it;
    a lightweight SimpleNamespace is sufficient for testing.
    """

    # ctx is not used by the callback, but Click passes one; a stub is fine.
    return types.SimpleNamespace()


def test_empty_uses_defaults():
    """When no levels are provided, return the default library logger levels."""
    ctx = make_ctx()
    assert parse_log_level(ctx, None, ()) == {
        "sqlalchemy": logging.WARNING,
        "alembic": logging.WARNING,
    }


def test_repeated_flags_override_order():
    """Later repeated CLI flags override earlier ones for the same logger."""
    ctx = make_ctx()
    value = ("sqlalchemy=INFO", "alembic=ERROR", "sqlalchemy=WARNING")
    out = parse_log_level(ctx, None, value)
    # later entries win
    assert out["sqlalchemy"] == logging.WARNING
    assert out["alembic"] == logging.ERROR


def test_envvar_string_with_commas_and_spaces():
    """Accept a plain string (e.g. from an env var) with commas and spaces."""
    ctx = make_ctx()
    value = "sqlalchemy=INFO,  urllib3=WARNING alembic=ERROR"
    out = parse_log_level(ctx, None, value)
    assert out["sqlalchemy"] == logging.INFO
    assert out["alembic"] == logging.ERROR
    assert out["urllib3"] == logging.WARNING


def test_case_insensitive_levels():
    """Level names should be parsed case-insensitively."""
    ctx = make_ctx()
    value = ("sqlalchemy=info", "alembic=WaRnInG")
    out = parse_log_level(ctx, None, value)
    assert out["sqlalchemy"] == logging.INFO
    assert out["alembic"] == logging.WARNING


def test_invalid_pair_raises():
    """Malformed NAME=LEVEL pairs should raise click.BadParameter."""
    ctx = make_ctx()
    with pytest.raises(click.BadParameter):
        parse_log_level(ctx, None, ("not-a-pair",))


def test_invalid_level_raises():
    """Unknown level names should raise click.BadParameter."""
    ctx = make_ctx()
    with pytest.raises(click.BadParameter):
        parse_log_level(ctx, None, ("sqlalchemy=LOUD",))


def test_parse_log_level_accepts_plain_string_env():
    """Ensure plain string inputs parse the same as repeated flags."""
    ctx = make_ctx()
    out = parse_log_level(ctx, None, "sqlalchemy=INFO, urllib3=WARNING alembic=ERROR")
    assert out["sqlalchemy"] == logging.INFO
    assert out["urllib3"] == logging.WARNING
    assert out["alembic"] == logging.ERROR

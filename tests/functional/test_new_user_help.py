"""Functional tests for CALISTA's CLI help/version output and OSC-8 links.

This suite verifies:
- The long-form `HELP` prose from `calista.cli.main` is actually rendered on
  `--help` (compared after stripping ANSI and normalizing whitespace).
- The help frame appears (Usage/Options/Commands + “See Also” links).
- Bare URLs are shown when OSC-8 is not supported (CliRunner default).
- OSC-8 BEL-terminated hyperlinks are emitted when supported (via monkeypatch).

Notes:
- Help text can be reflowed by Click; `_normalize()` collapses whitespace so the
  comparison is robust to wrapping.
- OSC-8 checks look for the exact BEL-delimited sequence around a bare URL.
"""

from __future__ import annotations

import importlib
import re
from textwrap import dedent
from typing import TYPE_CHECKING

import pytest
from click.testing import CliRunner

import calista
import calista.cli.main as main  # pylint: disable=consider-using-from-import # need it like this for patching

if TYPE_CHECKING:
    from click.testing import Result
    from pytest import MonkeyPatch

ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")  # strip SGR styling only


def _normalize(s: str) -> str:
    """Return `s` with leading/trailing space trimmed and internal whitespace collapsed."""
    return re.sub(r"\s+", " ", s.strip())


def _assert_help_displayed(result: Result):
    """Assert that help output contains the project HELP text and expected sections.

    - Strips ANSI before checking.
    - Normalizes whitespace to avoid failures from wrapping/reflow.
    - Also asserts presence of common help sections and the “See Also” labels.
    """
    # pylint: disable=magic-value-comparison
    text = ANSI_RE.sub("", result.output)
    expected_message = _normalize(dedent(main.HELP))
    assert expected_message
    assert expected_message in _normalize(text), "HELP text not rendered."
    assert "Usage:" in text
    assert "Options:" in text
    # assert "Commands:" in text # not yet, no subcommands
    # “See Also” links
    assert "Docs  :" in text
    assert "Issues:" in text


def _assert_links_displayed_non_osc8(result: Result):
    """Assert that plain (non-OSC-8) help/issue URLs are present in output."""
    expected_help_link = "https://mhallum.github.io/calista/"
    expected_issues_link = "https://github.com/mhallum/calista/issues"
    assert expected_help_link in result.output, "Help link missing."
    assert expected_issues_link in result.output, "Issues link missing."


def _assert_links_displayed_osc8(result: Result):
    """Assert that OSC-8 BEL-terminated hyperlinks wrap the bare URLs in output."""
    expected_help_link = (
        "\x1b]8;;https://mhallum.github.io/calista/\x07"
        "https://mhallum.github.io/calista/"
        "\x1b]8;;\x07"
    )
    assert expected_help_link in result.output, (
        "Expected bare URL wrapped in OSC-8 BEL sequence not found."
    )

    expected_issues_link = (
        "\x1b]8;;https://github.com/mhallum/calista/issues\x07"
        "https://github.com/mhallum/calista/issues"
        "\x1b]8;;\x07"
    )
    assert expected_issues_link in result.output, (
        "Expected bare URL wrapped in OSC-8 BEL sequence not found."
    )


# ============================================================================
#                           Tests
# ============================================================================


class TestNewCalistaUser:
    """A new user of CALISTA, unfamiliar with the tool, tries to get help."""

    @staticmethod
    @pytest.mark.parametrize("args", ([], ["-h"], ["--help"]))
    def test_calista_help_output(args: str):
        """Verify that help and links are shown with no args/-h/--help.

        Given CALISTA is available on the PATH
        When `calista` is invoked with no args, `-h`, or `--help`
        Then the long HELP prose and Docs/Issues links appear
        """

        # A new user looks for help by using the typical flags
        # i.e. `-h` or `--help`, or by running the command with no args.
        runner = CliRunner()
        result = runner.invoke(main.calista, args)

        # The user sees the help text
        # Which includes the long-form HELP message, usage, options, and commands
        _assert_help_displayed(result)

        # The user also sees links to the docs and issue tracker
        ## (CliRunner does not support OSC-8, so links should be plain text)
        _assert_links_displayed_non_osc8(result)

    @staticmethod
    def test_calista_version_output():
        """User runs --version and sees the version string."""
        # The user looks for the version by using the typical flag
        # i.e. `--version`
        runner = CliRunner()
        result = runner.invoke(main.calista, ["--version"])

        # The user sees the version text
        assert result.exit_code == 0
        assert calista.__version__ in result.output

    @staticmethod
    def test_osc8_links(monkeypatch: MonkeyPatch):
        """With OSC-8 support, user sees BEL-terminated hyperlink sequences."""
        # The user switches to a terminal that supports OSC-8 hyperlinks
        # and runs `calista --help` again.
        ## (We simulate this by monkeypatching the `supports_osc8` function.)
        monkeypatch.setattr(
            "calista.cli.helpers.hyperlinks.supports_osc8", lambda stream=None: True
        )

        importlib.reload(main)
        runner = CliRunner()
        result = runner.invoke(main.calista, ["--help"])

        _assert_links_displayed_osc8(result)

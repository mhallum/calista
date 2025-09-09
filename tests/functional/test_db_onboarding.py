"""Functional tests for ``calista db`` commands.

This module exercises the end-to-end behavior of Calista's database CLI:
``current``, ``heads``, ``history``, and ``upgrade``. It verifies both
the failure mode when ``CALISTA_DB_URL`` is missing and the happy path
against a scratch Postgres instance (via the ``pg_url_base`` fixture).

Key assertions:
  * When ``CALISTA_DB_URL`` is unset or empty, commands fail with exit code 1
    and emit :data:`calista.cli.db.MISSING_DB_URL_MSG`.
  * ``db heads`` includes the base Alembic revision for this project.
  * ``db current`` is empty prior to upgrade, verbose output shows extra context.
  * ``db history`` lists the lineage; ``-i`` annotates the current revision.
  * ``db upgrade`` prompts for confirmation, supports ``--sql`` dry-run, and
    applies migrations when confirmed.

These are functional tests (not unit tests): the CLI is invoked through
``click.testing.CliRunner`` so output, prompts, and exit codes are exercised
as a user would experience them.
"""

import re

import pytest
from click.testing import CliRunner

from calista.cli.db import MISSING_DB_URL_MSG
from calista.cli.main import calista as calista_cli

BASE_REVISION = "be411457bc58"
REV_RE = re.compile(r"\b[0-9a-f]{12,}\b")  # Alembic rev ids are 12+ hex chars


def _revs(text: str) -> set[str]:
    """Extract unique Alembic revision identifiers from ``text``.

    Alembic revision ids are hexadecimal strings (12+ chars). This helper
    centralizes the pattern and normalizes to a ``set`` for easy membership
    checks in assertions.
    """
    return set(REV_RE.findall(text))


@pytest.mark.parametrize(
    "cmd", [["db", "current"], ["db", "heads"], ["db", "history"], ["db", "upgrade"]]
)
def test_db_no_url(cmd):
    """db commands without CALISTA_DB_URL set should error"""
    runner = CliRunner(env={"CALISTA_DB_URL": ""})

    result = runner.invoke(calista_cli, cmd)
    assert result.exit_code == 1
    assert MISSING_DB_URL_MSG in result.output


@pytest.mark.slow
def test_new_user_initial_db_setup(pg_url_base: str):
    """Simulate a new user setting up CALISTA's database step by step.

    This test traces the path a first-time user might follow:

      1. Invoke a db command without ``CALISTA_DB_URL`` → expect a clear error.
      2. Set the environment variable → ``db heads`` shows the base revision.
      3. Check ``db current`` → empty at first; verbose mode adds details.
      4. Explore ``db history`` → shows lineage; ``-i`` highlights current rev.
      5. Run ``db upgrade``:
         * first without confirming (prompt declines → DB unchanged),
         * with ``--sql`` to preview statements,
         * finally confirming → migrations applied and ``current`` shows a rev.

    The intent is to cover the *typical onboarding flow*: encountering and
    resolving initial errors, verifying state at each step, and successfully
    applying the first upgrade.
    """

    # The user is new to Calista and has just installed it.
    # They have set up a postgres database, but have not yet set
    # the CALISTA_DB_URL environment variable.
    # They try to run a db command and get an error message.
    runner = CliRunner(env={"CALISTA_DB_URL": ""})
    result = runner.invoke(calista_cli, ["db", "heads"])
    assert result.exit_code == 1
    assert MISSING_DB_URL_MSG in result.output

    # They set the environment variable and try again.
    # This time, the command runs successfully.
    runner = CliRunner(env={"CALISTA_DB_URL": pg_url_base})
    result = runner.invoke(calista_cli, ["db", "heads"])
    assert result.exit_code == 0, result.output
    # They see the available head revisions, including the base revision.
    assert BASE_REVISION in result.output

    # They check the current revision, which should be empty.
    result = runner.invoke(calista_cli, ["db", "current"])
    assert result.exit_code == 0, result.output
    assert result.output == ""
    # If they include the verbose flag, they see more details.
    result = runner.invoke(calista_cli, ["db", "current", "-v"])
    assert result.exit_code == 0, result.output
    ## one of the extra fields displayed in verbose mode
    assert "Current revision(s) for postgresql+psycopg://" in result.output  # pylint: disable=magic-value-comparison

    # They check the migration history
    result = runner.invoke(calista_cli, ["db", "history"])
    assert result.exit_code == 0, result.output
    # They see the base revision in the history.
    assert BASE_REVISION in result.output
    # If they include the verbose flag, they see more details.
    result = runner.invoke(calista_cli, ["db", "history", "-v"])
    assert result.exit_code == 0, result.output
    assert (
        "Parent" in result.output  # pylint: disable=magic-value-comparison
    )  ## just one of the extra fields displayed in verbose mode
    # If they include the indicate-current flag, no revision is indicated
    result = runner.invoke(calista_cli, ["db", "history", "-i"])
    assert result.exit_code == 0, result.output
    assert "(current)" not in result.output  # pylint: disable=magic-value-comparison

    # The user decide to upgrade the database to the latest revision.
    result = runner.invoke(calista_cli, ["db", "upgrade"])
    # They see the confirmation prompt and decide not to proceed.
    assert result.exit_code == 1, result.output
    assert "Are you sure you want to proceed?" in result.output  # pylint: disable=magic-value-comparison
    # The database is still at the empty revision.
    result = runner.invoke(calista_cli, ["db", "current"])
    assert result.exit_code == 0, result.output
    assert result.output == ""

    # They decide to be extra safe and check the sql that will be run.
    result = runner.invoke(calista_cli, ["db", "upgrade", "--sql"])
    assert result.exit_code == 0, result.output
    # They see the SQL statements that will be executed.
    assert "CREATE TABLE" in result.output  # pylint: disable=magic-value-comparison
    # They double check that the database is still at the empty revision.
    result = runner.invoke(calista_cli, ["db", "current"])
    assert result.exit_code == 0, result.output
    assert result.output == ""

    # The user is now confident and decides to proceed with the upgrade.
    result = runner.invoke(calista_cli, ["db", "upgrade"], input="y\n")
    assert result.exit_code == 0, result.output
    # The database is now at the latest revision, which the user can check with the `current` command.
    result = runner.invoke(calista_cli, ["db", "current"])
    assert result.exit_code == 0, result.output
    assert REV_RE.search(result.output) is not None

    # Now they check the history with the indicate-current flag.
    result = runner.invoke(calista_cli, ["db", "history", "-i"])
    assert result.exit_code == 0, result.output
    # This time they see the current revision indicated.
    assert "(current)" in result.output  # pylint: disable=magic-value-comparison

    # The user has successfully set up their database and can now use Calista.

"""Functional tests for the ``calista db`` subcommands.

Scope
-----
End-to-end verification of CALISTA's database CLI via ``click.testing.CliRunner``.
Commands covered: ``current``, ``heads``, ``history``, ``status``, and ``upgrade``.

What these tests assert
-----------------------
* When ``CALISTA_DB_URL`` is unset/empty, commands that require a connection fail
  with exit code ``1`` and emit :data:`calista.cli.db.MISSING_DB_URL_MSG`.
* ``db heads`` includes the project's base Alembic revision.
* ``db current`` is empty before any upgrade; ``-v`` adds contextual details.
* ``db history`` lists the lineage; ``-i`` annotates the active ``(current)`` rev.
* ``db upgrade``:
  - prompts with a safety warning (backup guidance),
  - supports ``--sql`` dry-run output,
  - applies migrations when the user confirms.
* ``db status`` reports connectivity, backend, URL (masked), and schema state.

Notes
-----
These are functional (black-box) tests, not unit tests. They execute the CLI as a
user would, exercising prompts, output, and exit codes. Tests that talk to a
database are marked ``@pytest.mark.slow`` and rely on the ``pg_url_base`` fixture
to provide a scratch PostgreSQL instance.
"""

import re

import pytest
from click.testing import CliRunner

from calista.cli.db import (
    CANNOT_CONNECT_MSG,
    INVALID_URL_FORMAT_MSG,
    MISSING_DB_URL_MSG,
    UPGRADE_SCHEMA_INSTRUCTIONS,
    UPGRADE_SCHEMA_WARNING,
)
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
    "cmd",
    [["db", "current"], ["db", "history", "-i"], ["db", "upgrade"]],
)
def test_db_no_url(cmd):
    """db commands requiring db connection should error if CALISTA_DB_URL is not set"""
    runner = CliRunner(env={"CALISTA_DB_URL": ""})

    result = runner.invoke(calista_cli, cmd)
    assert result.exit_code == 1
    assert MISSING_DB_URL_MSG in result.output


@pytest.mark.slow
def test_new_user_initial_db_setup(pg_url_base: str):
    """Simulate a new user setting up CALISTA's database step by step.

    The intent is to cover the *typical onboarding flow*: encountering and
    resolving initial errors, verifying state at each step, and successfully
    applying the first upgrade.
    """

    # The user is new to Calista and has just installed it.
    # They have set up a postgres database, but have not yet set
    # the CALISTA_DB_URL environment variable.
    runner = CliRunner(env={"CALISTA_DB_URL": ""})

    # The user is familiar with Alembic and wants to check the
    # current state of the database and apply migrations.
    # They decide to use the `calista db` CLI commands to do this.

    # They user checks the available migrations heads.
    result = runner.invoke(calista_cli, ["db", "heads"])
    assert result.exit_code == 0, result.output

    # Forgetting that they haven't set CALISTA_DB_URL, the user runs
    # the `db current` command to check the current revision.
    result = runner.invoke(calista_cli, ["db", "current"])
    # They see an error message indicating that CALISTA_DB_URL is not set.
    assert result.exit_code == 1
    assert MISSING_DB_URL_MSG in result.output

    # They set the environment variable and try again.
    runner = CliRunner(env={"CALISTA_DB_URL": pg_url_base})
    result = runner.invoke(calista_cli, ["db", "current"])
    # This time, the command runs successfully.
    assert result.exit_code == 0
    # They see no current revision because the database is empty.
    assert result.output == ""
    # If they include the verbose flag, they see more details.
    result = runner.invoke(calista_cli, ["db", "current", "-v"])
    assert result.exit_code == 0
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
    # They see the confirmation prompt, including a warning about creating a backup,
    # and decide not to proceed.
    assert result.exit_code == 1, result.output
    assert UPGRADE_SCHEMA_WARNING in result.output
    assert "backup" in result.output.lower()  # pylint: disable=magic-value-comparison
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


@pytest.mark.slow
def test_new_user_initial_db_setup2(pg_url_base: str):
    """Simulate another new user setting up CALISTA's database step by step.

    The intent is to cover a less alembic heavy *typical onboarding flow*: confirming connectivity with
    ``calista db status``, addressing a couple of URL/connection issues, applying
    ``calista db upgrade``, and verifying the schema is up to date.
    """

    # Another user is now going through the same process.
    # This user has also set up a postgres database, and has
    # set the CALISTA_DB_URL environment variable.
    # However, they have unkowningly set it to a malformed value.
    invalid_url = "not a valid url"
    runner = CliRunner(env={"CALISTA_DB_URL": invalid_url})

    # They try to run `calista db upgrade` per the quickstart guide.
    result = runner.invoke(calista_cli, ["db", "upgrade"])
    # They see an error message indicating that the database URL is invalid.
    assert result.exit_code != 0, result.output
    assert INVALID_URL_FORMAT_MSG in result.output

    # The user realizes they set the environment variable incorrectly.
    # They check the value of CALISTA_DB_URL and see that it is indeed malformed.
    # They attempt to correct the value to point to their postgres database,
    # but make a typo and set it to another invalid value.
    # This one has the right format, but the wrong values.
    invalid_url2 = "postgresql+psycopg://user:pass@localhost:5432/wrongdb"
    runner = CliRunner(env={"CALISTA_DB_URL": invalid_url2})

    # The user tries to verify the database connection using `calista db status`.
    # (The docs say to try this if there are problems.)
    result = runner.invoke(calista_cli, ["db", "status"])
    # The status command indicates that it cannot connect to the database.
    assert "Cannot connect to database" in result.output  # pylint: disable=magic-value-comparison
    assert CANNOT_CONNECT_MSG in result.output

    # The user checks their environment variable again and realizes their mistake.
    # They correct the value to point to their postgres database.
    runner = CliRunner(env={"CALISTA_DB_URL": pg_url_base})

    # They run `calista db status` again to check the status of the database.
    result = runner.invoke(calista_cli, ["db", "status"])
    # This time, they see that the database is reachable, but is uninitialized.
    assert result.exit_code == 0, result.output
    assert "uninitialized" in result.output  # pylint: disable=magic-value-comparison
    # They also see that helpful information about the database (i.e. url, backend) is displayed,
    # confirming that CALISTA is connecting to the correct database.
    assert "Backend : postgresql" in result.output  # pylint: disable=magic-value-comparison
    assert "URL     : postgresql+psycopg://" in result.output  # pylint: disable=magic-value-comparison
    # They also see the instructions on how to initialize the database.
    assert UPGRADE_SCHEMA_INSTRUCTIONS in result.output

    # Following the instructions, the user runs `calista db upgrade`
    # and confirms the prompt to proceed.
    result = runner.invoke(calista_cli, ["db", "upgrade"], input="y\n")

    # They run `calista db status` again to check the status of the database.
    result = runner.invoke(calista_cli, ["db", "status"])
    # This time, they see that the database is up to date.
    assert result.exit_code == 0, result.output
    assert "Database reachable" in result.output  # pylint: disable=magic-value-comparison
    assert "Schema  :" in result.output  # pylint: disable=magic-value-comparison
    assert "up to date" in result.output  # pylint: disable=magic-value-comparison

    # The user has successfully set up their database and can now use Calista.

"""End-to-end CLI tests for calista's top-level `calista` command.

These tests exercise logging, verbosity flags, logger-level overrides, debug
formatting, and the in-memory flight-recorder by invoking the `log-demo`
command under various CLI flags and environment variables.
"""

import re
from pathlib import Path

import pytest

from calista.entrypoints.cli.main import calista

# pylint: disable=unused-argument


def assert_in_output(pattern: str, output: str) -> None:
    """Assert that a regex pattern is found in the output string.

    Args:
        pattern: Regular expression to search for.
        output: The text to search.
    """
    if not re.search(pattern, output, re.MULTILINE):
        raise AssertionError(f"Pattern '{pattern}' not found in output:\n{output}")


def assert_not_in_output(pattern: str, output: str) -> None:
    """Assert that a regex pattern is NOT found in the output string.

    Args:
        pattern: Regular expression that must not be present.
        output: The text to search.
    """
    if re.search(pattern, output, re.MULTILINE):
        raise AssertionError(f"Pattern '{pattern}' found in output:\n{output}")


def test_default_shows_warning(registered_log_demo, runner, fs):
    """Default invocation shows WARNING and above but not INFO."""
    result = runner.invoke(calista, ["log-demo"])
    assert result.exit_code == 0
    assert_in_output("WARNING", result.output)
    assert_not_in_output("INFO", result.output)


def test_verbose_shows_info(registered_log_demo, runner, fs):
    """Single -v should enable INFO-level console output (but not DEBUG)."""
    result = runner.invoke(calista, ["-v", "log-demo"])
    assert result.exit_code == 0
    assert_in_output("INFO", result.output)
    assert_not_in_output("DEBUG", result.output)


def test_vv_shows_debug(registered_log_demo, runner, fs):
    """-vv should enable DEBUG-level console output."""
    result = runner.invoke(calista, ["-vv", "log-demo"])
    assert result.exit_code == 0
    assert_in_output("DEBUG", result.output)


def test_quiet_suppresses_warning(registered_log_demo, runner, fs):
    """-q should lower verbosity so WARNING is suppressed and ERROR remains."""
    result = runner.invoke(calista, ["-q", "log-demo"])
    assert result.exit_code == 0
    assert_in_output("ERROR", result.output)
    assert_not_in_output("WARNING", result.output)


def test_logger_qq_suppresses_error(registered_log_demo, runner, fs):
    """-qq should lower verbosity to CRITICAL only."""
    result = runner.invoke(calista, ["-qq", "log-demo"])
    assert result.exit_code == 0
    assert_in_output("CRITICAL", result.output)
    assert_not_in_output("ERROR", result.output)


@pytest.mark.parametrize(
    "env, cli_args",
    [
        ({}, ["-vv", "-L", "some.thirdparty=INFO"]),
        ({"CALISTA_LOGGER_LEVEL": "some.thirdparty=INFO"}, ["-vv"]),
    ],
)
def test_logger_level_silences_debug(registered_log_demo, runner, fs, env, cli_args):
    """Logger-level overrides should silence third-party DEBUG while keeping INFO+."""
    result = runner.invoke(calista, cli_args + ["log-demo"], env=env)
    assert result.exit_code == 0
    # should NOT show DEBUG line
    assert_not_in_output(
        "This is a debug-level third-party test message.", result.output
    )
    # should still show INFO+
    assert_in_output("This is an info-level third-party test message.", result.output)


def test_debug_mode_shows_paths(registered_log_demo, runner, fs):
    """When --debug is set, log output includes file paths and line numbers."""
    result = runner.invoke(calista, ["--debug", "log-demo"])
    assert result.exit_code == 0
    # In debug mode, the log format includes file paths
    assert_in_output(r"conftest\.py:\d+\b", result.output)


def test_debug_mode_is_off_by_default(registered_log_demo, runner, fs):
    """By default, file paths should not be included in log output."""
    result = runner.invoke(calista, ["log-demo"])
    assert result.exit_code == 0
    # By default, file paths should NOT be in the output
    assert_not_in_output(r"conftest\.py:\d+\b", result.output)


def test_flight_recorder_flush_on_warning(registered_log_demo, runner, fs):
    """Flight recorder writes buffered DEBUG logs to disk when a WARNING occurs."""
    log_path = "flight_recorder.log"
    result = runner.invoke(
        calista,
        [
            "--log-path",
            log_path,
            "-L",
            "some.thirdparty=INFO",
            "log-demo",
        ],
    )
    assert result.exit_code == 0
    # flight recorder file should exist
    with open(log_path, "r", encoding="utf-8") as f:
        content = f.read()
    # should contain DEBUG lines from calista.demo logger
    assert_in_output("This is a debug-level test message.", content)
    # should NOT contain DEBUG lines from some.thirdparty logger
    assert_not_in_output("This is a debug-level third-party test message.", content)
    # should contain INFO+ lines from some.thirdparty logger
    assert_in_output("This is an info-level third-party test message.", content)
    # should contain WARNING+ lines from calista.demo logger
    assert_in_output("This is a warning-level test message.", content)
    assert_in_output("This is an error-level test message.", content)
    assert_in_output("This is a critical-level test message.", content)

    # should not contain final DEBUG line (after WARNING)
    assert_not_in_output("This is a final debug-level test message.", content)


@pytest.mark.parametrize(
    "env, cli_args",
    [({}, ["--force-flush"]), ({"CALISTA_FORCE_FLUSH_FLIGHT_RECORDER": "true"}, [])],
    ids=["cli-flag", "env-var"],
)
def test_flight_recorder_force_flush(registered_log_demo, runner, fs, env, cli_args):
    """When force-flush is enabled (CLI flag or env var), the final DEBUG buffer is written."""
    log_path = "flight_recorder.log"
    cli = ["--log-path", log_path] + cli_args + ["log-demo"]
    result = runner.invoke(calista, cli, env=env)
    assert result.exit_code == 0
    # flight recorder file should exist
    with open(log_path, "r", encoding="utf-8") as f:
        content = f.read()
    # should contain the last DEBUG lines from calista.demo logger
    assert_in_output("This is a final debug-level test message.", content)


@pytest.mark.parametrize(
    "env, cli_args",
    [({}, ["--no-flight-recorder"]), ({"CALISTA_FLIGHT_RECORDER": "0"}, [])],
    ids=["cli-flag", "env-var"],
)
def test_flight_recorder_can_be_disabled(
    registered_log_demo, runner, fs, env, cli_args
):
    """Disabling the flight recorder should prevent writing the log file."""
    log_path = "flight_recorder.log"
    cli = ["--log-path", log_path] + cli_args + ["log-demo"]
    result = runner.invoke(calista, cli, env=env)
    assert result.exit_code == 0
    # flight recorder file should not exist
    assert not Path(log_path).exists()


def test_flight_recorder_truncates_log(registered_log_demo, runner, fs):
    """Flight recorder log file should be truncated between runs (not appended)."""
    log_path = "flight_recorder.log"

    result1 = runner.invoke(calista, ["--log-path", log_path, "log-demo"])
    assert result1.exit_code == 0
    with open(log_path, "r", encoding="utf-8") as f:
        num_lines1 = sum(1 for _ in f)

    result2 = runner.invoke(calista, ["--log-path", log_path, "log-demo"])
    assert result2.exit_code == 0
    with open(log_path, "r", encoding="utf-8") as f:
        num_lines2 = sum(1 for _ in f)

    assert num_lines1 == num_lines2


def test_startup_logging(registered_log_demo, runner, fs):
    """Test that startup logging outputs the expected startup message."""
    log_path = "startup.log"
    result = runner.invoke(
        calista,
        ["--log-path", log_path, "--flight-recorder", "--force-flush", "log-demo"],
        env={"CALISTA_LOGGER_LEVEL": "some.thirdparty=INFO"},
    )
    assert result.exit_code == 0
    with open(log_path, "r", encoding="utf-8") as f:
        content = f.read()
    assert_in_output(r"CALISTA \d+\.\d+\.\d+", content)
    assert_in_output(r"console=WARNING", content)
    assert_in_output(r"flight-recorder=ON", content)
    assert_in_output(r"Python: \d+\.\d+\.\d+", content)
    assert_in_output(r"Platform: .+", content)
    assert_in_output(r"PID: \d+", content)
    assert_in_output(r"CWD: .+", content)
    assert_in_output(r"Alembic: \d+\.\d+\.\d+", content)
    assert_in_output(r"SQLAlchemy: \d+\.\d+\.\d+", content)
    assert_in_output(r"Handlers: .+", content)
    assert_in_output(
        r"Flight recorder: path=startup\.log, capacity=2000, flush_on_close=True",
        content,
    )
    assert_in_output(
        r"Per-logger overrides: {'sqlalchemy': 'WARNING', 'alembic': 'WARNING'}",
        content,
    )

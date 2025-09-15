"""Calista CLI entry point.

Defines the top-level ``calista`` command (via Click-Extra) and registers
subcommands exposed by the project.

Currently available groups
- ``calista db`` — forward-only database management (upgrade/current/heads/history).

Notes
- The CLI version is sourced from `calista.__version__` and displayed
  automatically by Click-Extra (``--version``).
- Additional command groups should be registered here via ``calista.add_command(...)``.

Examples
    $ calista --version
    $ calista db upgrade
"""

import click
import click_extra as clickx

from calista import __version__

from .db import db as db_group
from .helpers import hyperlink

HELP = """CALISTA command-line interface.

    CALISTA is a reproducible data-processing pipeline for astronomical data—covering
    photometry and spectroscopy. It turns raw observations into calibrated, measured
    results through deterministic steps, recording inputs, parameters, and versions so
    every outcome can be audited and regenerated.
    """


EPILOG = "\b\n" + "\n".join(
    [
        f"{click.style('See Also:', fg='blue', bold=True, underline=True)}",
        "  Docs  : " + hyperlink("https://mhallum.github.io/calista/"),
        "  Issues: " + hyperlink("https://github.com/mhallum/calista/issues"),
    ]
)


@clickx.extra_group(
    version=__version__,
    help=HELP,
    params=[
        clickx.VerbosityOption(),
        clickx.VerboseOption(),
        clickx.ColorOption(),
        clickx.TimerOption(),
        clickx.ExtraVersionOption(),
    ],
    epilog=EPILOG,
)
def calista():
    """CALISTA command-line interface."""


calista.add_command(db_group)

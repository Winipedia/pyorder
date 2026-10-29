"""Project-specific CLI commands.

Functions defined directly in this module are registered as top-level CLI
commands. Module-level `typer.Typer` instances are registered as command
groups, with each group's name derived from the kebab-case form of the
variable name.
"""

from pathlib import Path
from typing import Annotated

import typer


def check(
    files: Annotated[
        list[Path],
        typer.Argument(
            help="Files to check.",
        ),
    ],
    *,
    fix: Annotated[
        bool,
        typer.Option(
            help="Automatically fix issues.",
        ),
    ] = False,
) -> None:
    """Check order of Python source code.

    Args:
        files: Paths to Python source files.
        fix: Whether to apply ordering changes rather than only report them.

    Raises:
        typer.Exit: If any file was out of order, even when ``fix`` is true.
    """
    from pyorder.rig.cli.commands.check import check_order  # noqa: PLC0415

    check_order(files, fix=fix)

"""File-order checking for command-line use."""

from collections.abc import Iterable
from pathlib import Path

import typer

from pyorder.rig.order.module import Module


def check_order(files: Iterable[Path], *, fix: bool = False) -> None:
    """Check order of Python source code.

    Args:
        files: Paths to Python source files.
        fix: Whether to apply ordering changes rather than only report them.

    Raises:
        typer.Exit: If any file is not correctly ordered.
    """
    if all(tuple(Module.I.check_order(file, fix=fix) for file in files)):
        return

    raise typer.Exit(code=1)

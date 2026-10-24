"""Test module."""

from collections.abc import Callable, Iterable
from types import FunctionType

from pyorder.rig.cli.commands.check import check_order
from pyorder.rig.cli.subcommands import check


def test_check(
    command_works: Callable[[FunctionType], bool],
    command_calls_func: Callable[[FunctionType, FunctionType, Iterable[str]], bool],
) -> None:
    """Test function."""
    assert command_works(check)
    assert command_calls_func(check, check_order, [""])

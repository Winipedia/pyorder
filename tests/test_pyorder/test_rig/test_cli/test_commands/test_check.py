"""Check-command behavior against isolated source files."""

from pathlib import Path

import pytest
import typer

from pyorder.rig.cli.commands.check import check_order


@pytest.mark.parametrize("ordered", [False, True], ids=["unordered", "ordered"])
def test_check_order(tmp_path: Path, *, ordered: bool) -> None:
    """Report the original order, fix unordered code, and verify it then passes."""
    file = tmp_path / "example.py"
    code = """def zebra(): pass

def alpha(): pass
"""
    if ordered:
        code = """def alpha(): pass

def zebra(): pass
"""
    file.write_text(code, encoding="utf-8")

    if ordered:
        assert check_order(iter([file])) is None
    else:
        with pytest.raises(typer.Exit) as exc_info:
            check_order(iter([file]))
        assert exc_info.value.exit_code == 1

    assert file.read_text(encoding="utf-8") == code

    if ordered:
        assert check_order(iter([file]), fix=True) is None
    else:
        with pytest.raises(typer.Exit) as exc_info:
            check_order(iter([file]), fix=True)
        assert exc_info.value.exit_code == 1
    assert (
        file.read_text(encoding="utf-8")
        == """def alpha(): pass

def zebra(): pass
"""
    )
    assert check_order(iter([file])) is None

"""Test module."""

from pathlib import Path

import pytest
import typer

from pyorder.rig.cli.commands.check import check_order


def test_check_order(tmp_path: Path) -> None:
    """Test function."""
    files = Path("src").rglob("*.py")
    assert check_order(files) is None

    test_files = Path("tests").rglob("*.py")
    assert check_order(test_files) is None

    file = tmp_path / "unordered.py"
    code = """def zebra(): pass

def alpha(): pass
"""
    file.write_text(code, encoding="utf-8")

    with pytest.raises(typer.Exit) as exc_info:
        check_order([file])

    assert exc_info.value.exit_code == 1
    assert file.read_text(encoding="utf-8") == code

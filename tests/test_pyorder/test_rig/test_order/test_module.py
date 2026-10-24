"""Test module."""

import ast
from pathlib import Path
from uuid import UUID

import pytest

from pyorder.rig import order
from pyorder.rig.order.module import Module


class TestModule:
    """Test class."""

    def test_discovery_module(self) -> None:
        """Test method."""
        assert Module.I.discovery_module() is order

    def test_check_order(self, tmp_path: Path) -> None:
        """Test method."""
        file = tmp_path / "example.py"
        unordered = """def zebra(): pass

def alpha(): pass
"""
        ordered = """def alpha(): pass

def zebra(): pass
"""
        file.write_text(unordered, encoding="utf-8")

        assert Module.I.check_order(file) is False
        assert file.read_text(encoding="utf-8") == unordered
        assert Module.I.check_order(file, fix=True) is False
        assert file.read_text(encoding="utf-8") == ordered
        assert Module.I.check_order(file) is True

    def test_diff(self) -> None:
        """Test method."""
        assert Module.I.diff("old\n", "new\n") == (
            "--- \n+++ \n@@ -1 +1 @@\n-old\n+new"
        )

    def test_is_ordered(self) -> None:
        """Test method."""
        unordered = """def zebra(): pass

def alpha(): pass
"""
        ordered = """def alpha(): pass

def zebra(): pass
"""
        assert Module.I.is_ordered(ordered, ordered) is True
        assert Module.I.is_ordered(ordered, unordered) is False

    def test_fix_order(self, tmp_path: Path) -> None:
        """Test method."""
        file = tmp_path / "example.py"
        unordered = """def zebra(): pass

def alpha(): pass
"""
        ordered = """def alpha(): pass

def zebra(): pass
"""
        file.write_text(unordered, encoding="utf-8")

        Module.I.fix_order(file, ordered)

        assert file.read_text(encoding="utf-8") == ordered

    def test_order_code(self) -> None:
        """Test method."""
        code = """class Example: pass

def helper(): pass

def main(): helper()
"""
        expected = """def main(): helper()

def helper(): pass

class Example: pass
"""

        assert Module.I.order_code(code) == expected
        assert Module.I.order_code(expected) == expected

    def test_order_code_inheritance(self) -> None:
        """Keep a base before its child even when names sort the other way."""
        code = """class Alpha(Zebra): pass

class Zebra: pass
"""
        expected = """class Zebra: pass

class Alpha(Zebra): pass
"""

        assert Module.I.order_code(code) == expected
        assert Module.I.order_code(expected) == expected

    def test_order_code_inheritance_chain(self) -> None:
        """Order an inheritance chain from base to leaf."""
        code = """class Alpha(Middle): pass

class Middle(Zebra): pass

class Zebra: pass
"""
        expected = """class Zebra: pass

class Middle(Zebra): pass

class Alpha(Middle): pass
"""

        assert Module.I.order_code(code) == expected
        assert Module.I.order_code(expected) == expected

    def test_order_code_multiple_inheritance(self) -> None:
        """Put both bases first, using alphabetical order between them."""
        code = """class Alpha(Zebra, Other): pass

class Zebra: pass

class Other: pass
"""
        expected = """class Other: pass

class Zebra: pass

class Alpha(Zebra, Other): pass
"""

        assert Module.I.order_code(code) == expected
        assert Module.I.order_code(expected) == expected

    def test_reorder_definitions(self) -> None:
        """Test method."""
        code = """VALUE = 1

class Example: pass

def alpha(): pass
"""
        expected = """VALUE = 1

def alpha(): pass

class Example: pass
"""

        assert Module.I.reorder_definitions(code) == expected

    def test_reorder_code(self) -> None:
        """Test method."""
        code = """def first(): pass

def second(): pass
"""
        expected = """def second(): pass

def first(): pass
"""
        definitions = ast.parse(code).body

        assert (
            Module.I.reorder_code(code, iter(definitions), reversed(definitions))
            == expected
        )

    def test_source_placeholder(self) -> None:
        """Test method."""
        placeholder = Module.I.source_placeholder()

        assert UUID(placeholder).hex == placeholder

    def test_get_source_segment(self) -> None:
        """Test method."""
        code = """@decorate
def example():
    pass
"""
        definition = ast.parse(code).body[0]

        assert Module.I.get_source_segment(code, definition) == code.rstrip("\n")

        assignment_code = "VALUE = 1"
        assignment = ast.parse(assignment_code).body[0]

        assert (
            Module.I.get_source_segment(assignment_code, assignment) == assignment_code
        )

        with pytest.raises(LookupError, match="failed to get source segment"):
            Module.I.get_source_segment(assignment_code, ast.Name(id="VALUE"))

    def test_order_definitions(self) -> None:
        """Test method."""
        code = """class Example: pass
def _hidden(): pass
def zebra(): pass
def alpha(): pass
"""
        definitions = tuple(Module.I.definitions(ast.parse(code)))

        ordered = Module.I.order_definitions(definitions)

        assert [definition.name for definition in ordered] == [
            "alpha",
            "zebra",
            "_hidden",
            "Example",
        ]

    def test_definition_sort_key(self) -> None:
        """Test method."""
        code = """def main(): _helper()
def _helper(): pass
"""
        definitions = tuple(Module.I.definitions(ast.parse(code)))

        assert Module.I.definition_sort_key(definitions[1], definitions) == (
            0,
            1,
            1,
            "_helper",
        )

    def test_definition_sort_keys(self) -> None:
        """Test method."""
        assert Module.I.definition_sort_keys() == (
            Module.I.definition_kind_rank,
            Module.I.definition_reference_rank,
            Module.I.definition_visibility_rank,
            Module.I.definition_name_rank,
        )

    def test_definition_reference_rank(self) -> None:
        """Test method."""
        code = """def main(): helper()
def helper(): pass
"""
        definitions = tuple(Module.I.definitions(ast.parse(code)))

        assert Module.I.definition_reference_rank(definitions[0], definitions) == 0
        assert Module.I.definition_reference_rank(definitions[1], definitions) == 1

    def test_definition_reference_ranks(self) -> None:
        """Test method."""
        code = """def main(): helper()
def helper(): leaf()
def leaf(): pass
def independent(): pass
"""
        definitions = tuple(Module.I.definitions(ast.parse(code)))

        assert Module.I.definition_reference_ranks(definitions) == {
            "main": 0,
            "helper": 1,
            "leaf": 2,
            "independent": 0,
        }

    def test_definition_reference_ranks_inheritance(self) -> None:
        """Reverse bases while retaining user-first body references."""
        code = """def main(): return Child()
class Base: pass
class Child(Base[int]):
    def method(self): return Base()
class Factory:
    def create(self): return Item()
class Item: pass
class ExternalChild(external.Base): pass
"""
        definitions = tuple(Module.I.definitions(ast.parse(code)))

        assert Module.I.definition_reference_ranks(definitions) == {
            "main": 0,
            "Base": 0,
            "Child": 1,
            "Factory": 0,
            "Item": 1,
            "ExternalChild": 0,
        }

    def test_definition_dependencies(self) -> None:
        """Collect decorators and bases, but not class-body references."""
        code = """@first
@external.decorate(config)
class Child(Base[Item], Other):
    value = BodyReference()
"""
        definition = next(Module.I.definitions(ast.parse(code)))

        assert Module.I.definition_dependencies(definition) == {
            "first",
            "external",
            "config",
            "Base",
            "Item",
            "Other",
        }

    @pytest.mark.parametrize(
        "code",
        [
            """class Example:
    value = BodyReference()
""",
            """def example():
    return BodyReference()
""",
            """async def example():
    return BodyReference()
""",
        ],
    )
    def test_definition_dependencies_without_dependencies(self, code: str) -> None:
        """Body references are not dependencies for any definition kind."""
        definition = next(Module.I.definitions(ast.parse(code)))

        assert Module.I.definition_dependencies(definition) == set()

    @pytest.mark.parametrize("function_kind", ["def", "async def"])
    def test_order_code_function_decorator(self, function_kind: str) -> None:
        """Move a local decorator before a synchronous or async function."""
        code = f"""@decorate
{function_kind} example():
    pass

def decorate(value):
    return value
"""
        expected = f"""def decorate(value):
    return value

@decorate
{function_kind} example():
    pass
"""

        assert Module.I.order_code(code) == expected
        assert Module.I.order_code(expected) == expected

    def test_order_code_class_decorator(self) -> None:
        """Put a decorator and base before their dependent class."""
        code = """@decorate
class Alpha(Zebra): pass

class Zebra: pass

def decorate(value): return value
"""
        expected = """def decorate(value): return value

class Zebra: pass

@decorate
class Alpha(Zebra): pass
"""

        assert Module.I.order_code(code) == expected
        assert Module.I.order_code(expected) == expected

    def test_order_code_stacked_decorators(self) -> None:
        """Order decorator dependencies without changing decorator application."""
        code = """@first
@second(config)
def example(): pass

def second(value):
    return lambda function: function

def config(): pass

def first(value):
    return value
"""
        expected = """def config(): pass

def first(value):
    return value

def second(value):
    return lambda function: function

@first
@second(config)
def example(): pass
"""

        assert Module.I.order_code(code) == expected
        assert Module.I.order_code(expected) == expected

    def test_definition_references(self) -> None:
        """Test method."""
        code = """def main():
    callback = helper
    return Item(callback)
"""
        definition = next(Module.I.definitions(ast.parse(code)))

        assert Module.I.definition_references(definition) == {
            "helper",
            "Item",
            "callback",
        }

    def test_definition_name_rank(self) -> None:
        """Test method."""
        code = """def example(): pass
"""
        definition = next(Module.I.definitions(ast.parse(code)))

        assert Module.I.definition_name_rank(definition, (definition,)) == "example"

    def test_definition_kind_rank(self) -> None:
        """Test method."""
        code = """def sync(): pass
async def async_func(): pass
class Example: pass
"""
        definitions = tuple(Module.I.definitions(ast.parse(code)))

        assert [
            Module.I.definition_kind_rank(definition, definitions)
            for definition in definitions
        ] == [0, 0, 1]

    def test_definition_visibility_rank(self) -> None:
        """Test method."""
        code = """def public(): pass
def _private(): pass
def __hidden(): pass
"""
        definitions = tuple(Module.I.definitions(ast.parse(code)))

        assert [
            Module.I.definition_visibility_rank(definition, definitions)
            for definition in definitions
        ] == [0, 1, 2]

    def test_definitions(self) -> None:
        """Test method."""
        code = """VALUE = 1
def sync():
    def nested(): pass
async def async_func(): pass
class Example:
    def method(self): pass
"""
        tree = ast.parse(code)

        assert list(Module.I.definitions(tree)) == tree.body[1:]

    def test_read_text(self, tmp_path: Path) -> None:
        """Test method."""
        file = tmp_path / "example.py"
        file.write_bytes(b"# some comment\xc3\xa9\r\nVALUE = 1\r\n")

        assert (
            Module.I.read_text(file)
            == """# some comment\u00e9
VALUE = 1
"""
        )

    def test_write_text(self, tmp_path: Path) -> None:
        """Test method."""
        file = tmp_path / "example.py"
        file.write_bytes(b"old contents")
        code = """# some comment\u00e9
VALUE = 1
"""

        Module.I.write_text(file, code)

        assert file.read_bytes() == b"# some comment\xc3\xa9\nVALUE = 1\n"

    @pytest.mark.parametrize(
        "encoding",
        ["", "utf-8", "utf-8-sig", "iso-8859-1", "cp1252", "ascii"],
    )
    @pytest.mark.parametrize("newline", ["\n", "\r\n", "\r"])
    def test_file_info(
        self,
        tmp_path: Path,
        encoding: str,
        newline: str,
    ) -> None:
        """Test method."""
        file = tmp_path / "example.py"
        code = """def example():
    return "hello"
"""
        if encoding:
            code = f"# coding: {encoding}\n{code}"
        file.write_bytes(code.replace("\n", newline).encode(encoding or "utf-8"))

        assert Module.I.file_info(file) == (encoding or "utf-8", newline)

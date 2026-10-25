"""Mirror Module's API with focused policy, traversal and file-I/O tests."""

import ast
from pathlib import Path
from uuid import UUID

import pytest

from pyorder.rig import order
from pyorder.rig.order.module import Module


class TestModule:
    """Keep canonical test names aligned with Pyrig's source-method mirror."""

    def test_discovery_module(self) -> None:
        """Discover ordering policies in the order package."""
        assert Module.I.discovery_module() is order

    @pytest.mark.parametrize("fix", [False, True], ids=["check", "fix"])
    @pytest.mark.parametrize(
        "already_ordered",
        [False, True],
        ids=["unordered", "ordered"],
    )
    def test_check_order(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        *,
        fix: bool,
        already_ordered: bool,
    ) -> None:
        """Report the original status and write only when fixing unordered code."""
        file = tmp_path / "example.py"
        unordered = """def zebra(): pass

def alpha(): pass
"""
        ordered = """def alpha(): pass

def zebra(): pass
"""
        original = ordered if already_ordered else unordered
        file.write_text(original, encoding="utf-8")

        assert Module.I.check_order(file, fix=fix) is already_ordered
        assert file.read_text(encoding="utf-8") == (ordered if fix else original)
        output = capsys.readouterr().out
        if not already_ordered and not fix:
            assert (
                output
                == f"Incorrect order: {file}\n{Module.I.diff(original, ordered)}\n"
            )
        else:
            assert output == ""

    @pytest.mark.parametrize(
        ("unordered", "ordered", "expected"),
        [
            pytest.param(
                "old\n",
                "new\n",
                "--- \n+++ \n@@ -1 +1 @@\n-old\n+new",
                id="changed-line",
            ),
            pytest.param("same\n", "same\n", "", id="unchanged"),
            pytest.param("same\n", "same", "", id="split-lines-ignore-final-newline"),
        ],
    )
    def test_diff(self, unordered: str, ordered: str, expected: str) -> None:
        """Return the exact unified diff, without inventing newline-only changes."""
        assert Module.I.diff(unordered, ordered) == expected

    @pytest.mark.parametrize(
        ("unordered", "ordered", "expected"),
        [
            pytest.param("", "", True, id="empty"),
            pytest.param(
                "def alpha(): pass\n",
                "def alpha(): pass\n",
                True,
                id="equal",
            ),
            pytest.param("old", "new", False, id="different"),
            pytest.param("code\n", "code", False, id="trailing-newline"),
            pytest.param("code ", "code", False, id="trailing-space"),
        ],
    )
    def test_is_ordered(self, unordered: str, ordered: str, *, expected: bool) -> None:
        """Compare source exactly, including whitespace."""
        assert Module.I.is_ordered(unordered, ordered) is expected

    def test_fix_order(self, tmp_path: Path) -> None:
        """Write the supplied ordered source to the destination."""
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

    @pytest.mark.parametrize(
        ("code", "expected"),
        [
            pytest.param("", "", id="empty"),
            pytest.param("VALUE = 1\n", "VALUE = 1\n", id="no-definitions"),
            pytest.param(
                """class Example: pass

def helper(): Example()

def main(): helper()
""",
                """def main(): helper()

def helper(): Example()

class Example: pass
""",
                id="user-first-reference-chain",
            ),
            pytest.param(
                """class Alpha(Zebra): pass

class Zebra: pass
""",
                """class Zebra: pass

class Alpha(Zebra): pass
""",
                id="base-before-child",
            ),
            pytest.param(
                """class Alpha(Middle): pass

class Middle(Zebra): pass

class Zebra: pass
""",
                """class Zebra: pass

class Middle(Zebra): pass

class Alpha(Middle): pass
""",
                id="inheritance-chain",
            ),
            pytest.param(
                """class Alpha(Zebra, Other): pass

class Zebra: pass

class Other: pass
""",
                """class Other: pass

class Zebra: pass

class Alpha(Zebra, Other): pass
""",
                id="multiple-inheritance",
            ),
            pytest.param(
                """def zebra(): pass

def alpha(): pass
""",
                """def alpha(): pass

def zebra(): pass
""",
                id="alphabetical-independent-functions",
            ),
        ],
    )
    def test_order_code(self, code: str, expected: str) -> None:
        """Preserve exact source formatting and produce an idempotent ordering."""
        ordered = Module.I.order_code(code)

        assert ordered == expected
        assert Module.I.order_code(ordered) == ordered
        compile(ordered, "<ordered>", "exec")

    def test_reorder_definitions(self) -> None:
        """Reorder top-level definitions while preserving a leading assignment."""
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
        """Accept one-shot iterators and replace the selected definition slots."""
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
        """Produce a valid UUID hex placeholder."""
        placeholder = Module.I.source_placeholder()

        assert UUID(placeholder).hex == placeholder

    def test_get_source_segment(self) -> None:
        """Include decorators and support ordinary statement source segments."""
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

    def test_get_source_segment_missing_location(self) -> None:
        """Reject nodes without source locations explicitly."""
        with pytest.raises(LookupError, match="failed to get source segment"):
            Module.I.get_source_segment("VALUE = 1", ast.Name(id="VALUE"))

    def test_order_definitions(self) -> None:
        """Break independent ties by kind, visibility and alphabetical name."""
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
        """Place reference rank before kind, visibility and name in the tuple."""
        code = """def main(): _helper()
def _helper(): pass
"""
        definitions = tuple(Module.I.definitions(ast.parse(code)))

        assert Module.I.definition_sort_key(definitions[1], definitions) == (
            1,
            0,
            1,
            "_helper",
        )

    def test_definition_sort_keys(self) -> None:
        """Expose policy callables in descending priority order."""
        assert Module.I.definition_sort_keys() == (
            Module.I.definition_reference_rank,
            Module.I.definition_kind_rank,
            Module.I.definition_visibility_rank,
            Module.I.definition_name_rank,
        )

    def test_definition_reference_rank(self) -> None:
        """Look up each definition's rank in the shared reference graph."""
        code = """def main(): helper()
def helper(): pass
"""
        definitions = tuple(Module.I.definitions(ast.parse(code)))

        assert Module.I.definition_reference_rank(definitions[0], definitions) == 0
        assert Module.I.definition_reference_rank(definitions[1], definitions) == 1

    @pytest.mark.parametrize(
        ("code", "expected"),
        [
            pytest.param("", {}, id="empty"),
            pytest.param(
                """def main(): helper()
def helper(): leaf()
def leaf(): pass
def independent(): pass
""",
                {"main": 0, "helper": 1, "leaf": 2, "independent": 0},
                id="reference-layers",
            ),
            pytest.param(
                """def first(): second()
def second(): first()
""",
                {"first": 0, "second": 0},
                id="mutual-cycle",
            ),
            pytest.param(
                "def recursive(): recursive()\n",
                {"recursive": 0},
                id="self-reference",
            ),
            pytest.param(
                "def example(): external()\n",
                {"example": 0},
                id="external-reference",
            ),
            pytest.param(
                """def main(): helper()
def helper(): pass
def helper(): pass
""",
                {"main": 0, "helper": 1},
                id="duplicate-name",
            ),
        ],
    )
    def test_definition_reference_ranks(
        self,
        code: str,
        expected: dict[str, int],
    ) -> None:
        """Rank reference layers deterministically, including cycles and duplicates."""
        definitions = tuple(Module.I.definitions(ast.parse(code)))

        assert Module.I.definition_reference_ranks(definitions) == expected

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

    @pytest.mark.parametrize(
        ("code", "expected"),
        [
            pytest.param(
                """@external.decorate(config)
class Example: pass""",
                {"external", "config"},
                id="class-decorator",
            ),
            pytest.param(
                """@decorate
def example(): pass""",
                {"decorate"},
                id="function-decorator",
            ),
            pytest.param(
                "class Example(Base[Item], Other): pass",
                {"Base", "Item", "Other"},
                id="base-expressions",
            ),
            pytest.param(
                "class Example(metaclass=Meta, option=Config): pass",
                {"Meta", "Config"},
                id="class-keywords",
            ),
            pytest.param(
                """class Example:
    factory = helper""",
                {"helper"},
                id="class-attribute-reference",
            ),
            pytest.param(
                """class Example:
    value = Factory()""",
                {"Factory"},
                id="class-attribute-call",
            ),
            pytest.param(
                """class Example:
    @decorate(config)
    async def method(self): deferred()""",
                {"decorate", "config"},
                id="method-decorator",
            ),
            pytest.param(
                """class Example:
    class Inner(Base):
        value = Factory()""",
                {"Base", "Factory"},
                id="nested-class",
            ),
            pytest.param(
                "def example(value=Factory(), /, *, required, option=Option()): pass",
                {"Factory", "Option"},
                id="parameter-defaults",
            ),
            pytest.param(
                "async def example(value=Factory()): deferred()",
                {"Factory"},
                id="async-default",
            ),
            pytest.param(
                "def example(): deferred()",
                set(),
                id="function-body-excluded",
            ),
            pytest.param(
                "async def example(): deferred()",
                set(),
                id="async-body-excluded",
            ),
            pytest.param(
                "def example(value: Input) -> Output: pass",
                set(),
                id="function-annotations-excluded",
            ),
            pytest.param(
                """class Example:
    value: Annotation = Factory()""",
                {"Factory"},
                id="annotated-value",
            ),
            pytest.param(
                """class Example:
    callback = lambda value=Default(): deferred()""",
                {"Default"},
                id="lambda-default",
            ),
            pytest.param(
                """class Example:
    values = (deferred(x) for x in source() if check(x))""",
                {"source"},
                id="generator-outer-iterable",
            ),
            pytest.param(
                """class Example:
    with context(): value = Factory()""",
                {"context", "Factory"},
                id="context-manager",
            ),
            pytest.param(
                """class Example:
    if False: value = Factory()""",
                {"Factory"},
                id="branches-inspected-conservatively",
            ),
        ],
    )
    def test_definition_dependencies(
        self,
        code: str,
        expected: set[str],
    ) -> None:
        """Distinguish direct eager references from deferred bodies and annotations."""
        definition = next(Module.I.definitions(ast.parse(code)))
        original = ast.dump(definition, include_attributes=True)

        assert Module.I.definition_dependencies(definition) == expected
        assert Module.I.definition_dependencies(definition) == expected
        assert ast.dump(definition, include_attributes=True) == original

    def test_order_code_class_body_dependencies(self) -> None:
        """Keep eager providers before a class and deferred helpers after it."""
        code = """class Alpha:
    value = zebra()
    def method(self): return helper()

def helper(): return 2

def zebra(): return 1
"""
        expected = """def zebra(): return 1

class Alpha:
    value = zebra()
    def method(self): return helper()

def helper(): return 2
"""

        ordered = Module.I.order_code(code)
        assert ordered == expected
        assert Module.I.order_code(ordered) == ordered
        namespace: dict[str, object] = {}
        exec(compile(ordered, "<ordered>", "exec"), namespace)  # noqa: S102
        assert vars(namespace["Alpha"])["value"] == 1

    @pytest.mark.parametrize(
        ("statement", "expected"),
        [
            pytest.param(
                "for item in source(): pass",
                {"source"},
                id="for-iterable",
            ),
            pytest.param(
                "while condition(): break",
                {"condition"},
                id="while-condition",
            ),
            pytest.param(
                """try: run()
    except Error: recover()""",
                {"run", "Error", "recover"},
                id="exception-handler",
            ),
            pytest.param(
                """try: run()
    finally: cleanup()""",
                {"run", "cleanup"},
                id="finally",
            ),
            pytest.param(
                """match subject:
        case Pattern() if guard(): pass""",
                {"subject", "Pattern", "guard"},
                id="match-pattern-and-guard",
            ),
            pytest.param(
                "assert check(), message()",
                {"check", "message"},
                id="assert",
            ),
            pytest.param(
                "value = [Factory() for _ in source() if predicate()]",
                {"Factory", "source", "predicate"},
                id="list-comprehension",
            ),
            pytest.param(
                "value = {Factory() for _ in source()}",
                {"Factory", "source"},
                id="set-comprehension",
            ),
            pytest.param(
                "value = {key(): Factory() for _ in source()}",
                {"key", "Factory", "source"},
                id="dict-comprehension",
            ),
            pytest.param(
                "value = (transform(x, y) for x in source() for y in later(x))",
                {"source"},
                id="generator-later-clauses-deferred",
            ),
            pytest.param(
                "callback = lambda *, value=Factory(): Deferred(value)",
                {"Factory"},
                id="lambda-keyword-default",
            ),
            pytest.param(
                "callback = lambda callback=lambda: Deferred(): callback()",
                set(),
                id="nested-lambda-deferred",
            ),
            pytest.param(
                "def method(self, value=Factory()): return Deferred()",
                {"Factory"},
                id="sync-method-default",
            ),
            pytest.param(
                "async def method(self): return Deferred()",
                set(),
                id="async-method-body-deferred",
            ),
            pytest.param(
                "value: Annotation",
                set(),
                id="annotation-only",
            ),
            pytest.param(
                "type Alias = Deferred",
                set(),
                id="lazy-type-alias",
            ),
            pytest.param(
                "Counter += increment()",
                {"Counter", "increment"},
                id="augmented-name-read",
            ),
            pytest.param(
                "target.value += increment()",
                {"target", "increment"},
                id="augmented-attribute-read",
            ),
            pytest.param(
                "target[index()] += increment()",
                {"target", "index", "increment"},
                id="augmented-subscript-read",
            ),
            pytest.param(
                """helper = 1
    value = helper""",
                {"helper"},
                id="class-local-binding-not-resolved",
            ),
            pytest.param(
                "values = [Item for Item in range(3)]",
                {"Item", "range"},
                id="comprehension-local-binding-not-resolved",
            ),
        ],
    )
    def test_definition_dependencies_class_statement(
        self,
        statement: str,
        expected: set[str],
    ) -> None:
        """Check one class-body syntax case independently."""
        definition = ast.parse(f"""class Example:
    {statement}
""").body[0]
        assert isinstance(definition, ast.ClassDef)

        assert Module.I.definition_dependencies(definition) == expected

    @pytest.mark.parametrize(
        ("code", "names"),
        [
            pytest.param(
                """class Alpha:
    def method(self, value=Zebra()): return value

class Zebra: pass
""",
                ["Zebra", "Alpha"],
                id="method-default",
            ),
            pytest.param(
                """class Alpha:
    @zebra
    def method(self): pass

def zebra(function): return function
""",
                ["zebra", "Alpha"],
                id="method-decorator",
            ),
            pytest.param(
                """class Alpha:
    class Inner(Zebra): pass

class Zebra: pass
""",
                ["Zebra", "Alpha"],
                id="nested-class-base",
            ),
            pytest.param(
                """class Alpha:
    value = zebra()
    def method(self): return zebra()

def zebra(): return 1
""",
                ["zebra", "Alpha"],
                id="eager-use-wins-over-deferred-use",
            ),
        ],
    )
    def test_order_code_class_dependency_edge(
        self,
        code: str,
        names: list[str],
    ) -> None:
        """Verify each dependency through ranking, rewriting and execution."""
        ordered = Module.I.order_code(code)

        assert [
            definition.name for definition in Module.I.definitions(ast.parse(ordered))
        ] == names
        assert Module.I.order_code(ordered) == ordered
        namespace: dict[str, object] = {}
        exec(compile(ordered, "<ordered>", "exec"), namespace)  # noqa: S102
        assert set(names) <= namespace.keys()

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

    def test_order_code_class_metaclass(self) -> None:
        """Put a metaclass before its dependent class."""
        code = """class Child(metaclass=Meta): pass

class Meta(type): pass
"""
        expected = """class Meta(type): pass

class Child(metaclass=Meta): pass
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

    @pytest.mark.parametrize(
        ("code", "expected"),
        [
            pytest.param(
                """def main():
    callback = helper
    return Item(callback)""",
                {"helper", "Item", "callback"},
                id="body-loads-not-stores",
            ),
            pytest.param(
                "def example(value: Input) -> Output: pass",
                {"Input", "Output"},
                id="annotation-names",
            ),
            pytest.param(
                'def example(value: "Input") -> "Output": pass',
                set(),
                id="string-annotations",
            ),
            pytest.param(
                """class Example:
    def method(self): return helper()""",
                {"helper"},
                id="method-body",
            ),
            pytest.param(
                "def example(): external.helper()",
                {"external"},
                id="attribute-root-only",
            ),
        ],
    )
    def test_definition_references(self, code: str, expected: set[str]) -> None:
        """Collect syntactic loads, including deferred bodies and annotation names."""
        definition = next(Module.I.definitions(ast.parse(code)))

        assert Module.I.definition_references(definition) == expected

    def test_definition_name_rank(self) -> None:
        """Use the definition's unchanged name."""
        code = """def example(): pass
"""
        definition = next(Module.I.definitions(ast.parse(code)))

        assert Module.I.definition_name_rank(definition, (definition,)) == "example"

    def test_definition_kind_rank(self) -> None:
        """Give synchronous and asynchronous functions equal priority over classes."""
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
        """Count leading underscores, including dunder names."""
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
        """Yield direct module definitions, not assignments or nested definitions."""
        code = """VALUE = 1
def sync():
    def nested(): pass
async def async_func(): pass
class Example:
    def method(self): pass
"""
        tree = ast.parse(code)

        assert list(Module.I.definitions(tree)) == tree.body[1:]

    @pytest.mark.parametrize("newline", ["\n", "\r\n"], ids=["lf", "crlf"])
    @pytest.mark.parametrize("encoding", ["utf-8", "utf-8-sig", "cp1252"])
    def test_read_text(self, tmp_path: Path, encoding: str, newline: str) -> None:
        """Decode declared encodings and normalize line endings."""
        file = tmp_path / "example.py"
        code = f"""# coding: {encoding}
# some-comment\u00e9
VALUE = 1
"""
        file.write_bytes(code.replace("\n", newline).encode(encoding))

        assert Module.I.read_text(file) == code

    @pytest.mark.parametrize(
        "contents",
        [
            pytest.param(b"# coding: unknown-encoding\n", id="unknown-encoding"),
            pytest.param(b"# invalid utf8: \xff\n", id="undecodable-source"),
            pytest.param(
                b"\xef\xbb\xbf# coding: cp1252\n",
                id="bom-encoding-conflict",
            ),
        ],
    )
    def test_read_text_invalid_encoding(self, tmp_path: Path, contents: bytes) -> None:
        """Propagate tokenizer encoding errors rather than silently changing source."""
        file = tmp_path / "example.py"
        file.write_bytes(contents)

        with pytest.raises(SyntaxError):
            Module.I.read_text(file)

    @pytest.mark.parametrize("newline", ["\n", "\r\n", "\r"], ids=["lf", "crlf", "cr"])
    @pytest.mark.parametrize("encoding", ["utf-8", "utf-8-sig", "cp1252"])
    def test_write_text(self, tmp_path: Path, encoding: str, newline: str) -> None:
        """Preserve the existing encoding, BOM and newline convention."""
        file = tmp_path / "example.py"
        original = f"""# coding: {encoding}
old = 1
"""
        file.write_bytes(original.replace("\n", newline).encode(encoding))
        code = f"""# coding: {encoding}
# some-comment\u00e9
VALUE = 1
"""

        Module.I.write_text(file, code)

        assert file.read_bytes() == code.replace("\n", newline).encode(encoding)

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
        """Detect encoding declarations, optional BOMs and newline conventions."""
        file = tmp_path / "example.py"
        code = """def example():
    return "hello"
"""
        if encoding:
            code = f"# coding: {encoding}\n{code}"
        file.write_bytes(code.replace("\n", newline).encode(encoding or "utf-8"))

        assert Module.I.file_info(file) == (encoding or "utf-8", newline)

    @pytest.mark.parametrize(
        ("code", "expected"),
        [
            pytest.param(
                """@decorate
class Example(Base, metaclass=Meta):
    value = factory()""",
                ["decorate", "Base", "Meta", "value = factory()"],
                id="class-header-and-body",
            ),
            pytest.param(
                """@decorate
def example(value: Input = default, *, required, option=other) -> Output:
    deferred()""",
                ["decorate", "default", "other"],
                id="function-decorators-and-defaults",
            ),
            pytest.param(
                """@decorate
async def example(value=default):
    deferred()""",
                ["decorate", "default"],
                id="async-function",
            ),
            pytest.param(
                "def example(): deferred()",
                [],
                id="function-body-excluded",
            ),
            pytest.param(
                "lambda value=default, *, required, option=other: deferred(value)",
                ["default", "other"],
                id="lambda-defaults",
            ),
            pytest.param(
                "lambda: deferred()",
                [],
                id="lambda-body-excluded",
            ),
            pytest.param(
                "(transform(x, y) for x in source() if check(x) for y in later(x))",
                ["source()"],
                id="generator-outermost-iterable",
            ),
            pytest.param(
                "value: Annotation = factory()",
                ["value", "factory()"],
                id="annotated-assignment-value",
            ),
            pytest.param(
                "value: Annotation",
                ["value"],
                id="annotation-excluded",
            ),
            pytest.param(
                "type Alias = Deferred",
                [],
                id="type-alias-excluded",
            ),
            pytest.param(
                "value = factory()",
                ["value", "factory()"],
                id="ordinary-node-children",
            ),
        ],
    )
    def test_definition_dependency_children(
        self,
        code: str,
        expected: list[str],
    ) -> None:
        """Select immediate children without annotations or deferred bodies."""
        node = ast.parse(code).body[0]
        if isinstance(node, ast.Expr):
            node = node.value
        original = ast.dump(node, include_attributes=True)

        children = list(Module.I.definition_dependency_children(node))

        assert [ast.get_source_segment(code, child) for child in children] == expected
        assert ast.dump(node, include_attributes=True) == original

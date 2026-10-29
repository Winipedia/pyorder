"""Mirror Module's API with focused policy, traversal and file-I/O tests."""

import ast
from collections.abc import KeysView
from pathlib import Path
from uuid import UUID

import pytest

from pyorder.rig import order
from pyorder.rig.order.module import Module


class TestModule:
    """Keep canonical test names aligned with Pyrig's source-method mirror."""

    @pytest.mark.parametrize(
        ("code", "expected"),
        [
            pytest.param(
                """@abstractmethod
def run(self): ...""",
                0,
                id="name",
            ),
            pytest.param(
                """@abc.abstractmethod
def run(self): ...""",
                0,
                id="attribute",
            ),
            pytest.param(
                """@property
@abstractmethod
def run(self): ...""",
                0,
                id="stacked",
            ),
            pytest.param(
                """@abstractmethod
async def run(self): ...""",
                0,
                id="async",
            ),
            pytest.param("def run(self): pass", 1, id="undecorated"),
            pytest.param(
                """@property
def run(self): pass""",
                1,
                id="other-decorator",
            ),
        ],
    )
    def test_abstract_method_rank(self, code: str, expected: int) -> None:
        """Rank definitions decorated with abstractmethod before all others."""
        definition = next(Module.I.definitions(ast.parse(code)))

        assert Module.I.abstract_method_rank(definition, ()) == expected

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

    def test_classes(self) -> None:
        """Yield direct classes without descending into functions or methods."""
        code = """
class Outer:
    class Nested:
        pass

    def method(self):
        class Local:
            pass

class Other: pass
"""
        module = ast.parse(code)
        outer = module.body[0]
        assert isinstance(outer, ast.ClassDef)

        assert [node.name for node in Module.I.classes(module)] == ["Outer", "Other"]
        assert [node.name for node in Module.I.classes(outer)] == ["Nested"]

    @pytest.mark.parametrize(
        ("code", "expected"),
        [
            pytest.param(
                """@classmethod
def build(cls): pass""",
                0,
                id="classmethod",
            ),
            pytest.param("def build(self): pass", 1, id="undecorated"),
            pytest.param(
                """@staticmethod
def build(): pass""",
                1,
                id="staticmethod",
            ),
        ],
    )
    def test_classmethod_rank(self, code: str, expected: int) -> None:
        """Rank definitions decorated with classmethod before all others."""
        definition = next(Module.I.definitions(ast.parse(code)))

        assert Module.I.classmethod_rank(definition, ()) == expected

    def test_cls_definition_dependencies(self) -> None:
        """Return the shared definition-time dependencies."""
        code = """@decorate
def method(self, value=default): deferred()
"""
        definition = next(Module.I.definitions(ast.parse(code)))

        assert Module.I.cls_definition_dependencies(definition) == {
            "decorate",
            "default",
        }

    def test_cls_definition_ranks(self) -> None:
        """Expose class-body policy callables in descending priority order."""
        assert Module.I.cls_definition_ranks() == (
            Module.I.reverse_definition_kind_rank,
            Module.I.constructor_method_rank,
            Module.I.abstract_method_rank,
            Module.I.override_method_rank,
            Module.I.magic_method_rank,
            Module.I.classmethod_rank,
            Module.I.cls_definition_reference_rank,
            Module.I.definition_visibility_rank,
            Module.I.definition_name_rank,
        )

    def test_cls_definition_reference_rank(self) -> None:
        """Use method-reference collectors to rank class-body definitions."""
        code = """class Example:
    def main(self): self.helper()
    def helper(self): pass
"""
        cls = next(Module.I.classes(ast.parse(code)))
        definitions = tuple(Module.I.definitions(cls))

        assert [
            Module.I.cls_definition_reference_rank(definition, definitions)
            for definition in definitions
        ] == [0, 1]

    @pytest.mark.parametrize(
        ("code", "expected"),
        [
            pytest.param(
                "def method(self): self.helper()",
                {"helper"},
                id="call",
            ),
            pytest.param(
                "def method(self): return self.helper",
                {"helper"},
                id="uncalled-reference",
            ),
            pytest.param(
                "def method(self): return self.helper.__name__",
                {"helper"},
                id="attribute-of-reference",
            ),
            pytest.param(
                "def method(self): self.service.helper()",
                {"service"},
                id="direct-attribute-only",
            ),
            pytest.param(
                "def method(this): this.helper()",
                {"helper"},
                id="renamed-receiver",
            ),
            pytest.param(
                """@classmethod
def method(cls): cls.helper()""",
                {"helper"},
                id="cls-receiver",
            ),
            pytest.param(
                """@classmethod
def method(cls): cls().helper()""",
                {"helper"},
                id="constructed-cls-receiver",
            ),
            pytest.param(
                """@classmethod
def method(cls):
    instance = cls()
    instance.helper()""",
                {"helper"},
                id="assigned-constructed-cls-receiver",
            ),
            pytest.param(
                "def method(self, /): self.helper()",
                {"helper"},
                id="positional-only-receiver",
            ),
            pytest.param(
                "async def method(self): await self.helper()",
                {"helper"},
                id="async-method",
            ),
            pytest.param(
                """def method(self):
    def inner(): return self.helper
    return inner""",
                {"helper"},
                id="nested-function-closure",
            ),
            pytest.param(
                "def method(self): return lambda: self.helper",
                {"helper"},
                id="lambda-closure",
            ),
            pytest.param(
                "def method(self): return [self.helper(x) for x in ()]",
                {"helper"},
                id="comprehension",
            ),
            pytest.param(
                "def method(self): return super().helper()",
                set(),
                id="super-call",
            ),
            pytest.param(
                "def method(self): return type(self).helper()",
                set(),
                id="type-of-receiver",
            ),
            pytest.param(
                "def method(self): return getattr(self, 'helper')",
                set(),
                id="getattr",
            ),
            pytest.param(
                "def method(*args): args.helper()",
                set(),
                id="var-positional-only",
            ),
            pytest.param(
                "def method(self, other): other.helper()",
                set(),
                id="other-object",
            ),
            pytest.param(
                "def method(self): self.helper = None",
                set(),
                id="attribute-store",
            ),
            pytest.param(
                "def method(self): del self.helper",
                set(),
                id="attribute-delete",
            ),
            pytest.param(
                "def method(): self.helper()",
                set(),
                id="no-positional-parameter",
            ),
            pytest.param(
                "def method(*, self): self.helper()",
                set(),
                id="keyword-only-parameter",
            ),
            pytest.param(
                """class Inner:
    def method(self): self.helper()""",
                set(),
                id="nested-class",
            ),
        ],
    )
    def test_cls_definition_references(self, code: str, expected: set[str]) -> None:
        """Collect attributes read directly through the receiver parameter."""
        definition = next(Module.I.definitions(ast.parse(code)))

        assert set(Module.I.cls_definition_references(definition)) == expected

    def test_cls_definition_references_order(self) -> None:
        """Preserve first-seen receiver references and remove duplicates."""
        definition = ast.parse(
            "def main(self): self.second(); self.first(); self.second()",
        ).body[0]
        assert isinstance(definition, ast.FunctionDef)

        assert tuple(Module.I.cls_definition_references(definition)) == (
            "second",
            "first",
        )

    @pytest.mark.parametrize(
        ("name", "expected"),
        [
            ("__init_subclass__", 0),
            ("__new__", 1),
            ("__init__", 2),
            ("__post_init__", 3),
            ("__repr__", 3),
            ("run", 3),
        ],
    )
    def test_constructor_method_rank(self, name: str, expected: int) -> None:
        """Rank object's constructor hooks in call order, then everything else."""
        definition = next(Module.I.definitions(ast.parse(f"def {name}(self): pass")))

        assert Module.I.constructor_method_rank(definition, ()) == expected

    @pytest.mark.parametrize(
        ("code", "expected"),
        [
            pytest.param("def run(): pass", set(), id="undecorated"),
            pytest.param(
                """@first
@abc.second
def run(): pass""",
                {"first", "second"},
                id="name-and-attribute",
            ),
            pytest.param(
                """@factory()
@items[0]
def run(): pass""",
                set(),
                id="call-and-subscript-ignored",
            ),
            pytest.param(
                """@decorate
class Example: pass""",
                {"decorate"},
                id="class",
            ),
        ],
    )
    def test_decorator_names(self, code: str, expected: set[str]) -> None:
        """Return the final names of plain name and attribute decorators."""
        definition = next(Module.I.definitions(ast.parse(code)))

        assert set(Module.I.decorator_names(definition)) == expected

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
        assert ast.dump(definition, include_attributes=True) == original

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
    def test_definition_dependencies_cls_statement(
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

    def test_definition_name_rank(self) -> None:
        """Use the definition's unchanged name."""
        code = """def example(): pass
"""
        definition = next(Module.I.definitions(ast.parse(code)))

        assert Module.I.definition_name_rank(definition, (definition,)) == "example"

    def test_definition_reference_rank(self) -> None:
        """Rank definitions using the supplied reference and dependency collectors."""
        code = """def main(): pass
def helper(): pass
"""
        main, helper = Module.I.definitions(ast.parse(code))
        definitions = (main, helper)

        def references(definition: ast.AST) -> KeysView[str]:
            return dict.fromkeys(("helper",) if definition is main else ()).keys()

        def dependencies(_definition: ast.AST) -> KeysView[str]:
            return dict.fromkeys(()).keys()

        assert [
            Module.I.definition_reference_rank(
                definition,
                definitions,
                references,
                dependencies,
            )
            for definition in definitions
        ] == [0, 1]

    @pytest.mark.parametrize(
        ("code", "expected"),
        [
            pytest.param("", {}, id="empty"),
            pytest.param(
                """def first(): pass
def second(): pass
def main(): second(); first(); second()
""",
                {"main": 0, "second": 1, "first": 1},
                id="sibling-references-share-layer",
            ),
            pytest.param(
                """def main(): load(); save()
def save(): serialize()
def serialize(): pass
def load(): parse()
def parse(): pass
""",
                {"main": 0, "load": 1, "save": 1, "parse": 2, "serialize": 2},
                id="breadth-first-layers",
            ),
            pytest.param(
                """def shared(): pass
def first(): shared()
def second(): shared()
""",
                {"first": 0, "second": 0, "shared": 1},
                id="shared-target-after-all-users",
            ),
            pytest.param(
                """def main(): first(); second(); shared()
def first(): shared()
def second(): pass
def shared(): pass
""",
                {"main": 0, "first": 1, "second": 1, "shared": 2},
                id="shared-target-after-last-user-layer",
            ),
            pytest.param(
                """class Alpha: pass
def _private(): pass
def zeta(): pass
def alpha(): pass
""",
                {"alpha": 0, "zeta": 0, "_private": 0, "Alpha": 0},
                id="unreferenced-definitions-tie",
            ),
            pytest.param(
                """def first(): second()
def second(): first()
""",
                {"first": 0, "second": 0},
                id="mutual-cycle",
            ),
            pytest.param(
                """def recursive(): recursive()
""",
                {"recursive": 0},
                id="self-reference",
            ),
            pytest.param(
                """def main(): second(); first()
def first(): second()
def second(): first(); helper()
def helper(): pass
""",
                {"main": 0, "first": 1, "second": 1, "helper": 2},
                id="cycle-with-caller-and-helper",
            ),
            pytest.param(
                """def example(): external()
""",
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
        """Rank reference layers, including cycles and duplicate names."""
        definitions = tuple(Module.I.definitions(ast.parse(code)))

        assert (
            Module.I.definition_reference_ranks(
                definitions,
                Module.I.module_definition_references,
                Module.I.module_definition_dependencies,
            )
            == expected
        )

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

        assert Module.I.definition_reference_ranks(
            definitions,
            Module.I.module_definition_references,
            Module.I.module_definition_dependencies,
        ) == {
            "main": 0,
            "Base": 0,
            "Child": 1,
            "ExternalChild": 0,
            "Factory": 0,
            "Item": 1,
        }

    def test_definition_sort_key(self) -> None:
        """Place reference rank before kind, visibility and name in the tuple."""
        code = """def main(): _helper()
def _helper(): pass
"""
        definitions = tuple(Module.I.definitions(ast.parse(code)))

        assert Module.I.definition_sort_key(
            definitions[1],
            definitions,
            Module.I.module_definition_ranks(),
        ) == (
            1,
            0,
            1,
            "_helper",
        )

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

    @pytest.mark.parametrize(
        ("unordered", "ordered", "expected"),
        [
            pytest.param(
                """old
""",
                """new
""",
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

    def test_discovery_module(self) -> None:
        """Discover ordering policies in the order package."""
        assert Module.I.discovery_module() is order

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

    @pytest.mark.parametrize(
        ("unordered", "ordered", "expected"),
        [
            pytest.param("", "", True, id="empty"),
            pytest.param(
                """def alpha(): pass
""",
                """def alpha(): pass
""",
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

    @pytest.mark.parametrize(
        ("name", "expected"),
        [
            ("__repr__", 0),
            ("__init__", 0),
            ("run", 1),
            ("_run", 1),
            ("__run", 1),
            ("__run_", 1),
            ("_run__", 1),
        ],
    )
    def test_magic_method_rank(self, name: str, expected: int) -> None:
        """Rank dunder methods before all other definitions."""
        definition = next(Module.I.definitions(ast.parse(f"def {name}(self): pass")))

        assert Module.I.magic_method_rank(definition, ()) == expected

    def test_module_definition_dependencies(self) -> None:
        """Return the shared definition-time dependencies."""
        code = """@decorate
def example(value=default): deferred()
"""
        definition = next(Module.I.definitions(ast.parse(code)))

        assert Module.I.module_definition_dependencies(definition) == {
            "decorate",
            "default",
        }

    def test_module_definition_ranks(self) -> None:
        """Expose policy callables in descending priority order."""
        assert Module.I.module_definition_ranks() == (
            Module.I.module_definition_reference_rank,
            Module.I.definition_kind_rank,
            Module.I.definition_visibility_rank,
            Module.I.definition_name_rank,
        )

    def test_module_definition_reference_rank(self) -> None:
        """Use module-name collectors to rank module-level definitions."""
        code = """def main(): helper()
def helper(): pass
"""
        definitions = tuple(Module.I.definitions(ast.parse(code)))

        assert (
            Module.I.module_definition_reference_rank(definitions[0], definitions) == 0
        )
        assert (
            Module.I.module_definition_reference_rank(definitions[1], definitions) == 1
        )

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
            pytest.param(
                "def example(): return other_func.__name__",
                {"other_func"},
                id="attribute-access-without-call",
            ),
        ],
    )
    def test_module_definition_references(self, code: str, expected: set[str]) -> None:
        """Collect syntactic loads, including deferred bodies and annotation names."""
        definition = next(Module.I.definitions(ast.parse(code)))

        assert set(Module.I.module_definition_references(definition)) == expected

    def test_module_definition_references_order(self) -> None:
        """Preserve first-seen loaded names and remove duplicates."""
        definition = next(
            Module.I.definitions(
                ast.parse("def main(): second(); first(); second()"),
            ),
        )

        assert tuple(Module.I.module_definition_references(definition)) == (
            "second",
            "first",
        )

    @pytest.mark.parametrize(
        ("code", "expected"),
        [
            pytest.param("", "", id="empty"),
            pytest.param(
                """VALUE = 1
""",
                """VALUE = 1
""",
                id="no-definitions",
            ),
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
                """def first(): pass

def second(): pass

def main(): second(); first()
""",
                """def main(): second(); first()

def first(): pass

def second(): pass
""",
                id="module-reference-layer-name-tie-breaker",
            ),
            pytest.param(
                """class Example:
    def first(self): pass

    def second(self): pass

    def main(self): self.second(); self.first()
""",
                """class Example:
    def main(self): self.second(); self.first()

    def first(self): pass

    def second(self): pass
""",
                id="method-reference-layer-name-tie-breaker",
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
            pytest.param(
                """class Zebra:
    def zebra(self): pass

    def alpha(self): pass

class Alpha: pass
""",
                """class Alpha: pass

class Zebra:
    def alpha(self): pass

    def zebra(self): pass
""",
                id="class-body-after-moved-class",
            ),
            pytest.param(
                """class Example:
    def alpha(self): pass

    def zebra(self): return self.alpha()
""",
                """class Example:
    def zebra(self): return self.alpha()

    def alpha(self): pass
""",
                id="method-caller-before-callee",
            ),
            pytest.param(
                """class Example:
    def zebra(self): pass

    def alpha(self, callback=zebra): pass
""",
                """class Example:
    def zebra(self): pass

    def alpha(self, callback=zebra): pass
""",
                id="method-default-dependency-kept-first",
            ),
            pytest.param(
                """class Example:
    def _helper(self): pass

    def run(self): return self.load()

    @classmethod
    def from_value(cls, value): return cls()

    def __repr__(self): return "Example"

    @abstractmethod
    def load(self): ...

    @abstractmethod
    def __len__(self): ...

    def __init__(self): pass

    def __new__(cls): return super().__new__(cls)

    class Meta: pass
""",
                """class Example:
    class Meta: pass

    def __new__(cls): return super().__new__(cls)

    def __init__(self): pass

    @abstractmethod
    def __len__(self): ...

    @abstractmethod
    def load(self): ...

    def __repr__(self): return "Example"

    @classmethod
    def from_value(cls, value): return cls()

    def run(self): return self.load()

    def _helper(self): pass
""",
                id="cls-style-order",
            ),
            pytest.param(
                """class Example:
    def zebra(self): pass

    def middle(self): return self.zebra()

    def alpha(self): return self.middle()
""",
                """class Example:
    def alpha(self): return self.middle()

    def middle(self): return self.zebra()

    def zebra(self): pass
""",
                id="cls-method-reference-chain",
            ),
            pytest.param(
                """class Example:
    def _save(self): return self._serialize()

    def _serialize(self): pass

    def run(self): return self._load(), self._save()

    def _parse(self): pass

    def _load(self): return self._parse()
""",
                """class Example:
    def run(self): return self._load(), self._save()

    def _load(self): return self._parse()

    def _save(self): return self._serialize()

    def _parse(self): pass

    def _serialize(self): pass
""",
                id="cls-method-branches-by-layer",
            ),
            pytest.param(
                """class Example:
    def zebra(self): return self.alpha()

    def alpha(self): return self.zebra()

    def main(self): return self.zebra()
""",
                """class Example:
    def main(self): return self.zebra()

    def alpha(self): return self.zebra()

    def zebra(self): return self.alpha()
""",
                id="cls-method-cycle-after-user",
            ),
            pytest.param(
                """class Example:
    value = 1

    def zebra(self): pass

    other = 2

    def alpha(self): pass
""",
                """class Example:
    value = 1

    def alpha(self): pass

    other = 2

    def zebra(self): pass
""",
                id="cls-attributes-keep-their-slots",
            ),
            pytest.param(
                """class Example:
    @property
    def size(self): return self._size

    @size.setter
    def size(self, value): self._size = value

    def alpha(self): pass
""",
                """class Example:
    def alpha(self): pass

    @property
    def size(self): return self._size

    @size.setter
    def size(self, value): self._size = value
""",
                id="cls-property-setter-kept-together",
            ),
            pytest.param(
                """class Example:
    @overload
    def get(self, key: int) -> int: ...

    @overload
    def get(self, key: str) -> str: ...

    def get(self, key): return key

    def alpha(self): pass
""",
                """class Example:
    def alpha(self): pass

    @overload
    def get(self, key: int) -> int: ...

    @overload
    def get(self, key: str) -> str: ...

    def get(self, key): return key
""",
                id="cls-overloads-kept-in-order",
            ),
            pytest.param(
                """def factory():
    class Local:
        def zebra(self): pass

        def alpha(self): pass

    return Local
""",
                """def factory():
    class Local:
        def zebra(self): pass

        def alpha(self): pass

    return Local
""",
                id="function-local-class-unchanged",
            ),
        ],
    )
    def test_order_code(self, code: str, expected: str) -> None:
        """Preserve exact source formatting and produce an idempotent ordering."""
        ordered = Module.I.order_code(code)

        assert ordered == expected
        assert Module.I.order_code(ordered) == ordered
        compile(ordered, "<ordered>", "exec")

    def test_order_code_cls_body_dependencies(self) -> None:
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

    def test_order_code_cls_decorator(self) -> None:
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
    def test_order_code_cls_dependency_edge(
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

    def test_order_code_cls_metaclass(self) -> None:
        """Put a metaclass before its dependent class."""
        code = """class Child(metaclass=Meta): pass

class Meta(type): pass
"""
        expected = """class Meta(type): pass

class Child(metaclass=Meta): pass
"""

        assert Module.I.order_code(code) == expected
        assert Module.I.order_code(expected) == expected

    @pytest.mark.parametrize("func_kind", ["def", "async def"])
    def test_order_code_func_decorator(self, func_kind: str) -> None:
        """Move a local decorator before a synchronous or async function."""
        code = f"""@decorate
{func_kind} example():
    pass

def decorate(value):
    return value
"""
        expected = f"""def decorate(value):
    return value

@decorate
{func_kind} example():
    pass
"""

        assert Module.I.order_code(code) == expected
        assert Module.I.order_code(expected) == expected

    def test_order_code_override_priority(self) -> None:
        """Place overrides after abstract methods and before ordinary methods."""
        code = """class Example:
    def alpha(self): return self.zebra()

    @classmethod
    def build(cls): pass

    def __repr__(self): pass

    @override
    def zebra(self): return self.helper()

    @abstractmethod
    def required(self): ...

    @override
    def __init__(self): pass

    class Nested: pass

    def helper(self): pass
"""
        ordered = Module.I.order_code(code)
        cls = next(Module.I.classes(ast.parse(ordered)))

        assert [definition.name for definition in Module.I.definitions(cls)] == [
            "Nested",
            "__init__",
            "required",
            "zebra",
            "__repr__",
            "build",
            "alpha",
            "helper",
        ]
        assert Module.I.order_code(ordered) == ordered
        compile(ordered, "<ordered>", "exec")

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

    def test_order_definitions(self) -> None:
        """Break independent ties by kind, visibility and alphabetical name."""
        code = """class Example: pass
def _hidden(): pass
def zebra(): pass
def alpha(): pass
"""
        definitions = tuple(Module.I.definitions(ast.parse(code)))

        ordered = Module.I.order_definitions(
            definitions,
            Module.I.module_definition_ranks(),
        )

        assert [definition.name for definition in ordered] == [
            "alpha",
            "zebra",
            "_hidden",
            "Example",
        ]

    @pytest.mark.parametrize(
        ("code", "expected"),
        [
            pytest.param(
                "@override\ndef run(self): pass",
                0,
                id="name",
            ),
            pytest.param(
                "@typing.override\ndef run(self): pass",
                0,
                id="typing-attribute",
            ),
            pytest.param(
                "@typing_extensions.override\ndef run(self): pass",
                0,
                id="typing-extensions-attribute",
            ),
            pytest.param(
                "@classmethod\n@override\ndef run(cls): pass",
                0,
                id="stacked",
            ),
            pytest.param(
                "@override\nasync def run(self): pass",
                0,
                id="async",
            ),
            pytest.param("def run(self): pass", 1, id="undecorated"),
            pytest.param(
                "@abstractmethod\ndef run(self): ...",
                1,
                id="other-decorator",
            ),
            pytest.param(
                "@override()\ndef run(self): pass",
                1,
                id="called-decorator-ignored",
            ),
        ],
    )
    def test_override_method_rank(self, code: str, expected: int) -> None:
        """Recognize override decorators using the shared decorator collector."""
        definition = next(Module.I.definitions(ast.parse(code)))

        assert Module.I.override_method_rank(definition, ()) == expected

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

    def test_reorder_cls_definitions(self) -> None:
        """Order each module-level class body, leaving other bodies untouched."""
        code = """def zebra(): pass

def alpha(): pass

class First:
    def zebra(self): pass

    def alpha(self): pass

class Second:
    def yak(self): pass

    def bee(self): pass

    class Inner:
        def second(self): pass

        def first(self): pass
"""
        expected = """def zebra(): pass

def alpha(): pass

class First:
    def alpha(self): pass

    def zebra(self): pass

class Second:
    class Inner:
        def second(self): pass

        def first(self): pass

    def bee(self): pass

    def yak(self): pass
"""

        assert Module.I.reorder_cls_definitions(code, ast.parse(code)) == expected

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

    def test_reorder_definitions(self) -> None:
        """Use supplied definitions and ranks without moving other source."""
        code = """def alpha(): pass

def middle(): pass

def zebra(): pass
"""

        module = ast.parse(code)
        definitions = tuple(Module.I.definitions(module))

        def zebra_first(
            definition: ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef,
            _definitions: tuple[
                ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef,
                ...,
            ],
        ) -> bool:
            return definition.name != "zebra"

        expected = """def zebra(): pass

def middle(): pass

def alpha(): pass
"""

        assert (
            Module.I.reorder_definitions(
                code,
                (definitions[0], definitions[2]),
                (zebra_first,),
            )
            == expected
        )

    def test_reorder_module_definitions(self) -> None:
        """Order direct module definitions using module-level ranking policies."""
        code = """class Example: pass

def zebra(): pass

def alpha(): pass
"""
        expected = """def alpha(): pass

def zebra(): pass

class Example: pass
"""

        assert Module.I.reorder_module_definitions(code, ast.parse(code)) == expected

    def test_reorderers(self) -> None:
        """Return module-level and class-body passes in application order."""
        assert Module.I.reorderers() == (
            Module.I.reorder_module_definitions,
            Module.I.reorder_cls_definitions,
        )

    def test_reverse_definition_kind_rank(self) -> None:
        """Rank classes before functions."""
        code = """def sync(): pass
async def async_func(): pass
class Example: pass
"""
        definitions = tuple(Module.I.definitions(ast.parse(code)))

        assert [
            Module.I.reverse_definition_kind_rank(definition, definitions)
            for definition in definitions
        ] == [0, 0, -1]

    def test_source_placeholder(self) -> None:
        """Produce a valid UUID hex placeholder."""
        placeholder = Module.I.source_placeholder()

        assert UUID(placeholder).hex == placeholder

    def test_standard_definition_ranks(self) -> None:
        """Order ties by visibility, then name."""
        assert Module.I.standard_definition_ranks() == (
            Module.I.definition_visibility_rank,
            Module.I.definition_name_rank,
        )

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

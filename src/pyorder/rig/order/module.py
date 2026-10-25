"""Readability-oriented ordering of definitions in Python modules."""

import ast
import difflib
import tokenize
from collections.abc import Callable, Iterable, Iterator
from functools import lru_cache
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING
from uuid import uuid4

import networkx as nx
import typer
from pyrig_runtime.core.dependencies.subclass import DependencySubclass

from pyorder.rig import order

if TYPE_CHECKING:
    from _typeshed import SupportsRichComparison


type AnyFuncDefinition = ast.FunctionDef | ast.AsyncFunctionDef
type AnyDefinition = AnyFuncDefinition | ast.ClassDef

FUNC_DEFINITIONS = (ast.FunctionDef, ast.AsyncFunctionDef)
DEFINITIONS = (*FUNC_DEFINITIONS, ast.ClassDef)


class Module(DependencySubclass):
    """Readability-oriented ordering policies for Python source modules."""

    @classmethod
    def discovery_module(cls) -> ModuleType:
        """Return the package that scopes subclass discovery."""
        return order

    def check_order(self, file: Path, *, fix: bool = False) -> bool:
        """Check the order of Python source code in a file.

        When `fix` is false and the file is out of order, show the diff.

        Args:
            file: Path to a Python source file.
            fix: Whether to also apply ordering changes.

        Returns:
            True if the file is already correctly ordered, `False` otherwise,
            even when ordering changes are applied.
        """
        code = self.read_text(file)

        ordered = self.order_code(code)

        if self.is_ordered(code, ordered):
            return True

        if fix:
            self.fix_order(file, ordered)
        else:
            typer.echo(f"""Incorrect order: {file}
{self.diff(code, ordered)}""")
        return False

    def diff(self, unordered: str, ordered: str) -> str:
        """Return a unified line diff between unordered and ordered source.

        Args:
            unordered: Original source.
            ordered: Source to compare against the original.

        Returns:
            The diff text, or an empty string if the split lines match.
        """
        return "\n".join(
            difflib.unified_diff(
                unordered.splitlines(),
                ordered.splitlines(),
                lineterm="",
            ),
        )

    def is_ordered(self, unordered: str, ordered: str) -> bool:
        """Return whether the source matches its expected ordering.

        Args:
            unordered: Source being checked.
            ordered: Expected source.

        Returns:
            Whether both strings are equal, including whitespace.
        """
        return unordered == ordered

    def fix_order(self, file: Path, code: str) -> None:
        """Write replacement source to an existing file.

        Args:
            file: Existing destination file.
            code: Replacement source with LF-normalized line endings.
        """
        self.write_text(file, code)

    def order_code(self, code: str) -> str:
        """Return source with the module's ordering policies applied.

        Args:
            code: Python source to reorder.

        Returns:
            Transformed and ordered source code.
        """
        return self.reorder_definitions(code)

    def reorder_definitions(
        self,
        code: str,
    ) -> str:
        """Reorder direct module-level function and class definitions.

        Nested definitions are not independently reordered.

        Args:
            code: Python source code.

        Returns:
            Source with reordered definitions according to the ordering policies.
        """
        definitions = tuple(self.definitions(ast.parse(code)))
        return self.reorder_code(code, definitions, self.order_definitions(definitions))

    def reorder_code(
        self,
        code: str,
        unordered: Iterable[ast.AST],
        ordered: Iterable[ast.AST],
    ) -> str:
        """Replace selected source segments with their requested ordering.

        Segments are matched by their first textual occurrence, not their
        location. Identical text elsewhere can therefore be replaced instead.

        Args:
            code: Original source from which the nodes were parsed.
            unordered: Nodes in their original source order.
            ordered: The same nodes in the desired order.

        Returns:
            Source with the selected segments replaced in the requested order.
        """
        unordered_sources = tuple(self.get_source_segment(code, uo) for uo in unordered)
        placeholders = tuple(self.source_placeholder() for _ in unordered_sources)
        ordered_sources = tuple(
            self.get_source_segment(code, definition) for definition in ordered
        )

        for source, placeholder in zip(
            unordered_sources,
            placeholders,
            strict=True,
        ):
            code = code.replace(source, placeholder, 1)

        for placeholder, source in zip(
            placeholders,
            ordered_sources,
            strict=True,
        ):
            code = code.replace(placeholder, source, 1)

        return code

    def source_placeholder(self) -> str:
        """Return a random UUID4 hex token for use as a source placeholder.

        Returns:
            A practically unique string for use as a placeholder in source code.
        """
        return uuid4().hex

    def get_source_segment(
        self,
        code: str,
        node: ast.AST,
    ) -> str:
        """Extract a node's source segment.

        For definitions, updates `node.lineno` to the first decorator
        expression's line. A decorator's opening syntax on an earlier line
        is not included.

        Args:
            code: Source corresponding to the node's locations.
            node: Node whose source segment is required.

        Returns:
            The selected source text, excluding surrounding comments.

        Raises:
            LookupError: If the node lacks locations needed for extraction.
        """
        if isinstance(node, DEFINITIONS):
            node.lineno = next(iter(node.decorator_list), node).lineno

        source = ast.get_source_segment(code, node)
        if source is None:
            msg = f"failed to get source segment {node=}"
            raise LookupError(msg)
        return source

    def order_definitions(
        self,
        definitions: tuple[AnyDefinition, ...],
    ) -> list[AnyDefinition]:
        """Return definitions in stable, ascending policy-key order.

        Args:
            definitions: Definitions to sort together.

        Returns:
            A sorted list retaining original order when keys compare equal.
        """

        def sort_key(definition: AnyDefinition) -> tuple["SupportsRichComparison", ...]:
            return self.definition_sort_key(definition, definitions)

        return sorted(
            definitions,
            key=sort_key,
        )

    def definition_sort_key(
        self,
        definition: AnyDefinition,
        definitions: tuple[AnyDefinition, ...],
    ) -> tuple["SupportsRichComparison", ...]:
        """Return the policy values used to sort a definition.

        Args:
            definition: Definition to rank.
            definitions: All definitions participating in the sort.

        Returns:
            A lexicographic key whose earlier values take precedence.
        """
        return tuple(
            key(definition, definitions) for key in self.definition_sort_keys()
        )

    def definition_sort_keys(
        self,
    ) -> tuple[
        Callable[[AnyDefinition, tuple[AnyDefinition, ...]], "SupportsRichComparison"],
        ...,
    ]:
        """Return the ordered policies used to rank definitions.

        Each rule takes a definition and the full set of definitions, returning
        a comparable value. Earlier rules have higher priority.

        Returns:
            Tuple of ranking rules represented as callables.
        """
        return (
            self.definition_reference_rank,
            self.definition_kind_rank,
            self.definition_visibility_rank,
            self.definition_name_rank,
        )

    def definition_reference_rank(
        self,
        definition: AnyDefinition,
        definitions: tuple[AnyDefinition, ...],
    ) -> int:
        """Return the reference-layer rank associated with a definition's name.

        Args:
            definition: Definition whose rank is required.
            definitions: Definitions that establish the reference relationships.

        Returns:
            The name's rank, with lower ranks preceding higher ones.
        """
        return self.definition_reference_ranks(definitions)[definition.name]

    @classmethod
    @lru_cache(maxsize=1)
    def definition_reference_ranks(
        cls,
        definitions: tuple[AnyDefinition, ...],
    ) -> dict[str, int]:
        """Rank names in reference layers, reversing dependency references.

        Only references matching supplied definition names contribute.
        Independent names have rank zero; duplicate names share a rank.
        Between distinct reference groups, users have lower ranks than their
        targets, except that definition-time dependencies precede
        their dependent definitions. Each group occupies its earliest layer
        after all incoming groups. Cycles share a rank.

        Args:
            definitions: Definitions whose names and references establish ranks.

        Returns:
            A name-to-rank mapping. Treat the cached result as read-only;
            changing references within the same nodes does not invalidate it.
        """
        names = {definition.name for definition in definitions}
        graph = nx.DiGraph()
        graph.add_nodes_from(names)
        self = cls()
        for definition in definitions:
            used = self.definition_references(definition) & names
            dependencies = self.definition_dependencies(definition) & names
            graph.add_edges_from(
                (definition.name, name) for name in used - dependencies
            )
            graph.add_edges_from((name, definition.name) for name in dependencies)

        condensed = nx.condensation(graph)
        return {
            name: rank
            for rank, generation in enumerate(nx.topological_generations(condensed))
            for component in generation
            for name in condensed.nodes[component]["members"]
        }

    def definition_dependencies(self, definition: AnyDefinition) -> set[str]:
        """Collect direct definition-time references, excluding annotations.

        Inspect decorators, defaults, class headers, and class-suite statements.
        Ignore annotations, deferred function, lambda, and generator bodies,
        and type-alias statements. Conditional branches are included without
        resolving names across scopes or through calls.

        Args:
            definition: Definition whose dependencies to collect.

        Returns:
            Names referenced by the definition-time expressions inspected.
        """
        pending: list[ast.AST] = [definition]
        dependencies: set[str] = set()
        while pending:
            node = pending.pop()
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                dependencies.add(node.id)
            if isinstance(node, ast.AugAssign) and isinstance(node.target, ast.Name):
                dependencies.add(node.target.id)
            pending.extend(self.definition_dependency_children(node))
        return dependencies

    def definition_dependency_children(self, node: ast.AST) -> Iterator[ast.AST]:
        """Yield AST children used to inspect definition-time evaluation.

        Args:
            node: Node whose evaluation boundaries determine its children.

        Yields:
            Children to inspect, excluding annotations and deferred bodies.
        """
        if isinstance(node, ast.ClassDef):
            yield from node.decorator_list
            yield from node.bases
            yield from (keyword.value for keyword in node.keywords)
            yield from node.body
        elif isinstance(node, (*FUNC_DEFINITIONS, ast.Lambda)):
            if isinstance(node, FUNC_DEFINITIONS):
                yield from node.decorator_list
            yield from node.args.defaults
            yield from filter(None, node.args.kw_defaults)
        elif isinstance(node, ast.GeneratorExp):
            yield node.generators[0].iter
        elif isinstance(node, ast.AnnAssign):
            yield node.target
            if node.value is not None:
                yield node.value
        elif not isinstance(node, ast.TypeAlias):
            yield from ast.iter_child_nodes(node)

    def definition_references(self, definition: AnyDefinition) -> set[str]:
        """Collect loaded names appearing in a definition's syntax tree.

        Args:
            definition: Definition whose contents to inspect.

        Returns:
            Loaded names found anywhere in the definition's syntax tree.
        """
        return {
            node.id
            for node in ast.walk(definition)
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)
        }

    def definition_name_rank(
        self,
        definition: AnyDefinition,
        _definitions: tuple[AnyDefinition, ...],
    ) -> str:
        """Return the unchanged name for case-sensitive alphabetical ordering.

        Args:
            definition: Definition whose name determines the rank.
            _definitions: Other definitions; not used by this rule.

        Returns:
            The definition's name.
        """
        return definition.name

    def definition_kind_rank(
        self,
        definition: AnyDefinition,
        _definitions: tuple[AnyDefinition, ...],
    ) -> int:
        """Rank functions before classes.

        Args:
            definition: Definition whose kind determines the rank.
            _definitions: Other definitions; not used by this rule.

        Returns:
            Zero for functions and one for classes.
        """
        if isinstance(definition, FUNC_DEFINITIONS):
            return 0
        return 1

    def definition_visibility_rank(
        self,
        definition: AnyDefinition,
        _definitions: tuple[AnyDefinition, ...],
    ) -> int:
        """Rank names by their number of leading underscores, fewest first.

        Dunder names receive no special treatment.

        Args:
            definition: Definition whose name determines the rank.
            _definitions: Other definitions; unused by this rule.

        Returns:
            The number of leading underscores in the name.
        """
        name = definition.name
        return len(name) - len(name.lstrip("_"))

    def definitions(self, tree: ast.Module) -> Iterator[AnyDefinition]:
        """Yield direct module-level function and class definitions.

        Args:
            tree: Parsed module to inspect.

        Yields:
            Synchronous functions, asynchronous functions, and classes in
            source order, excluding definitions nested in other statements.
        """
        return (node for node in tree.body if isinstance(node, DEFINITIONS))

    def read_text(self, file: Path) -> str:
        """Read Python source using its detected encoding.

        Args:
            file: Path to an existing Python source file.

        Returns:
            The decoded contents with line endings normalized to LF and any
            leading UTF-8 byte-order mark removed.
        """
        encoding, _ = self.file_info(file)
        return file.read_text(encoding=encoding)

    def write_text(self, file: Path, code: str) -> None:
        """Overwrite a file using its detected encoding and first-line newline.

        If the first line has no line terminator, use LF.

        Args:
            file: Path to an existing Python source file.
            code: Replacement contents with LF-normalized line endings.
        """
        encoding, newline = self.file_info(file)
        file.write_text(code, encoding=encoding, newline=newline)

    def file_info(self, file: Path) -> tuple[str, str]:
        """Detect the source encoding and first-line newline sequence.

        Args:
            file: Path to an existing Python source file.

        Returns:
            A pair of the encoding name and newline sequence. The sequence
            defaults to LF if the first line has no terminator.
        """
        with tokenize.open(file) as f:
            f.readline()
            newlines = f.newlines
            newline = (
                newlines
                if isinstance(newlines, str)
                else next(iter(newlines or ()), "\n")
            )
            return f.encoding, newline

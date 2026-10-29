"""Readability-oriented ordering of definitions in Python modules."""

import ast
import difflib
import tokenize
from abc import abstractmethod
from collections.abc import Callable, Iterable, Iterator, KeysView
from functools import lru_cache
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING, override
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
    @override
    def discovery_module(cls) -> ModuleType:
        """Return the package that scopes subclass discovery."""
        return order

    @classmethod
    @lru_cache(maxsize=1)
    def definition_reference_ranks(
        cls,
        definitions: tuple[AnyDefinition, ...],
        references: Callable[[AnyDefinition], KeysView[str]],
        dependencies: Callable[[AnyDefinition], KeysView[str]],
    ) -> dict[str, int]:
        """Group definition names into top-down reference layers.

        Users precede their references, but definition-time dependencies precede
        their users. Only names in ``definitions`` contribute. Cycles share a
        rank, so ordering constraints within them are not enforced.

        Args:
            definitions: Definitions to rank together.
            references: Collector of names referenced by a definition.
            dependencies: Collector of names needed when a definition is created.

        Returns:
            Name-to-layer mapping, starting at zero. Lower layers come first;
            names in the same layer tie. Treat the cached mapping as read-only.
        """
        names = {definition.name for definition in definitions}
        graph = nx.DiGraph()
        graph.add_nodes_from(names)
        for definition in definitions:
            used = references(definition) & names
            needed = dependencies(definition) & names
            graph.add_edges_from((definition.name, name) for name in used - needed)
            graph.add_edges_from((name, definition.name) for name in needed)

        condensed = nx.condensation(graph)
        return {
            name: rank
            for rank, generation in enumerate(nx.topological_generations(condensed))
            for component in generation
            for name in condensed.nodes[component]["members"]
        }

    def check_order(self, file: Path, *, fix: bool = False) -> bool:
        """Check the order of Python source code in a file.

        When `fix` is false and the file is out of order, show the diff.

        Args:
            file: Path to a Python source file.
            fix: Whether to also apply ordering changes.

        Returns:
            `True` if the file is already correctly ordered, `False` otherwise,
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

    def fix_order(self, file: Path, code: str) -> None:
        """Write replacement source to an existing file.

        Args:
            file: Existing destination file.
            code: Replacement source with LF-normalized line endings.
        """
        self.write_text(file, code)

    def is_ordered(self, unordered: str, ordered: str) -> bool:
        """Return whether the source matches its expected ordering.

        Args:
            unordered: Source being checked.
            ordered: Expected source.

        Returns:
            Whether both strings are equal, including whitespace.
        """
        return unordered == ordered

    def order_code(self, code: str) -> str:
        """Return source with the module's ordering policies applied.

        Args:
            code: Python source to reorder.

        Returns:
            Transformed and ordered source code.
        """
        for reorder in self.reorderers():
            code = reorder(code, ast.parse(code))
        return code

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

    def reorderers(self) -> tuple[Callable[[str, ast.Module], str], ...]:
        """Return the source-reordering passes in application order.

        Returns:
            Module-level definition ordering followed by class-body ordering.
        """
        return (
            self.reorder_module_definitions,
            self.reorder_cls_definitions,
        )

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

    def reorder_cls_definitions(self, code: str, module: ast.Module) -> str:
        """Reorder definitions directly in each module-level class body.

        Args:
            code: Python source corresponding to ``module``.
            module: Parsed module containing the classes to process.

        Returns:
            Source with each module-level class body ordered by its policies.
        """
        for cls in self.classes(module):
            code = self.reorder_definitions(
                code,
                self.definitions(cls),
                self.cls_definition_ranks(),
            )
        return code

    def reorder_module_definitions(self, code: str, module: ast.Module) -> str:
        """Reorder definitions directly in the module body.

        Args:
            code: Python source corresponding to ``module``.
            module: Parsed module whose direct definitions are reordered.

        Returns:
            Source with module-level definitions ordered by their policies.
        """
        return self.reorder_definitions(
            code,
            self.definitions(module),
            self.module_definition_ranks(),
        )

    def classes(self, tree: ast.Module | AnyDefinition) -> Iterator[AnyDefinition]:
        """Yield direct class definitions from an AST node.

        Args:
            tree: Parsed module, function, or class to inspect.

        Yields:
            Direct class definitions in source order.
        """
        return (node for node in tree.body if isinstance(node, ast.ClassDef))

    def cls_definition_ranks(
        self,
    ) -> tuple[
        Callable[[AnyDefinition, tuple[AnyDefinition, ...]], "SupportsRichComparison"],
        ...,
    ]:
        """Return the ranking policies for definitions in a class body.

        Returns:
            Ranking callables, with earlier entries taking precedence.
        """
        return (
            self.reverse_definition_kind_rank,
            self.constructor_method_rank,
            self.abstract_method_rank,
            self.override_method_rank,
            self.magic_method_rank,
            self.classmethod_rank,
            self.cls_definition_reference_rank,
            *self.standard_definition_ranks(),
        )

    def definitions(self, tree: ast.Module | AnyDefinition) -> Iterator[AnyDefinition]:
        """Yield direct function and class definitions from an AST node.

        Args:
            tree: Parsed module, function, or class to inspect.

        Yields:
            Synchronous functions, asynchronous functions, and classes in
            source order, excluding definitions nested in other statements.
        """
        return (node for node in tree.body if isinstance(node, DEFINITIONS))

    def module_definition_ranks(
        self,
    ) -> tuple[
        Callable[[AnyDefinition, tuple[AnyDefinition, ...]], "SupportsRichComparison"],
        ...,
    ]:
        """Return the ordered policies used to rank module-level definitions.

        Each rule takes a definition and the full set of definitions, returning
        a comparable value. Earlier rules have higher priority.

        Returns:
            Tuple of ranking rules represented as callables.
        """
        return (
            self.module_definition_reference_rank,
            self.definition_kind_rank,
            *self.standard_definition_ranks(),
        )

    def reorder_definitions(
        self,
        code: str,
        definitions: Iterable[AnyDefinition],
        ranks: tuple[
            Callable[
                [AnyDefinition, tuple[AnyDefinition, ...]],
                "SupportsRichComparison",
            ],
            ...,
        ],
    ) -> str:
        """Reorder the supplied definitions according to their ranking policies.

        Nested definitions are not independently reordered.

        Args:
            code: Python source code.
            definitions: Definitions to reorder.
            ranks: Ranking policies applied in priority order.

        Returns:
            Source with reordered definitions according to the ordering policies.
        """
        definitions = tuple(definitions)
        return self.reorder_code(
            code,
            definitions,
            self.order_definitions(definitions, ranks),
        )

    def abstract_method_rank(
        self,
        definition: AnyDefinition,
        _definitions: tuple[AnyDefinition, ...],
    ) -> "SupportsRichComparison":
        """Rank abstract methods before other definitions.

        Args:
            definition: Definition whose decorators determine the rank.
            _definitions: Other definitions; not used by this rule.

        Returns:
            Zero if decorated with ``abstractmethod``, otherwise one.
        """
        if abstractmethod.__name__ in self.decorator_names(definition):
            return 0
        return 1

    def classmethod_rank(
        self,
        definition: AnyDefinition,
        _definitions: tuple[AnyDefinition, ...],
    ) -> "SupportsRichComparison":
        """Rank class methods before other definitions.

        Args:
            definition: Definition whose decorators determine the rank.
            _definitions: Other definitions; not used by this rule.

        Returns:
            Zero if decorated with ``classmethod``, otherwise one.
        """
        if classmethod.__name__ in self.decorator_names(definition):
            return 0
        return 1

    def cls_definition_reference_rank(
        self,
        definition: AnyDefinition,
        definitions: tuple[AnyDefinition, ...],
    ) -> "SupportsRichComparison":
        """Return a class-body definition's reference-layer rank.

        Args:
            definition: Class-body definition whose rank is required.
            definitions: Class-body definitions establishing the graph.

        Returns:
            The name's rank, with lower ranks preceding higher ones.
        """
        return self.definition_reference_rank(
            definition,
            definitions,
            self.cls_definition_references,
            self.cls_definition_dependencies,
        )

    def constructor_method_rank(
        self,
        definition: AnyDefinition,
        _definitions: tuple[AnyDefinition, ...],
    ) -> "SupportsRichComparison":
        """Rank object's constructor hooks in call order before other definitions.

        Args:
            definition: Definition whose name determines the rank.
            _definitions: Other definitions; not used by this rule.

        Returns:
            Zero for ``__init_subclass__``, one for ``__new__``, two for
            ``__init__``, and three otherwise.
        """
        name = definition.name
        return (
            object.__init_subclass__.__name__,
            object.__new__.__name__,
            object.__init__.__name__,
            name,
        ).index(name)

    def magic_method_rank(
        self,
        definition: AnyDefinition,
        _definitions: tuple[AnyDefinition, ...],
    ) -> "SupportsRichComparison":
        """Rank dunder names before other definitions.

        Args:
            definition: Definition whose name determines the rank.
            _definitions: Other definitions; not used by this rule.

        Returns:
            Zero if the name starts and ends with two underscores, otherwise one.
        """
        name = definition.name
        if name.startswith("__") and name.endswith("__"):
            return 0
        return 1

    def module_definition_reference_rank(
        self,
        definition: AnyDefinition,
        definitions: tuple[AnyDefinition, ...],
    ) -> int:
        """Return a module-level definition's reference-layer rank.

        Args:
            definition: Module-level definition whose rank is required.
            definitions: Module-level definitions establishing the graph.

        Returns:
            The name's rank, with lower ranks preceding higher ones.
        """
        return self.definition_reference_rank(
            definition,
            definitions,
            self.module_definition_references,
            self.module_definition_dependencies,
        )

    def order_definitions(
        self,
        definitions: tuple[AnyDefinition, ...],
        ranks: tuple[
            Callable[
                [AnyDefinition, tuple[AnyDefinition, ...]],
                "SupportsRichComparison",
            ],
            ...,
        ],
    ) -> list[AnyDefinition]:
        """Return definitions in stable, ascending policy-key order.

        Args:
            definitions: Definitions to sort together.
            ranks: Ranking rules applied in tuple order.

        Returns:
            A sorted list retaining original order when keys compare equal.
        """

        def sort_key(definition: AnyDefinition) -> tuple["SupportsRichComparison", ...]:
            return self.definition_sort_key(
                definition,
                definitions,
                ranks,
            )

        return sorted(
            definitions,
            key=sort_key,
        )

    def override_method_rank(
        self,
        definition: AnyDefinition,
        _definitions: tuple[AnyDefinition, ...],
    ) -> "SupportsRichComparison":
        """Rank explicitly overridden methods before other definitions.

        Args:
            definition: Definition whose decorators determine the rank.
            _definitions: Other definitions; not used by this rule.

        Returns:
            Zero if decorated with ``override``, otherwise one.
        """
        if override.__name__ in self.decorator_names(definition):
            return 0
        return 1

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

    def reverse_definition_kind_rank(
        self,
        definition: AnyDefinition,
        definitions: tuple[AnyDefinition, ...],
    ) -> int:
        """Rank classes before functions.

        Args:
            definition: Definition whose kind determines the rank.
            definitions: Other definitions, passed to ``definition_kind_rank``.

        Returns:
            Minus one for classes and zero for functions.
        """
        return -self.definition_kind_rank(definition, definitions)

    def standard_definition_ranks(
        self,
    ) -> tuple[
        Callable[[AnyDefinition, tuple[AnyDefinition, ...]], "SupportsRichComparison"],
        ...,
    ]:
        """Return the final tie-breaking policies shared by all scopes.

        Returns:
            The visibility rank followed by the name rank.
        """
        return (
            self.definition_visibility_rank,
            self.definition_name_rank,
        )

    def cls_definition_dependencies(self, definition: AnyDefinition) -> KeysView[str]:
        """Return definition-time dependencies for a class-body definition."""
        return self.definition_dependencies(definition)

    def cls_definition_references(self, definition: AnyDefinition) -> KeysView[str]:
        """Collect attributes a method loads from its first parameter or instance.

        Args:
            definition: Class-body definition whose contents to inspect.

        Returns:
            Attribute names read directly from the first positional parameter,
            from a call to it, or from a name assigned that call's result.
        """
        if not isinstance(definition, FUNC_DEFINITIONS):
            return dict.fromkeys(()).keys()
        receiver = next(
            (arg.arg for arg in (*definition.args.posonlyargs, *definition.args.args)),
            None,
        )
        instances = {
            target.id
            for node in ast.walk(definition)
            if isinstance(node, (ast.Assign, ast.AnnAssign))
            and isinstance(node.value, ast.Call)
            and isinstance(node.value.func, ast.Name)
            and node.value.func.id == receiver
            for target in (
                node.targets if isinstance(node, ast.Assign) else (node.target,)
            )
            if isinstance(target, ast.Name)
        }
        receivers = instances | {receiver}
        return dict.fromkeys(
            node.attr
            for node in ast.walk(definition)
            if isinstance(node, ast.Attribute)
            and isinstance(node.ctx, ast.Load)
            and (
                (isinstance(node.value, ast.Name) and node.value.id in receivers)
                or (
                    isinstance(node.value, ast.Call)
                    and isinstance(node.value.func, ast.Name)
                    and node.value.func.id == receiver
                )
            )
        ).keys()

    def decorator_names(self, definition: AnyDefinition) -> Iterator[str]:
        """Return the final names of plain name and attribute decorators.

        Called decorators and other expressions are ignored.

        Args:
            definition: Definition whose decorators to inspect.

        Returns:
            Names such as ``name`` for ``@name`` and ``attr`` for ``@obj.attr``.
        """
        return (
            decorator.id if isinstance(decorator, ast.Name) else decorator.attr
            for decorator in definition.decorator_list
            if isinstance(decorator, (ast.Name, ast.Attribute))
        )

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

    def definition_reference_rank(
        self,
        definition: AnyDefinition,
        definitions: tuple[AnyDefinition, ...],
        references: Callable[[AnyDefinition], KeysView[str]],
        dependencies: Callable[[AnyDefinition], KeysView[str]],
    ) -> int:
        """Return the reference-layer rank associated with a definition's name.

        Args:
            definition: Definition whose rank is required.
            definitions: Definitions that establish the reference relationships.
            references: Function to extract references from a definition.
            dependencies: Function to extract dependencies from a definition.

        Returns:
            The name's rank, with lower ranks preceding higher ones.
        """
        return self.definition_reference_ranks(
            definitions,
            references,
            dependencies,
        )[definition.name]

    def definition_sort_key(
        self,
        definition: AnyDefinition,
        definitions: tuple[AnyDefinition, ...],
        ranks: tuple[
            Callable[
                [AnyDefinition, tuple[AnyDefinition, ...]],
                "SupportsRichComparison",
            ],
            ...,
        ],
    ) -> tuple["SupportsRichComparison", ...]:
        """Return the policy values used to sort a definition.

        Args:
            definition: Definition to rank.
            definitions: All definitions participating in the sort.
            ranks: Ranking rules used to produce the key.

        Returns:
            A lexicographic key whose earlier values take precedence.
        """
        return tuple(key(definition, definitions) for key in ranks)

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

    def module_definition_dependencies(
        self,
        definition: AnyDefinition,
    ) -> KeysView[str]:
        """Return definition-time dependencies for a module-level definition."""
        return self.definition_dependencies(definition)

    def module_definition_references(self, definition: AnyDefinition) -> KeysView[str]:
        """Collect names loaded anywhere in a definition's syntax tree.

        Args:
            definition: Definition whose contents to inspect.

        Returns:
            Loaded names found anywhere in the definition's syntax tree.
        """
        return dict.fromkeys(
            node.id
            for node in ast.walk(definition)
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)
        ).keys()

    def source_placeholder(self) -> str:
        """Return a random UUID4 hex token for use as a source placeholder.

        Returns:
            A practically unique string for use as a placeholder in source code.
        """
        return uuid4().hex

    def definition_dependencies(self, definition: AnyDefinition) -> KeysView[str]:
        """Collect definition-time names, excluding annotations.

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
        dependencies: dict[str, None] = {}
        while pending:
            node = pending.pop()
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                dependencies[node.id] = None
            if isinstance(node, ast.AugAssign) and isinstance(node.target, ast.Name):
                dependencies[node.target.id] = None
            pending.extend(self.definition_dependency_children(node))
        return dependencies.keys()

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

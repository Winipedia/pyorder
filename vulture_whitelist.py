"""Explicit references for reviewed dead code false positives."""

from _typeshed import SupportsRichComparison
from pyrig_runtime.core.dependencies.subclass import DependencySubclass

from pyorder.rig.cli.subcommands import check

_COMMANDS = (check,)
_DEPENDENCY_SUBCLASS_OVERRIDES = (
    DependencySubclass.discovery_module,
    DependencySubclass.merge_key,
)
_TYPE_CHECKING = (SupportsRichComparison,)

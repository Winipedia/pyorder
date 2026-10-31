# Customize ordering with a plugin

`pyorder` uses `pyrig-runtime`'s subclass discovery system. A plugin is an
installed Python package that depends on `pyorder` and provides a subclass at
the module path corresponding to `pyorder.rig.order`. No separate registration
step is needed.

For example, to make alphabetical name ordering case-insensitive, place a
subclass in `src/example_plugin/rig/order/module.py`, where `example_plugin`
is your plugin's importable package name. Make `example_plugin`, `rig`, and
`order` importable packages with an `__init__.py` file in each directory:

```python
from typing import override

from pyorder.rig.order.module import AnyDefinition, Module as BaseModule


class Module(BaseModule):
    @override
    def definition_name_rank(
        self,
        definition: AnyDefinition,
        _definitions: tuple[AnyDefinition, ...],
    ) -> str:
        return definition.name.casefold()
```

Keep the subclass in the equivalent `rig/order` module path so discovery can find
it. Declare `pyorder` as a dependency of the plugin package and install the plugin
in the environment where `pyorder` runs. Once installed, the `pyorder check`
command uses the discovered implementation. For a local plugin, install the
project into the environment as well as installing its dependencies.

Subclass discovery imports modules in the discovery scope. Keep plugin module
imports free of unnecessary side effects. If multiple plugins override the
same method, do not rely on which implementation wins; combine behavior in a
single subclass when the order matters.

The example overrides a tie-break rule. To add or reorder policies, inspect
the inherited `module_definition_ranks` or `cls_definition_ranks` methods and
override the relevant method in the subclass. Earlier entries have higher
priority, so inserting a rule at the wrong position can make it ineffective.

For more on the runtime's discovery and subclass model, see the
[pyrig-runtime repository](https://github.com/Winipedia/pyrig-runtime) and the
[pyrig plugin guide](https://winipedia.github.io/pyrig/plugins/).

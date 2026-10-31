# Reordering examples

Each pair shows the source before ordering and the result of
`pyorder check --fix example.py`. Examples isolate a rule where possible; in
real files, the first rule that differs takes precedence. The rule sections
within each scope are listed in priority order.

## Module-level definitions

### Callers before callees

A function that calls another same-module function is placed before it:

Before:

```python
def helper():
    return 1


def caller():
    return helper()
```

After:

```python
def caller():
    return helper()


def helper():
    return 1
```

Definition-time dependencies go the other way: a base class must be defined
before the class that inherits from it. The source before ordering is valid
Python syntax, but raises `NameError` when executed because `Parent` is not
yet defined.

Before:

```python
class Child(Parent):
    pass


class Parent:
    pass
```

After:

```python
class Parent:
    pass


class Child(Parent):
    pass
```

### Functions before classes

When references and dependencies do not decide the order, module-level
functions precede classes:

Before:

```python
class Example:
    pass


def utility():
    return 1
```

After:

```python
def utility():
    return 1


class Example:
    pass
```

### Public before private

Names with fewer leading underscores come first:

Before:

```python
def _private():
    pass


def public():
    pass
```

After:

```python
def public():
    pass


def _private():
    pass
```

### Alphabetical order

Names at the same earlier priority levels are ordered alphabetically:

Before:

```python
def zebra():
    pass


def alpha():
    pass
```

After:

```python
def alpha():
    pass


def zebra():
    pass
```

## Definitions in classes

### Classes before methods

Direct nested classes precede methods:

Before:

```python
class Example:
    def run(self):
        pass

    class Nested:
        pass
```

After:

```python
class Example:
    class Nested:
        pass

    def run(self):
        pass
```

### Constructors first

The constructor hooks come first in the order they become relevant in Python's
class and instance creation process.

Before:

```python
class Example:
    def run(self):
        pass

    def __init__(self):
        pass

    def __new__(cls):
        return super().__new__(cls)

    def __init_subclass__(cls):
        pass
```

After:

```python
class Example:
    def __init_subclass__(cls):
        pass

    def __new__(cls):
        return super().__new__(cls)

    def __init__(self):
        pass

    def run(self):
        pass
```

### Abstract methods first

Methods decorated with `@abstractmethod` precede ordinary methods:

Before:

```python
from abc import ABC, abstractmethod


class Example(ABC):
    def run(self):
        pass

    @abstractmethod
    def required(self):
        pass
```

After:

```python
from abc import ABC, abstractmethod


class Example(ABC):
    @abstractmethod
    def required(self):
        pass

    def run(self):
        pass
```

### Overrides first

Methods decorated with `@override` precede methods that are not marked as
overrides:

Before:

```python
from typing import override


class Base:
    def inherited_method(self):
        pass


class Example(Base):
    def run(self):
        pass

    @override
    def inherited_method(self):
        pass
```

After:

```python
from typing import override


class Base:
    def inherited_method(self):
        pass


class Example(Base):
    @override
    def inherited_method(self):
        pass

    def run(self):
        pass
```

### Special methods first

Dunder-named methods precede ordinary methods:

Before:

```python
class Example:
    def run(self):
        pass

    def __repr__(self):
        pass
```

After:

```python
class Example:
    def __repr__(self):
        pass

    def run(self):
        pass
```

### Class methods first

Methods decorated with `@classmethod` precede other methods:

Before:

```python
class Example:
    def run(self):
        pass

    @classmethod
    def create(cls):
        pass
```

After:

```python
class Example:
    @classmethod
    def create(cls):
        pass

    def run(self):
        pass
```

### Callers before callees

For methods, the tool uses attribute reads through the first parameter (usually
`self` or `cls`) to find references:

Before:

```python
class Example:
    def helper(self):
        return 1

    def run(self):
        return self.helper()
```

After:

```python
class Example:
    def run(self):
        return self.helper()

    def helper(self):
        return 1
```

### Public before private

This visibility rule also applies to methods and nested classes:

Before:

```python
class Example:
    def _helper(self):
        pass

    def run(self):
        pass
```

After:

```python
class Example:
    def run(self):
        pass

    def _helper(self):
        pass
```

### Alphabetical order

Methods at the same earlier priority levels are ordered alphabetically:

Before:

```python
class Example:
    def zebra(self):
        pass

    def alpha(self):
        pass
```

After:

```python
class Example:
    def alpha(self):
        pass

    def zebra(self):
        pass
```

## Edge cases

### Annotations are not runtime dependencies

Annotations are not considered definition-time dependencies because quoting them
or using `from __future__ import annotations` prevents them from being evaluated
at definition time. Unquoted annotations still count as references.

Before:

```python
from __future__ import annotations


def alpha():
    pass


def zebra(value: alpha):
    pass
```

After:

```python
from __future__ import annotations


def zebra(value: alpha):
    pass


def alpha():
    pass
```

Quoting the annotation as `"alpha"` removes this reference from the AST, so
alphabetical ordering would place `alpha` first instead.

### Non-definition statements stay in place

Calls are not reordered, even when definitions move around them. In this
example, ordering moves `zebra` below the module-level call to it. The result
is valid syntax but raises `NameError` when executed:

Before:

```python
def zebra():
    return 1


zebra()


def caller():
    return zebra()
```

After:

```python
def caller():
    return zebra()


zebra()


def zebra():
    return 1
```

Review fixed files and run your normal tests; `--fix` does not verify runtime
behavior. It merely switches definitions around to order them according to the rules.

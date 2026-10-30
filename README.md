# pyorder

[![pyorder](docs/assets/banner.svg)](docs/assets/banner.svg)

<!-- project-status -->
[![CI](https://img.shields.io/github/actions/workflow/status/Winipedia/pyorder/health_check.yml?label=CI&logo=github)](https://github.com/Winipedia/pyorder/actions/workflows/health_check.yml)
[![CD](https://img.shields.io/github/actions/workflow/status/Winipedia/pyorder/release.yml?label=CD&logo=github)](https://github.com/Winipedia/pyorder/actions/workflows/release.yml)
[![ProjectTester](https://codecov.io/gh/Winipedia/pyorder/branch/main/graph/badge.svg)](https://codecov.io/gh/Winipedia/pyorder)
<!-- code-quality -->
[![ByteOrderMarkerFormatter](https://img.shields.io/badge/BOM-fix--byte--order--marker-orange)](https://prek.j178.dev/reference/built-in-hooks/#fix-byte-order-marker)
[![CICDLinter](https://img.shields.io/badge/CI/CD-actionlint-blue)](https://github.com/rhysd/actionlint)
[![CICDSecurityChecker](https://img.shields.io/badge/%F0%9F%8C%88-zizmor-white?labelColor=white)](https://github.com/zizmorcore/zizmor)
[![CaseConflictChecker](https://img.shields.io/badge/case--conflict-check--case--conflict-blue)](https://prek.j178.dev/reference/built-in-hooks/#check-case-conflict)
[![DeadCodeChecker](https://img.shields.io/badge/dead--code-vulture-blue)](https://github.com/jendrikseipp/vulture)
[![DependencyChecker](https://img.shields.io/badge/dependencies-deptry-blue)](https://github.com/osprey-oss/deptry)
[![EndOfFileFormatter](https://img.shields.io/badge/EOF-end--of--file--fixer-orange)](https://prek.j178.dev/reference/built-in-hooks/#end-of-file-fixer)
[![EndOfLineFormatter](https://img.shields.io/badge/EOL-mixed--line--ending-orange)](https://prek.j178.dev/reference/built-in-hooks/#mixed-line-ending)
[![JSONFormatter](https://img.shields.io/badge/JSON-pretty--format--json-orange)](https://prek.j178.dev/reference/built-in-hooks/#pretty-format-json)
[![JSONLinter](https://img.shields.io/badge/JSON-check--json-blue)](https://prek.j178.dev/reference/built-in-hooks/#check-json)
[![LargeFileChecker](https://img.shields.io/badge/large--files-check--added--large--files-blue)](https://prek.j178.dev/reference/built-in-hooks/#check-added-large-files)
[![MarkdownLinter](https://img.shields.io/badge/Markdown-rumdl-darkgreen)](https://github.com/rvben/rumdl)
[![MergeConflictChecker](https://img.shields.io/badge/merge--conflict-check--merge--conflict-blue)](https://prek.j178.dev/reference/built-in-hooks/#check-merge-conflict)
[![ModuleTestNamingChecker](https://img.shields.io/badge/test--naming-name--tests--test-blue)](https://github.com/pre-commit/pre-commit-hooks#name-tests-test)
[![PythonLinter](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![PythonOrderLinter](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/Winipedia/pyorder/main/docs/assets/badge.json)](https://github.com/Winipedia/pyorder)
[![SecretsChecker](https://img.shields.io/badge/secrets-detect--secrets-blue)](https://github.com/Yelp/detect-secrets)
[![SecurityChecker](https://img.shields.io/badge/security-bandit-yellow.svg)](https://github.com/PyCQA/bandit)
[![ShellFormatter](https://img.shields.io/badge/shell-shfmt-orange)](https://github.com/mvdan/sh)
[![ShellLinter](https://img.shields.io/badge/shell-shellcheck-blue)](https://github.com/koalaman/shellcheck)
[![SpellChecker](https://img.shields.io/badge/spell--check-typos-blue)](https://github.com/crate-ci/typos)
[![TOMLLinter](https://img.shields.io/badge/TOML-tombi-blueviolet)](https://github.com/tombi-toml/tombi)
[![TrailingWhitespaceFormatter](https://img.shields.io/badge/whitespace-trailing--whitespace-orange)](https://prek.j178.dev/reference/built-in-hooks/#trailing-whitespace)
[![TypeChecker](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ty/main/assets/badge/v0.json)](https://github.com/astral-sh/ty)
[![XMLLinter](https://img.shields.io/badge/XML-check--xml-blue)](https://prek.j178.dev/reference/built-in-hooks/#check-xml)
[![YAMLLinter](https://img.shields.io/badge/YAML-ryl-red)](https://github.com/owenlamont/ryl)
<!-- tooling -->
[![PackageManager](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Pyrigger](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/Winipedia/pyrig/main/docs/assets/badge.json)](https://github.com/Winipedia/pyrig)
[![RemoteVersionController](https://img.shields.io/github/stars/Winipedia/pyorder?style=social)](https://github.com/Winipedia/pyorder)
[![VersionControlHookManager](https://raw.githubusercontent.com/j178/prek/master/docs/assets/badge.svg)](https://github.com/j178/prek)
[![VersionController](https://img.shields.io/badge/Git-F05032?logo=git&logoColor=white)](https://git-scm.com)
<!-- project-info -->
[![DocsBuilder](https://img.shields.io/badge/Documentation-zensical-326CE5)](https://Winipedia.github.io/pyorder)
[![PackageIndex](https://img.shields.io/pypi/v/pyorder?logo=pypi&logoColor=white)](https://pypi.org/project/pyorder)
[![ProgrammingLanguage](https://img.shields.io/pypi/pyversions/pyorder)](https://www.python.org)
[![License](https://img.shields.io/github/license/Winipedia/pyorder)](https://github.com/Winipedia/pyorder/blob/main/LICENSE)

---

> A Python source code ordering linter.

---

## Overview

`pyorder` is a development tool built on the `ast` library for ordering Python
source code according to specified rules and conventions. Specifically, it is
designed to order definitions within a Python module. It does not attempt to order
everything in a source file, like attributes or statements outside of definitions.
`pyorder` focuses on ordering Python code according to best practices regarding
readability of Python code.

## Usage

```bash
# install pyorder as a development dependency
uv add pyorder --dev
# check Python files
uv run pyorder path/to/your/file1.py path/to/your/file2.py
# fix Python files
uv run pyorder --fix path/to/your/file1.py path/to/your/file2.py
```

The `--fix` option will modify all files that are not ordered according to the rules.
Although `pyorder` attempts to respect valid Python syntax, it does NOT guarantee
valid Python syntax or that no logical errors will be introduced after reordering.
It simply reorders the definitions according to the rules. Run `pyorder` without
the `--fix` option first to see the diff output of files that would be modified.
Please check all modified files after fixing to ensure that your code is correct.

## What exactly is being ordered

`pyorder` parses a given file as an abstract syntax tree (AST) and considers the
following types of definitions within a Python module:

- Module-level definitions, specifically instances of `ast.FunctionDef`, `ast.AsyncFunctionDef`
and `ast.ClassDef`
- Module-level class definitions, specifically instances of `ast.ClassDef`, `ast.FunctionDef`,
and `ast.AsyncFunctionDef`

## Ordering Rules

`pyorder` enforces the rules on two levels, module-level definitions and
class-level definitions of module-level classes.
The listed rules below are applied as a sorting key in that priority order within
each level of definitions.

### Module-level definitions

- callers-before-callees: a definition that calls another definition appears
before that definition (excluded are hard dependencies that are needed at definition
time, e.g. base classes, arg/kwargs defaults, or decorators).
- functions-before-classes: functions should be defined before classes within
the module.
- visibility-ordering: public before private definitions (e.g.,
`public`, `_private`, `__more_private`)
- alphabetical-ordering: definitions are ordered alphabetically.

### Class-level definitions

- classes-before-methods: nested classes should be defined before methods.
- constructor-first: Constructor methods (e.g., `__new__`, `__init__`) should be
defined before other methods.
- abstract-first: methods decorated with `@abstractmethod` should be defined
before other methods.
- overrides-first: methods decorated with `@override` should be defined before
other methods.
- special-methods-first: special methods (e.g., `__str__`, `__repr__`) should be
defined before other methods.
- classmethods-first: methods decorated with `@classmethod` should be defined
before other methods.
- callers-before-callees: a definition that calls another definition should be defined
before that definition (excluded are hard dependencies that are needed at definition
time, e.g. base classes, arg/kwargs defaults, or decorators).
- visibility-ordering: public before private definitions (e.g., `public`,
`_private`, `__more_private`) within the class.
- alphabetical-ordering: definitions are ordered alphabetically within the class.

## Customization

`pyorder` does not support inline comments like `# noqa`. The missing support for
inline comments is intentional and is part of this tool's philosophy of enforcing
a consistent ordering of Python source code.However `pyorder` is built on [`pyrig-runtime`](https://github.com/Winipedia/pyrig-runtime).
Therefore customization can be done by writing a plugin. [`pyrig`](https://github.com/Winipedia/pyrig)
is another tool built on `pyrig-runtime` and describes [how to write a plugin](https://winipedia.github.io/pyrig/plugins/)
based on the system of `pyrig-runtime` subclasses.

## Documentation

Please refer to the [official documentation](https://winipedia.github.io/pyorder/) for more details and examples.

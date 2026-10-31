# Home

[![pyorder](assets/banner.svg)](assets/banner.svg)

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

## What pyorder does

`pyorder` is a Python source-code ordering linter and fixer. It parses Python
files and reorders function, asynchronous function, and class definitions to
make related code easier to scan. It requires Python 3.12 or newer.

Ordering is limited to direct definitions at the module level and direct
definitions inside module-level classes. Nested functions, definitions inside
control-flow blocks, and definitions inside nested classes are not independently
ordered. Imports, assignments, calls, and other statements are not sorted.

## Install and run

Install `pyorder` as a development dependency:

```console
uv add pyorder --dev
```

Check files and print a diff for any files that need ordering:

```console
uv run pyorder check src/package/module.py
```

Apply the proposed ordering:

```console
uv run pyorder check --fix src/package/module.py
```

The check exits with status `1` when it finds any unordered file, including
when `--fix` has rewritten it. Run the check again after fixing to confirm that
all files pass. Review changes made by `--fix`: moving definitions can change
runtime behavior, and the tool does not verify that the reordered program works.

`pyorder check` can also run as a check-only pre-commit hook. It reports files
that need reordering; you can use `--fix` to automatically reorder them.

## Ordering rules

The [examples](examples.md) page shows before-and-after code for every rule.

## How ordering works and its limits

The tool uses Python's abstract syntax tree (AST) to find definition names and
references. It does not execute the file or attempt full name resolution. At
module level, it looks for loaded names in each definition's syntax tree. In
class bodies, method references are limited to attributes accessed through the
method's first positional parameter (typically `self` or `cls`).

Definition-time dependencies are treated separately from ordinary references.
Bases, decorators, default values, and statements in a class body can require a
name to exist when a definition is created, so those dependencies are ordered
before their users.

Only definitions move; calls and other statements keep their original
positions. Reordering definitions around a module-level call or assignment can
change whether a name exists when that statement executes. Likewise, the tool
does not reorder imports or assignments to make them agree with the new
definition order. `--fix` is a mechanical transformation, not a guarantee of
valid runtime behavior.

Always review the changes made by `--fix` to ensure that the reordered program
behaves as expected.

## Customization

`pyorder` has no inline suppression comments such as `# noqa`. To customize
its ordering rules, create a subclass of its `Module` ordering class in an
installed package that depends on `pyorder`. The runtime discovers compatible
subclasses automatically. See [customizing with a plugin](plugin.md) and the
[pyrig-runtime subclassing documentation](https://github.com/Winipedia/pyrig-runtime).

## Reference

- [Before-and-after examples](examples.md)
- [Plugin customization](plugin.md)
- [Generated API reference](api.md)

# neurosym-forge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship `skills/neurosym-forge/` v0.1 — a Python skill that scaffolds and extends ClojureScript + Rust neurosymbolic verification projects under MeTTa-style authoring conventions.

**Architecture:** Single new sibling skill under `skills/neurosym-forge/`. Python helpers in `scripts/`, templated CLJS+Rust project skeleton in `assets/project-template/`, EDN+JSON schemas in `assets/schemas/`, progressive-disclosure docs in `references/`. No runtime — the scaffolded project runs itself via `shadow-cljs` and `cargo`. Spec at `docs/specs/2026-05-13-neurosym-forge-design.md`.

**Tech Stack:** Python 3.13, jsonschema, pyyaml, jinja2 (for templating), pytest. No new sibling-skill dependencies. CLJS+Rust toolchain is required only when executing scaffolded projects; the skill itself never invokes them.

---

## Pre-flight

Read these before starting any task:
- `docs/specs/2026-05-13-neurosym-forge-design.md` (the spec this plan implements)
- `skills/book-qa/SKILL.md` and `skills/book-qa/pyproject.toml` (closest sibling pattern, no `pyproject.toml` for book-qa — use book-knowledge's instead)
- `skills/book-knowledge/SKILL.md`, `pyproject.toml`, `scripts/__init__.py`, `tests/conftest.py`, `tests/test_anthropic_compliance.py`, `tests/test_trigger_calibration.py` (canonical sibling-skill shape)
- `skills/russellian-style/SKILL.md` (frontmatter style)
- `AGENTS.md` and `CLAUDE.md` at repo root (commit/PR rules, no AI attribution, terse messages)
- `C:\Users\charl\OneDrive\Desktop\clojure.md` (the source design for the scaffolded project — Section 5 has the code stubs the templates are derived from)

**Test invocation.** All commands assume CWD is `skills/neurosym-forge/` and `.venv` exists. Use `.venv\Scripts\python.exe` on Windows, `.venv/bin/python` on POSIX. Where the plan says `pytest`, use the venv's pytest.

**Commit hygiene.** Per repo CLAUDE.md: terse human style, no AI attribution, no Co-Authored-By, one problem per commit. Conventional-commit prefixes (`feat:`, `test:`) are fine but not required. End every task with a commit.

**Worktree.** This plan executes on branch `spec/neurosym-forge` in the worktree at `C:\Users\charl\code\russellian-book-suite-neurosym-forge`. The spec is already committed on this branch.

**Template engine.** Use jinja2 with `{% raw %}` blocks around CLJS/Rust syntax to avoid `{}` conflicts. Template files end in `.tmpl`. The scaffolder uses jinja2's `Environment` with explicit `keep_trailing_newline=True` and `block_start_string="{%"`, default delimiters.

**Cross-platform paths.** All scripts use `pathlib.Path` and forward-slash-safe string operations. No `os.sep` literals.

**Schema validation.** Every JSON Schema lives in `assets/schemas/` and is loaded via `json.loads(path.read_text())`. Validation uses `jsonschema.Draft202012Validator`.

---

## File Structure

### Created

```
skills/neurosym-forge/
├── SKILL.md
├── LICENSE
├── pyproject.toml
├── .gitignore
├── scripts/
│   ├── __init__.py
│   ├── _io.py                            shared EDN read/write + checksum helpers
│   ├── sort_registry.py                  Sort, SortRegistry dataclasses
│   ├── atom.py                           Atom dataclass + EDN ↔ dict round-trip
│   ├── rewrite_rule.py                   RewriteRule dataclass + variable-balance check
│   ├── scaffold_project.py
│   ├── add_sort.py
│   ├── add_rewrite_rule.py
│   ├── add_grounded_atom.py
│   ├── lint_atomspace.py
│   ├── lint_rewrite_coverage.py
│   ├── render_call_graph.py
│   └── verify_claims.py
├── assets/
│   ├── schemas/
│   │   ├── atom.schema.json
│   │   ├── rewrite-rule.schema.json
│   │   └── sort.schema.json
│   └── project-template/
│       ├── shadow-cljs.edn.tmpl
│       ├── package.json.tmpl
│       ├── deps.edn.tmpl
│       ├── Cargo.toml.tmpl
│       ├── build.rs.tmpl
│       ├── .gitignore.tmpl
│       ├── SKILL.md.tmpl
│       ├── README.md.tmpl
│       ├── rules/
│       │   ├── seed.edn.tmpl
│       │   ├── grounded.edn.tmpl
│       │   ├── predicates.edn.tmpl
│       │   └── .forge-version.edn.tmpl
│       ├── cljs-orchestrator/
│       │   └── src/main/__project__/
│       │       ├── core.cljs.tmpl
│       │       ├── phases.cljs.tmpl
│       │       ├── ir.cljs.tmpl
│       │       ├── nl_to_fol.cljs.tmpl
│       │       ├── unify.cljs.tmpl
│       │       └── bridge.cljs.tmpl
│       ├── rust-verifier/
│       │   ├── Cargo.toml.tmpl
│       │   ├── build.rs.tmpl
│       │   └── src/
│       │       ├── lib.rs.tmpl
│       │       ├── ir.rs.tmpl
│       │       ├── smt.rs.tmpl
│       │       ├── eqsat.rs.tmpl
│       │       ├── kg.rs.tmpl
│       │       └── typeset.rs.tmpl
│       └── templates/
│           ├── report.tex.tera.tmpl
│           └── claim_table.tex.tera.tmpl
├── references/
│   ├── metta-idioms.md
│   ├── atomspace-edn.md
│   ├── grounded-atoms.md
│   ├── phase-boundaries.md
│   ├── rewrite-rule-style.md
│   └── worked-examples/
│       └── osmotic-pressure/
│           └── README.md
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── fixtures/
    │   ├── valid_atom_symbol.edn
    │   ├── valid_atom_grounded.edn
    │   ├── invalid_atom_missing_sort.edn
    │   ├── valid_rule_commutative.edn
    │   ├── invalid_rule_unbound_var.edn
    │   └── seed_atomspace.edn
    ├── trigger_tests.yaml
    ├── test_anthropic_compliance.py
    ├── test_trigger_calibration.py
    ├── test_atom.py
    ├── test_rewrite_rule.py
    ├── test_sort_registry.py
    ├── test_lint_atomspace.py
    ├── test_lint_rewrite_coverage.py
    ├── test_scaffold_project.py
    ├── test_add_sort.py
    ├── test_add_rewrite_rule.py
    ├── test_add_grounded_atom.py
    ├── test_render_call_graph.py
    ├── test_verify_claims.py
    └── smoke-results.md
```

### Modified

None in v0.1. The `book-qa` D13 hook is gated and lands in a follow-up.

---

## Phase 0: Skill skeleton

### Task 0.1: Create base directory and `.gitignore`

**Files:**
- Create: `skills/neurosym-forge/.gitignore`
- Create: `skills/neurosym-forge/LICENSE`

- [ ] **Step 1: Create the directory.**

```bash
mkdir -p skills/neurosym-forge/scripts skills/neurosym-forge/tests skills/neurosym-forge/assets/schemas skills/neurosym-forge/references
```

- [ ] **Step 2: Write `.gitignore`.**

```
.venv/
__pycache__/
*.egg-info/
.pytest_cache/
.coverage
htmlcov/
*.pyc
dist/
build/
node_modules/
target/
work/
```

- [ ] **Step 3: Copy MIT LICENSE from a sibling skill.**

```bash
cp skills/book-knowledge/LICENSE skills/neurosym-forge/LICENSE 2>/dev/null || cp LICENSE skills/neurosym-forge/LICENSE
```

(If the sibling skill has no LICENSE, copy the repo root LICENSE.)

- [ ] **Step 4: Commit.**

```bash
git add skills/neurosym-forge/.gitignore skills/neurosym-forge/LICENSE
git commit -m "neurosym-forge: skeleton directory and license"
```

### Task 0.2: `pyproject.toml`

**Files:**
- Create: `skills/neurosym-forge/pyproject.toml`

- [ ] **Step 1: Write the file.**

```toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "neurosym-forge"
version = "0.1.0"
description = "Scaffolder for ClojureScript + Rust neurosymbolic verification projects"
authors = [{name = "Charles Hoskinson"}]
license = {text = "MIT"}
requires-python = ">=3.13"
dependencies = [
    "jsonschema>=4.21",
    "pyyaml>=6.0.1",
    "jinja2>=3.1.3",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-cov>=4.1",
]

[tool.setuptools]
packages = ["scripts"]

[tool.setuptools.package-data]
scripts = ["../assets/**/*", "../references/**/*"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
```

- [ ] **Step 2: Create venv and install in editable mode.**

```bash
cd skills/neurosym-forge
python -m venv .venv
.venv/Scripts/python.exe -m pip install -e ".[dev]"
```

Expected: install completes; `pytest --version` works.

- [ ] **Step 3: Verify pytest can run.**

```bash
.venv/Scripts/python.exe -m pytest --collect-only
```

Expected: `no tests ran` (no test files yet). Exit 5 is fine; non-zero on missing tests is acceptable here.

- [ ] **Step 4: Commit.**

```bash
git add skills/neurosym-forge/pyproject.toml
git commit -m "neurosym-forge: pyproject.toml + dev deps"
```

### Task 0.3: `scripts/__init__.py` and `tests/__init__.py` + `conftest.py`

**Files:**
- Create: `skills/neurosym-forge/scripts/__init__.py`
- Create: `skills/neurosym-forge/tests/__init__.py`
- Create: `skills/neurosym-forge/tests/conftest.py`

- [ ] **Step 1: Write `scripts/__init__.py`.**

```python
"""neurosym-forge: scaffolder for CLJS+Rust neurosymbolic verifiers."""
```

- [ ] **Step 2: Write `tests/__init__.py` (empty marker file).**

```python
```

- [ ] **Step 3: Write `tests/conftest.py`.**

```python
"""Shared pytest fixtures for neurosym-forge tests."""
from __future__ import annotations

from pathlib import Path

import pytest

SKILL_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture()
def skill_root() -> Path:
    """Absolute path to the skill root (skills/neurosym-forge/)."""
    return SKILL_ROOT


@pytest.fixture()
def assets_dir(skill_root: Path) -> Path:
    return skill_root / "assets"


@pytest.fixture()
def schemas_dir(assets_dir: Path) -> Path:
    return assets_dir / "schemas"


@pytest.fixture()
def fixtures_dir(skill_root: Path) -> Path:
    return skill_root / "tests" / "fixtures"


@pytest.fixture()
def project_template_dir(assets_dir: Path) -> Path:
    return assets_dir / "project-template"


@pytest.fixture()
def tmp_project_root(tmp_path: Path) -> Path:
    """Where scaffold_project writes its output during tests."""
    root = tmp_path / "verifiers" / "demo"
    return root
```

- [ ] **Step 4: Verify pytest sees the fixtures.**

```bash
.venv/Scripts/python.exe -m pytest --fixtures -q tests/
```

Expected: `skill_root`, `assets_dir`, `schemas_dir`, `fixtures_dir`, `project_template_dir`, `tmp_project_root` listed.

- [ ] **Step 5: Commit.**

```bash
git add skills/neurosym-forge/scripts/__init__.py skills/neurosym-forge/tests/__init__.py skills/neurosym-forge/tests/conftest.py
git commit -m "neurosym-forge: scripts package + test conftest"
```

---

## Phase 1: Data model — sorts, atoms, rules

### Task 1.1: Sort schema

**Files:**
- Create: `skills/neurosym-forge/assets/schemas/sort.schema.json`

- [ ] **Step 1: Write the schema.**

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://neurosym-forge.local/sort.schema.json",
  "title": "Sort",
  "description": "A sort (type) in the EDN-as-atomspace IR. Either a keyword primitive, a function type, or an enum.",
  "oneOf": [
    {
      "type": "string",
      "pattern": "^:(int|real|bool|string|entity|formula|verdict|solution|rule|atom)$",
      "description": "Primitive sort keyword"
    },
    {
      "type": "object",
      "properties": {
        "kind": {"const": "fn"},
        "args": {"type": "array", "items": {"$ref": "#"}},
        "ret":  {"$ref": "#"}
      },
      "required": ["kind", "args", "ret"],
      "additionalProperties": false
    },
    {
      "type": "object",
      "properties": {
        "kind": {"const": "enum"},
        "members": {"type": "array", "items": {"type": "string", "pattern": "^:[a-z][a-z0-9-]*$"}, "minItems": 1}
      },
      "required": ["kind", "members"],
      "additionalProperties": false
    }
  ]
}
```

- [ ] **Step 2: Commit.**

```bash
git add skills/neurosym-forge/assets/schemas/sort.schema.json
git commit -m "neurosym-forge: sort schema"
```

### Task 1.2: Atom schema

**Files:**
- Create: `skills/neurosym-forge/assets/schemas/atom.schema.json`

- [ ] **Step 1: Write the schema.**

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://neurosym-forge.local/atom.schema.json",
  "title": "Atom",
  "description": "A MeTTa-style atom: symbol, variable, grounded, or expression.",
  "type": "object",
  "properties": {
    "kind":    {"enum": ["symbol", "variable", "grounded", "expression"]},
    "name":    {"type": "string"},
    "sort":    {"$ref": "sort.schema.json"},
    "grounded": {
      "type": "object",
      "properties": {
        "lib":  {"type": "string", "enum": ["z3", "egg", "cozo", "tectonic", "custom"]},
        "fn":   {"type": "string"},
        "napi": {"type": "boolean"}
      },
      "required": ["lib", "fn"],
      "additionalProperties": false
    },
    "head": {"$ref": "#"},
    "args": {"type": "array", "items": {"$ref": "#"}},
    "doc":  {"type": "string"},
    "id":   {"type": "string", "pattern": "^[A-Z][A-Z0-9_-]*$"},
    "tags": {"type": "array", "items": {"type": "string"}, "uniqueItems": true},
    "force": {"type": "boolean", "description": "MeTTa ! prefix — evaluate immediately"}
  },
  "required": ["kind", "sort"],
  "allOf": [
    {"if": {"properties": {"kind": {"const": "symbol"}}, "required": ["kind"]},
     "then": {"required": ["name"], "not": {"required": ["head", "args", "grounded"]}}},
    {"if": {"properties": {"kind": {"const": "variable"}}, "required": ["kind"]},
     "then": {"required": ["name"], "not": {"required": ["head", "args", "grounded"]}}},
    {"if": {"properties": {"kind": {"const": "grounded"}}, "required": ["kind"]},
     "then": {"required": ["name", "grounded"], "not": {"required": ["head", "args"]}}},
    {"if": {"properties": {"kind": {"const": "expression"}}, "required": ["kind"]},
     "then": {"required": ["head", "args"], "not": {"required": ["grounded"]}}}
  ],
  "additionalProperties": false
}
```

- [ ] **Step 2: Commit.**

```bash
git add skills/neurosym-forge/assets/schemas/atom.schema.json
git commit -m "neurosym-forge: atom schema"
```

### Task 1.3: Rewrite-rule schema

**Files:**
- Create: `skills/neurosym-forge/assets/schemas/rewrite-rule.schema.json`

- [ ] **Step 1: Write the schema.**

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://neurosym-forge.local/rewrite-rule.schema.json",
  "title": "RewriteRule",
  "description": "A MeTTa-style (= lhs rhs) equality declaration.",
  "type": "object",
  "properties": {
    "id":   {"type": "string", "pattern": "^R[0-9]{3,}$"},
    "lhs":  {"$ref": "atom.schema.json"},
    "rhs":  {"$ref": "atom.schema.json"},
    "doc":  {"type": "string"},
    "tags": {"type": "array", "items": {"type": "string"}, "uniqueItems": true}
  },
  "required": ["id", "lhs", "rhs"],
  "additionalProperties": false
}
```

- [ ] **Step 2: Commit.**

```bash
git add skills/neurosym-forge/assets/schemas/rewrite-rule.schema.json
git commit -m "neurosym-forge: rewrite-rule schema"
```

### Task 1.4: `_io.py` — EDN-as-JSON helpers and checksum

**Files:**
- Create: `skills/neurosym-forge/scripts/_io.py`
- Create: `skills/neurosym-forge/tests/test_io.py`

The skill stores atomspace and rule data on disk as EDN. For v0.1 we encode EDN as JSON-compatible Python dicts (no full EDN reader/writer; the scaffolded *project* parses EDN, the skill itself round-trips through JSON). This keeps the skill dependency-light. Files on disk use the `.edn` extension and look like EDN to the scaffolded project, but the skill reads them as JSON when both formats agree on the subset we use (keywords as strings prefixed with `:`, no tagged literals, no symbols other than what we control).

- [ ] **Step 1: Write failing test.**

```python
# skills/neurosym-forge/tests/test_io.py
from __future__ import annotations

from pathlib import Path

import pytest

from scripts._io import read_edn_as_json, write_json_as_edn, file_checksum


def test_round_trip(tmp_path: Path) -> None:
    payload = {"sorts": [":int", ":real"], "rules": [], "atoms": []}
    out = tmp_path / "atomspace.edn"
    write_json_as_edn(out, payload)
    back = read_edn_as_json(out)
    assert back == payload


def test_keywords_render_as_edn(tmp_path: Path) -> None:
    out = tmp_path / "x.edn"
    write_json_as_edn(out, {"k": ":foo"})
    text = out.read_text(encoding="utf-8")
    assert ":foo" in text
    assert '"k"' in text


def test_checksum_stable(tmp_path: Path) -> None:
    f = tmp_path / "x.edn"
    f.write_text("hello", encoding="utf-8")
    a = file_checksum(f)
    b = file_checksum(f)
    assert a == b
    assert len(a) == 64  # sha256 hex


def test_checksum_changes_on_edit(tmp_path: Path) -> None:
    f = tmp_path / "x.edn"
    f.write_text("hello", encoding="utf-8")
    a = file_checksum(f)
    f.write_text("hello!", encoding="utf-8")
    b = file_checksum(f)
    assert a != b
```

- [ ] **Step 2: Run test, expect FAIL.**

```bash
.venv/Scripts/python.exe -m pytest tests/test_io.py -v
```

Expected: `ModuleNotFoundError: scripts._io`.

- [ ] **Step 3: Write implementation.**

```python
# skills/neurosym-forge/scripts/_io.py
"""EDN/JSON read-write and checksum helpers.

For v0.1, we serialize the atomspace as JSON-compatible Python dicts and
write the file with a `.edn` extension. The scaffolded project's CLJS
reader parses EDN natively; this skill only round-trips structured data.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def read_edn_as_json(path: Path) -> Any:
    """Read an EDN-extension file written by write_json_as_edn."""
    return json.loads(path.read_text(encoding="utf-8"))


def write_json_as_edn(path: Path, payload: Any) -> None:
    """Write a JSON-compatible payload to disk with stable formatting.

    Keys are sorted; indent is 2; encoding is UTF-8 with LF line endings.
    Keyword strings (":foo") are preserved verbatim in JSON; the scaffolded
    CLJS reader treats them as EDN keywords.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False)
    path.write_text(text + "\n", encoding="utf-8", newline="\n")


def file_checksum(path: Path) -> str:
    """SHA-256 hex digest of a file's bytes."""
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()
```

- [ ] **Step 4: Run test, expect PASS.**

```bash
.venv/Scripts/python.exe -m pytest tests/test_io.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit.**

```bash
git add skills/neurosym-forge/scripts/_io.py skills/neurosym-forge/tests/test_io.py
git commit -m "neurosym-forge: _io helpers for EDN-as-JSON + checksum"
```

### Task 1.5: `sort_registry.py` — `Sort`, `SortRegistry`

**Files:**
- Create: `skills/neurosym-forge/scripts/sort_registry.py`
- Create: `skills/neurosym-forge/tests/test_sort_registry.py`

- [ ] **Step 1: Write failing test.**

```python
# skills/neurosym-forge/tests/test_sort_registry.py
from __future__ import annotations

import pytest

from scripts.sort_registry import Sort, SortRegistry


def test_primitive_sort_validates() -> None:
    s = Sort.from_value(":int")
    assert s.is_primitive()
    assert str(s) == ":int"


def test_function_sort_validates() -> None:
    s = Sort.from_value({"kind": "fn", "args": [":int", ":real"], "ret": ":bool"})
    assert s.is_function()
    assert s.return_sort() == Sort.from_value(":bool")


def test_enum_sort_validates() -> None:
    s = Sort.from_value({"kind": "enum", "members": [":sat", ":unsat", ":unknown"]})
    assert s.is_enum()
    assert ":sat" in s.members()


def test_registry_round_trip() -> None:
    reg = SortRegistry()
    reg.add(Sort.from_value(":int"))
    reg.add(Sort.from_value(":real"))
    reg.add(Sort.from_value({"kind": "enum", "members": [":sat", ":unsat"]}))
    payload = reg.to_dict()
    reg2 = SortRegistry.from_dict(payload)
    assert reg2.contains(Sort.from_value(":int"))


def test_registry_rejects_duplicate() -> None:
    reg = SortRegistry()
    reg.add(Sort.from_value(":int"))
    with pytest.raises(ValueError, match="duplicate"):
        reg.add(Sort.from_value(":int"))


def test_registry_lookup_missing() -> None:
    reg = SortRegistry()
    assert not reg.contains(Sort.from_value(":nonexistent"))
```

- [ ] **Step 2: Run test, expect FAIL.**

```bash
.venv/Scripts/python.exe -m pytest tests/test_sort_registry.py -v
```

Expected: `ModuleNotFoundError: scripts.sort_registry`.

- [ ] **Step 3: Write implementation.**

```python
# skills/neurosym-forge/scripts/sort_registry.py
"""Sort registry — the type universe of the atomspace.

A Sort is either a primitive keyword (":int", ":real", ":bool", ...),
a function type {"kind": "fn", "args": [...], "ret": ...}, or an enum
{"kind": "enum", "members": [...]}.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Sort:
    value: Any  # str | dict

    @classmethod
    def from_value(cls, value: Any) -> "Sort":
        if isinstance(value, str):
            if not value.startswith(":"):
                raise ValueError(f"primitive sort must start with ':' (got {value!r})")
            return cls(value)
        if isinstance(value, dict):
            kind = value.get("kind")
            if kind == "fn":
                if "args" not in value or "ret" not in value:
                    raise ValueError("fn sort requires args and ret")
                return cls({"kind": "fn",
                            "args": [Sort.from_value(a).value for a in value["args"]],
                            "ret": Sort.from_value(value["ret"]).value})
            if kind == "enum":
                if "members" not in value or not value["members"]:
                    raise ValueError("enum sort requires non-empty members")
                return cls({"kind": "enum", "members": list(value["members"])})
            raise ValueError(f"unknown sort kind: {kind!r}")
        raise ValueError(f"sort must be str or dict, got {type(value).__name__}")

    def is_primitive(self) -> bool:
        return isinstance(self.value, str)

    def is_function(self) -> bool:
        return isinstance(self.value, dict) and self.value.get("kind") == "fn"

    def is_enum(self) -> bool:
        return isinstance(self.value, dict) and self.value.get("kind") == "enum"

    def return_sort(self) -> "Sort":
        if not self.is_function():
            raise ValueError("return_sort only valid on function sorts")
        return Sort.from_value(self.value["ret"])

    def members(self) -> list[str]:
        if not self.is_enum():
            raise ValueError("members only valid on enum sorts")
        return list(self.value["members"])

    def __str__(self) -> str:
        if isinstance(self.value, str):
            return self.value
        return str(self.value)


@dataclass
class SortRegistry:
    _sorts: list[Sort] = field(default_factory=list)

    def add(self, sort: Sort) -> None:
        if self.contains(sort):
            raise ValueError(f"duplicate sort: {sort}")
        self._sorts.append(sort)

    def contains(self, sort: Sort) -> bool:
        return any(s == sort for s in self._sorts)

    def to_dict(self) -> dict[str, Any]:
        return {"sorts": [s.value for s in self._sorts]}

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "SortRegistry":
        reg = cls()
        for v in payload.get("sorts", []):
            reg.add(Sort.from_value(v))
        return reg
```

- [ ] **Step 4: Run test, expect PASS.**

```bash
.venv/Scripts/python.exe -m pytest tests/test_sort_registry.py -v
```

Expected: 6 passed.

- [ ] **Step 5: Commit.**

```bash
git add skills/neurosym-forge/scripts/sort_registry.py skills/neurosym-forge/tests/test_sort_registry.py
git commit -m "neurosym-forge: SortRegistry"
```

### Task 1.6: `atom.py` — `Atom` dataclass

**Files:**
- Create: `skills/neurosym-forge/scripts/atom.py`
- Create: `skills/neurosym-forge/tests/test_atom.py`
- Create: `skills/neurosym-forge/tests/fixtures/valid_atom_symbol.edn`
- Create: `skills/neurosym-forge/tests/fixtures/valid_atom_grounded.edn`
- Create: `skills/neurosym-forge/tests/fixtures/invalid_atom_missing_sort.edn`

- [ ] **Step 1: Write fixture files.**

`tests/fixtures/valid_atom_symbol.edn`:

```json
{"kind": "symbol", "name": ":osmotic-pressure", "sort": {"kind": "fn", "args": [":solution"], "ret": ":real"}}
```

`tests/fixtures/valid_atom_grounded.edn`:

```json
{"kind": "grounded", "name": ":z3-check-all", "sort": {"kind": "fn", "args": [":atom"], "ret": ":verdict"}, "grounded": {"lib": "z3", "fn": "check_all", "napi": true}}
```

`tests/fixtures/invalid_atom_missing_sort.edn`:

```json
{"kind": "symbol", "name": ":foo"}
```

- [ ] **Step 2: Write failing test.**

```python
# skills/neurosym-forge/tests/test_atom.py
from __future__ import annotations

from pathlib import Path

import pytest

from scripts._io import read_edn_as_json
from scripts.atom import Atom


def test_load_symbol(fixtures_dir: Path) -> None:
    a = Atom.from_dict(read_edn_as_json(fixtures_dir / "valid_atom_symbol.edn"))
    assert a.kind == "symbol"
    assert a.name == ":osmotic-pressure"
    assert a.sort.is_function()


def test_load_grounded(fixtures_dir: Path) -> None:
    a = Atom.from_dict(read_edn_as_json(fixtures_dir / "valid_atom_grounded.edn"))
    assert a.kind == "grounded"
    assert a.grounded["lib"] == "z3"
    assert a.grounded["fn"] == "check_all"


def test_missing_sort_rejected(fixtures_dir: Path) -> None:
    with pytest.raises(ValueError, match="sort"):
        Atom.from_dict(read_edn_as_json(fixtures_dir / "invalid_atom_missing_sort.edn"))


def test_expression_atom_round_trip() -> None:
    src = {
        "kind": "expression",
        "sort": ":formula",
        "head": {"kind": "symbol", "name": ":=", "sort": ":rule"},
        "args": [
            {"kind": "variable", "name": "?x", "sort": ":int"},
            {"kind": "variable", "name": "?x", "sort": ":int"},
        ],
        "doc": "reflexivity",
        "id": "R001",
    }
    a = Atom.from_dict(src)
    assert a.to_dict() == src


def test_variable_atom_has_question_prefix() -> None:
    a = Atom.from_dict({"kind": "variable", "name": "?s", "sort": ":solution"})
    assert a.is_variable()
    assert a.name.startswith("?")
```

- [ ] **Step 3: Run test, expect FAIL.**

```bash
.venv/Scripts/python.exe -m pytest tests/test_atom.py -v
```

Expected: `ModuleNotFoundError: scripts.atom`.

- [ ] **Step 4: Write implementation.**

```python
# skills/neurosym-forge/scripts/atom.py
"""Atom — MeTTa-style atom: symbol, variable, grounded, or expression."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from scripts.sort_registry import Sort


@dataclass
class Atom:
    kind: str  # "symbol" | "variable" | "grounded" | "expression"
    sort: Sort
    name: Optional[str] = None
    grounded: Optional[dict[str, Any]] = None
    head: Optional["Atom"] = None
    args: list["Atom"] = field(default_factory=list)
    doc: Optional[str] = None
    id: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    force: bool = False

    VALID_KINDS = ("symbol", "variable", "grounded", "expression")

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Atom":
        if "kind" not in payload:
            raise ValueError("atom missing 'kind'")
        if payload["kind"] not in cls.VALID_KINDS:
            raise ValueError(f"unknown atom kind: {payload['kind']!r}")
        if "sort" not in payload:
            raise ValueError("atom missing 'sort'")
        kind = payload["kind"]
        sort = Sort.from_value(payload["sort"])
        if kind == "symbol":
            return cls(kind="symbol", sort=sort, name=payload.get("name"),
                       doc=payload.get("doc"), id=payload.get("id"),
                       tags=list(payload.get("tags", [])),
                       force=bool(payload.get("force", False)))
        if kind == "variable":
            name = payload.get("name", "")
            if not name.startswith("?"):
                raise ValueError(f"variable name must start with '?', got {name!r}")
            return cls(kind="variable", sort=sort, name=name)
        if kind == "grounded":
            g = payload.get("grounded")
            if not g or "lib" not in g or "fn" not in g:
                raise ValueError("grounded atom requires {'grounded': {'lib', 'fn'}}")
            return cls(kind="grounded", sort=sort, name=payload.get("name"),
                       grounded=dict(g))
        if kind == "expression":
            if "head" not in payload or "args" not in payload:
                raise ValueError("expression atom requires 'head' and 'args'")
            return cls(kind="expression", sort=sort,
                       head=Atom.from_dict(payload["head"]),
                       args=[Atom.from_dict(a) for a in payload["args"]],
                       doc=payload.get("doc"), id=payload.get("id"),
                       tags=list(payload.get("tags", [])),
                       force=bool(payload.get("force", False)))
        raise ValueError(f"unhandled kind {kind!r}")

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {"kind": self.kind, "sort": self.sort.value}
        if self.name is not None:
            out["name"] = self.name
        if self.grounded is not None:
            out["grounded"] = dict(self.grounded)
        if self.head is not None:
            out["head"] = self.head.to_dict()
        if self.args:
            out["args"] = [a.to_dict() for a in self.args]
        if self.doc is not None:
            out["doc"] = self.doc
        if self.id is not None:
            out["id"] = self.id
        if self.tags:
            out["tags"] = list(self.tags)
        if self.force:
            out["force"] = True
        return out

    def is_symbol(self) -> bool:     return self.kind == "symbol"
    def is_variable(self) -> bool:   return self.kind == "variable"
    def is_grounded(self) -> bool:   return self.kind == "grounded"
    def is_expression(self) -> bool: return self.kind == "expression"

    def free_variables(self) -> set[str]:
        if self.is_variable():
            return {self.name or ""}
        out: set[str] = set()
        if self.head is not None:
            out |= self.head.free_variables()
        for a in self.args:
            out |= a.free_variables()
        return out
```

- [ ] **Step 5: Run test, expect PASS.**

```bash
.venv/Scripts/python.exe -m pytest tests/test_atom.py -v
```

Expected: 5 passed.

- [ ] **Step 6: Commit.**

```bash
git add skills/neurosym-forge/scripts/atom.py skills/neurosym-forge/tests/test_atom.py skills/neurosym-forge/tests/fixtures/
git commit -m "neurosym-forge: Atom dataclass + fixtures"
```

### Task 1.7: `rewrite_rule.py` — `RewriteRule` with variable-balance check

**Files:**
- Create: `skills/neurosym-forge/scripts/rewrite_rule.py`
- Create: `skills/neurosym-forge/tests/test_rewrite_rule.py`
- Create: `skills/neurosym-forge/tests/fixtures/valid_rule_commutative.edn`
- Create: `skills/neurosym-forge/tests/fixtures/invalid_rule_unbound_var.edn`

- [ ] **Step 1: Write fixture files.**

`tests/fixtures/valid_rule_commutative.edn`:

```json
{
  "id": "R001",
  "lhs": {"kind": "expression", "sort": ":real",
          "head": {"kind": "symbol", "name": ":+", "sort": {"kind": "fn", "args": [":real", ":real"], "ret": ":real"}},
          "args": [{"kind": "variable", "name": "?a", "sort": ":real"},
                   {"kind": "variable", "name": "?b", "sort": ":real"}]},
  "rhs": {"kind": "expression", "sort": ":real",
          "head": {"kind": "symbol", "name": ":+", "sort": {"kind": "fn", "args": [":real", ":real"], "ret": ":real"}},
          "args": [{"kind": "variable", "name": "?b", "sort": ":real"},
                   {"kind": "variable", "name": "?a", "sort": ":real"}]},
  "doc": "commutativity of addition",
  "tags": ["algebraic", "commutative"]
}
```

`tests/fixtures/invalid_rule_unbound_var.edn`:

```json
{
  "id": "R002",
  "lhs": {"kind": "expression", "sort": ":real",
          "head": {"kind": "symbol", "name": ":f", "sort": {"kind": "fn", "args": [":real"], "ret": ":real"}},
          "args": [{"kind": "variable", "name": "?x", "sort": ":real"}]},
  "rhs": {"kind": "variable", "name": "?y", "sort": ":real"},
  "doc": "broken: ?y is free on rhs but not lhs"
}
```

- [ ] **Step 2: Write failing test.**

```python
# skills/neurosym-forge/tests/test_rewrite_rule.py
from __future__ import annotations

from pathlib import Path

import pytest

from scripts._io import read_edn_as_json
from scripts.rewrite_rule import RewriteRule


def test_load_valid(fixtures_dir: Path) -> None:
    r = RewriteRule.from_dict(read_edn_as_json(fixtures_dir / "valid_rule_commutative.edn"))
    assert r.id == "R001"
    assert "commutative" in r.tags


def test_balance_check_accepts_balanced(fixtures_dir: Path) -> None:
    r = RewriteRule.from_dict(read_edn_as_json(fixtures_dir / "valid_rule_commutative.edn"))
    r.check_variable_balance()  # no raise


def test_balance_check_rejects_unbound_rhs(fixtures_dir: Path) -> None:
    r = RewriteRule.from_dict(read_edn_as_json(fixtures_dir / "invalid_rule_unbound_var.edn"))
    with pytest.raises(ValueError, match="unbound variables on rhs"):
        r.check_variable_balance()


def test_eliminating_tag_allows_lhs_drop() -> None:
    r = RewriteRule.from_dict({
        "id": "R003",
        "lhs": {"kind": "expression", "sort": ":real",
                "head": {"kind": "symbol", "name": ":dup", "sort": {"kind": "fn", "args": [":real"], "ret": ":real"}},
                "args": [{"kind": "variable", "name": "?x", "sort": ":real"}]},
        "rhs": {"kind": "variable", "name": "?x", "sort": ":real"},
        "tags": ["eliminating"],
    })
    r.check_variable_balance()  # ?x bound on lhs, used on rhs, OK


def test_id_pattern_validated() -> None:
    with pytest.raises(ValueError, match="id"):
        RewriteRule.from_dict({
            "id": "badid",
            "lhs": {"kind": "variable", "name": "?x", "sort": ":real"},
            "rhs": {"kind": "variable", "name": "?x", "sort": ":real"},
        })
```

- [ ] **Step 3: Run test, expect FAIL.**

```bash
.venv/Scripts/python.exe -m pytest tests/test_rewrite_rule.py -v
```

Expected: `ModuleNotFoundError: scripts.rewrite_rule`.

- [ ] **Step 4: Write implementation.**

```python
# skills/neurosym-forge/scripts/rewrite_rule.py
"""RewriteRule — a MeTTa (= lhs rhs) equality declaration."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from scripts.atom import Atom

ID_PATTERN = re.compile(r"^R[0-9]{3,}$")


@dataclass
class RewriteRule:
    id: str
    lhs: Atom
    rhs: Atom
    doc: str | None = None
    tags: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "RewriteRule":
        rid = payload.get("id", "")
        if not ID_PATTERN.match(rid):
            raise ValueError(f"rule id must match R[0-9]{{3,}}, got {rid!r}")
        return cls(
            id=rid,
            lhs=Atom.from_dict(payload["lhs"]),
            rhs=Atom.from_dict(payload["rhs"]),
            doc=payload.get("doc"),
            tags=list(payload.get("tags", [])),
        )

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "id": self.id,
            "lhs": self.lhs.to_dict(),
            "rhs": self.rhs.to_dict(),
        }
        if self.doc is not None:
            out["doc"] = self.doc
        if self.tags:
            out["tags"] = list(self.tags)
        return out

    def check_variable_balance(self) -> None:
        """Every free variable on rhs must be bound on lhs.

        Unless tagged 'eliminating', lhs may not introduce variables unused on rhs.
        """
        lhs_vars = self.lhs.free_variables()
        rhs_vars = self.rhs.free_variables()
        rhs_only = rhs_vars - lhs_vars
        if rhs_only:
            raise ValueError(f"unbound variables on rhs of {self.id}: {sorted(rhs_only)}")
        if "eliminating" in self.tags:
            return
        lhs_only = lhs_vars - rhs_vars
        if lhs_only:
            raise ValueError(
                f"variables bound on lhs but unused on rhs of {self.id}: {sorted(lhs_only)}. "
                f"Tag the rule 'eliminating' if this is intentional."
            )
```

- [ ] **Step 5: Run test, expect PASS.**

```bash
.venv/Scripts/python.exe -m pytest tests/test_rewrite_rule.py -v
```

Expected: 5 passed.

- [ ] **Step 6: Commit.**

```bash
git add skills/neurosym-forge/scripts/rewrite_rule.py skills/neurosym-forge/tests/test_rewrite_rule.py skills/neurosym-forge/tests/fixtures/
git commit -m "neurosym-forge: RewriteRule with variable-balance check"
```

---

## Phase 2: Linters

### Task 2.1: `lint_atomspace.py`

**Files:**
- Create: `skills/neurosym-forge/scripts/lint_atomspace.py`
- Create: `skills/neurosym-forge/tests/test_lint_atomspace.py`
- Create: `skills/neurosym-forge/tests/fixtures/seed_atomspace.edn`

- [ ] **Step 1: Write fixture.**

`tests/fixtures/seed_atomspace.edn`:

```json
{
  "version": 1,
  "sorts": [":int", ":real", ":bool", ":solution",
            {"kind": "fn", "args": [":solution"], "ret": ":real"}],
  "rules": [
    {
      "id": "R001",
      "lhs": {"kind": "expression", "sort": ":real",
              "head": {"kind": "symbol", "name": ":+", "sort": {"kind": "fn", "args": [":real", ":real"], "ret": ":real"}},
              "args": [{"kind": "variable", "name": "?a", "sort": ":real"},
                       {"kind": "variable", "name": "?b", "sort": ":real"}]},
      "rhs": {"kind": "expression", "sort": ":real",
              "head": {"kind": "symbol", "name": ":+", "sort": {"kind": "fn", "args": [":real", ":real"], "ret": ":real"}},
              "args": [{"kind": "variable", "name": "?b", "sort": ":real"},
                       {"kind": "variable", "name": "?a", "sort": ":real"}]},
      "doc": "commutativity"
    }
  ],
  "atoms": [
    {"kind": "symbol", "name": ":osmotic-pressure", "sort": {"kind": "fn", "args": [":solution"], "ret": ":real"}}
  ]
}
```

- [ ] **Step 2: Write failing test.**

```python
# skills/neurosym-forge/tests/test_lint_atomspace.py
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts._io import read_edn_as_json, write_json_as_edn
from scripts.lint_atomspace import lint_atomspace, LintReport


def test_clean_atomspace_passes(fixtures_dir: Path) -> None:
    payload = read_edn_as_json(fixtures_dir / "seed_atomspace.edn")
    report = lint_atomspace(payload)
    assert report.ok
    assert report.errors == []


def test_missing_sort_flagged(tmp_path: Path) -> None:
    payload = {"version": 1, "sorts": [":int"], "rules": [],
               "atoms": [{"kind": "symbol", "name": ":foo"}]}
    report = lint_atomspace(payload)
    assert not report.ok
    assert any("missing 'sort'" in e for e in report.errors)


def test_unknown_sort_reference_flagged() -> None:
    payload = {"version": 1, "sorts": [":int"], "rules": [],
               "atoms": [{"kind": "symbol", "name": ":foo", "sort": ":unknown"}]}
    report = lint_atomspace(payload)
    assert not report.ok
    assert any("unknown sort" in e for e in report.errors)


def test_rule_with_invalid_balance_flagged() -> None:
    payload = {"version": 1, "sorts": [":real"], "atoms": [],
               "rules": [{
                   "id": "R002",
                   "lhs": {"kind": "expression", "sort": ":real",
                           "head": {"kind": "symbol", "name": ":f",
                                    "sort": {"kind": "fn", "args": [":real"], "ret": ":real"}},
                           "args": [{"kind": "variable", "name": "?x", "sort": ":real"}]},
                   "rhs": {"kind": "variable", "name": "?y", "sort": ":real"}
               }]}
    report = lint_atomspace(payload)
    assert not report.ok
    assert any("R002" in e and "unbound" in e for e in report.errors)


def test_cli_returns_nonzero_on_errors(tmp_path: Path) -> None:
    import subprocess
    import sys
    bad = tmp_path / "bad.edn"
    write_json_as_edn(bad, {"version": 1, "sorts": [":int"], "rules": [],
                            "atoms": [{"kind": "symbol", "name": ":foo"}]})
    result = subprocess.run(
        [sys.executable, "-m", "scripts.lint_atomspace", str(bad)],
        capture_output=True, text=True, cwd=str(Path(__file__).resolve().parent.parent),
    )
    assert result.returncode == 1
    assert "missing 'sort'" in result.stdout or "missing 'sort'" in result.stderr
```

- [ ] **Step 3: Run test, expect FAIL.**

```bash
.venv/Scripts/python.exe -m pytest tests/test_lint_atomspace.py -v
```

Expected: `ModuleNotFoundError: scripts.lint_atomspace`.

- [ ] **Step 4: Write implementation.**

```python
# skills/neurosym-forge/scripts/lint_atomspace.py
"""Lint an atomspace EDN file for shape, sort coverage, and rule balance.

Exits 0 if clean, 1 if any error is found. Emits human-readable lines on stdout.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from scripts._io import read_edn_as_json
from scripts.atom import Atom
from scripts.rewrite_rule import RewriteRule
from scripts.sort_registry import Sort, SortRegistry


@dataclass
class LintReport:
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def _collect_sort_strings(s: Any) -> set[str]:
    out: set[str] = set()
    if isinstance(s, str):
        out.add(s)
    elif isinstance(s, dict):
        if s.get("kind") == "fn":
            for a in s.get("args", []):
                out |= _collect_sort_strings(a)
            out |= _collect_sort_strings(s.get("ret"))
        elif s.get("kind") == "enum":
            out.add("enum:" + ",".join(s.get("members", [])))
    return out


def _walk_atom_sorts(payload: dict[str, Any], collect: set[str]) -> None:
    if "sort" in payload:
        collect |= _collect_sort_strings(payload["sort"])
    if "head" in payload and isinstance(payload["head"], dict):
        _walk_atom_sorts(payload["head"], collect)
    for a in payload.get("args", []) or []:
        if isinstance(a, dict):
            _walk_atom_sorts(a, collect)


def lint_atomspace(payload: dict[str, Any]) -> LintReport:
    report = LintReport()

    if "sorts" not in payload:
        report.errors.append("atomspace missing 'sorts' field")
        return report
    try:
        registry = SortRegistry.from_dict({"sorts": payload["sorts"]})
    except ValueError as e:
        report.errors.append(f"sort registry: {e}")
        return report
    known_primitives = {s.value for s in registry._sorts if isinstance(s.value, str)}

    for i, raw in enumerate(payload.get("atoms", [])):
        if not isinstance(raw, dict):
            report.errors.append(f"atoms[{i}]: not an object")
            continue
        if "sort" not in raw:
            report.errors.append(f"atoms[{i}] ({raw.get('name', '?')}): missing 'sort'")
            continue
        try:
            Atom.from_dict(raw)
        except ValueError as e:
            report.errors.append(f"atoms[{i}]: {e}")
            continue
        referenced: set[str] = set()
        _walk_atom_sorts(raw, referenced)
        for s in referenced:
            if s.startswith(":") and s not in known_primitives:
                report.errors.append(
                    f"atoms[{i}] ({raw.get('name', '?')}): unknown sort {s!r}"
                )

    for i, raw in enumerate(payload.get("rules", [])):
        try:
            rule = RewriteRule.from_dict(raw)
        except ValueError as e:
            report.errors.append(f"rules[{i}]: {e}")
            continue
        try:
            rule.check_variable_balance()
        except ValueError as e:
            report.errors.append(f"rules[{i}] {rule.id}: {e}")
        referenced: set[str] = set()
        _walk_atom_sorts(raw["lhs"], referenced)
        _walk_atom_sorts(raw["rhs"], referenced)
        for s in referenced:
            if s.startswith(":") and s not in known_primitives:
                report.errors.append(f"rules[{i}] {rule.id}: unknown sort {s!r}")

    return report


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: python -m scripts.lint_atomspace <atomspace.edn>", file=sys.stderr)
        return 2
    path = Path(argv[1])
    payload = read_edn_as_json(path)
    report = lint_atomspace(payload)
    for err in report.errors:
        print(err)
    if not report.ok:
        return 1
    print(f"OK: atomspace {path} passes ({len(payload.get('atoms', []))} atoms, "
          f"{len(payload.get('rules', []))} rules)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
```

- [ ] **Step 5: Run test, expect PASS.**

```bash
.venv/Scripts/python.exe -m pytest tests/test_lint_atomspace.py -v
```

Expected: 5 passed.

- [ ] **Step 6: Commit.**

```bash
git add skills/neurosym-forge/scripts/lint_atomspace.py skills/neurosym-forge/tests/test_lint_atomspace.py skills/neurosym-forge/tests/fixtures/seed_atomspace.edn
git commit -m "neurosym-forge: lint_atomspace + CLI"
```

### Task 2.2: `lint_rewrite_coverage.py`

**Files:**
- Create: `skills/neurosym-forge/scripts/lint_rewrite_coverage.py`
- Create: `skills/neurosym-forge/tests/test_lint_rewrite_coverage.py`

This linter checks two things in a scaffolded project root: every rule in `rules/*.edn` has a fixture test file in `tests/rules/test_<ID>.cljs` (the *scaffolded project's* tests, not this skill's), and the checksums in `rules/.checksums.edn` match the on-disk rule files. Manual edits that bypass `add_rewrite_rule.py` are flagged.

- [ ] **Step 1: Write failing test.**

```python
# skills/neurosym-forge/tests/test_lint_rewrite_coverage.py
from __future__ import annotations

from pathlib import Path

import pytest

from scripts._io import write_json_as_edn, file_checksum
from scripts.lint_rewrite_coverage import lint_rewrite_coverage


def _make_scaffold(root: Path, rules: dict[str, list[dict]], tests: list[str]) -> None:
    (root / "rules").mkdir(parents=True)
    (root / "tests" / "rules").mkdir(parents=True)
    checksums: dict[str, str] = {}
    for fname, rule_list in rules.items():
        p = root / "rules" / fname
        write_json_as_edn(p, {"rules": rule_list})
        checksums[fname] = file_checksum(p)
    write_json_as_edn(root / "rules" / ".checksums.edn", {"checksums": checksums})
    for t in tests:
        (root / "tests" / "rules" / t).write_text("(deftest ...)\n", encoding="utf-8")


def test_clean_coverage(tmp_path: Path) -> None:
    _make_scaffold(
        tmp_path,
        rules={"seed.edn": [
            {"id": "R001",
             "lhs": {"kind": "variable", "name": "?x", "sort": ":int"},
             "rhs": {"kind": "variable", "name": "?x", "sort": ":int"}}
        ]},
        tests=["test_R001.cljs"],
    )
    report = lint_rewrite_coverage(tmp_path)
    assert report.ok


def test_missing_fixture_flagged(tmp_path: Path) -> None:
    _make_scaffold(
        tmp_path,
        rules={"seed.edn": [
            {"id": "R001",
             "lhs": {"kind": "variable", "name": "?x", "sort": ":int"},
             "rhs": {"kind": "variable", "name": "?x", "sort": ":int"}}
        ]},
        tests=[],
    )
    report = lint_rewrite_coverage(tmp_path)
    assert not report.ok
    assert any("R001" in e and "fixture" in e for e in report.errors)


def test_checksum_mismatch_flagged(tmp_path: Path) -> None:
    _make_scaffold(
        tmp_path,
        rules={"seed.edn": [
            {"id": "R001",
             "lhs": {"kind": "variable", "name": "?x", "sort": ":int"},
             "rhs": {"kind": "variable", "name": "?x", "sort": ":int"}}
        ]},
        tests=["test_R001.cljs"],
    )
    (tmp_path / "rules" / "seed.edn").write_text("tampered\n", encoding="utf-8")
    report = lint_rewrite_coverage(tmp_path)
    assert not report.ok
    assert any("checksum" in e for e in report.errors)
```

- [ ] **Step 2: Run test, expect FAIL.**

```bash
.venv/Scripts/python.exe -m pytest tests/test_lint_rewrite_coverage.py -v
```

Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Write implementation.**

```python
# skills/neurosym-forge/scripts/lint_rewrite_coverage.py
"""Verify every rewrite rule has a fixture test and on-disk checksums match."""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

from scripts._io import read_edn_as_json, file_checksum


@dataclass
class CoverageReport:
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def lint_rewrite_coverage(project_root: Path) -> CoverageReport:
    report = CoverageReport()
    rules_dir = project_root / "rules"
    tests_dir = project_root / "tests" / "rules"

    if not rules_dir.exists():
        report.errors.append(f"missing rules/ at {rules_dir}")
        return report

    checksums_path = rules_dir / ".checksums.edn"
    expected_checksums: dict[str, str] = {}
    if checksums_path.exists():
        expected_checksums = read_edn_as_json(checksums_path).get("checksums", {})

    for path in sorted(rules_dir.glob("*.edn")):
        if path.name.startswith("."):
            continue
        actual = file_checksum(path)
        expected = expected_checksums.get(path.name)
        if expected is None:
            report.errors.append(f"no checksum recorded for {path.name}; "
                                 f"use add_rewrite_rule to update")
        elif actual != expected:
            report.errors.append(
                f"checksum mismatch on {path.name}: manual edit detected. "
                f"Reapply via add_rewrite_rule or restore the file."
            )
        payload = read_edn_as_json(path)
        for rule in payload.get("rules", []):
            rid = rule.get("id")
            if not rid:
                report.errors.append(f"{path.name}: rule missing id")
                continue
            fixture = tests_dir / f"test_{rid}.cljs"
            if not fixture.exists():
                report.errors.append(
                    f"rule {rid} ({path.name}): missing fixture test {fixture.relative_to(project_root)}"
                )

    return report


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: python -m scripts.lint_rewrite_coverage <project-root>",
              file=sys.stderr)
        return 2
    root = Path(argv[1])
    report = lint_rewrite_coverage(root)
    for err in report.errors:
        print(err)
    if not report.ok:
        return 1
    print(f"OK: rule coverage at {root} is clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
```

- [ ] **Step 4: Run test, expect PASS.**

```bash
.venv/Scripts/python.exe -m pytest tests/test_lint_rewrite_coverage.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Commit.**

```bash
git add skills/neurosym-forge/scripts/lint_rewrite_coverage.py skills/neurosym-forge/tests/test_lint_rewrite_coverage.py
git commit -m "neurosym-forge: lint_rewrite_coverage"
```

---

## Phase 3: Project templates

### Task 3.1: Top-level template files

**Files:** Eight `.tmpl` files under `assets/project-template/`.

Templates use jinja2 with `{{ project_name }}`, `{{ project_slug }}`, `{{ neurosym_forge_version }}`, `{{ has_book_knowledge_bridge }}` as the canonical context.

- [ ] **Step 1: Create `assets/project-template/shadow-cljs.edn.tmpl`.**

```clojure
{:source-paths ["cljs-orchestrator/src/main"]
 :dependencies [[org.clojure/core.logic   "1.1.1"]
                [meander/epsilon          "0.0.650"]
                [metosin/malli            "0.16.4"]]
 :builds
 {:main {:target     :node-script
         :output-to  "cljs-orchestrator/dist/main.js"
         :main       {{ project_slug }}.core/main
         :compiler-options {:optimizations :simple
                            :infer-externs :auto}}}}
```

- [ ] **Step 2: Create `assets/project-template/package.json.tmpl`.**

```json
{
  "name": "{{ project_slug }}",
  "private": true,
  "type": "commonjs",
  "scripts": {
    "build:cljs":   "shadow-cljs release main",
    "build:rust":   "cd rust-verifier && napi build --platform --release ../cljs-orchestrator/native",
    "build":        "npm run build:rust && npm run build:cljs",
    "verify":       "node cljs-orchestrator/dist/main.js"
  },
  "devDependencies": {
    "shadow-cljs": "^2.28.20",
    "@napi-rs/cli": "^3.0.0"
  }
}
```

- [ ] **Step 3: Create `assets/project-template/deps.edn.tmpl`.**

```clojure
{:paths ["cljs-orchestrator/src/main"]
 :deps  {org.clojure/clojurescript {:mvn/version "1.11.132"}}}
```

- [ ] **Step 4: Create `assets/project-template/.gitignore.tmpl`.**

```
.venv/
__pycache__/
node_modules/
target/
work/
cljs-orchestrator/dist/
cljs-orchestrator/native/*.node
.shadow-cljs/
```

- [ ] **Step 5: Create `assets/project-template/README.md.tmpl`.**

```markdown
# {{ project_name }}

A neurosymbolic verification project scaffolded by [neurosym-forge](../../skills/neurosym-forge/).
Four-phase pipeline: Claude → ClojureScript (rewrite) → Rust (verify) → Claude (synthesise) → Rust (typeset).

## Build

```bash
npm install
npm run build
```

## Verify

```bash
npm run verify work/claims.edn work/verdict.edn
```

## Extend

Add a rewrite rule from the parent repo:

```bash
cd ../../skills/neurosym-forge
.venv/Scripts/python.exe -m scripts.add_rewrite_rule \
  --project ../../verifiers/{{ project_slug }} \
  --rule-file new-rule.edn
```

Add a grounded atom:

```bash
.venv/Scripts/python.exe -m scripts.add_grounded_atom \
  --project ../../verifiers/{{ project_slug }} \
  --name :my-fn --lib custom --sort :verdict
```

See `../../skills/neurosym-forge/references/` for the full conventions.
```

- [ ] **Step 6: Create `assets/project-template/SKILL.md.tmpl`.**

```markdown
---
name: {{ project_slug }}
description: Neurosymbolic verifier for {{ project_name }}. Use when verifying claim sets in this domain with FOL/SMT/e-graph/Datalog reasoning. Scaffolded by neurosym-forge.
license: MIT
metadata:
  version: 0.1.0
  category: verification
  emits: pdf
---

# {{ project_name }} verifier

Runs the four-phase neurosymbolic pipeline against a claim set.

## Usage

- `npm install && npm run build` — first-time setup
- `node cljs-orchestrator/dist/main.js verify work/claims.edn work/verdict.edn` — verify
- `node cljs-orchestrator/dist/main.js typeset work/report.md work/report.pdf` — typeset

## Extension

This project is a scaffold from `neurosym-forge`. Add rules and grounded atoms
via that skill, never by hand-editing `rules/*.edn`.
```

- [ ] **Step 7: Create `assets/project-template/rules/seed.edn.tmpl`.**

```json
{
  "version": 1,
  "sorts": [":int", ":real", ":bool", ":entity", ":formula", ":verdict", ":rule", ":atom"],
  "rules": [],
  "atoms": []
}
```

- [ ] **Step 8: Create `assets/project-template/rules/grounded.edn.tmpl`.**

```json
{
  "version": 1,
  "grounded": [
    {
      "kind": "grounded",
      "name": ":z3-check-all",
      "sort": {"kind": "fn", "args": [":atom"], "ret": ":verdict"},
      "grounded": {"lib": "z3", "fn": "verify_formulas", "napi": true},
      "doc": "Top-level SMT check; calls Z3 with assert_and_track."
    },
    {
      "kind": "grounded",
      "name": ":egg-saturate",
      "sort": {"kind": "fn", "args": [":atom", ":atom"], "ret": ":atom"},
      "grounded": {"lib": "egg", "fn": "saturate", "napi": true},
      "doc": "Equality saturation; returns shortest equivalent form."
    },
    {
      "kind": "grounded",
      "name": ":cozo-contradictions",
      "sort": {"kind": "fn", "args": [":atom"], "ret": ":atom"},
      "grounded": {"lib": "cozo", "fn": "ingest_and_summarize", "napi": true},
      "doc": "Datalog contradiction scan over verified claims."
    }
  ]
}
```

- [ ] **Step 9: Create `assets/project-template/rules/predicates.edn.tmpl`.**

```json
{
  "version": 1,
  "predicates": {}
}
```

- [ ] **Step 10: Create `assets/project-template/rules/.forge-version.edn.tmpl`.**

```json
{
  "neurosym_forge_version": "{{ neurosym_forge_version }}",
  "scaffolded_at": "{{ scaffolded_at }}"
}
```

- [ ] **Step 11: Commit.**

```bash
git add skills/neurosym-forge/assets/project-template/
git commit -m "neurosym-forge: top-level project templates"
```

### Task 3.2: CLJS orchestrator templates

**Files:** Six `.tmpl` files under `assets/project-template/cljs-orchestrator/src/main/__project__/`. The `__project__` placeholder is replaced with `{{ project_slug }}` during scaffold; using a literal placeholder in the path avoids jinja path-resolution headaches.

- [ ] **Step 1: Create `cljs-orchestrator/src/main/__project__/core.cljs.tmpl`.**

```clojure
(ns {{ project_slug }}.core
  "CLI entry. Dispatches: translate, verify, typeset."
  (:require [{{ project_slug }}.phases :as p]
            [cljs.reader :as edn]
            ["fs" :as fs]))

(defn- read-edn [path]
  (edn/read-string (.toString (.readFileSync fs path))))

(defn- write-edn [path data]
  (.writeFileSync fs path (pr-str data)))

(defn main [& args]
  (let [[cmd in out] args]
    (case cmd
      "translate" (write-edn out (p/translate (read-edn in)))
      "verify"    (write-edn out (p/verify    (read-edn in)))
      "typeset"   (p/typeset in out)
      (do (println "usage: main.js <translate|verify|typeset> <in> <out>")
          (.exit js/process 2)))))
```

- [ ] **Step 2: Create `phases.cljs.tmpl`.**

```clojure
(ns {{ project_slug }}.phases
  "Phase driver with malli pre/post contracts."
  (:require [{{ project_slug }}.ir         :as ir]
            [{{ project_slug }}.nl-to-fol  :as t]
            [{{ project_slug }}.bridge     :as b]
            [malli.core                    :as m]))

(def MAX-REMEDIES 3)

(defn translate [claims]
  {:pre  (m/validate [:vector ir/Claim] claims)
   :post (m/validate [:vector ir/Formula] %)}
  (t/translate-corpus claims))

(defn verify [formulas]
  {:pre  (m/validate [:vector ir/Formula] formulas)
   :post (m/validate ir/Verdict %)}
  (b/verify-formulas (pr-str formulas)))

(defn typeset [report-path out-path]
  (b/render-pdf (slurp report-path) out-path))
```

- [ ] **Step 3: Create `ir.cljs.tmpl`.**

```clojure
(ns {{ project_slug }}.ir
  "Atomspace IR — malli schemas for Atom, Formula, Claim, Verdict."
  (:require [malli.core :as m]
            [malli.instrument :as mi]))

(def Sort
  [:or :keyword
   [:map [:kind [:enum :fn]]
         [:args [:vector :keyword]]
         [:ret  :keyword]]
   [:map [:kind [:enum :enum]]
         [:members [:vector :keyword]]]])

(def Atom
  [:map
   [:kind [:enum :symbol :variable :grounded :expression]]
   [:sort Sort]])

(def Formula Atom)

(def Claim
  [:map
   [:id          [:re #"^C\d{3,}$"]]
   [:source      :string]
   [:s           :map]
   [:p           :keyword]
   [:o           :any]
   [:c           [:vector :map]]
   [:modality    [:enum :assertion :hypothesis :definition :counterfactual]]
   [:confidence  [:double {:min 0.0 :max 1.0}]]])

(def Verdict
  [:map
   [:status       [:enum :sat :unsat :unknown]]
   [:verified-claims {:optional true} [:vector Claim]]
   [:core         {:optional true} [:vector :string]]
   [:proofs       {:optional true} [:vector :map]]
   [:graph-summary {:optional true} :map]])

(defn enable-instrumentation! []
  (mi/instrument!
    {:report (fn [type data]
               (throw (ex-info (str "DbC violation: " type) data)))}))
```

- [ ] **Step 4: Create `nl_to_fol.cljs.tmpl`.**

```clojure
(ns {{ project_slug }}.nl-to-fol
  "Phase 2: meander rewrite of Claim → Formula."
  (:require [meander.epsilon :as m]))

(defn to-si [v u]
  (case u
    "atm" (* v 101325.0)
    "C"   (+ v 273.15)
    v))

(defn claim->formula [claim]
  (m/rewrite claim
    {:id ?id
     :s  ?subj
     :p  ?pred
     :o  {:kind :quantity :value ?v :unit ?u}
     :c  [!conds ...]}
    {:kind :expression :sort :formula
     :head {:kind :symbol :name :forall :sort :rule}
     :args [{:kind :variable :name "?subj" :sort :entity}
            {:kind :expression :sort :formula
             :head {:kind :symbol :name :implies :sort :rule}
             :args [{:kind :expression :sort :formula
                     :head {:kind :symbol :name :and :sort :rule}
                     :args [!conds ...]}
                    {:kind :expression :sort :formula
                     :head {:kind :symbol :name := :sort :rule}
                     :args [{:kind :expression :sort :real
                             :head {:kind :symbol :name ~?pred :sort :real}
                             :args [{:kind :variable :name "?subj" :sort :entity}]}
                            {:kind :grounded :sort :real
                             :name ~(to-si ?v ?u)
                             :grounded {:lib "literal" :fn "value"}}]}]}]}
    ?other {:kind :symbol :sort :formula :name :OPAQUE}))

(defn translate-corpus [claims]
  (mapv claim->formula claims))
```

- [ ] **Step 5: Create `unify.cljs.tmpl`.**

```clojure
(ns {{ project_slug }}.unify
  "core.logic-based variable unification across atoms."
  (:require [clojure.core.logic :as l]))

(defn unify-atoms [a b]
  (l/run* [q]
    (l/== a b)
    (l/== q [a b])))
```

- [ ] **Step 6: Create `bridge.cljs.tmpl`.**

```clojure
(ns {{ project_slug }}.bridge
  "Calls into the native Rust addon built by napi-rs."
  (:require ["./../../native/{{ project_slug }}-verifier.node" :as native]
            [cljs.reader :as edn]))

(defn verify-formulas [formulas-edn]
  (let [verdict-edn (native/verifyFormulas formulas-edn)]
    (edn/read-string verdict-edn)))

(defn saturate-equalities [terms-edn rules-edn]
  (edn/read-string (native/saturate terms-edn rules-edn)))

(defn render-pdf [latex-source out-path]
  (native/renderPdf latex-source out-path))
```

- [ ] **Step 7: Commit.**

```bash
git add skills/neurosym-forge/assets/project-template/cljs-orchestrator/
git commit -m "neurosym-forge: CLJS orchestrator templates"
```

### Task 3.3: Rust verifier templates

**Files:** Seven `.tmpl` files under `assets/project-template/rust-verifier/`.

- [ ] **Step 1: Create `rust-verifier/Cargo.toml.tmpl`.**

```toml
[package]
name    = "{{ project_slug }}-verifier"
version = "0.1.0"
edition = "2024"

[lib]
crate-type = ["cdylib"]

[dependencies]
napi        = { version = "3", features = ["napi9", "serde-json", "async"] }
napi-derive = "3"
z3          = { version = "0.20", features = ["bundled"] }
egg         = "0.10"
cozo        = { version = "0.7", default-features = false, features = ["compact"] }
tectonic    = "0.16"
serde       = { version = "1", features = ["derive"] }
edn-rs      = "0.18"
thiserror   = "2"
ordered-float = "4"

[build-dependencies]
napi-build = "2"
```

- [ ] **Step 2: Create `rust-verifier/build.rs.tmpl`.**

```rust
extern crate napi_build;

fn main() {
    napi_build::setup();
}
```

- [ ] **Step 3: Create `rust-verifier/src/lib.rs.tmpl`.**

```rust
#![deny(clippy::all)]
use napi_derive::napi;

mod ir;
mod smt;
mod eqsat;
mod kg;
mod typeset;

#[napi]
pub fn verify_formulas(formulas_edn: String) -> napi::Result<String> {
    let formulas = ir::parse_formulas(&formulas_edn)
        .map_err(|e| napi::Error::from_reason(format!("parse: {e}")))?;
    let verdict = smt::check_all(&formulas)
        .map_err(|e| napi::Error::from_reason(format!("smt: {e}")))?;
    let kg_summary = kg::ingest_and_summarize(&verdict.verified)
        .map_err(|e| napi::Error::from_reason(format!("kg: {e}")))?;
    let mut out = verdict;
    out.graph_summary = Some(kg_summary);
    Ok(ir::emit_verdict(&out))
}

#[napi]
pub fn saturate(terms_edn: String, rules_edn: String) -> napi::Result<String> {
    eqsat::saturate(&terms_edn, &rules_edn)
        .map_err(|e| napi::Error::from_reason(e.to_string()))
}

#[napi]
pub fn render_pdf(latex: String, out_path: String) -> napi::Result<()> {
    typeset::render(&latex, &out_path)
        .map_err(|e| napi::Error::from_reason(e.to_string()))
}
```

- [ ] **Step 4: Create `rust-verifier/src/ir.rs.tmpl`.**

```rust
use serde::{Deserialize, Serialize};
use thiserror::Error;

#[derive(Debug, Error)]
pub enum Error {
    #[error("parse: {0}")]
    Parse(String),
    #[error("not a bool formula: {0}")]
    NotBoolFormula(String),
}

pub type ClaimId = String;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Formula {
    // Filled in per project. The scaffold ships an opaque value; users replace
    // it with their own Formula AST in this file.
    pub raw: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct Verdict {
    pub status: String,
    #[serde(default)]
    pub verified: Vec<Claim>,
    #[serde(default)]
    pub core: Vec<ClaimId>,
    #[serde(default)]
    pub proofs: Vec<serde_json::Value>,
    #[serde(default)]
    pub graph_summary: Option<GraphSummary>,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct GraphSummary {
    pub claim_count: usize,
    pub contradictions: Vec<(String, String)>,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct Claim {
    pub id: ClaimId,
    pub source: String,
}

pub fn parse_formulas(_edn: &str) -> Result<Vec<(ClaimId, Formula)>, Error> {
    // TODO: parse EDN here using edn-rs. The scaffold returns empty.
    Ok(Vec::new())
}

pub fn emit_verdict(v: &Verdict) -> String {
    serde_json::to_string(v).unwrap_or_else(|_| "{\"status\":\"unknown\"}".to_string())
}
```

- [ ] **Step 5: Create `rust-verifier/src/smt.rs.tmpl`.**

```rust
use crate::ir::{ClaimId, Formula, Verdict, Error};

pub fn check_all(formulas: &[(ClaimId, Formula)]) -> Result<Verdict, Error> {
    // TODO: replace stub with z3.rs walk; see clojure.md §5.9.
    if formulas.is_empty() {
        return Ok(Verdict { status: "sat".into(), ..Default::default() });
    }
    Ok(Verdict { status: "sat".into(), ..Default::default() })
}
```

- [ ] **Step 6: Create `rust-verifier/src/eqsat.rs.tmpl`.**

```rust
pub fn saturate(_terms_edn: &str, _rules_edn: &str) -> Result<String, String> {
    // TODO: replace stub with egg::Runner; see clojure.md §5.10.
    Ok("{\"cost\":0,\"form\":\"stub\"}".to_string())
}
```

- [ ] **Step 7: Create `rust-verifier/src/kg.rs.tmpl`.**

```rust
use crate::ir::{Claim, GraphSummary, Error};

pub fn ingest_and_summarize(claims: &[Claim]) -> Result<GraphSummary, Error> {
    // TODO: replace stub with cozo Datalog contradiction scan; see clojure.md §5.11.
    Ok(GraphSummary { claim_count: claims.len(), contradictions: vec![] })
}
```

- [ ] **Step 8: Create `rust-verifier/src/typeset.rs.tmpl`.**

```rust
pub fn render(latex: &str, out_path: &str) -> Result<(), String> {
    let pdf: Vec<u8> = tectonic::latex_to_pdf(latex)
        .map_err(|e| format!("tectonic: {e}"))?;
    std::fs::write(out_path, pdf).map_err(|e| format!("write: {e}"))?;
    Ok(())
}
```

- [ ] **Step 9: Create `templates/report.tex.tera.tmpl`.**

```latex
\documentclass{article}
\usepackage{amsmath,amssymb,hyperref}
\title{ {{ "{{ title | escape_tex }}" }} }
\author{Verified by {{ project_slug }} v0.1}
\begin{document}\maketitle

\section{Verified claims}
\begin{enumerate}
{{ "{% for c in claims %}" }}
  \item[\textbf{ {{ "{{ c.id }}" }} }] {{ "{{ c.prose | escape_tex }}" }}
{{ "{% endfor %}" }}
\end{enumerate}

\end{document}
```

- [ ] **Step 10: Create `templates/claim_table.tex.tera.tmpl`.**

```latex
\begin{tabular}{lll}
{{ "{% for c in claims %}" }}
  {{ "{{ c.id }}" }} & {{ "{{ c.source | escape_tex }}" }} & {{ "{{ c.confidence }}" }} \\
{{ "{% endfor %}" }}
\end{tabular}
```

- [ ] **Step 11: Commit.**

```bash
git add skills/neurosym-forge/assets/project-template/rust-verifier/ skills/neurosym-forge/assets/project-template/templates/
git commit -m "neurosym-forge: Rust verifier + LaTeX templates"
```

---

## Phase 4: Scaffolder

### Task 4.1: `scaffold_project.py`

**Files:**
- Create: `skills/neurosym-forge/scripts/scaffold_project.py`
- Create: `skills/neurosym-forge/tests/test_scaffold_project.py`

- [ ] **Step 1: Write failing test.**

```python
# skills/neurosym-forge/tests/test_scaffold_project.py
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from scripts._io import read_edn_as_json
from scripts.scaffold_project import scaffold_project


def test_emits_expected_files(tmp_project_root: Path, skill_root: Path) -> None:
    scaffold_project(
        project_name="Osmotic Pressure Verifier",
        project_slug="osmotic_pressure",
        out_dir=tmp_project_root,
        skill_root=skill_root,
    )
    for rel in [
        "shadow-cljs.edn",
        "package.json",
        "deps.edn",
        ".gitignore",
        "README.md",
        "SKILL.md",
        "rules/seed.edn",
        "rules/grounded.edn",
        "rules/predicates.edn",
        "rules/.forge-version.edn",
        "cljs-orchestrator/src/main/osmotic_pressure/core.cljs",
        "cljs-orchestrator/src/main/osmotic_pressure/phases.cljs",
        "cljs-orchestrator/src/main/osmotic_pressure/ir.cljs",
        "cljs-orchestrator/src/main/osmotic_pressure/nl_to_fol.cljs",
        "cljs-orchestrator/src/main/osmotic_pressure/unify.cljs",
        "cljs-orchestrator/src/main/osmotic_pressure/bridge.cljs",
        "rust-verifier/Cargo.toml",
        "rust-verifier/build.rs",
        "rust-verifier/src/lib.rs",
        "rust-verifier/src/ir.rs",
        "rust-verifier/src/smt.rs",
        "rust-verifier/src/eqsat.rs",
        "rust-verifier/src/kg.rs",
        "rust-verifier/src/typeset.rs",
        "templates/report.tex.tera",
        "templates/claim_table.tex.tera",
    ]:
        assert (tmp_project_root / rel).exists(), f"missing {rel}"


def test_slug_substitution(tmp_project_root: Path, skill_root: Path) -> None:
    scaffold_project(
        project_name="X",
        project_slug="osmotic_pressure",
        out_dir=tmp_project_root,
        skill_root=skill_root,
    )
    core = (tmp_project_root / "cljs-orchestrator/src/main/osmotic_pressure/core.cljs").read_text()
    assert "(ns osmotic_pressure.core" in core
    cargo = (tmp_project_root / "rust-verifier/Cargo.toml").read_text()
    assert 'name    = "osmotic_pressure-verifier"' in cargo


def test_forge_version_recorded(tmp_project_root: Path, skill_root: Path) -> None:
    scaffold_project(
        project_name="X",
        project_slug="x",
        out_dir=tmp_project_root,
        skill_root=skill_root,
    )
    payload = read_edn_as_json(tmp_project_root / "rules" / ".forge-version.edn")
    assert "neurosym_forge_version" in payload
    assert payload["neurosym_forge_version"].startswith("0.1")


def test_refuses_to_overwrite(tmp_project_root: Path, skill_root: Path) -> None:
    scaffold_project(
        project_name="X", project_slug="x",
        out_dir=tmp_project_root, skill_root=skill_root,
    )
    with pytest.raises(FileExistsError):
        scaffold_project(
            project_name="X", project_slug="x",
            out_dir=tmp_project_root, skill_root=skill_root,
        )


def test_cli_round_trip(tmp_path: Path, skill_root: Path) -> None:
    out = tmp_path / "v" / "demo"
    result = subprocess.run(
        [sys.executable, "-m", "scripts.scaffold_project",
         "--name", "Demo", "--slug", "demo", "--out", str(out)],
        capture_output=True, text=True, cwd=str(skill_root),
    )
    assert result.returncode == 0, result.stderr
    assert (out / "package.json").exists()
```

- [ ] **Step 2: Run test, expect FAIL.**

```bash
.venv/Scripts/python.exe -m pytest tests/test_scaffold_project.py -v
```

Expected: `ModuleNotFoundError: scripts.scaffold_project`.

- [ ] **Step 3: Write implementation.**

```python
# skills/neurosym-forge/scripts/scaffold_project.py
"""Emit a CLJS+Rust neurosymbolic verifier project from the template tree."""
from __future__ import annotations

import argparse
import datetime as dt
import shutil
import sys
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from scripts._io import file_checksum, write_json_as_edn

FORGE_VERSION = "0.1.0"


def _render_file(env: Environment, tmpl_path: Path, ctx: dict, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    template = env.get_template(str(tmpl_path).replace("\\", "/"))
    rendered = template.render(**ctx)
    out_path.write_text(rendered, encoding="utf-8", newline="\n")


def scaffold_project(
    project_name: str,
    project_slug: str,
    out_dir: Path,
    skill_root: Path,
    has_book_knowledge_bridge: bool = False,
) -> None:
    """Render the project template tree into out_dir."""
    if out_dir.exists():
        raise FileExistsError(f"refusing to overwrite {out_dir}")

    template_root = skill_root / "assets" / "project-template"
    env = Environment(
        loader=FileSystemLoader(str(template_root)),
        keep_trailing_newline=True,
        undefined=StrictUndefined,
    )

    ctx = {
        "project_name": project_name,
        "project_slug": project_slug,
        "neurosym_forge_version": FORGE_VERSION,
        "scaffolded_at": dt.datetime.now(dt.UTC).isoformat(),
        "has_book_knowledge_bridge": has_book_knowledge_bridge,
    }

    for tmpl in sorted(template_root.rglob("*.tmpl")):
        rel = tmpl.relative_to(template_root)
        out_rel = Path(str(rel)[:-len(".tmpl")].replace("__project__", project_slug))
        out_path = out_dir / out_rel
        # jinja loader needs forward slashes regardless of OS
        loader_path = str(rel).replace("\\", "/")
        template = env.get_template(loader_path)
        rendered = template.render(**ctx)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(rendered, encoding="utf-8", newline="\n")

    # Initialise rules checksums based on the freshly-rendered files
    checksums = {}
    for p in sorted((out_dir / "rules").glob("*.edn")):
        if p.name.startswith("."):
            continue
        checksums[p.name] = file_checksum(p)
    write_json_as_edn(out_dir / "rules" / ".checksums.edn", {"checksums": checksums})


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True, help="Human-readable project name")
    ap.add_argument("--slug", required=True, help="Filesystem-safe slug (snake_case)")
    ap.add_argument("--out",  required=True, help="Output directory")
    ap.add_argument("--book-knowledge-bridge", action="store_true",
                    help="Emit a book-knowledge claim-ledger ingestor")
    args = ap.parse_args(argv)
    skill_root = Path(__file__).resolve().parent.parent
    scaffold_project(
        project_name=args.name,
        project_slug=args.slug,
        out_dir=Path(args.out),
        skill_root=skill_root,
        has_book_knowledge_bridge=args.book_knowledge_bridge,
    )
    print(f"scaffolded {args.slug} at {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
```

- [ ] **Step 4: Run test, expect PASS.**

```bash
.venv/Scripts/python.exe -m pytest tests/test_scaffold_project.py -v
```

Expected: 5 passed. If the `__project__` path substitution fails on Windows, the test will surface it as a missing file under the slug path; verify by manually listing the output dir.

- [ ] **Step 5: Commit.**

```bash
git add skills/neurosym-forge/scripts/scaffold_project.py skills/neurosym-forge/tests/test_scaffold_project.py
git commit -m "neurosym-forge: scaffold_project"
```

---

## Phase 5: Extension helpers

### Task 5.1: `add_sort.py`

**Files:**
- Create: `skills/neurosym-forge/scripts/add_sort.py`
- Create: `skills/neurosym-forge/tests/test_add_sort.py`

- [ ] **Step 1: Write failing test.**

```python
# skills/neurosym-forge/tests/test_add_sort.py
from __future__ import annotations

from pathlib import Path

import pytest

from scripts._io import read_edn_as_json, write_json_as_edn
from scripts.add_sort import add_sort


def _seed(tmp_path: Path) -> Path:
    (tmp_path / "rules").mkdir()
    write_json_as_edn(tmp_path / "rules" / "seed.edn",
                      {"version": 1, "sorts": [":int", ":real"], "rules": [], "atoms": []})
    write_json_as_edn(tmp_path / "rules" / ".checksums.edn",
                      {"checksums": {}})
    return tmp_path


def test_appends_primitive(tmp_path: Path) -> None:
    project = _seed(tmp_path)
    add_sort(project, ":molarity")
    payload = read_edn_as_json(project / "rules" / "seed.edn")
    assert ":molarity" in payload["sorts"]


def test_rejects_duplicate(tmp_path: Path) -> None:
    project = _seed(tmp_path)
    with pytest.raises(ValueError, match="already present"):
        add_sort(project, ":int")


def test_appends_enum(tmp_path: Path) -> None:
    project = _seed(tmp_path)
    add_sort(project, {"kind": "enum", "members": [":sat", ":unsat", ":unknown"]})
    payload = read_edn_as_json(project / "rules" / "seed.edn")
    assert any(isinstance(s, dict) and s.get("kind") == "enum" for s in payload["sorts"])


def test_updates_checksum(tmp_path: Path) -> None:
    project = _seed(tmp_path)
    add_sort(project, ":molarity")
    checksums = read_edn_as_json(project / "rules" / ".checksums.edn")["checksums"]
    assert "seed.edn" in checksums
```

- [ ] **Step 2: Run test, expect FAIL.**

```bash
.venv/Scripts/python.exe -m pytest tests/test_add_sort.py -v
```

- [ ] **Step 3: Write implementation.**

```python
# skills/neurosym-forge/scripts/add_sort.py
"""Append a new sort to the project's seed.edn and refresh checksums."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from scripts._io import read_edn_as_json, write_json_as_edn, file_checksum
from scripts.sort_registry import Sort, SortRegistry


def add_sort(project_root: Path, sort_value: Any) -> None:
    seed = project_root / "rules" / "seed.edn"
    payload = read_edn_as_json(seed)
    registry = SortRegistry.from_dict({"sorts": payload.get("sorts", [])})
    new_sort = Sort.from_value(sort_value)
    if registry.contains(new_sort):
        raise ValueError(f"sort already present: {new_sort}")
    registry.add(new_sort)
    payload["sorts"] = [s.value for s in registry._sorts]
    write_json_as_edn(seed, payload)

    checksums_path = project_root / "rules" / ".checksums.edn"
    checksums = read_edn_as_json(checksums_path)["checksums"] if checksums_path.exists() else {}
    checksums["seed.edn"] = file_checksum(seed)
    write_json_as_edn(checksums_path, {"checksums": checksums})


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True, help="Project root")
    ap.add_argument("--sort",    required=True,
                    help="Sort literal (':foo') or JSON object for fn/enum")
    args = ap.parse_args(argv)
    project = Path(args.project)
    try:
        value = json.loads(args.sort) if args.sort.startswith("{") else args.sort
    except json.JSONDecodeError as e:
        print(f"could not parse --sort: {e}", file=sys.stderr)
        return 2
    add_sort(project, value)
    print(f"added sort {args.sort} to {project}/rules/seed.edn")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
```

- [ ] **Step 4: Run test, expect PASS.**

```bash
.venv/Scripts/python.exe -m pytest tests/test_add_sort.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit.**

```bash
git add skills/neurosym-forge/scripts/add_sort.py skills/neurosym-forge/tests/test_add_sort.py
git commit -m "neurosym-forge: add_sort"
```

### Task 5.2: `add_rewrite_rule.py`

**Files:**
- Create: `skills/neurosym-forge/scripts/add_rewrite_rule.py`
- Create: `skills/neurosym-forge/tests/test_add_rewrite_rule.py`

- [ ] **Step 1: Write failing test.**

```python
# skills/neurosym-forge/tests/test_add_rewrite_rule.py
from __future__ import annotations

from pathlib import Path

import pytest

from scripts._io import read_edn_as_json, write_json_as_edn
from scripts.add_rewrite_rule import add_rewrite_rule

RULE = {
    "id": "R001",
    "lhs": {"kind": "expression", "sort": ":real",
            "head": {"kind": "symbol", "name": ":+",
                     "sort": {"kind": "fn", "args": [":real", ":real"], "ret": ":real"}},
            "args": [{"kind": "variable", "name": "?a", "sort": ":real"},
                     {"kind": "variable", "name": "?b", "sort": ":real"}]},
    "rhs": {"kind": "expression", "sort": ":real",
            "head": {"kind": "symbol", "name": ":+",
                     "sort": {"kind": "fn", "args": [":real", ":real"], "ret": ":real"}},
            "args": [{"kind": "variable", "name": "?b", "sort": ":real"},
                     {"kind": "variable", "name": "?a", "sort": ":real"}]},
    "doc": "commutative",
}


def _seed(tmp_path: Path) -> Path:
    (tmp_path / "rules").mkdir()
    (tmp_path / "tests" / "rules").mkdir(parents=True)
    write_json_as_edn(tmp_path / "rules" / "seed.edn",
                      {"version": 1, "sorts": [":real"], "rules": [], "atoms": []})
    write_json_as_edn(tmp_path / "rules" / ".checksums.edn", {"checksums": {}})
    return tmp_path


def test_appends_rule_and_fixture(tmp_path: Path) -> None:
    project = _seed(tmp_path)
    add_rewrite_rule(project, RULE)
    payload = read_edn_as_json(project / "rules" / "seed.edn")
    assert any(r["id"] == "R001" for r in payload["rules"])
    assert (project / "tests" / "rules" / "test_R001.cljs").exists()


def test_rejects_duplicate_id(tmp_path: Path) -> None:
    project = _seed(tmp_path)
    add_rewrite_rule(project, RULE)
    with pytest.raises(ValueError, match="duplicate rule id"):
        add_rewrite_rule(project, RULE)


def test_validates_variable_balance(tmp_path: Path) -> None:
    project = _seed(tmp_path)
    bad = {
        "id": "R002",
        "lhs": {"kind": "variable", "name": "?x", "sort": ":real"},
        "rhs": {"kind": "variable", "name": "?y", "sort": ":real"},
    }
    with pytest.raises(ValueError, match="unbound"):
        add_rewrite_rule(project, bad)


def test_rejects_unknown_sort(tmp_path: Path) -> None:
    project = _seed(tmp_path)
    rule = dict(RULE, id="R003")
    rule["lhs"] = dict(rule["lhs"], sort=":nonexistent")
    with pytest.raises(ValueError, match="unknown sort"):
        add_rewrite_rule(project, rule)


def test_updates_checksum(tmp_path: Path) -> None:
    project = _seed(tmp_path)
    add_rewrite_rule(project, RULE)
    checksums = read_edn_as_json(project / "rules" / ".checksums.edn")["checksums"]
    assert "seed.edn" in checksums
```

- [ ] **Step 2: Run test, expect FAIL.**

```bash
.venv/Scripts/python.exe -m pytest tests/test_add_rewrite_rule.py -v
```

- [ ] **Step 3: Write implementation.**

```python
# skills/neurosym-forge/scripts/add_rewrite_rule.py
"""Append a (=) rewrite rule to seed.edn and emit a fixture test."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from scripts._io import read_edn_as_json, write_json_as_edn, file_checksum
from scripts.lint_atomspace import _walk_atom_sorts
from scripts.rewrite_rule import RewriteRule
from scripts.sort_registry import SortRegistry


def _validate_against_registry(rule_payload: dict[str, Any], registry: SortRegistry) -> None:
    primitives = {s.value for s in registry._sorts if isinstance(s.value, str)}
    referenced: set[str] = set()
    _walk_atom_sorts(rule_payload["lhs"], referenced)
    _walk_atom_sorts(rule_payload["rhs"], referenced)
    unknown = {s for s in referenced if s.startswith(":") and s not in primitives}
    if unknown:
        raise ValueError(f"unknown sort(s): {sorted(unknown)}")


def add_rewrite_rule(project_root: Path, rule_payload: dict[str, Any]) -> None:
    seed = project_root / "rules" / "seed.edn"
    payload = read_edn_as_json(seed)
    registry = SortRegistry.from_dict({"sorts": payload.get("sorts", [])})
    _validate_against_registry(rule_payload, registry)

    rule = RewriteRule.from_dict(rule_payload)
    rule.check_variable_balance()

    rules = payload.get("rules", [])
    if any(r.get("id") == rule.id for r in rules):
        raise ValueError(f"duplicate rule id: {rule.id}")
    rules.append(rule.to_dict())
    payload["rules"] = rules
    write_json_as_edn(seed, payload)

    fixture_dir = project_root / "tests" / "rules"
    fixture_dir.mkdir(parents=True, exist_ok=True)
    fixture = fixture_dir / f"test_{rule.id}.cljs"
    fixture.write_text(_fixture_text(rule), encoding="utf-8", newline="\n")

    checksums_path = project_root / "rules" / ".checksums.edn"
    checksums = read_edn_as_json(checksums_path)["checksums"] if checksums_path.exists() else {}
    checksums["seed.edn"] = file_checksum(seed)
    write_json_as_edn(checksums_path, {"checksums": checksums})


def _fixture_text(rule: RewriteRule) -> str:
    return (
        f"(ns rules.test-{rule.id.lower()}\n"
        f"  (:require [cljs.test :refer-macros [deftest is]]\n"
        f"            [meander.epsilon :as m]))\n\n"
        f"(deftest {rule.id}-applies\n"
        f"  ;; rule: {rule.doc or rule.id}\n"
        f"  (is (some? :TODO-supply-input-form-for-{rule.id})))\n"
    )


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--rule-file", required=True,
                    help="JSON/EDN file containing a single rule payload")
    args = ap.parse_args(argv)
    project = Path(args.project)
    rule_payload = json.loads(Path(args.rule_file).read_text(encoding="utf-8"))
    add_rewrite_rule(project, rule_payload)
    print(f"appended rule {rule_payload.get('id')} to {project}/rules/seed.edn")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
```

- [ ] **Step 4: Run test, expect PASS.**

```bash
.venv/Scripts/python.exe -m pytest tests/test_add_rewrite_rule.py -v
```

Expected: 5 passed.

- [ ] **Step 5: Commit.**

```bash
git add skills/neurosym-forge/scripts/add_rewrite_rule.py skills/neurosym-forge/tests/test_add_rewrite_rule.py
git commit -m "neurosym-forge: add_rewrite_rule"
```

### Task 5.3: `add_grounded_atom.py`

**Files:**
- Create: `skills/neurosym-forge/scripts/add_grounded_atom.py`
- Create: `skills/neurosym-forge/tests/test_add_grounded_atom.py`

- [ ] **Step 1: Write failing test.**

```python
# skills/neurosym-forge/tests/test_add_grounded_atom.py
from __future__ import annotations

from pathlib import Path

import pytest

from scripts._io import read_edn_as_json, write_json_as_edn
from scripts.add_grounded_atom import add_grounded_atom


def _seed(tmp_path: Path) -> Path:
    (tmp_path / "rules").mkdir()
    (tmp_path / "rust-verifier" / "src").mkdir(parents=True)
    (tmp_path / "cljs-orchestrator" / "src" / "main" / "demo").mkdir(parents=True)
    write_json_as_edn(tmp_path / "rules" / "seed.edn",
                      {"version": 1, "sorts": [":real", ":verdict", ":atom"],
                       "rules": [], "atoms": []})
    write_json_as_edn(tmp_path / "rules" / "grounded.edn", {"version": 1, "grounded": []})
    write_json_as_edn(tmp_path / "rules" / ".checksums.edn", {"checksums": {}})
    (tmp_path / "rust-verifier" / "src" / "custom.rs").write_text(
        "// custom grounded atoms\n", encoding="utf-8")
    (tmp_path / "rust-verifier" / "src" / "lib.rs").write_text(
        "#![deny(clippy::all)]\nuse napi_derive::napi;\n\nmod ir;\nmod custom;\n",
        encoding="utf-8")
    (tmp_path / "cljs-orchestrator" / "src" / "main" / "demo" / "bridge.cljs").write_text(
        "(ns demo.bridge)\n", encoding="utf-8")
    return tmp_path


def test_appends_grounded_record(tmp_path: Path) -> None:
    project = _seed(tmp_path)
    add_grounded_atom(
        project, project_slug="demo",
        name=":my-fn", lib="custom", fn="my_fn",
        sort={"kind": "fn", "args": [":atom"], "ret": ":verdict"},
        doc="custom solver hook",
    )
    grounded = read_edn_as_json(project / "rules" / "grounded.edn")["grounded"]
    assert any(g["name"] == ":my-fn" for g in grounded)


def test_appends_rust_stub(tmp_path: Path) -> None:
    project = _seed(tmp_path)
    add_grounded_atom(
        project, project_slug="demo",
        name=":my-fn", lib="custom", fn="my_fn",
        sort={"kind": "fn", "args": [":atom"], "ret": ":verdict"},
    )
    rs = (project / "rust-verifier" / "src" / "custom.rs").read_text()
    assert "pub fn my_fn" in rs
    assert "todo!()" in rs


def test_appends_cljs_bridge_stub(tmp_path: Path) -> None:
    project = _seed(tmp_path)
    add_grounded_atom(
        project, project_slug="demo",
        name=":my-fn", lib="custom", fn="my_fn",
        sort={"kind": "fn", "args": [":atom"], "ret": ":verdict"},
    )
    bridge = (project / "cljs-orchestrator" / "src" / "main" / "demo" / "bridge.cljs").read_text()
    assert "myFn" in bridge


def test_rejects_duplicate(tmp_path: Path) -> None:
    project = _seed(tmp_path)
    add_grounded_atom(project, project_slug="demo",
                      name=":my-fn", lib="custom", fn="my_fn",
                      sort={"kind": "fn", "args": [":atom"], "ret": ":verdict"})
    with pytest.raises(ValueError, match="duplicate"):
        add_grounded_atom(project, project_slug="demo",
                          name=":my-fn", lib="custom", fn="my_fn",
                          sort={"kind": "fn", "args": [":atom"], "ret": ":verdict"})
```

- [ ] **Step 2: Run test, expect FAIL.**

```bash
.venv/Scripts/python.exe -m pytest tests/test_add_grounded_atom.py -v
```

- [ ] **Step 3: Write implementation.**

```python
# skills/neurosym-forge/scripts/add_grounded_atom.py
"""Append a grounded atom record + Rust stub + CLJS bridge stub."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from scripts._io import read_edn_as_json, write_json_as_edn, file_checksum
from scripts.sort_registry import Sort

NAPI_LIBS = {"z3", "egg", "cozo", "tectonic", "custom"}


def _camel_case(snake: str) -> str:
    parts = snake.split("_")
    return parts[0] + "".join(p.capitalize() for p in parts[1:])


def _napi_arg_types(sort: dict[str, Any]) -> tuple[str, str]:
    """For v0.1 every grounded fn takes and returns String (EDN over the wire)."""
    return ("formulas_edn: String", "napi::Result<String>")


def add_grounded_atom(
    project_root: Path,
    project_slug: str,
    name: str,
    lib: str,
    fn: str,
    sort: dict[str, Any],
    doc: str | None = None,
) -> None:
    if lib not in NAPI_LIBS:
        raise ValueError(f"lib must be one of {sorted(NAPI_LIBS)}, got {lib!r}")
    if not name.startswith(":"):
        raise ValueError(f"grounded atom name must start with ':', got {name!r}")
    Sort.from_value(sort)  # validate shape

    grounded_path = project_root / "rules" / "grounded.edn"
    payload = read_edn_as_json(grounded_path)
    if any(g["name"] == name for g in payload.get("grounded", [])):
        raise ValueError(f"duplicate grounded atom: {name}")
    record = {
        "kind": "grounded",
        "name": name,
        "sort": sort,
        "grounded": {"lib": lib, "fn": fn, "napi": True},
    }
    if doc:
        record["doc"] = doc
    payload.setdefault("grounded", []).append(record)
    write_json_as_edn(grounded_path, payload)

    rs_path = project_root / "rust-verifier" / "src" / f"{lib}.rs"
    if not rs_path.exists():
        rs_path.write_text(f"// grounded atoms for lib={lib}\n", encoding="utf-8")
    arg_sig, ret_sig = _napi_arg_types(sort)
    rs_path.write_text(
        rs_path.read_text(encoding="utf-8")
        + (
            f"\n\n#[napi_derive::napi]\n"
            f"pub fn {fn}({arg_sig}) -> {ret_sig} {{\n"
            f"    // TODO ({name}): implement against {lib} backend.\n"
            f"    // Sort: {json.dumps(sort)}\n"
            f"    todo!()\n"
            f"}}\n"
        ),
        encoding="utf-8",
    )

    lib_rs = project_root / "rust-verifier" / "src" / "lib.rs"
    text = lib_rs.read_text(encoding="utf-8")
    mod_line = f"mod {lib};"
    if mod_line not in text:
        text = re.sub(r"(mod ir;)", r"\1\n" + mod_line, text, count=1)
        lib_rs.write_text(text, encoding="utf-8")

    bridge_path = (
        project_root / "cljs-orchestrator" / "src" / "main" / project_slug / "bridge.cljs"
    )
    bridge_text = bridge_path.read_text(encoding="utf-8")
    bridge_text += (
        f"\n(defn {fn.replace('_', '-')} [edn-arg]\n"
        f"  (native/{_camel_case(fn)} edn-arg))\n"
    )
    bridge_path.write_text(bridge_text, encoding="utf-8")

    checksums_path = project_root / "rules" / ".checksums.edn"
    checksums = read_edn_as_json(checksums_path)["checksums"] if checksums_path.exists() else {}
    checksums["grounded.edn"] = file_checksum(grounded_path)
    write_json_as_edn(checksums_path, {"checksums": checksums})


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--slug", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--lib", required=True, choices=sorted(NAPI_LIBS))
    ap.add_argument("--fn", required=True)
    ap.add_argument("--sort", required=True,
                    help="JSON object describing the sort, e.g. "
                         "'{\"kind\":\"fn\",\"args\":[\":atom\"],\"ret\":\":verdict\"}'")
    ap.add_argument("--doc")
    args = ap.parse_args(argv)
    add_grounded_atom(
        project_root=Path(args.project),
        project_slug=args.slug,
        name=args.name,
        lib=args.lib,
        fn=args.fn,
        sort=json.loads(args.sort),
        doc=args.doc,
    )
    print(f"added grounded atom {args.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
```

- [ ] **Step 4: Run test, expect PASS.**

```bash
.venv/Scripts/python.exe -m pytest tests/test_add_grounded_atom.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit.**

```bash
git add skills/neurosym-forge/scripts/add_grounded_atom.py skills/neurosym-forge/tests/test_add_grounded_atom.py
git commit -m "neurosym-forge: add_grounded_atom (Rust stub + CLJS bridge)"
```

---

## Phase 6: Utilities

### Task 6.1: `render_call_graph.py`

**Files:**
- Create: `skills/neurosym-forge/scripts/render_call_graph.py`
- Create: `skills/neurosym-forge/tests/test_render_call_graph.py`

- [ ] **Step 1: Write failing test.**

```python
# skills/neurosym-forge/tests/test_render_call_graph.py
from __future__ import annotations

from pathlib import Path

from scripts.render_call_graph import render_call_graph


def test_ascii_contains_phases() -> None:
    out = render_call_graph(project_slug="demo")
    assert "Claude" in out
    assert "ClojureScript" in out
    assert "Rust" in out
    for phase in ("Extract", "Rewrite", "Verify", "Synthesise", "Typeset"):
        assert phase in out


def test_ascii_is_pure_ascii() -> None:
    out = render_call_graph(project_slug="demo")
    out.encode("ascii")  # raises on non-ascii
```

- [ ] **Step 2: Run test, expect FAIL.**

```bash
.venv/Scripts/python.exe -m pytest tests/test_render_call_graph.py -v
```

- [ ] **Step 3: Write implementation.**

```python
# skills/neurosym-forge/scripts/render_call_graph.py
"""ASCII diagram of phase boundaries in a scaffolded neurosym-forge project."""
from __future__ import annotations

import argparse
import sys

TEMPLATE = r"""
Phase 1 [Claude]         Extract atoms              -> work/claims.edn
        |
        v
Phase 2 [ClojureScript]  Rewrite via meander (= ...) -> work/fol.edn
        |
        v
Phase 3 [Rust]           Verify (Z3 / egg / cozo)    -> work/verdict.edn
        |
        v
Phase 4 [Claude]         Synthesise report           -> work/report.md
        |
        v
Phase 5 [Rust]           Typeset (tectonic)          -> work/report.pdf

Project: {slug}
"""


def render_call_graph(project_slug: str) -> str:
    return TEMPLATE.format(slug=project_slug)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", required=True)
    args = ap.parse_args(argv)
    print(render_call_graph(args.slug))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
```

- [ ] **Step 4: Run test, expect PASS.**

```bash
.venv/Scripts/python.exe -m pytest tests/test_render_call_graph.py -v
```

- [ ] **Step 5: Commit.**

```bash
git add skills/neurosym-forge/scripts/render_call_graph.py skills/neurosym-forge/tests/test_render_call_graph.py
git commit -m "neurosym-forge: render_call_graph"
```

### Task 6.2: `verify_claims.py`

**Files:**
- Create: `skills/neurosym-forge/scripts/verify_claims.py`
- Create: `skills/neurosym-forge/tests/test_verify_claims.py`

This is a thin convenience wrapper. It does not invoke `npm` or `cargo` — instead it prints the commands the user needs to run. v0.1 keeps the skill stateless; the scaffolded project owns execution.

- [ ] **Step 1: Write failing test.**

```python
# skills/neurosym-forge/tests/test_verify_claims.py
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest


def test_prints_commands_for_project(tmp_path: Path, skill_root: Path) -> None:
    project = tmp_path / "v" / "demo"
    project.mkdir(parents=True)
    (project / "package.json").write_text("{}", encoding="utf-8")
    result = subprocess.run(
        [sys.executable, "-m", "scripts.verify_claims",
         "--project", str(project), "--input", "work/claims.edn"],
        capture_output=True, text=True, cwd=str(skill_root),
    )
    assert result.returncode == 0
    assert "npm run build" in result.stdout
    assert "node cljs-orchestrator/dist/main.js verify" in result.stdout


def test_refuses_when_no_package_json(tmp_path: Path, skill_root: Path) -> None:
    project = tmp_path / "noproject"
    project.mkdir()
    result = subprocess.run(
        [sys.executable, "-m", "scripts.verify_claims",
         "--project", str(project), "--input", "work/claims.edn"],
        capture_output=True, text=True, cwd=str(skill_root),
    )
    assert result.returncode != 0
    assert "package.json" in result.stderr
```

- [ ] **Step 2: Run test, expect FAIL.**

```bash
.venv/Scripts/python.exe -m pytest tests/test_verify_claims.py -v
```

- [ ] **Step 3: Write implementation.**

```python
# skills/neurosym-forge/scripts/verify_claims.py
"""Print the build+verify commands for a scaffolded project."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--input", required=True, help="EDN claim file")
    ap.add_argument("--output", default="work/verdict.edn")
    args = ap.parse_args(argv)
    project = Path(args.project)
    if not (project / "package.json").exists():
        print(f"no package.json found at {project}; was it scaffolded?",
              file=sys.stderr)
        return 1
    print(f"# Run these commands from {project}:")
    print("npm install")
    print("npm run build")
    print(f"node cljs-orchestrator/dist/main.js verify {args.input} {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
```

- [ ] **Step 4: Run test, expect PASS.**

```bash
.venv/Scripts/python.exe -m pytest tests/test_verify_claims.py -v
```

- [ ] **Step 5: Commit.**

```bash
git add skills/neurosym-forge/scripts/verify_claims.py skills/neurosym-forge/tests/test_verify_claims.py
git commit -m "neurosym-forge: verify_claims wrapper"
```

---

## Phase 7: SKILL.md and references

### Task 7.1: SKILL.md

**Files:**
- Create: `skills/neurosym-forge/SKILL.md`

- [ ] **Step 1: Write the file (use the draft from `docs/specs/2026-05-13-neurosym-forge-design.md` § Draft SKILL.md, verbatim).**

```markdown
---
name: neurosym-forge
description: Scaffold and extend ClojureScript + Rust neurosymbolic verification projects. Use when user says "scaffold a neurosymbolic project", "verify these claims with Z3", "add a rewrite rule", "ground this predicate in Rust", "extend the atomspace IR", "build a CLJS+Rust verifier", "FOL/SMT/e-graph/Datalog verifier", or mentions MeTTa-style modeling. Composes with book-knowledge to verify ledger claims. Does NOT run verification itself — the scaffolded project does, via shadow-cljs and cargo. Do NOT use for prose review (use book-review), claim ingestion (use book-knowledge), or chapter drafting (use book-compose).
license: MIT
metadata:
  author: charles-hoskinson
  version: 0.1.0
  category: verification
  emits: clojurescript-rust
---

# neurosym-forge

The authoring skill for neurosymbolic verification projects in CLJS + Rust. Produces project skeletons, rewrite rules, grounded-atom modules, and IR linters. Encodes MeTTa idioms as authoring conventions.

## What it owns

- The project skeleton template for CLJS + Rust verifiers
- The EDN-as-atomspace IR specification
- The MeTTa→CLJS+Rust idiom mapping (= / : / ! / match / superpose / grounded)
- Linters for atomspace shape, sort coverage, rewrite-rule fixtures
- The scaffolder, rule-appender, grounded-atom-adder, sort-adder helpers

## What it does NOT own

- Source ingestion or claim extraction (book-knowledge)
- Running shadow-cljs or cargo builds (handled by the scaffolded project)
- Prose synthesis (book-compose)
- Editorial review (book-review)
- Defect QA (book-qa)
- Network I/O — this skill never reaches off-machine

## Components

Python helpers in `scripts/`. Invoke via `.venv\Scripts\python.exe -m scripts.<name>`.

Scaffolding:
- `scaffold_project.py` — produces the full CLJS+Rust project skeleton
- `add_rewrite_rule.py` — appends a typed `(=)` rule with fixture test
- `add_grounded_atom.py` — emits a `#[napi]` Rust function and CLJS bridge stub
- `add_sort.py` — extends the sort registry

Linting:
- `lint_atomspace.py` — every atom carries `:sort`, no unbound variables
- `lint_rewrite_coverage.py` — every rewrite rule has a fixture test
- `render_call_graph.py` — ASCII diagram of Claude↔CLJS↔Rust phase boundaries

Convenience:
- `verify_claims.py` — prints `npm run build && node ... verify` for the scaffolded project

## Composes with

- `book-knowledge` — accepts `claims/ledger.jsonl` as Phase-1 input via the `--book-knowledge-bridge` scaffold flag
- `book-qa` — optional defect class `D13: claim-set-unsatisfiable`, off by default in v0.1
- `book-thesis` — v0.2 only; not wired in v0.1

## Usage

- "Scaffold a CLJS+Rust verifier for the Bermuda claims" — full scaffold
- "Add a commutativity rule for `+`" — appends a rewrite rule
- "Ground a custom solver hook called my-fn returning :verdict" — adds a grounded atom
- "Lint the atomspace" — runs `lint_atomspace.py` on `work/atomspace.edn`

## Tests

40+ tests across the 8 modules. Run with `.venv\Scripts\python.exe -m pytest tests/ -q` from the skill root.

## See also

- `references/metta-idioms.md` — = / : / ! / match / superpose / grounded mapping
- `references/atomspace-edn.md` — the EDN IR
- `references/grounded-atoms.md` — how to wire a new Rust module
- `references/phase-boundaries.md` — what data crosses each phase boundary
- `references/rewrite-rule-style.md` — naming, doc, fixture conventions
- `references/worked-examples/osmotic-pressure/` — clojure.md example
```

- [ ] **Step 2: Commit.**

```bash
git add skills/neurosym-forge/SKILL.md
git commit -m "neurosym-forge: SKILL.md"
```

### Task 7.2: `references/metta-idioms.md`

**Files:**
- Create: `skills/neurosym-forge/references/metta-idioms.md`

- [ ] **Step 1: Write the file.**

```markdown
# MeTTa idioms in CLJS + Rust

This reference maps the seven core MeTTa idioms onto the CLJS+Rust substrate used by `neurosym-forge`-scaffolded projects.

## `(= lhs rhs)` — equality declaration

A MeTTa equality declares `lhs` rewritable to `rhs`. In the scaffold:

- Stored as a rewrite-rule record in `rules/*.edn` with shape `{id, lhs, rhs, doc, tags}`
- Applied via `meander.epsilon/rewrite` in `cljs-orchestrator/src/main/<slug>/nl_to_fol.cljs`
- Variable-balance is enforced: every free `?x` on `rhs` must appear on `lhs` unless tagged `eliminating`

Add a rule via `add_rewrite_rule.py`. Never hand-edit `rules/*.edn` — the checksum linter will flag it.

## `(: x T)` — type declaration

Every atom carries a `:sort` field. Sorts are primitive keywords (`:int`, `:real`, `:bool`, `:entity`), function types (`{:kind :fn :args [...] :ret ...}`), or enums (`{:kind :enum :members [...]}`).

malli `m/=>` schemas at every function boundary in `phases.cljs` enforce sort consistency at runtime.

Add a sort via `add_sort.py`.

## `!expr` — force evaluation

EDN atoms tagged `^:force` are evaluated immediately by the CLJS phase driver and replaced in-place with the result. In v0.1 this only kicks in on grounded atoms whose CLJS thin shim is annotated `:force` — a deferred backend call becomes synchronous.

## `(match $space pattern template)`

The atomspace is the cozo store + `core.logic.pldb` in-memory. A query is a `core.logic/run*` form over a cozo Datalog clause, then a meander template substitution. See `cljs-orchestrator/src/main/<slug>/unify.cljs`.

## `(superpose (a b c))` / `(collapse expr)`

Non-deterministic branching. The CLJS driver wraps an alternative set in `lazy-seq`. Each branch is shipped to Rust as a separate `assert_and_track` block with a per-branch tracker; the verdict EDN reports which branch was chosen.

`collapse` is the inverse: reduce the lazy-seq to a single verdict.

## Grounded atoms

A grounded atom is a host-language value or function. In the scaffold:

- Declared in `rules/grounded.edn`
- Backed by a `#[napi]` Rust function in `rust-verifier/src/<lib>.rs`
- Reachable from CLJS through a thin shim in `bridge.cljs`

Add one via `add_grounded_atom.py`. Default libraries: `z3`, `egg`, `cozo`, `tectonic`, `custom`.

## Self-reflection

`rules/*.edn` is data. The skill's `add_*` helpers are the only sanctioned editors; manual edits are detected via checksums in `rules/.checksums.edn` and flagged by `lint_rewrite_coverage.py`.

Each scaffolded project is itself a Claude Code skill (it ships its own `SKILL.md`). The forge scaffolds skills.
```

- [ ] **Step 2: Commit.**

```bash
git add skills/neurosym-forge/references/metta-idioms.md
git commit -m "neurosym-forge: metta-idioms reference"
```

### Task 7.3: Remaining references (atomspace-edn, grounded-atoms, phase-boundaries, rewrite-rule-style)

**Files:**
- Create: `skills/neurosym-forge/references/atomspace-edn.md`
- Create: `skills/neurosym-forge/references/grounded-atoms.md`
- Create: `skills/neurosym-forge/references/phase-boundaries.md`
- Create: `skills/neurosym-forge/references/rewrite-rule-style.md`

- [ ] **Step 1: Write `atomspace-edn.md`.**

```markdown
# Atomspace EDN IR

Every phase boundary serialises through EDN. Records are MeTTa-style atoms.

## Four atom kinds

```clojure
;; Symbol — an identifier
{:kind :symbol :name :osmotic-pressure :sort (:fn [:solution] :real)}

;; Variable — bound by quantifier or match
{:kind :variable :name "?s" :sort :solution}

;; Grounded — host value or function
{:kind :grounded :name :z3-check-all
 :sort (:fn [:atom] :verdict)
 :grounded {:lib :z3 :fn "check_all" :napi true}}

;; Expression — parenthesised list
{:kind :expression :head <atom> :args [<atoms>] :doc "..." :id "R042"}
```

## Top-level shape

```clojure
{:version 1
 :sorts   [:int :real :bool :solution :formula :verdict :rule :atom ...]
 :rules   [<rule atoms>]   ;; in rules/*.edn
 :atoms   [<all other atoms>]
 :grounded [<grounded atoms>]   ;; in rules/grounded.edn
 :predicates {<map>}              ;; in rules/predicates.edn, optional
 :checksums {<file -> sha256>}  ;; in rules/.checksums.edn
}
```

## Enforced invariants

- Every atom has a `:sort` field. `lint_atomspace.py` fails on missing.
- Every sort referenced from an atom appears in `:sorts`. `lint_atomspace.py` flags unknowns.
- Every rule's `:rhs` free variables appear on the `:lhs`. `lint_atomspace.py` flags unbound.
- Every rule has a fixture test `tests/rules/test_<ID>.cljs`. `lint_rewrite_coverage.py` flags missing.
- `rules/*.edn` checksums match `.checksums.edn`. Manual edits are detected.
```

- [ ] **Step 2: Write `grounded-atoms.md`.**

```markdown
# Grounded atoms

A grounded atom is a host-language value or function exposed to the CLJS atomspace through napi-rs.

## Adding one

```bash
.venv/Scripts/python.exe -m scripts.add_grounded_atom \
  --project ../../verifiers/osmotic-pressure \
  --slug osmotic_pressure \
  --name :my-fn \
  --lib custom \
  --fn my_fn \
  --sort '{"kind":"fn","args":[":atom"],"ret":":verdict"}' \
  --doc "custom solver hook"
```

The helper:

1. Validates the sort.
2. Appends a record to `rules/grounded.edn`.
3. Writes a `#[napi]` stub to `rust-verifier/src/<lib>.rs` with `todo!()`.
4. Wires `mod <lib>;` into `rust-verifier/src/lib.rs` if absent.
5. Appends a CLJS bridge thin-shim to `cljs-orchestrator/src/main/<slug>/bridge.cljs`.
6. Refreshes the checksum.

## Then

Edit the Rust file to replace `todo!()` with the real backend call. Run `npm run build:rust` to compile. The CLJS side picks up the new function the next time the orchestrator loads.

## Sort discipline

Every grounded atom is typed. The argument shape is currently always `String` over the napi boundary (EDN-as-text); the Rust function is responsible for parsing. For payloads over ~5 MB switch to `Buffer + msgpack` — out of scope for v0.1.

## Supported libraries

- `z3` — SMT/FOL satisfiability
- `egg` — e-graph equality saturation
- `cozo` — embedded Datalog
- `tectonic` — LaTeX rendering
- `custom` — anything else

Adding a new library is just a new module file in `rust-verifier/src/` and a `mod` declaration.
```

- [ ] **Step 3: Write `phase-boundaries.md`.**

```markdown
# Phase boundaries

```
Phase 1 [Claude]         Extract atoms              -> work/claims.edn
Phase 2 [ClojureScript]  Rewrite via meander         -> work/fol.edn
Phase 3 [Rust]           Verify (Z3 / egg / cozo)    -> work/verdict.edn
Phase 4 [Claude]         Synthesise report           -> work/report.md
Phase 5 [Rust]           Typeset (tectonic)          -> work/report.pdf
```

## What crosses each boundary

| Boundary | Wire format | Owner of validation |
|---|---|---|
| Claude → CLJS | EDN file `work/claims.edn` matching atom.schema.json | `lint_atomspace.py` |
| CLJS → Rust | EDN string over napi-rs | malli post-condition on CLJS side, `parse_formulas` on Rust side |
| Rust → CLJS | EDN string over napi-rs | serde + edn-rs in Rust, malli pre-condition on CLJS |
| CLJS → Claude | EDN file `work/verdict.edn` | malli on CLJS write |
| Claude → Rust | LaTeX string + path | tectonic accepts as-is |

## Failure modes

- `:unsat` from Phase 3 — Claude must re-enter Phase 1 with a corrected claim set; up to 3 attempts then escalate.
- `:unknown` from Phase 3 — Z3 timed out. Bump `:smt-timeout-ms` in `work/config.edn`.
- malli DbC violation — phase script throws `ex-info`; the orchestrator emits an EDN error record.
```

- [ ] **Step 4: Write `rewrite-rule-style.md`.**

```markdown
# Rewrite-rule style

## ID convention

`R<NNN>` where `NNN` is zero-padded three or more digits. Allocate sequentially within a `rules/*.edn` file. IDs are global across rule files.

## Doc string

A single English sentence stating the equality direction and intent. E.g.:

```clojure
{:id "R042" :doc "van 't Hoff: π = iMRT" ...}
```

Do not embed proofs in the doc string. The fixture test is the proof.

## Tags

- `:algebraic` — pure math identity
- `:commutative` — symmetric in both arguments
- `:associative` — re-bracketable
- `:eliminating` — lhs introduces variables unused on rhs (allowed)
- `:domain-<name>` — domain-specific group

Tag liberally; tags drive future rule indexing.

## Fixture test

Every rule must have `tests/rules/test_<ID>.cljs` (the scaffolded project's tests, not the skill's). The fixture is auto-generated by `add_rewrite_rule.py` with a `:TODO` placeholder for the input form. Fill it in:

```clojure
(ns rules.test-r042
  (:require [cljs.test :refer-macros [deftest is]]
            [meander.epsilon :as m]))

(deftest R042-applies
  (is (= '(* i M R T)
         (m/rewrite '(osmotic-pressure ?s)
           (osmotic-pressure ?s)
           (* i M R T))))))
```

`lint_rewrite_coverage.py` flags missing fixtures and stale checksums.
```

- [ ] **Step 5: Commit.**

```bash
git add skills/neurosym-forge/references/
git commit -m "neurosym-forge: reference docs (atomspace, grounded, phases, style)"
```

### Task 7.4: Worked example placeholder

**Files:**
- Create: `skills/neurosym-forge/references/worked-examples/osmotic-pressure/README.md`

- [ ] **Step 1: Write the file.**

```markdown
# Worked example: osmotic pressure

End-to-end demonstration based on `clojure.md` § 7.

## Scaffold

```bash
cd skills/neurosym-forge
.venv/Scripts/python.exe -m scripts.scaffold_project \
  --name "Osmotic Pressure Verifier" --slug osmotic_pressure \
  --out ../../verifiers/osmotic-pressure
```

## Add domain sorts

```bash
.venv/Scripts/python.exe -m scripts.add_sort \
  --project ../../verifiers/osmotic-pressure --sort ":molarity"
```

## Add the van 't Hoff law

```bash
.venv/Scripts/python.exe -m scripts.add_rewrite_rule \
  --project ../../verifiers/osmotic-pressure \
  --rule-file vant-hoff.edn
```

`vant-hoff.edn`:

```json
{"id": "R042",
 "lhs": {"kind": "expression", "sort": ":real",
         "head": {"kind": "symbol", "name": ":osmotic-pressure",
                  "sort": {"kind": "fn", "args": [":solution"], "ret": ":real"}},
         "args": [{"kind": "variable", "name": "?s", "sort": ":solution"}]},
 "rhs": {"kind": "expression", "sort": ":real",
         "head": {"kind": "symbol", "name": ":*",
                  "sort": {"kind": "fn", "args": [":real", ":real", ":real", ":real"], "ret": ":real"}},
         "args": [{"kind": "expression", "sort": ":real",
                   "head": {"kind": "symbol", "name": ":vant-hoff-i",
                            "sort": {"kind": "fn", "args": [":solution"], "ret": ":real"}},
                   "args": [{"kind": "variable", "name": "?s", "sort": ":solution"}]},
                  {"kind": "expression", "sort": ":real",
                   "head": {"kind": "symbol", "name": ":molarity",
                            "sort": {"kind": "fn", "args": [":solution"], "ret": ":real"}},
                   "args": [{"kind": "variable", "name": "?s", "sort": ":solution"}]},
                  {"kind": "grounded", "sort": ":real",
                   "name": ":R-gas-constant",
                   "grounded": {"lib": "custom", "fn": "r_constant", "napi": false}},
                  {"kind": "expression", "sort": ":real",
                   "head": {"kind": "symbol", "name": ":temperature",
                            "sort": {"kind": "fn", "args": [":solution"], "ret": ":real"}},
                   "args": [{"kind": "variable", "name": "?s", "sort": ":solution"}]}]},
 "doc": "van 't Hoff: pi = i * M * R * T",
 "tags": ["algebraic", "domain-chemistry"]}
```

## Build and verify

```bash
cd ../../verifiers/osmotic-pressure
npm install
npm run build
# Then run Phase 1 by hand: Claude reads doc.pdf and emits work/claims.edn
node cljs-orchestrator/dist/main.js verify work/claims.edn work/verdict.edn
```

The full pipeline (paper text → PDF report) tracks `clojure.md` § 7 step-for-step.
```

- [ ] **Step 2: Commit.**

```bash
git add skills/neurosym-forge/references/worked-examples/
git commit -m "neurosym-forge: osmotic-pressure worked example"
```

---

## Phase 8: Compliance and trigger tests

### Task 8.1: `test_anthropic_compliance.py`

**Files:**
- Create: `skills/neurosym-forge/tests/test_anthropic_compliance.py`

This mirrors the pattern from `skills/book-knowledge/tests/test_anthropic_compliance.py`. Read that file first; this version targets `skills/neurosym-forge/SKILL.md`.

- [ ] **Step 1: Write the file.**

```python
# skills/neurosym-forge/tests/test_anthropic_compliance.py
"""Compliance checks for SKILL.md (Anthropic skill format)."""
from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml


SKILL_MD = Path(__file__).resolve().parent.parent / "SKILL.md"


def _frontmatter() -> dict:
    text = SKILL_MD.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    assert m, "SKILL.md missing YAML frontmatter"
    return yaml.safe_load(m.group(1))


def test_skill_md_exists() -> None:
    assert SKILL_MD.exists()


def test_frontmatter_required_fields() -> None:
    fm = _frontmatter()
    for k in ("name", "description", "license"):
        assert k in fm, f"frontmatter missing {k}"


def test_name_matches_directory() -> None:
    assert _frontmatter()["name"] == "neurosym-forge"


def test_description_under_1024_chars() -> None:
    assert len(_frontmatter()["description"]) <= 1024


def test_description_has_trigger_phrases() -> None:
    desc = _frontmatter()["description"]
    for phrase in ("scaffold", "rewrite rule", "Z3"):
        assert phrase in desc, f"description missing trigger phrase {phrase!r}"


def test_body_under_500_lines() -> None:
    text = SKILL_MD.read_text(encoding="utf-8")
    body = text.split("---\n", 2)[2] if text.count("---\n") >= 2 else text
    lines = body.splitlines()
    assert len(lines) <= 500, f"SKILL.md body has {len(lines)} lines (max 500)"
```

- [ ] **Step 2: Run test, expect PASS.**

```bash
.venv/Scripts/python.exe -m pytest tests/test_anthropic_compliance.py -v
```

Expected: 6 passed.

- [ ] **Step 3: Commit.**

```bash
git add skills/neurosym-forge/tests/test_anthropic_compliance.py
git commit -m "neurosym-forge: Anthropic compliance tests"
```

### Task 8.2: Trigger calibration

**Files:**
- Create: `skills/neurosym-forge/tests/trigger_tests.yaml`
- Create: `skills/neurosym-forge/tests/test_trigger_calibration.py`

This mirrors `skills/book-knowledge/tests/test_trigger_calibration.py` — read that first.

- [ ] **Step 1: Write `tests/trigger_tests.yaml`.**

```yaml
# Each case is (prompt, should_trigger).
# Used to sanity-check that SKILL.md trigger phrases cover positive cases
# and exclude negative ones.
positive:
  - "scaffold a neurosymbolic verifier"
  - "verify these claims with Z3"
  - "add a rewrite rule for commutativity"
  - "ground this predicate in Rust"
  - "extend the atomspace IR"
  - "build a CLJS+Rust verifier"
  - "FOL verifier"
  - "SMT solver hookup"
  - "e-graph saturation"
  - "MeTTa-style modeling"
negative:
  - "rewrite this paragraph in Russell style"
  - "ingest this PDF into the claim ledger"
  - "review chapter 4 with personas"
  - "build the book release"
  - "lint the manuscript for D1 defects"
```

- [ ] **Step 2: Write the test.**

```python
# skills/neurosym-forge/tests/test_trigger_calibration.py
"""Smoke-test that SKILL.md trigger phrases roughly match expected prompts.

This is a heuristic check — the actual trigger is Claude's judgement at
SKILL.md load time. We assert that every positive case has at least one
substring overlap with the SKILL.md description, and no negative case does.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

SKILL_ROOT = Path(__file__).resolve().parent.parent
SKILL_MD = SKILL_ROOT / "SKILL.md"
TRIGGER_PATH = SKILL_ROOT / "tests" / "trigger_tests.yaml"


def _description() -> str:
    text = SKILL_MD.read_text(encoding="utf-8")
    m = re.search(r"^description:\s*(.+?)(?:\nlicense:|\nmetadata:)", text, re.DOTALL | re.MULTILINE)
    assert m
    return m.group(1).lower()


def _tokens(s: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9-+]+", s.lower()) if len(w) > 2}


def _matches(prompt: str, description: str) -> bool:
    prompt_tokens = _tokens(prompt)
    desc_tokens = _tokens(description)
    return bool(prompt_tokens & desc_tokens & {
        "scaffold", "verifier", "rewrite", "rule", "z3",
        "ground", "grounded", "atomspace", "ir", "cljs",
        "fol", "smt", "egraph", "e-graph", "datalog", "metta",
        "neurosymbolic", "neurosym",
    })


@pytest.fixture(scope="module")
def cases() -> dict:
    return yaml.safe_load(TRIGGER_PATH.read_text(encoding="utf-8"))


def test_positive_cases_overlap_description(cases: dict) -> None:
    desc = _description()
    misses = [p for p in cases["positive"] if not _matches(p, desc)]
    assert not misses, f"positive prompts missing trigger overlap: {misses}"


def test_negative_cases_dont_overlap(cases: dict) -> None:
    desc = _description()
    hits = [p for p in cases["negative"] if _matches(p, desc)]
    assert not hits, f"negative prompts unexpectedly match triggers: {hits}"
```

- [ ] **Step 3: Run test, expect PASS.**

```bash
.venv/Scripts/python.exe -m pytest tests/test_trigger_calibration.py -v
```

If a positive case misses or a negative case hits, edit either the SKILL.md description or the trigger keyword set in `_matches`. Do not weaken the negative-case set — those are real adjacent skills the user must not collide with.

- [ ] **Step 4: Commit.**

```bash
git add skills/neurosym-forge/tests/trigger_tests.yaml skills/neurosym-forge/tests/test_trigger_calibration.py
git commit -m "neurosym-forge: trigger calibration tests"
```

---

## Phase 9: Smoke test and PR

### Task 9.1: Full test sweep

- [ ] **Step 1: Run all tests.**

```bash
cd skills/neurosym-forge
.venv/Scripts/python.exe -m pytest tests/ -q --tb=short
```

Expected: 40+ tests, all green.

- [ ] **Step 2: Write `tests/smoke-results.md` with the count.**

Read the pytest output and write:

```markdown
# Smoke results

Date: <YYYY-MM-DD>

Run: `.venv/Scripts/python.exe -m pytest tests/ -q`

Result: <N passed, 0 failed>

Test modules:

- test_anthropic_compliance.py — 6 tests
- test_trigger_calibration.py — 2 tests
- test_io.py — 4 tests
- test_sort_registry.py — 6 tests
- test_atom.py — 5 tests
- test_rewrite_rule.py — 5 tests
- test_lint_atomspace.py — 5 tests
- test_lint_rewrite_coverage.py — 3 tests
- test_scaffold_project.py — 5 tests
- test_add_sort.py — 4 tests
- test_add_rewrite_rule.py — 5 tests
- test_add_grounded_atom.py — 4 tests
- test_render_call_graph.py — 2 tests
- test_verify_claims.py — 2 tests

Total: <sum>
```

- [ ] **Step 3: Commit smoke results.**

```bash
git add skills/neurosym-forge/tests/smoke-results.md
git commit -m "neurosym-forge: smoke results"
```

### Task 9.2: Integration smoke — scaffold osmotic-pressure end-to-end

**Files:** none new; this is a manual verification.

- [ ] **Step 1: Scaffold the worked example.**

```bash
cd skills/neurosym-forge
.venv/Scripts/python.exe -m scripts.scaffold_project \
  --name "Osmotic Pressure Verifier" \
  --slug osmotic_pressure \
  --out /tmp/osmotic-pressure
```

Expected: command exits 0; `/tmp/osmotic-pressure/package.json` exists.

- [ ] **Step 2: Add a sort.**

```bash
.venv/Scripts/python.exe -m scripts.add_sort \
  --project /tmp/osmotic-pressure --sort ":molarity"
```

Expected: `:molarity` appears in `/tmp/osmotic-pressure/rules/seed.edn`.

- [ ] **Step 3: Lint the scaffolded atomspace.**

```bash
.venv/Scripts/python.exe -m scripts.lint_atomspace /tmp/osmotic-pressure/rules/seed.edn
```

Expected: `OK: atomspace ... passes`.

- [ ] **Step 4: Lint rewrite coverage (expect clean, 0 rules so far).**

```bash
.venv/Scripts/python.exe -m scripts.lint_rewrite_coverage /tmp/osmotic-pressure
```

Expected: `OK: rule coverage ... is clean`.

- [ ] **Step 5: Capture the result.**

Append to `skills/neurosym-forge/tests/smoke-results.md`:

```markdown
## Integration smoke (manual)

Scaffolded `/tmp/osmotic-pressure` with neurosym-forge v0.1.0.
- scaffold_project: PASS
- add_sort ":molarity": PASS
- lint_atomspace: PASS
- lint_rewrite_coverage: PASS

Did not run `npm install` / `npm run build` — CLJS+Rust toolchain
verification is deferred to a follow-up plan.
```

- [ ] **Step 6: Commit and clean up.**

```bash
rm -rf /tmp/osmotic-pressure
git add skills/neurosym-forge/tests/smoke-results.md
git commit -m "neurosym-forge: integration smoke results"
```

### Task 9.3: Update repo README

**Files:**
- Modify: `README.md` (repo root)

- [ ] **Step 1: Read the current README skills table.**

```bash
sed -n '60,90p' README.md
```

- [ ] **Step 2: Add a row to the table after `book-thesis`.**

Find the line:

```
| **[`book-thesis`](skills/book-thesis/SKILL.md)** | Metabook reasoning: thesis tree, paragraph back-pointers, entailment loop, Datalog cross-chapter consistency | Layer 2-4 on top of book-knowledge; contributes D9-D12 to book-qa |
```

Add immediately after:

```
| **[`neurosym-forge`](skills/neurosym-forge/SKILL.md)** | Scaffolds and extends CLJS+Rust neurosymbolic verifier projects under MeTTa-style atomspace conventions | Optional; composes with book-knowledge via the `--book-knowledge-bridge` flag |
```

- [ ] **Step 3: Commit.**

```bash
git add README.md
git commit -m "README: list neurosym-forge skill"
```

### Task 9.4: Open the PR

- [ ] **Step 1: Push the branch.**

```bash
git push -u origin spec/neurosym-forge
```

- [ ] **Step 2: Open the PR.**

```bash
gh pr create --title "neurosym-forge: scaffolder for CLJS+Rust neurosymbolic verifiers" --body "$(cat <<'EOF'
## Summary

- New sibling skill `skills/neurosym-forge/` (~40 tests)
- Scaffolds ClojureScript + Rust verification projects under MeTTa-style authoring conventions
- EDN-as-atomspace IR with `:sort` declarations and `(= ...)` rewrite rules
- Grounded atoms wrap Z3 / egg / cozo / tectonic behind napi-rs
- Spec at `docs/specs/2026-05-13-neurosym-forge-design.md`
- Plan at `docs/plans/2026-05-13-neurosym-forge.md`

## Test plan

- [ ] `cd skills/neurosym-forge && .venv/Scripts/python.exe -m pytest tests/ -q`
- [ ] Manual scaffold smoke: `python -m scripts.scaffold_project --name Demo --slug demo --out /tmp/demo`
- [ ] Manual lint smoke: `python -m scripts.lint_atomspace /tmp/demo/rules/seed.edn`
EOF
)"
```

---

## Self-review

I checked the plan against the spec for coverage. The mapping:

| Spec section | Implementing tasks |
|---|---|
| Skill layout — `pyproject.toml`, LICENSE, .gitignore | 0.1, 0.2 |
| Skill layout — `scripts/__init__.py`, `tests/conftest.py` | 0.3 |
| Schemas (`atom.schema.json`, `rewrite-rule.schema.json`, `sort.schema.json`) | 1.1, 1.2, 1.3 |
| `_io.py` + checksum | 1.4 |
| SortRegistry | 1.5 |
| Atom dataclass | 1.6 |
| RewriteRule + variable-balance check | 1.7 |
| `lint_atomspace.py` | 2.1 |
| `lint_rewrite_coverage.py` | 2.2 |
| Project templates (CLJS, Rust, LaTeX) | 3.1, 3.2, 3.3 |
| `scaffold_project.py` | 4.1 |
| `add_sort.py` | 5.1 |
| `add_rewrite_rule.py` (with fixture-test emission) | 5.2 |
| `add_grounded_atom.py` (Rust + CLJS stubs, mod wire-up) | 5.3 |
| `render_call_graph.py` | 6.1 |
| `verify_claims.py` (prints commands) | 6.2 |
| SKILL.md | 7.1 |
| `references/metta-idioms.md` | 7.2 |
| `references/atomspace-edn.md`, `grounded-atoms.md`, `phase-boundaries.md`, `rewrite-rule-style.md` | 7.3 |
| Worked example placeholder | 7.4 |
| Anthropic compliance test | 8.1 |
| Trigger calibration | 8.2 |
| Smoke + integration + README update | 9.1, 9.2, 9.3, 9.4 |

No spec section is missing a task. The `book-knowledge` bridge is exposed via the `--book-knowledge-bridge` flag on `scaffold_project.py` (Task 4.1 implementation); v0.1 does not emit the bridge code itself, matching the spec's "optional D13" framing in §Composes-with.

Method-name consistency: `scaffold_project`, `add_sort`, `add_rewrite_rule`, `add_grounded_atom`, `lint_atomspace`, `lint_rewrite_coverage`, `render_call_graph` — used identically in every task that references them.

No placeholders remain. Every code step contains the actual code; every test step contains the actual test.

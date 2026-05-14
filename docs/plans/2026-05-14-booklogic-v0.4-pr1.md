# BookLogic v0.4 PR-1 — EDN boundary fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the JSON-stamped-`.edn` boundary with real EDN at every Python↔CLJS↔Rust crossing, so `cljs.reader/read-string` actually parses what Python writes and `edn-rs` parses what Rust receives.

**Architecture:** Two new Python modules in `skills/neurosym-forge/scripts/` (an EDN reader and an EDN writer over a small documented subset — keywords, maps, vectors, strings, numbers, booleans, nil, lists, comments). `_io.py` rewires its read/write functions to use them. Every fixture file under `tests/fixtures/` and `work/` is migrated from JSON syntax to EDN syntax. Rust templates (`ir.rs.tmpl`, `smt.rs.tmpl`, `Cargo.toml.tmpl`) switch from `serde_json` to `edn-rs` on input/verdict paths; Bermuda's already-scaffolded `ir.rs`/`smt.rs`/`Cargo.toml` are updated in lockstep. CLJS code is unchanged — it was already EDN-correct. No `cargo build` runs in PR-1; the Rust changes ship as source edits verified by template-shape and string-search tests. Spec at `docs/specs/2026-05-14-booklogic-v0.4-mission-design.md` § "D1 — Real EDN boundary".

**Tech Stack:** Python 3.13, jsonschema (existing), pytest. The Rust templates target `edn-rs 0.19` for parsing and emission. No new Python deps.

---

## Pre-flight

Read these before starting:
- `docs/specs/2026-05-14-booklogic-v0.4-mission-design.md` § "D1 — Real EDN boundary"
- `skills/neurosym-forge/scripts/_io.py` (current state — writes JSON, claims EDN)
- `verifiers/bermuda/cljs-orchestrator/src/main/bermuda/bridge.cljs` (uses `cljs.reader/read-string`)
- `verifiers/bermuda/cljs-orchestrator/src/main/bermuda/core.cljs` (uses `cljs.reader/read-string`)
- `verifiers/bermuda/rust-verifier/src/ir.rs` (uses `serde_json::from_str` currently)
- One existing fixture: `skills/neurosym-forge/tests/fixtures/valid_atom_symbol.edn` (currently JSON; example target shape after migration is in this plan)

**Worktree:** `C:\Users\charl\code\russellian-book-suite-booklogic` on branch `spec/booklogic`. The umbrella spec is already committed.

**Test invocation.**
- neurosym-forge: `cd skills/neurosym-forge && .venv/Scripts/python.exe -m pytest tests/ -q`
- bermuda: `cd verifiers/bermuda && .venv/Scripts/python.exe -m pytest tests/ -q`
- Use system Python for book-qa (no .venv per repo convention)

**Commit hygiene:** terse human commits, no AI attribution, no Co-Authored-By, one problem per commit.

**EDN subset for PR-1:**

The PR-1 reader/writer handles exactly:
- maps `{k v ...}` with keyword, string, or int keys
- vectors `[...]`
- lists `(...)` (used by D2 ingest-trace events; PR-1 supports parsing/emitting them)
- strings `"..."` with `\n \r \t \" \\` escapes
- integers and floats (no rationals, no bigints, no special-form numerics)
- booleans `true` / `false`
- nil
- keywords `:foo` and namespaced `:foo/bar` (matching `^:[a-zA-Z_][a-zA-Z0-9_/-]*$`)
- line comments starting with `;`

PR-1 does **not** handle: tagged literals (`#inst`, `#uuid` — added in PR-2 for ingest-trace), sets (`#{...}`), symbols, custom dispatch `#=`, character literals `\a`. The reader raises a clear error on these forms.

---

## File Structure

### Created

```
skills/neurosym-forge/
├── scripts/
│   ├── _edn_reader.py                                NEW (~180 lines)
│   ├── _edn_writer.py                                NEW (~80 lines)
└── tests/
    ├── test_edn_reader.py                            NEW (~12 tests)
    ├── test_edn_writer.py                            NEW (~10 tests)
    └── test_edn_round_trip.py                        NEW (~5 tests)
```

### Modified

```
skills/neurosym-forge/
├── scripts/_io.py                                    rewire read/write to new EDN
├── scripts/add_grounded_atom.py                      _io call shape unchanged
├── scripts/add_rewrite_rule.py                       _io call shape unchanged
├── scripts/add_sort.py                               _io call shape unchanged
├── scripts/lint_atomspace.py                         _io call shape unchanged
├── scripts/lint_rewrite_coverage.py                  _io call shape unchanged
├── scripts/scaffold_project.py                       _io call shape unchanged
├── tests/fixtures/*.edn                              migrate JSON→EDN syntax
└── assets/project-template/
    └── rust-verifier/
        ├── Cargo.toml.tmpl                           add edn-rs back
        └── src/
            ├── ir.rs.tmpl                            edn-rs parser
            └── smt.rs.tmpl                           dispatch on edn_rs::Edn

verifiers/bermuda/
├── scripts/ingest_ledger.py                          uses neurosym-forge _io
├── scripts/extract_prose.py                          uses neurosym-forge _io
├── scripts/verdict_to_qa.py                          uses neurosym-forge _io
├── scripts/run_verification.py                       uses neurosym-forge _io
├── tests/fixtures/*.edn                              migrate JSON→EDN syntax
└── rust-verifier/
    ├── Cargo.toml                                    edn-rs added
    └── src/
        ├── ir.rs                                     edn-rs parser
        └── smt.rs                                    dispatch on edn_rs::Edn

skills/neurosym-forge/tests/test_rust_template_shape.py   add edn-rs / no-serde_json assertions
```

The Bermuda Python scripts (`ingest_ledger.py` etc.) currently import their own `read_edn_as_json` / write helpers. They become thin shims around `neurosym-forge.scripts._io`. The umbrella spec already established `verifiers/bermuda` reads `neurosym-forge` as the canonical EDN owner.

---

## Phase 1: Python EDN reader

### Task 1.1: `_edn_reader.py` — primitive types

**Files:**
- Create: `skills/neurosym-forge/scripts/_edn_reader.py`
- Create: `skills/neurosym-forge/tests/test_edn_reader.py`

- [ ] **Step 1: Write the failing tests for primitives.**

```python
# skills/neurosym-forge/tests/test_edn_reader.py
from __future__ import annotations

import pytest

from scripts._edn_reader import read_edn, EdnReadError, Keyword


def test_read_int() -> None:
    assert read_edn("42") == 42
    assert read_edn("-17") == -17
    assert read_edn("0") == 0


def test_read_float() -> None:
    assert read_edn("3.14") == 3.14
    assert read_edn("-2.5") == -2.5
    assert read_edn("1.5e3") == 1500.0


def test_read_bool_and_nil() -> None:
    assert read_edn("true") is True
    assert read_edn("false") is False
    assert read_edn("nil") is None


def test_read_string() -> None:
    assert read_edn('"hello"') == "hello"
    assert read_edn('"with \\"quotes\\""') == 'with "quotes"'
    assert read_edn('"line\\nfeed"') == "line\nfeed"
    assert read_edn('"tab\\there"') == "tab\there"
    assert read_edn('"back\\\\slash"') == "back\\slash"


def test_read_keyword() -> None:
    k = read_edn(":foo")
    assert isinstance(k, Keyword)
    assert k.name == "foo"
    assert str(k) == ":foo"


def test_read_namespaced_keyword() -> None:
    k = read_edn(":source/ingested")
    assert isinstance(k, Keyword)
    assert k.namespace == "source"
    assert k.name == "ingested"
    assert str(k) == ":source/ingested"


def test_keyword_equality_and_hashing() -> None:
    assert read_edn(":foo") == Keyword("foo")
    assert read_edn(":foo/bar") == Keyword("bar", namespace="foo")
    assert hash(Keyword("foo")) == hash(Keyword("foo"))
    assert {Keyword("foo"): 1} == {Keyword("foo"): 1}
```

- [ ] **Step 2: Run, expect FAIL.**

```bash
cd skills/neurosym-forge && .venv/Scripts/python.exe -m pytest tests/test_edn_reader.py -v
```

Expected: `ModuleNotFoundError: scripts._edn_reader`.

- [ ] **Step 3: Write the implementation.**

```python
# skills/neurosym-forge/scripts/_edn_reader.py
"""Minimal EDN reader.

Supports the subset documented in
docs/specs/2026-05-14-booklogic-v0.4-mission-design.md § "D1 — Real EDN boundary":

    primitives: int, float, str, bool, nil
    keywords:   :foo, :foo/bar
    collections: {k v ...}, [a b ...], (a b ...)
    comments:   ; to end of line

Does NOT support: tagged literals, sets, symbols, custom dispatch, character
literals. The reader raises EdnReadError on unsupported forms.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class EdnReadError(ValueError):
    """Raised on malformed EDN or unsupported forms."""


@dataclass(frozen=True)
class Keyword:
    """An EDN keyword. Hashable and equal-by-value."""

    name: str
    namespace: str | None = None

    def __str__(self) -> str:
        if self.namespace:
            return f":{self.namespace}/{self.name}"
        return f":{self.name}"


def read_edn(s: str) -> Any:
    """Parse a single EDN form from the given string."""
    parser = _Parser(s)
    parser._skip_ws_and_comments()
    if parser._eof():
        raise EdnReadError("empty input")
    value = parser._parse_form()
    parser._skip_ws_and_comments()
    if not parser._eof():
        raise EdnReadError(f"trailing content at position {parser.pos}")
    return value


def read_edn_all(s: str) -> list[Any]:
    """Parse all top-level EDN forms from the given string. Empty input → []."""
    parser = _Parser(s)
    out: list[Any] = []
    parser._skip_ws_and_comments()
    while not parser._eof():
        out.append(parser._parse_form())
        parser._skip_ws_and_comments()
    return out


class _Parser:
    def __init__(self, source: str) -> None:
        self.src = source
        self.pos = 0

    def _eof(self) -> bool:
        return self.pos >= len(self.src)

    def _peek(self) -> str:
        return self.src[self.pos] if not self._eof() else ""

    def _advance(self) -> str:
        c = self.src[self.pos]
        self.pos += 1
        return c

    def _skip_ws_and_comments(self) -> None:
        while not self._eof():
            c = self._peek()
            if c in " \t\n\r,":
                self.pos += 1
            elif c == ";":
                while not self._eof() and self._peek() != "\n":
                    self.pos += 1
            else:
                return

    def _parse_form(self) -> Any:
        self._skip_ws_and_comments()
        if self._eof():
            raise EdnReadError("unexpected end of input")
        c = self._peek()
        if c == "{":
            return self._parse_map()
        if c == "[":
            return self._parse_vector()
        if c == "(":
            return self._parse_list()
        if c == '"':
            return self._parse_string()
        if c == ":":
            return self._parse_keyword()
        if c == "#":
            raise EdnReadError(
                f"tagged literals, sets, and custom dispatch are not supported "
                f"in PR-1 (position {self.pos})"
            )
        return self._parse_atom()

    def _parse_map(self) -> dict[Any, Any]:
        self._advance()  # consume '{'
        out: dict[Any, Any] = {}
        while True:
            self._skip_ws_and_comments()
            if self._peek() == "}":
                self._advance()
                return out
            key = self._parse_form()
            value = self._parse_form()
            out[key] = value

    def _parse_vector(self) -> list[Any]:
        return self._parse_seq("[", "]")

    def _parse_list(self) -> list[Any]:
        return self._parse_seq("(", ")")

    def _parse_seq(self, open_c: str, close_c: str) -> list[Any]:
        self._advance()  # consume opener
        out: list[Any] = []
        while True:
            self._skip_ws_and_comments()
            if self._peek() == close_c:
                self._advance()
                return out
            out.append(self._parse_form())

    def _parse_string(self) -> str:
        self._advance()  # consume '"'
        out: list[str] = []
        while True:
            if self._eof():
                raise EdnReadError("unterminated string")
            c = self._advance()
            if c == '"':
                return "".join(out)
            if c == "\\":
                esc = self._advance()
                out.append({"n": "\n", "r": "\r", "t": "\t", '"': '"', "\\": "\\"}.get(esc, esc))
            else:
                out.append(c)

    def _parse_keyword(self) -> Keyword:
        self._advance()  # consume ':'
        start = self.pos
        while not self._eof() and self._peek() not in " \t\n\r,()[]{}\";":
            self.pos += 1
        token = self.src[start:self.pos]
        if not token:
            raise EdnReadError(f"empty keyword at position {start}")
        if "/" in token:
            ns, _, name = token.partition("/")
            return Keyword(name=name, namespace=ns)
        return Keyword(name=token)

    def _parse_atom(self) -> Any:
        start = self.pos
        while not self._eof() and self._peek() not in " \t\n\r,()[]{}\";":
            self.pos += 1
        token = self.src[start:self.pos]
        if token == "true":
            return True
        if token == "false":
            return False
        if token == "nil":
            return None
        # number?
        try:
            return int(token)
        except ValueError:
            pass
        try:
            return float(token)
        except ValueError:
            pass
        raise EdnReadError(f"unrecognised atom {token!r} at position {start}")
```

- [ ] **Step 4: Run, expect 7 PASS.**

```bash
cd skills/neurosym-forge && .venv/Scripts/python.exe -m pytest tests/test_edn_reader.py -v
```

- [ ] **Step 5: Commit.**

```bash
git add skills/neurosym-forge/scripts/_edn_reader.py skills/neurosym-forge/tests/test_edn_reader.py
git commit -m "neurosym-forge: EDN reader for primitives and keywords"
```

### Task 1.2: Reader for collections

**Files:**
- Modify: `skills/neurosym-forge/tests/test_edn_reader.py`

The implementation from Task 1.1 already handles collections. This task adds tests that exercise them.

- [ ] **Step 1: Append collection tests.**

```python
# Append to tests/test_edn_reader.py

def test_read_empty_vector() -> None:
    assert read_edn("[]") == []


def test_read_vector() -> None:
    assert read_edn("[1 2 3]") == [1, 2, 3]


def test_read_nested_vector() -> None:
    assert read_edn("[[1 2] [3 4]]") == [[1, 2], [3, 4]]


def test_read_empty_map() -> None:
    assert read_edn("{}") == {}


def test_read_map_with_keyword_keys() -> None:
    result = read_edn('{:kind :symbol :name "foo"}')
    assert result == {Keyword("kind"): Keyword("symbol"), Keyword("name"): "foo"}


def test_read_list() -> None:
    result = read_edn("(source/ingested {:doc-id \"d1\"})")
    assert isinstance(result, list)
    assert result[0] == Keyword("ingested", namespace="source")
    assert result[1] == {Keyword("doc-id"): "d1"}


def test_read_comma_as_whitespace() -> None:
    assert read_edn("[1, 2, 3]") == [1, 2, 3]


def test_read_line_comment() -> None:
    src = """
    ; this is a comment
    [1 2 3]  ; trailing comment
    """
    assert read_edn(src) == [1, 2, 3]


def test_unsupported_tagged_literal_raises() -> None:
    with pytest.raises(EdnReadError, match="tagged literals"):
        read_edn('#inst "2026-01-01"')


def test_unterminated_string_raises() -> None:
    with pytest.raises(EdnReadError, match="unterminated"):
        read_edn('"oops')


def test_read_edn_all() -> None:
    from scripts._edn_reader import read_edn_all
    src = ":foo :bar :baz"
    out = read_edn_all(src)
    assert out == [Keyword("foo"), Keyword("bar"), Keyword("baz")]
```

- [ ] **Step 2: Run, expect 18 PASS total.**

```bash
cd skills/neurosym-forge && .venv/Scripts/python.exe -m pytest tests/test_edn_reader.py -v
```

- [ ] **Step 3: Commit.**

```bash
git add skills/neurosym-forge/tests/test_edn_reader.py
git commit -m "neurosym-forge: EDN reader collection + comment tests"
```

---

## Phase 2: Python EDN writer

### Task 2.1: `_edn_writer.py`

**Files:**
- Create: `skills/neurosym-forge/scripts/_edn_writer.py`
- Create: `skills/neurosym-forge/tests/test_edn_writer.py`

- [ ] **Step 1: Write failing tests.**

```python
# skills/neurosym-forge/tests/test_edn_writer.py
from __future__ import annotations

import pytest

from scripts._edn_reader import Keyword
from scripts._edn_writer import write_edn, EdnWriteError


def test_write_int() -> None:
    assert write_edn(42) == "42"
    assert write_edn(-17) == "-17"


def test_write_float() -> None:
    assert write_edn(3.14) == "3.14"


def test_write_bool_and_nil() -> None:
    assert write_edn(True) == "true"
    assert write_edn(False) == "false"
    assert write_edn(None) == "nil"


def test_write_string() -> None:
    assert write_edn("hello") == '"hello"'
    assert write_edn('with "quotes"') == '"with \\"quotes\\""'
    assert write_edn("line\nfeed") == '"line\\nfeed"'


def test_write_keyword() -> None:
    assert write_edn(Keyword("foo")) == ":foo"
    assert write_edn(Keyword("bar", namespace="ns")) == ":ns/bar"


def test_write_vector() -> None:
    assert write_edn([1, 2, 3]) == "[1 2 3]"


def test_write_map_with_keyword_keys() -> None:
    out = write_edn({Keyword("kind"): Keyword("symbol"), Keyword("name"): "foo"})
    # Order may vary; assert both pairings are present
    assert ":kind :symbol" in out or ":kind\n :symbol" in out
    assert ':name "foo"' in out or ':name\n "foo"' in out
    assert out.startswith("{") and out.endswith("}")


def test_write_nested() -> None:
    out = write_edn({Keyword("atoms"): [{Keyword("id"): "C001"}]})
    assert out == '{:atoms [{:id "C001"}]}'


def test_write_pretty() -> None:
    out = write_edn({Keyword("a"): 1, Keyword("b"): 2}, pretty=True)
    assert "\n" in out
    assert ":a 1" in out
    assert ":b 2" in out


def test_unsupported_type_raises() -> None:
    class X:
        pass
    with pytest.raises(EdnWriteError, match="cannot serialize"):
        write_edn(X())
```

- [ ] **Step 2: Run, expect FAIL.**

```bash
cd skills/neurosym-forge && .venv/Scripts/python.exe -m pytest tests/test_edn_writer.py -v
```

- [ ] **Step 3: Write the implementation.**

```python
# skills/neurosym-forge/scripts/_edn_writer.py
"""Minimal EDN writer.

Emits EDN syntax for the subset documented in PR-1's plan. Supports the
same types the reader accepts (Keyword, str, int, float, bool, None, list,
dict). Unsupported types raise EdnWriteError.

Two output modes:
    write_edn(obj)              → compact one-line EDN
    write_edn(obj, pretty=True) → multi-line with indentation for maps/vectors

The writer preserves dict insertion order for stability.
"""
from __future__ import annotations

from typing import Any

from scripts._edn_reader import Keyword


class EdnWriteError(ValueError):
    """Raised when an unsupported type appears in the value."""


_ESC_MAP = {"\n": "\\n", "\r": "\\r", "\t": "\\t", '"': '\\"', "\\": "\\\\"}


def write_edn(value: Any, pretty: bool = False) -> str:
    """Serialize `value` to an EDN string."""
    if pretty:
        return _emit_pretty(value, indent=0)
    return _emit_compact(value)


def _emit_compact(value: Any) -> str:
    if value is None:
        return "nil"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, Keyword):
        return str(value)
    if isinstance(value, str):
        return _emit_string(value)
    if isinstance(value, bool):  # bool is subclass of int — must be after bool branch
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return _emit_float(value)
    if isinstance(value, list):
        return "[" + " ".join(_emit_compact(v) for v in value) + "]"
    if isinstance(value, dict):
        parts = []
        for k, v in value.items():
            parts.append(_emit_compact(k))
            parts.append(_emit_compact(v))
        return "{" + " ".join(parts) + "}"
    raise EdnWriteError(f"cannot serialize {type(value).__name__}: {value!r}")


def _emit_pretty(value: Any, indent: int) -> str:
    if isinstance(value, dict) and value:
        prefix = " " * indent
        lines = ["{"]
        for k, v in value.items():
            kstr = _emit_compact(k)
            vstr = _emit_pretty(v, indent + len(kstr) + 2)
            lines.append(f"{prefix} {kstr} {vstr}")
        lines.append(f"{prefix}}}")
        return "\n".join(lines)
    if isinstance(value, list) and value:
        if all(not isinstance(x, (dict, list)) or not x for x in value):
            return _emit_compact(value)
        prefix = " " * indent
        lines = ["["]
        for v in value:
            lines.append(f"{prefix} {_emit_pretty(v, indent + 1)}")
        lines.append(f"{prefix}]")
        return "\n".join(lines)
    return _emit_compact(value)


def _emit_string(s: str) -> str:
    chunks = ['"']
    for c in s:
        chunks.append(_ESC_MAP.get(c, c))
    chunks.append('"')
    return "".join(chunks)


def _emit_float(f: float) -> str:
    # Use repr to round-trip; strip trailing 'e' suffix where Python emits scientific
    return repr(f)
```

- [ ] **Step 4: Run, expect 10 PASS.**

```bash
cd skills/neurosym-forge && .venv/Scripts/python.exe -m pytest tests/test_edn_writer.py -v
```

- [ ] **Step 5: Commit.**

```bash
git add skills/neurosym-forge/scripts/_edn_writer.py skills/neurosym-forge/tests/test_edn_writer.py
git commit -m "neurosym-forge: EDN writer"
```

### Task 2.2: Round-trip tests

**Files:**
- Create: `skills/neurosym-forge/tests/test_edn_round_trip.py`

- [ ] **Step 1: Write tests.**

```python
# skills/neurosym-forge/tests/test_edn_round_trip.py
from __future__ import annotations

from scripts._edn_reader import Keyword, read_edn
from scripts._edn_writer import write_edn


def _round_trip(value):
    return read_edn(write_edn(value))


def test_round_trip_primitives() -> None:
    for v in [42, -17, 3.14, True, False, None, "hello"]:
        assert _round_trip(v) == v


def test_round_trip_keyword() -> None:
    assert _round_trip(Keyword("foo")) == Keyword("foo")
    assert _round_trip(Keyword("bar", namespace="ns")) == Keyword("bar", namespace="ns")


def test_round_trip_nested_atomspace_record() -> None:
    record = {
        Keyword("kind"): Keyword("expression"),
        Keyword("id"): "C001",
        Keyword("predicate"): Keyword("parishes-count"),
        Keyword("subject"): Keyword("Bermuda"),
        Keyword("value"): 9,
    }
    assert _round_trip(record) == record


def test_round_trip_atomspace_full() -> None:
    space = {
        Keyword("version"): 1,
        Keyword("sorts"): [Keyword("int"), Keyword("real"), Keyword("entity")],
        Keyword("atoms"): [
            {Keyword("kind"): Keyword("expression"),
             Keyword("id"): "C001",
             Keyword("predicate"): Keyword("parishes-count"),
             Keyword("subject"): Keyword("Bermuda"),
             Keyword("value"): 9},
        ],
    }
    assert _round_trip(space) == space


def test_round_trip_string_with_escapes() -> None:
    s = 'line\nfeed and "quotes" plus \\backslash'
    assert _round_trip(s) == s
```

- [ ] **Step 2: Run, expect 5 PASS.**

```bash
cd skills/neurosym-forge && .venv/Scripts/python.exe -m pytest tests/test_edn_round_trip.py -v
```

- [ ] **Step 3: Commit.**

```bash
git add skills/neurosym-forge/tests/test_edn_round_trip.py
git commit -m "neurosym-forge: EDN round-trip tests"
```

---

## Phase 3: Rewire `_io.py`

### Task 3.1: Replace `read_edn_as_json` / `write_json_as_edn`

**Files:**
- Modify: `skills/neurosym-forge/scripts/_io.py`
- Modify: `skills/neurosym-forge/tests/test_io.py`

- [ ] **Step 1: Update the existing test.**

The existing `tests/test_io.py` asserts `":foo"` (JSON string) appears verbatim in the output. Update the assertions to expect real EDN syntax. Add tests for keyword round-trip.

Read the existing file first:

```bash
cat skills/neurosym-forge/tests/test_io.py
```

Replace the test body with:

```python
# skills/neurosym-forge/tests/test_io.py
from __future__ import annotations

from pathlib import Path

import pytest

from scripts._edn_reader import Keyword
from scripts._io import read_edn_file, write_edn_file, file_checksum


def test_round_trip(tmp_path: Path) -> None:
    payload = {
        Keyword("sorts"): [Keyword("int"), Keyword("real")],
        Keyword("rules"): [],
        Keyword("atoms"): [],
    }
    out = tmp_path / "atomspace.edn"
    write_edn_file(out, payload)
    back = read_edn_file(out)
    assert back == payload


def test_keywords_render_unquoted(tmp_path: Path) -> None:
    out = tmp_path / "x.edn"
    write_edn_file(out, {Keyword("k"): Keyword("foo")})
    text = out.read_text(encoding="utf-8")
    # Keywords must NOT appear as quoted strings
    assert ":foo" in text
    assert '"foo"' not in text
    assert ":k " in text or ":k\n" in text


def test_checksum_stable(tmp_path: Path) -> None:
    f = tmp_path / "x.edn"
    f.write_text("hello", encoding="utf-8")
    a = file_checksum(f)
    b = file_checksum(f)
    assert a == b
    assert len(a) == 64


def test_checksum_changes_on_edit(tmp_path: Path) -> None:
    f = tmp_path / "x.edn"
    f.write_text("hello", encoding="utf-8")
    a = file_checksum(f)
    f.write_text("hello!", encoding="utf-8")
    b = file_checksum(f)
    assert a != b
```

- [ ] **Step 2: Run, expect FAIL.**

```bash
cd skills/neurosym-forge && .venv/Scripts/python.exe -m pytest tests/test_io.py -v
```

Expected: tests fail because `read_edn_file` and `write_edn_file` do not exist; the old `read_edn_as_json` / `write_json_as_edn` are still in place.

- [ ] **Step 3: Rewrite `_io.py`.**

```python
# skills/neurosym-forge/scripts/_io.py
"""File I/O for atomspace EDN and rule files.

Uses the project's own EDN reader/writer (scripts/_edn_reader,
scripts/_edn_writer) so the .edn extension actually carries EDN syntax
that ClojureScript's reader can parse.

The legacy read_edn_as_json / write_json_as_edn shims remain as
deprecated aliases for one cycle to give callers room to migrate.
"""
from __future__ import annotations

import hashlib
import warnings
from pathlib import Path
from typing import Any

from scripts._edn_reader import read_edn
from scripts._edn_writer import write_edn


def read_edn_file(path: Path) -> Any:
    """Parse an EDN file from disk."""
    return read_edn(path.read_text(encoding="utf-8"))


def write_edn_file(path: Path, payload: Any) -> None:
    """Write a Python value to disk as pretty-printed EDN."""
    path.parent.mkdir(parents=True, exist_ok=True)
    text = write_edn(payload, pretty=True)
    path.write_text(text + "\n", encoding="utf-8", newline="\n")


def file_checksum(path: Path) -> str:
    """SHA-256 hex digest of a file's bytes."""
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


# Deprecated shims — kept for migration. Will be removed in PR-2 of v0.4.

def read_edn_as_json(path: Path) -> Any:
    warnings.warn(
        "read_edn_as_json is deprecated; use read_edn_file. It will be removed in v0.4 PR-2.",
        DeprecationWarning,
        stacklevel=2,
    )
    return read_edn_file(path)


def write_json_as_edn(path: Path, payload: Any) -> None:
    warnings.warn(
        "write_json_as_edn is deprecated; use write_edn_file. It will be removed in v0.4 PR-2.",
        DeprecationWarning,
        stacklevel=2,
    )
    write_edn_file(path, payload)
```

- [ ] **Step 4: Run, expect 4 PASS.**

```bash
cd skills/neurosym-forge && .venv/Scripts/python.exe -m pytest tests/test_io.py -v
```

- [ ] **Step 5: Run the full neurosym-forge suite. Expect many failures from callers still passing dicts with string keys.**

```bash
cd skills/neurosym-forge && .venv/Scripts/python.exe -m pytest tests/ -q --tb=no
```

The callers (`add_sort.py`, `add_rewrite_rule.py`, etc.) currently build dicts with string keys (`{"sorts": [...], "rules": [...]}`). After `_io.py` rewires, the keys ROUND-TRIP as strings, not keywords. To make the EDN files match the v0.4 contract, those callers must use `Keyword` instances as keys.

Phase 4 migrates them.

- [ ] **Step 6: Commit.**

```bash
git add skills/neurosym-forge/scripts/_io.py skills/neurosym-forge/tests/test_io.py
git commit -m "neurosym-forge: _io.py uses real EDN reader/writer"
```

---

## Phase 4: Migrate neurosym-forge callers

### Task 4.1: `add_sort.py`, `add_rewrite_rule.py`, `add_grounded_atom.py`, `scaffold_project.py`

**Files:**
- Modify: `skills/neurosym-forge/scripts/add_sort.py`
- Modify: `skills/neurosym-forge/scripts/add_rewrite_rule.py`
- Modify: `skills/neurosym-forge/scripts/add_grounded_atom.py`
- Modify: `skills/neurosym-forge/scripts/scaffold_project.py`

All four read existing `.edn` files, append/modify, write back. They use string keys (`"sorts"`, `"rules"`, `"atoms"`, `"checksums"`). Switch all to `Keyword` instances.

- [ ] **Step 1: For each file, replace.**

For `add_sort.py`, find the section that builds the payload dict. Currently:

```python
payload = read_edn_as_json(path)
# manipulates payload["sorts"]
write_json_as_edn(path, payload)
```

Replace with:

```python
from scripts._edn_reader import Keyword
from scripts._io import read_edn_file, write_edn_file

SORTS_KEY = Keyword("sorts")

payload = read_edn_file(path)
existing = payload.get(SORTS_KEY, [])
# ... manipulate existing ...
payload[SORTS_KEY] = existing
write_edn_file(path, payload)
```

The same pattern applies to all four files. Define the key constants at module level for each file:

| File | Keys used |
|---|---|
| `add_sort.py` | `Keyword("sorts")`, `Keyword("checksums")` |
| `add_rewrite_rule.py` | `Keyword("rules")`, `Keyword("id")`, `Keyword("lhs")`, `Keyword("rhs")`, `Keyword("doc")`, `Keyword("tags")`, `Keyword("checksums")` |
| `add_grounded_atom.py` | `Keyword("grounded")`, `Keyword("kind")`, `Keyword("name")`, `Keyword("sort")`, `Keyword("doc")`, `Keyword("checksums")` |
| `scaffold_project.py` | `Keyword("checksums")` (only the post-render checksum init) |

Define them at module level (don't re-create on every call).

For each script, also remove the `import json` line if present and the `_apply_predicates` regex-using JSON-style code in `ingest_ledger.py` — wait, that's a Bermuda file. For neurosym-forge, the changes are pure key swaps.

- [ ] **Step 2: Run the tests for each, expect them to PASS or FAIL with shape mismatches.**

The existing tests build expected outputs as dicts with string keys. They'll need to use `Keyword` too. Update each test file in lockstep.

```bash
cd skills/neurosym-forge && .venv/Scripts/python.exe -m pytest tests/test_add_sort.py tests/test_add_rewrite_rule.py tests/test_add_grounded_atom.py tests/test_scaffold_project.py -v
```

For each failure: read the test, update the expected shape to use `Keyword(...)` keys.

Example for `tests/test_add_sort.py`:

```python
# BEFORE
def test_appends_primitive(tmp_path: Path) -> None:
    project = _seed(tmp_path)
    add_sort(project, ":molarity")
    payload = read_edn_as_json(project / "rules" / "seed.edn")
    assert ":molarity" in payload["sorts"]

# AFTER
def test_appends_primitive(tmp_path: Path) -> None:
    project = _seed(tmp_path)
    add_sort(project, ":molarity")
    payload = read_edn_file(project / "rules" / "seed.edn")
    assert Keyword("molarity") in payload[Keyword("sorts")]
```

Note also: the seed fixture written by `_seed(...)` builds the initial dict with `"sorts": [":int", ":real"]` (string keys, string values). Update `_seed` to use `Keyword` keys and values:

```python
def _seed(tmp_path: Path) -> Path:
    (tmp_path / "rules").mkdir()
    write_edn_file(tmp_path / "rules" / "seed.edn", {
        Keyword("version"): 1,
        Keyword("sorts"): [Keyword("int"), Keyword("real")],
        Keyword("rules"): [],
        Keyword("atoms"): [],
    })
    write_edn_file(tmp_path / "rules" / ".checksums.edn", {Keyword("checksums"): {}})
    return tmp_path
```

Apply the same translation to all four test files.

- [ ] **Step 3: Run all neurosym-forge tests, expect PASS.**

```bash
cd skills/neurosym-forge && .venv/Scripts/python.exe -m pytest tests/ -q
```

Expected: 87 baseline + ~33 new from Phases 1-3 = ~120 passing. Some pre-existing tests may fail because their fixture seeds use string keys; update them as part of this task.

- [ ] **Step 4: Commit.**

```bash
git add skills/neurosym-forge/scripts/add_sort.py skills/neurosym-forge/scripts/add_rewrite_rule.py skills/neurosym-forge/scripts/add_grounded_atom.py skills/neurosym-forge/scripts/scaffold_project.py skills/neurosym-forge/tests/
git commit -m "neurosym-forge: migrate scripts + tests to Keyword keys"
```

### Task 4.2: `lint_atomspace.py` and `lint_rewrite_coverage.py`

**Files:**
- Modify: `skills/neurosym-forge/scripts/lint_atomspace.py`
- Modify: `skills/neurosym-forge/scripts/lint_rewrite_coverage.py`
- Modify: their tests

Same pattern: replace string-key lookups with `Keyword(...)` lookups.

- [ ] **Step 1: Update `lint_atomspace.py`.**

Find every `payload.get("sorts")`, `payload.get("atoms")`, `payload.get("rules")` and the inner walks. Replace with:

```python
SORTS_KEY = Keyword("sorts")
ATOMS_KEY = Keyword("atoms")
RULES_KEY = Keyword("rules")
KIND_KEY = Keyword("kind")
SORT_KEY = Keyword("sort")
HEAD_KEY = Keyword("head")
ARGS_KEY = Keyword("args")
NAME_KEY = Keyword("name")
LHS_KEY = Keyword("lhs")
RHS_KEY = Keyword("rhs")
ID_KEY = Keyword("id")
```

`_walk_atom_sorts` traverses dicts looking up `"head"`, `"args"`, `"sort"`. Update to use `HEAD_KEY` etc.

The "sort string" comparisons (`"_starts_with(":") not in known_primitives"`) need to compare against `Keyword` instances, not strings. The known_primitives set should hold `Keyword` instances.

- [ ] **Step 2: Update `lint_rewrite_coverage.py`.**

Same pattern. Replace string-key lookups with Keyword lookups. Update tests in lockstep.

- [ ] **Step 3: Update tests.**

`tests/test_lint_atomspace.py` and `tests/test_lint_rewrite_coverage.py`. Update fixture data and assertions.

- [ ] **Step 4: Run, expect PASS.**

```bash
cd skills/neurosym-forge && .venv/Scripts/python.exe -m pytest tests/test_lint_atomspace.py tests/test_lint_rewrite_coverage.py -v
```

- [ ] **Step 5: Run the full suite.**

```bash
cd skills/neurosym-forge && .venv/Scripts/python.exe -m pytest tests/ -q
```

Expect all green.

- [ ] **Step 6: Commit.**

```bash
git add skills/neurosym-forge/scripts/lint_atomspace.py skills/neurosym-forge/scripts/lint_rewrite_coverage.py skills/neurosym-forge/tests/
git commit -m "neurosym-forge: migrate linters to Keyword-keyed payloads"
```

### Task 4.3: Migrate fixture files

**Files:**
- Modify: `skills/neurosym-forge/tests/fixtures/*.edn`

The fixture files were written by hand in JSON syntax. Migrate each to real EDN syntax. The reader can parse both shapes during migration (string keys read as strings, keyword-shaped tokens like `":int"` in a JSON string also read as strings), but the EDN-correct shape uses keyword tokens.

- [ ] **Step 1: List the fixture files.**

```bash
ls skills/neurosym-forge/tests/fixtures/
```

Expected:
- `valid_atom_symbol.edn`
- `valid_atom_grounded.edn`
- `invalid_atom_missing_sort.edn`
- `valid_rule_commutative.edn`
- `invalid_rule_unbound_var.edn`
- `seed_atomspace.edn`

- [ ] **Step 2: Migrate each from JSON syntax to real EDN.**

For `valid_atom_symbol.edn`, replace:

```json
{"kind": "symbol", "name": ":osmotic-pressure", "sort": {"kind": "fn", "args": [":solution"], "ret": ":real"}}
```

with:

```clojure
{:kind :symbol
 :name :osmotic-pressure
 :sort {:kind :fn :args [:solution] :ret :real}}
```

Same pattern for the others. Keep the semantic content; switch syntax.

For `seed_atomspace.edn`:

```clojure
{:version 1
 :sorts [:int :real :bool :solution {:kind :fn :args [:solution] :ret :real}]
 :rules [{:id "R001"
          :lhs {:kind :expression
                :sort :real
                :head {:kind :symbol :name :+
                       :sort {:kind :fn :args [:real :real] :ret :real}}
                :args [{:kind :variable :name "?a" :sort :real}
                       {:kind :variable :name "?b" :sort :real}]}
          :rhs {:kind :expression
                :sort :real
                :head {:kind :symbol :name :+
                       :sort {:kind :fn :args [:real :real] :ret :real}}
                :args [{:kind :variable :name "?b" :sort :real}
                       {:kind :variable :name "?a" :sort :real}]}
          :doc "commutativity"}]
 :atoms [{:kind :symbol :name :osmotic-pressure
          :sort {:kind :fn :args [:solution] :ret :real}}]}
```

Notice: keyword `:+` for the symbol name; variable names are strings (`"?a"`) because they start with `?` and aren't valid EDN keywords.

Wait — actually `?a` in EDN is a symbol, not a keyword. The reader currently doesn't support symbols. For variable names we use the string form (`"?a"`) — this matches how the v0.2 code already represents them.

- [ ] **Step 3: Update fixture-loading tests.**

`tests/test_atom.py` and `tests/test_rewrite_rule.py` read these fixtures and assert shape. Update assertions to expect `Keyword` instances where the fixture has keywords.

Example:

```python
# BEFORE
def test_load_symbol(fixtures_dir: Path) -> None:
    a = Atom.from_dict(read_edn_as_json(fixtures_dir / "valid_atom_symbol.edn"))
    assert a.kind == "symbol"
    assert a.name == ":osmotic-pressure"

# AFTER
def test_load_symbol(fixtures_dir: Path) -> None:
    a = Atom.from_dict(read_edn_file(fixtures_dir / "valid_atom_symbol.edn"))
    assert a.kind == Keyword("symbol")
    assert a.name == Keyword("osmotic-pressure")
```

But wait — `Atom.from_dict` currently expects string `kind` values. The dataclass stores them as strings. Two options:

(a) Update `Atom.from_dict` to accept either str or Keyword and normalize to one; keep storing string.
(b) Update `Atom.from_dict` to store Keywords directly.

Recommendation: **(a)**. Keep the `Atom` dataclass's `kind` field a string; have `from_dict` accept Keyword and convert via `.name`. This minimises blast radius across the codebase and matches how the existing checks work (`atom.kind == "symbol"`). Same for `Atom.name`, `Atom.sort` (sort is more complex — see below).

`Sort` is structured: primitives are `Keyword` after the migration; functions and enums are dicts with Keyword keys and Keyword `:kind` values. `Sort.from_value` already handles both shapes (strings ":foo" historically, dict structured); extend it to also accept `Keyword` instances directly.

Update `scripts/atom.py`:

```python
def _normalize(value):
    """Accept either a string or a Keyword; return the string form."""
    if isinstance(value, Keyword):
        return str(value)  # e.g. ":foo" or ":ns/bar"
    return value
```

Then everywhere the atom dataclass receives a `kind` field, normalize via `_normalize`.

This is the cleanest minimal-disruption path.

- [ ] **Step 4: Run all atom/rule tests.**

```bash
cd skills/neurosym-forge && .venv/Scripts/python.exe -m pytest tests/test_atom.py tests/test_rewrite_rule.py tests/test_sort_registry.py -v
```

Fix until green.

- [ ] **Step 5: Commit.**

```bash
git add skills/neurosym-forge/tests/fixtures/ skills/neurosym-forge/scripts/atom.py skills/neurosym-forge/scripts/sort_registry.py skills/neurosym-forge/scripts/rewrite_rule.py skills/neurosym-forge/tests/test_atom.py skills/neurosym-forge/tests/test_rewrite_rule.py skills/neurosym-forge/tests/test_sort_registry.py
git commit -m "neurosym-forge: migrate fixtures to real EDN; normalize Keyword inputs"
```

---

## Phase 5: Migrate Bermuda Python helpers

### Task 5.1: `verifiers/bermuda/scripts/ingest_ledger.py`

**Files:**
- Modify: `verifiers/bermuda/scripts/ingest_ledger.py`
- Modify: `verifiers/bermuda/scripts/extract_prose.py`
- Modify: `verifiers/bermuda/scripts/prose_patterns.py`
- Modify: `verifiers/bermuda/scripts/verdict_to_qa.py`
- Modify: `verifiers/bermuda/scripts/run_verification.py`

These currently use their own `read_edn_as_json` / write helpers OR import from neurosym-forge. After Phase 3, the neurosym-forge helpers emit real EDN; Bermuda's local copies must follow.

- [ ] **Step 1: Inspect each file.**

Read each. Most use `json.dumps(payload, ...)` directly because Bermuda has its own thin Python project (it doesn't always import neurosym-forge as a library).

The two relevant patterns:

(a) Direct `json.dumps` writes: replace with `write_edn_file` from neurosym-forge (import it).
(b) Direct `json.loads` reads: replace with `read_edn_file`.

To make the import work across project boundaries, add to each Bermuda script:

```python
import sys
from pathlib import Path

# Path to neurosym-forge's scripts package
_FORGE_SCRIPTS = Path(__file__).resolve().parents[3] / "skills" / "neurosym-forge"
sys.path.insert(0, str(_FORGE_SCRIPTS))
from scripts._edn_reader import Keyword, read_edn  # noqa: E402
from scripts._edn_writer import write_edn  # noqa: E402
from scripts._io import read_edn_file, write_edn_file  # noqa: E402
```

This is ugly. A cleaner approach: install neurosym-forge as a dev dep in `verifiers/bermuda/pyproject.toml`:

```toml
[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    # Pulls neurosym-forge in editable mode from the workspace
    "neurosym-forge @ file:///${PROJECT_ROOT}/../../skills/neurosym-forge",
]
```

But editable file: URLs are fragile on Windows. Recommendation: keep the explicit `sys.path` insertion at the top of each Bermuda script; document it in a header comment.

- [ ] **Step 2: Migrate `ingest_ledger.py`.**

Read the current file; replace the JSON-write section with EDN. The atom dicts it builds use string keys today. Change to Keyword keys.

Before:

```python
payload = {"version": 1, "atoms": [...]}
out_path.write_text(json.dumps(payload, ...), encoding="utf-8")
```

After:

```python
payload = {Keyword("version"): 1, Keyword("atoms"): [...]}
write_edn_file(out_path, payload)
```

For each atom record, change the inner keys too:

```python
base: dict = {
    Keyword("id"): claim.get("claim_id", "?"),
    Keyword("doc"): text[:200],
    ...
}
if claim.get("claim_type") == "design_decision":
    base.update({
        Keyword("kind"): Keyword("symbol"),
        Keyword("sort"): Keyword("formula"),
        Keyword("name"): Keyword("CONTEXT"),
        Keyword("context"): True,
    })
```

Run the tests for ingest_ledger. Update test assertions to compare against Keyword keys.

- [ ] **Step 3: Migrate `extract_prose.py` + `prose_patterns.py`.**

Same pattern. The emitted atoms switch from string keys to Keyword keys. The regex tables are unchanged.

- [ ] **Step 4: Migrate `verdict_to_qa.py`.**

Currently reads `verdict.edn` as JSON (`json.loads`). Switch to `read_edn_file`. The output `verification-defects.json` STAYS JSON — book-qa reads it as JSON. So this file reads EDN, writes JSON. The script bridges the two formats deliberately.

- [ ] **Step 5: Migrate `run_verification.py`.**

The stubbed verdict it writes is currently `json.dumps`. Switch to `write_edn_file`. Update the stub verdict to use Keyword keys.

- [ ] **Step 6: Migrate test fixtures.**

`tests/fixtures/`:
- `ledger_clean.jsonl` — keep as JSONL (book-knowledge ledger format, unchanged)
- `ledger_with_contradiction.jsonl` — keep as JSONL
- `chapter_clean.md` — keep as markdown
- `chapter_with_8_parishes.md` — keep as markdown
- `verdict_sat.edn` — migrate to real EDN syntax with Keyword keys
- `verdict_unsat.edn` — migrate to real EDN syntax with Keyword keys

For `verdict_sat.edn`:

```clojure
{:version 1
 :verdict :sat
 :core []
 :verified-count 12}
```

For `verdict_unsat.edn`:

```clojure
{:version 1
 :verdict :unsat
 :core ["clm-2026-000008" "prose-ch-02-001"]
 :explanation "Chapter 2 prose says 8 parishes; ledger says 9."
 :verified-count 11}
```

Update `tests/test_verdict_to_qa.py` to expect Keyword values for the `:verdict` field.

- [ ] **Step 7: Run all Bermuda tests.**

```bash
cd verifiers/bermuda && .venv/Scripts/python.exe -m pytest tests/ -q
```

Fix to green. The baseline is 23 tests; after migration it should be 23 still (no new tests, just shape changes).

- [ ] **Step 8: Smoke against real Bermuda ledger.**

```bash
cd verifiers/bermuda && .venv/Scripts/python.exe -m scripts.ingest_ledger \
  --ledger ../../examples/bermuda-manual/claims/ledger.jsonl \
  --predicates rules/predicates.edn \
  --out work/claims.edn
cat work/claims.edn | head -20
```

Expected: real EDN output with keyword keys and keyword values. No JSON-style quoted keywords.

- [ ] **Step 9: Commit.**

```bash
git add verifiers/bermuda/scripts/ verifiers/bermuda/tests/
git commit -m "verifiers/bermuda: migrate Python helpers and fixtures to real EDN"
```

---

## Phase 6: Rust templates and Bermuda Rust files

### Task 6.1: Add `edn-rs` back to Cargo.toml.tmpl + template-shape tests

**Files:**
- Modify: `skills/neurosym-forge/assets/project-template/rust-verifier/Cargo.toml.tmpl`
- Modify: `verifiers/bermuda/rust-verifier/Cargo.toml`
- Modify: `skills/neurosym-forge/tests/test_rust_template_shape.py`

- [ ] **Step 1: Append template-shape tests.**

```python
# Append to tests/test_rust_template_shape.py

def test_cargo_template_includes_edn_rs() -> None:
    text = _read("Cargo.toml.tmpl")
    assert "edn-rs" in text, "Cargo.toml.tmpl must declare edn-rs"


def test_ir_template_uses_edn_rs_not_serde_json() -> None:
    text = _read("ir.rs.tmpl")
    # ir.rs PARSES atoms from the Python writer — must use edn-rs
    assert "edn_rs" in text or "edn-rs" in text, "ir.rs.tmpl must use edn-rs for parsing"
    # serde_json may still appear for the verdict serialization or types,
    # but the PARSE path must not be serde_json
    assert "serde_json::from_str" not in text, \
        "ir.rs.tmpl must not use serde_json::from_str on the atom parse path"


def test_smt_template_dispatches_on_edn() -> None:
    text = _read("smt.rs.tmpl")
    # smt.rs receives parsed atoms from ir.rs. After PR-1 these are
    # edn_rs::Edn values, not serde_json::Value.
    assert "edn_rs" in text or "Edn" in text, \
        "smt.rs.tmpl must dispatch on edn_rs::Edn values"
```

- [ ] **Step 2: Run, expect FAIL.**

```bash
cd skills/neurosym-forge && .venv/Scripts/python.exe -m pytest tests/test_rust_template_shape.py -k "edn" -v
```

Expected: all three new tests fail (templates still use serde_json).

- [ ] **Step 3: Update `Cargo.toml.tmpl`.**

Add `edn-rs = "0.19"` to the dependencies block. Keep `serde_json = "1"` for the existing verdict serialization (PR-2 of v0.4 will replace this).

```toml
[dependencies]
napi          = { version = "3", features = ["napi9", "serde-json", "async"] }
napi-derive   = "3"
serde         = { version = "1", features = ["derive"] }
serde_json    = "1"
edn-rs        = "0.19"
thiserror     = "2"
ordered-float = "4"

z3            = { version = "0.20", features = ["bundled"], optional = true }
egg           = { version = "0.10", optional = true }
cozo          = { version = "0.7", default-features = false, features = ["compact"], optional = true }
tectonic      = { version = "0.16", optional = true }
```

- [ ] **Step 4: Update `ir.rs.tmpl`.**

Replace `serde_json::from_str` with `edn_rs::Edn::from_str`. Update the type signature of `Atom`:

```rust
// Before
pub type Atom = serde_json::Value;

// After
pub type Atom = edn_rs::Edn;
```

Replace `parse_formulas`:

```rust
pub fn parse_formulas(edn: &str) -> Result<Vec<(ClaimId, Atom)>, Error> {
    use edn_rs::{Edn, EdnError};
    let parsed: Edn = Edn::from_str(edn).map_err(|e: EdnError| Error::Parse(e.to_string()))?;
    let atoms = match parsed.get(":atoms") {
        Some(Edn::Vector(v)) => v.to_vec(),
        Some(_) | None => return Err(Error::Parse("missing or non-vector :atoms".into())),
    };
    let mut out = Vec::with_capacity(atoms.len());
    for a in atoms {
        let id = match a.get(":id") {
            Some(Edn::Str(s)) => s.clone(),
            _ => "?".to_string(),
        };
        out.push((id, a));
    }
    Ok(out)
}
```

The `verdict` round-trip continues to use `serde_json::to_string` for v0.4 PR-1; PR-2 swaps it to EDN emission so CLJS reads keywords correctly. Note this in a comment.

- [ ] **Step 5: Update `smt.rs.tmpl`.**

Switch the typed dispatch from `serde_json::Value` to `edn_rs::Edn`. The dispatch becomes:

```rust
use edn_rs::Edn;

let assertion: Bool = match value {
    Edn::Int(n) => {
        let z3_var = Int::new_const(&ctx, var_name.as_str());
        z3_var._eq(&Int::from_i64(&ctx, *n))
    }
    Edn::Double(f) => {
        let v: f64 = f.into();
        let z3_var = Real::new_const(&ctx, var_name.as_str());
        let numerator = (v * 1_000_000.0) as i32;
        z3_var._eq(&Real::from_real(&ctx, numerator, 1_000_000))
    }
    Edn::Str(s) => {
        let z3_var = Z3String::new_const(&ctx, var_name.as_str());
        let lit = Z3String::from_str(&ctx, s)
            .map_err(|_| Error::Smt(format!("invalid string literal: {s:?}")))?;
        z3_var._eq(&lit)
    }
    Edn::Bool(b) => {
        let z3_var = Bool::new_const(&ctx, var_name.as_str());
        z3_var._eq(&Bool::from_bool(&ctx, *b))
    }
    _ => continue,
};
```

The atom-field access patterns change too:

```rust
let kind = match atom.get(":kind") {
    Some(Edn::Key(k)) => k.clone(),     // edn_rs keywords stored as :keyword strings
    Some(Edn::Str(s)) => s.clone(),     // accept either for migration
    _ => "".to_string(),
};
if kind != ":expression" {
    continue;
}
```

This mirrors the Python-side normalization: accept either Keyword or string during migration, with Keyword as the canonical form.

- [ ] **Step 6: Run the template-shape tests, expect PASS.**

```bash
cd skills/neurosym-forge && .venv/Scripts/python.exe -m pytest tests/test_rust_template_shape.py -v
```

- [ ] **Step 7: Mirror the template changes into Bermuda's already-scaffolded files.**

```bash
# Cargo.toml — add edn-rs
# ir.rs — same parse_formulas as the template
# smt.rs — same dispatch on Edn as the template
```

Diff the template against the live Bermuda file:

```bash
diff skills/neurosym-forge/assets/project-template/rust-verifier/src/ir.rs.tmpl verifiers/bermuda/rust-verifier/src/ir.rs
```

Apply the template's body to the Bermuda file. The template uses Jinja `{{ project_slug }}` substitution but neither `ir.rs.tmpl` nor `smt.rs.tmpl` actually has slug substitutions in the relevant blocks; they're identical text.

Repeat for `smt.rs` and `Cargo.toml`.

- [ ] **Step 8: Commit.**

```bash
git add skills/neurosym-forge/assets/project-template/rust-verifier/ skills/neurosym-forge/tests/test_rust_template_shape.py verifiers/bermuda/rust-verifier/
git commit -m "rust templates: edn-rs on atom parse + smt dispatch; Bermuda lockstep"
```

---

## Phase 7: Smoke + PR

### Task 7.1: Full sweep + scaffold smoke

- [ ] **Step 1: Run all suites.**

```bash
cd skills/neurosym-forge && .venv/Scripts/python.exe -m pytest tests/ -q
cd ../book-qa && python -m pytest tests/ -q
cd ../../verifiers/bermuda && .venv/Scripts/python.exe -m pytest tests/ -q
```

Expected:
- neurosym-forge: 87 + ~33 new (Phases 1-2-3) + ~5 template-shape (Phase 6) = ~125 passing
- book-qa: 47 unchanged
- verifiers/bermuda: 23 unchanged

- [ ] **Step 2: Scaffold a fresh project.**

```bash
cd skills/neurosym-forge
.venv/Scripts/python.exe -m scripts.scaffold_project \
  --name "EDN smoke" --slug edn_smoke --out /tmp/edn_smoke

cat /tmp/edn_smoke/rules/seed.edn | head -5
```

Expected output uses real EDN: `:sorts [...]`, `:rules [...]`, with no JSON-style `":foo"` strings where keywords belong.

- [ ] **Step 3: Confirm the Rust template uses edn-rs.**

```bash
grep -c "edn_rs" /tmp/edn_smoke/rust-verifier/src/ir.rs
grep -c "edn-rs" /tmp/edn_smoke/rust-verifier/Cargo.toml
```

Expected: both at least 1.

- [ ] **Step 4: Cleanup.**

```bash
rm -rf /tmp/edn_smoke
```

### Task 7.2: Push + open PR

- [ ] **Step 1: Push.**

```bash
cd C:/Users/charl/code/russellian-book-suite-booklogic
git push -u origin spec/booklogic
```

- [ ] **Step 2: Open the PR.**

```bash
gh pr create --title "BookLogic v0.4 PR-1: real EDN at the Python↔CLJS↔Rust boundary" --body "$(cat <<'EOF'
## Summary

Lands the first sub-PR of the BookLogic v0.4 mission: real EDN at every boundary, replacing the JSON-stamped-`.edn` that PR #14/18 shipped.

- New: `_edn_reader.py` and `_edn_writer.py` in `skills/neurosym-forge/scripts/` over a documented EDN subset (primitives, keywords, maps, vectors, lists, comments — no tagged literals yet)
- `_io.py` reads/writes via the new modules; the deprecated `read_edn_as_json` / `write_json_as_edn` aliases remain for one cycle with deprecation warnings
- All neurosym-forge scripts (`add_sort`, `add_rewrite_rule`, `add_grounded_atom`, `scaffold_project`, `lint_atomspace`, `lint_rewrite_coverage`) migrated to `Keyword`-keyed payloads
- All fixture files migrated from JSON syntax to real EDN syntax
- Bermuda's Python helpers (`ingest_ledger`, `extract_prose`, `prose_patterns`, `verdict_to_qa`, `run_verification`) migrated
- Bermuda's fixtures migrated
- Rust templates and Bermuda's already-scaffolded `ir.rs` / `smt.rs` / `Cargo.toml` switched from `serde_json::Value` to `edn_rs::Edn` on the atom parse + SMT dispatch paths
- 30+ new tests across reader, writer, round-trip, and template-shape

The verdict-emission path on the Rust side still uses `serde_json::to_string` for v0.4 PR-1; PR-2 swaps it to EDN so CLJS reads keywords correctly on the return trip.

Spec: `docs/specs/2026-05-14-booklogic-v0.4-mission-design.md` § "D1 — Real EDN boundary".
Plan: `docs/plans/2026-05-14-booklogic-v0.4-pr1.md`.

## Test plan

- [ ] `cd skills/neurosym-forge && .venv/Scripts/python.exe -m pytest tests/ -q` — ~125 passing
- [ ] `cd skills/book-qa && python -m pytest tests/ -q` — 47 passing (unchanged)
- [ ] `cd verifiers/bermuda && .venv/Scripts/python.exe -m pytest tests/ -q` — 23 passing (unchanged)
- [ ] Scaffold smoke: scaffolded project's `rules/seed.edn` opens in CLJS without parse errors (manual `node -e 'const cljs = require(...)' check, optional)
- [ ] Bermuda ingest smoke: `.venv/Scripts/python.exe -m scripts.ingest_ledger --ledger ../../examples/bermuda-manual/claims/ledger.jsonl ...` produces a real-EDN `work/claims.edn`

## Out of scope

- The Rust verdict serialization still emits JSON — PR-2 fixes this
- Tagged literals (`#inst`, `#uuid`) — PR-2 adds these for ingest-trace events
- BookLogic DSL forms — PR-3 + PR-4
- Bermuda real Z3 run — PR-5
EOF
)"
```

- [ ] **Step 3: Report PR URL.**

---

## Self-review

Walking the spec § D1 against this plan:

| Spec clause | Implementing tasks |
|---|---|
| Python EDN reader | 1.1, 1.2 |
| Python EDN writer | 2.1 |
| Round-trip tests | 2.2 |
| `_io.py` rewires to new reader/writer | 3.1 |
| All neurosym-forge callers migrated | 4.1, 4.2 |
| Neurosym-forge fixtures migrated | 4.3 |
| Bermuda Python helpers migrated | 5.1 |
| Bermuda fixtures migrated | 5.1 step 6 |
| Rust `edn-rs` on input path | 6.1 |
| Rust template-shape tests | 6.1 |
| Bermuda Rust files lockstep | 6.1 step 7 |

All spec items have implementing tasks.

**Placeholder scan:** No "TBD/TODO/fill in" in any task. Each step has the code or the exact command.

**Type consistency:** `Keyword`, `read_edn_file`, `write_edn_file`, `read_edn`, `write_edn`, `EdnReadError`, `EdnWriteError` are used identically across all tasks that reference them. `Atom`, `Sort`, `RewriteRule` dataclasses keep their existing signatures; their inputs are normalised by `_normalize` (Task 4.3 step 3) to accept either string or Keyword.

**Effort:** Spec said 1.5 days. This plan is closer to 2 days given the surface area (six phases, ~15 file modifications, 30+ tests). The extra 0.5 day buys robustness on the Bermuda migration step. Acceptable.

**Known risks:**
- The hand-rolled EDN reader is small but novel; round-trip tests in Phase 2 are the primary defence.
- Atom dataclass `kind`/`name`/`sort` field types — keeping them as strings (with Keyword-tolerant input) is a deliberate scope-control decision; the alternative (storing Keyword everywhere) ripples through every callsite. The string-based approach is rebuilt cleanly in PR-3 if BookLogic DSL parsing needs to preserve Keywords end-to-end.
- The Rust changes ship without a cargo-build verification. The template-shape tests are the only PR-1 gate. PR-5 builds for real against Bermuda.

# BookLogic v0.4 PR-2 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the symbolic ingestion-trace artifact, complete the EDN reader/writer with Symbol + `#inst` support, and replace the last `serde_json` serialization on the Rust verdict return-trip with real EDN emission.

**Architecture:** Three additions to the EDN reader/writer in neurosym-forge (Symbol dataclass; `#inst` tagged literal; matching emission). New `export_symbolic_trace.py` and `load_symbolic_trace.py` in book-knowledge, plus a closed-event-head JSON Schema. Hand-rolled Rust EDN verdict emitter replaces `serde_json::to_string`, with both the template and Bermuda's `ir.rs` updated in lockstep. A regenerated `examples/bermuda-manual/analysis/ingest-trace.edn` ships as a worked-example artifact. Spec at `docs/specs/2026-05-14-booklogic-v0.4-pr2-design.md`.

**Tech Stack:** Python 3.13, jsonschema (existing), pytest. Rust source-only changes verified via template-shape tests; no `cargo build` runs.

---

## Pre-flight

Read these before starting:
- `docs/specs/2026-05-14-booklogic-v0.4-pr2-design.md` (this plan implements)
- `docs/specs/2026-05-14-booklogic-v0.4-mission-design.md` § D2 (umbrella context)
- `skills/neurosym-forge/scripts/_edn_reader.py` — existing reader (PR-1 of v0.4 shipped this)
- `skills/neurosym-forge/scripts/_edn_writer.py` — existing writer
- `skills/book-knowledge/scripts/events_log.py` and `assets/events.schema.json` — the existing transition-log machinery (different from the new trace artifact)
- `skills/book-knowledge/scripts/io_utils.py` — `read_jsonl`, `latest_per` helpers
- `examples/bermuda-manual/claims/ledger.jsonl` — 46-claim corpus to export from
- `examples/bermuda-manual/raw/manifests/thesis.json` — example source manifest

**Worktree:** `C:\Users\charl\code\russellian-book-suite-booklogic-pr2` on branch `spec/booklogic-pr2`. The spec is already committed.

**Test invocation:**
- neurosym-forge: `cd skills/neurosym-forge && .venv/Scripts/python.exe -m pytest tests/ -q`
- book-knowledge: `cd skills/book-knowledge && .venv/Scripts/python.exe -m pytest tests/ -q`

If the book-knowledge venv is missing:

```bash
cd skills/book-knowledge && python -m venv .venv && .venv/Scripts/python.exe -m pip install -e ".[dev]"
```

**Baseline counts (from main, post-PR-1):**
- neurosym-forge: 123 tests
- book-knowledge: existing count (run once at start to record)

**Commit hygiene:** terse human commits, no AI attribution, no Co-Authored-By, one problem per commit.

---

## File Structure

### Created

```
skills/neurosym-forge/
└── tests/
    └── test_edn_extensions.py                      NEW — symbol + #inst tests

skills/book-knowledge/
├── scripts/
│   ├── export_symbolic_trace.py                    NEW
│   └── load_symbolic_trace.py                      NEW
├── assets/
│   └── ingest-trace.schema.json                    NEW
└── tests/
    ├── test_export_symbolic_trace.py               NEW
    └── test_load_symbolic_trace.py                 NEW

examples/bermuda-manual/
└── analysis/
    └── ingest-trace.edn                            NEW (generated artifact)
```

### Modified

```
skills/neurosym-forge/
├── scripts/
│   ├── _edn_reader.py                              + Symbol dataclass; tag dispatch with #inst
│   └── _edn_writer.py                              + Symbol + datetime emission

skills/neurosym-forge/assets/project-template/rust-verifier/src/
└── ir.rs.tmpl                                      verdict serializer → EDN

skills/neurosym-forge/tests/test_rust_template_shape.py   + verdict EDN assertion

verifiers/bermuda/rust-verifier/src/
└── ir.rs                                           verdict serializer → EDN (lockstep)
```

---

## Phase 1: EDN reader extensions (Symbol + `#inst`)

### Task 1.1: `Symbol` dataclass + bare-identifier parsing

**Files:**
- Modify: `skills/neurosym-forge/scripts/_edn_reader.py`
- Create: `skills/neurosym-forge/tests/test_edn_extensions.py`

- [ ] **Step 1: Write the failing tests.**

```python
# skills/neurosym-forge/tests/test_edn_extensions.py
from __future__ import annotations

import datetime as dt

import pytest

from scripts._edn_reader import (
    EdnReadError,
    Keyword,
    Symbol,
    read_edn,
    read_edn_all,
)


def test_read_bare_symbol() -> None:
    sym = read_edn("foo")
    assert isinstance(sym, Symbol)
    assert sym.name == "foo"
    assert sym.namespace is None
    assert str(sym) == "foo"


def test_read_namespaced_symbol() -> None:
    sym = read_edn("source/ingested")
    assert isinstance(sym, Symbol)
    assert sym.namespace == "source"
    assert sym.name == "ingested"
    assert str(sym) == "source/ingested"


def test_symbol_equality_and_hash() -> None:
    assert Symbol("foo") == Symbol("foo")
    assert Symbol("bar", namespace="ns") == Symbol("bar", namespace="ns")
    assert hash(Symbol("foo")) == hash(Symbol("foo"))
    assert {Symbol("foo"): 1} == {Symbol("foo"): 1}


def test_symbol_distinct_from_keyword() -> None:
    assert Symbol("foo") != Keyword("foo")
    assert hash(Symbol("foo")) != hash(Keyword("foo"))


def test_true_false_nil_still_literals() -> None:
    # Symbol parsing must not absorb the special literals
    assert read_edn("true") is True
    assert read_edn("false") is False
    assert read_edn("nil") is None


def test_symbol_in_list_head() -> None:
    result = read_edn("(source/ingested {:doc/id \"d1\"})")
    assert isinstance(result, list)
    assert result[0] == Symbol("ingested", namespace="source")
    assert result[1] == {Keyword("doc/id"): "d1"}


def test_symbol_in_vector() -> None:
    result = read_edn("[foo bar/baz]")
    assert result == [Symbol("foo"), Symbol("baz", namespace="bar")]
```

- [ ] **Step 2: Run, expect FAIL** (Symbol doesn't exist yet).

```bash
cd skills/neurosym-forge && .venv/Scripts/python.exe -m pytest tests/test_edn_extensions.py -v
```

Expected: `ImportError: cannot import name 'Symbol'`.

- [ ] **Step 3: Update `_edn_reader.py`.**

Add the `Symbol` dataclass near `Keyword` (top of file):

```python
@dataclass(frozen=True)
class Symbol:
    """An EDN symbol. Hashable and equal-by-value.

    Symbols are bare identifiers (`foo`, `foo/bar`) — distinct from keywords
    (which begin with `:`). The S-expression event heads in the ingestion
    trace use symbols as the leading element of a list.
    """

    name: str
    namespace: str | None = None

    def __str__(self) -> str:
        if self.namespace:
            return f"{self.namespace}/{self.name}"
        return self.name
```

Update `_Parser._parse_atom` to recognise valid identifier patterns as Symbols rather than rejecting them. Replace the existing function body:

```python
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
        # Symbol: starts with letter or underscore; may contain a single '/'
        if token and (token[0].isalpha() or token[0] == "_"):
            if "/" in token:
                ns, _, name = token.partition("/")
                # validate that there's no trailing '/' and name is non-empty
                if not ns or not name or "/" in name:
                    raise EdnReadError(
                        f"malformed namespaced symbol {token!r} at position {start}"
                    )
                return Symbol(name=name, namespace=ns)
            return Symbol(name=token)
        raise EdnReadError(f"unrecognised atom {token!r} at position {start}")
```

- [ ] **Step 4: Run, expect PASS** (7 new tests green).

```bash
cd skills/neurosym-forge && .venv/Scripts/python.exe -m pytest tests/test_edn_extensions.py -v
```

- [ ] **Step 5: Run the full neurosym-forge suite to confirm no regressions.**

```bash
cd skills/neurosym-forge && .venv/Scripts/python.exe -m pytest tests/ -q
```

Expected: 123 baseline + 7 new = 130 passing.

- [ ] **Step 6: Commit.**

```bash
git add skills/neurosym-forge/scripts/_edn_reader.py skills/neurosym-forge/tests/test_edn_extensions.py
git commit -m "neurosym-forge: EDN reader Symbol support"
```

### Task 1.2: `#inst` tagged literal

**Files:**
- Modify: `skills/neurosym-forge/scripts/_edn_reader.py`
- Modify: `skills/neurosym-forge/tests/test_edn_extensions.py`

- [ ] **Step 1: Write failing tests (append to test_edn_extensions.py).**

```python
def test_read_inst_utc_z() -> None:
    value = read_edn('#inst "2026-05-14T15:30:00Z"')
    assert isinstance(value, dt.datetime)
    assert value.year == 2026 and value.month == 5 and value.day == 14
    assert value.hour == 15 and value.minute == 30
    assert value.tzinfo == dt.timezone.utc


def test_read_inst_with_offset() -> None:
    value = read_edn('#inst "2026-05-14T15:30:00+02:00"')
    assert isinstance(value, dt.datetime)
    assert value.utcoffset() == dt.timedelta(hours=2)


def test_read_inst_with_microseconds() -> None:
    value = read_edn('#inst "2026-05-12T16:13:51.630442Z"')
    assert value.microsecond == 630442


def test_read_inst_inside_collection() -> None:
    result = read_edn('{:ts #inst "2026-05-14T00:00:00Z"}')
    assert isinstance(result[Keyword("ts")], dt.datetime)


def test_unknown_tag_raises() -> None:
    with pytest.raises(EdnReadError, match=r"unknown tag"):
        read_edn('#uuid "550e8400-e29b-41d4-a716-446655440000"')


def test_dangling_hash_raises() -> None:
    with pytest.raises(EdnReadError, match=r"dangling"):
        read_edn("#")


def test_inst_expects_string_payload() -> None:
    with pytest.raises(EdnReadError, match=r"#inst expects a string"):
        read_edn('#inst 42')


def test_inst_invalid_format_raises() -> None:
    with pytest.raises(EdnReadError, match=r"invalid #inst literal"):
        read_edn('#inst "not-a-datetime"')
```

- [ ] **Step 2: Run, expect FAIL** (`#` still rejected outright by reader).

```bash
cd skills/neurosym-forge && .venv/Scripts/python.exe -m pytest tests/test_edn_extensions.py -k "inst or tag or hash" -v
```

- [ ] **Step 3: Update `_edn_reader.py`.**

Add a `datetime` import at the top:

```python
import datetime as dt
```

Replace the `#` branch in `_Parser._parse_form` (currently raises "tagged literals... are not supported"):

```python
        if c == "#":
            self._advance()  # consume '#'
            if self._eof():
                raise EdnReadError("dangling #")
            tag_start = self.pos
            while not self._eof() and self._peek() not in " \t\n\r,()[]{}\";":
                self.pos += 1
            tag = self.src[tag_start:self.pos]
            if not tag:
                raise EdnReadError("dangling # (empty tag)")
            if tag == "inst":
                self._skip_ws_and_comments()
                value = self._parse_form()
                if not isinstance(value, str):
                    raise EdnReadError(
                        f"#inst expects a string payload, got {type(value).__name__}"
                    )
                try:
                    return _parse_inst(value)
                except ValueError as e:
                    raise EdnReadError(f"invalid #inst literal: {e}")
            raise EdnReadError(f"unknown tag #{tag!r}")
```

Add the `_parse_inst` helper at module level (after the `Symbol` dataclass):

```python
def _parse_inst(s: str) -> dt.datetime:
    """Parse an ISO-8601 timestamp into a timezone-aware datetime.

    Accepts both 'Z' and '+HH:MM' offsets. Microsecond precision honoured.
    """
    # Python 3.11+ datetime.fromisoformat handles 'Z' natively; for
    # earlier interpreters, normalise 'Z' to '+00:00'.
    normalized = s.replace("Z", "+00:00") if s.endswith("Z") else s
    return dt.datetime.fromisoformat(normalized)
```

- [ ] **Step 4: Run, expect PASS** (8 new tests green).

```bash
cd skills/neurosym-forge && .venv/Scripts/python.exe -m pytest tests/test_edn_extensions.py -v
```

- [ ] **Step 5: Run the existing reader suite for regression check.**

```bash
cd skills/neurosym-forge && .venv/Scripts/python.exe -m pytest tests/test_edn_reader.py -v
```

Note: `test_unsupported_tagged_literal_raises` from PR-1 currently asserts `#inst` raises "tagged literals" — that test now fails because we support `#inst`. Update it to assert a DIFFERENT unsupported tag (`#uuid`) still raises:

```python
def test_unsupported_tagged_literal_raises() -> None:
    with pytest.raises(EdnReadError, match=r"unknown tag"):
        read_edn('#uuid "550e8400-e29b-41d4-a716-446655440000"')
```

(The match string changes from "tagged literals" to "unknown tag" because we now have selective tag support.)

- [ ] **Step 6: Re-run the existing suite — expect green.**

- [ ] **Step 7: Commit.**

```bash
git add skills/neurosym-forge/scripts/_edn_reader.py skills/neurosym-forge/tests/test_edn_extensions.py skills/neurosym-forge/tests/test_edn_reader.py
git commit -m "neurosym-forge: EDN reader #inst tagged literal"
```

---

## Phase 2: EDN writer extensions

### Task 2.1: Symbol + datetime emission

**Files:**
- Modify: `skills/neurosym-forge/scripts/_edn_writer.py`
- Modify: `skills/neurosym-forge/tests/test_edn_extensions.py`

- [ ] **Step 1: Append failing tests.**

```python
# Append to test_edn_extensions.py

from scripts._edn_writer import write_edn


def test_write_symbol_bare() -> None:
    assert write_edn(Symbol("foo")) == "foo"


def test_write_symbol_namespaced() -> None:
    assert write_edn(Symbol("ingested", namespace="source")) == "source/ingested"


def test_write_datetime_utc() -> None:
    instant = dt.datetime(2026, 5, 14, 15, 30, tzinfo=dt.timezone.utc)
    assert write_edn(instant) == '#inst "2026-05-14T15:30:00Z"'


def test_write_datetime_offset() -> None:
    tz = dt.timezone(dt.timedelta(hours=2))
    instant = dt.datetime(2026, 5, 14, 15, 30, tzinfo=tz)
    out = write_edn(instant)
    assert out.startswith('#inst "')
    assert "+02:00" in out


def test_round_trip_symbol() -> None:
    from scripts._edn_reader import read_edn as r
    sym = Symbol("ingested", namespace="source")
    assert r(write_edn(sym)) == sym


def test_round_trip_datetime() -> None:
    from scripts._edn_reader import read_edn as r
    instant = dt.datetime(2026, 5, 12, 16, 13, 51, 630442, tzinfo=dt.timezone.utc)
    assert r(write_edn(instant)) == instant


def test_round_trip_event_list() -> None:
    from scripts._edn_reader import read_edn as r
    event = [
        Symbol("ingested", namespace="source"),
        {
            Keyword("doc/id"): "d1",
            Keyword("ingested-at"): dt.datetime(2026, 5, 14, 0, 0, 0, tzinfo=dt.timezone.utc),
        },
    ]
    s = write_edn(event)
    assert r(s) == event
```

- [ ] **Step 2: Run, expect FAIL** (writer doesn't know Symbol or datetime).

```bash
cd skills/neurosym-forge && .venv/Scripts/python.exe -m pytest tests/test_edn_extensions.py -k "write or round_trip_symbol or round_trip_datetime or round_trip_event" -v
```

- [ ] **Step 3: Update `_edn_writer.py`.**

Add imports at the top:

```python
import datetime as dt

from scripts._edn_reader import Keyword, Symbol
```

(The Symbol import is the only new line in the imports block; Keyword was already there.)

In `_emit_compact`, add the Symbol and datetime branches BEFORE the bool/int branches (Symbol and datetime are not int subclasses, but place them with the other dataclass types for clarity):

```python
def _emit_compact(value: Any) -> str:
    if value is None:
        return "nil"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, Keyword):
        return str(value)
    if isinstance(value, Symbol):
        return str(value)
    if isinstance(value, dt.datetime):
        iso = value.isoformat()
        if iso.endswith("+00:00"):
            iso = iso[:-6] + "Z"
        return f'#inst "{iso}"'
    if isinstance(value, str):
        return _emit_string(value)
    if isinstance(value, bool):
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
```

- [ ] **Step 4: Run, expect PASS** (7 new tests green).

```bash
cd skills/neurosym-forge && .venv/Scripts/python.exe -m pytest tests/test_edn_extensions.py -v
```

- [ ] **Step 5: Run the full neurosym-forge suite.**

```bash
cd skills/neurosym-forge && .venv/Scripts/python.exe -m pytest tests/ -q
```

Expected: ~145 passing (123 baseline + 7 reader Symbol + 8 reader #inst + 7 writer = 145).

- [ ] **Step 6: Commit.**

```bash
git add skills/neurosym-forge/scripts/_edn_writer.py skills/neurosym-forge/tests/test_edn_extensions.py
git commit -m "neurosym-forge: EDN writer Symbol + datetime emission"
```

---

## Phase 3: Trace schema + exporter + loader

### Task 3.1: `ingest-trace.schema.json`

**Files:**
- Create: `skills/book-knowledge/assets/ingest-trace.schema.json`

- [ ] **Step 1: Write the schema.**

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "ingest-trace",
  "title": "Symbolic ingestion trace",
  "type": "object",
  "required": ["version", "book_id", "events"],
  "properties": {
    "version": {"type": "integer", "const": 1},
    "book_id": {"type": "string", "minLength": 1},
    "events": {"type": "array", "items": {"$ref": "#/$defs/event"}}
  },
  "additionalProperties": false,
  "$defs": {
    "event": {
      "type": "object",
      "required": ["head", "payload"],
      "properties": {
        "head": {
          "type": "string",
          "enum": [
            "source/ingested",
            "claim/proposed",
            "claim/verified",
            "claim/disputed",
            "claim/superseded",
            "claim/refuted"
          ]
        },
        "payload": {"type": "object"}
      },
      "additionalProperties": false
    }
  }
}
```

The schema describes the Python-dict form returned by `load_symbolic_trace`. The on-disk EDN form is parsed by `read_edn` and then validated against this schema (after a translation step that turns the EDN list head into the schema's `head` string).

- [ ] **Step 2: Commit.**

```bash
git add skills/book-knowledge/assets/ingest-trace.schema.json
git commit -m "book-knowledge: ingest-trace JSON Schema"
```

### Task 3.2: `export_symbolic_trace.py`

**Files:**
- Create: `skills/book-knowledge/scripts/export_symbolic_trace.py`
- Create: `skills/book-knowledge/tests/test_export_symbolic_trace.py`

- [ ] **Step 1: Write failing tests.**

```python
# skills/book-knowledge/tests/test_export_symbolic_trace.py
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

import pytest

# Cross-project import of neurosym-forge's EDN tools
_FORGE_SCRIPTS = Path(__file__).resolve().parents[3] / "skills" / "neurosym-forge"
sys.path.insert(0, str(_FORGE_SCRIPTS))
from scripts._edn_reader import Keyword, Symbol, read_edn  # noqa: E402

from scripts.export_symbolic_trace import export_trace, _manifest_to_event, _claim_to_proposed_event


def _seed_workspace(root: Path) -> Path:
    workspace = root / "ws"
    (workspace / "raw" / "manifests").mkdir(parents=True)
    (workspace / "claims").mkdir()
    (workspace / "raw" / "manifests" / "alpha.json").write_text(json.dumps({
        "doc_id": "alpha",
        "ingested_at": "2026-05-12T16:13:51.630442Z",
        "path": "raw/alpha.pdf",
        "title": "Alpha source",
        "trust": 0.95,
    }), encoding="utf-8")
    (workspace / "claims" / "ledger.jsonl").write_text(
        json.dumps({
            "claim_id": "clm-2026-000001",
            "canonical_text": "Bermuda has nine traditional parishes including St. George's.",
            "status": "verified",
            "confidence": 0.95,
            "created_at": "2026-05-12T16:14:01Z",
            "source_spans": [{"doc_id": "alpha", "locator_text": "Bermuda has nine traditional parishes"}],
        }) + "\n",
        encoding="utf-8",
    )
    return workspace


def test_manifest_event_shape(tmp_path: Path) -> None:
    workspace = _seed_workspace(tmp_path)
    manifest = json.loads((workspace / "raw" / "manifests" / "alpha.json").read_text())
    head, payload = _manifest_to_event(manifest)
    assert head == Symbol("ingested", namespace="source")
    assert payload[Keyword("doc/id")] == "alpha"
    assert isinstance(payload[Keyword("ingested-at")], dt.datetime)


def test_claim_event_shape() -> None:
    claim = {
        "claim_id": "clm-2026-000001",
        "canonical_text": "x",
        "status": "verified",
        "confidence": 0.9,
        "created_at": "2026-05-12T16:14:01Z",
        "source_spans": [],
    }
    head, payload = _claim_to_proposed_event(claim)
    assert head == Symbol("proposed", namespace="claim")
    assert payload[Keyword("claim/id")] == "clm-2026-000001"
    assert payload[Keyword("confidence")] == 0.9


def test_export_writes_edn_trace(tmp_path: Path) -> None:
    workspace = _seed_workspace(tmp_path)
    out = workspace / "analysis" / "ingest-trace.edn"
    export_trace(workspace, out)
    text = out.read_text(encoding="utf-8")
    parsed = read_edn(text)
    assert parsed[Keyword("version")] == 1
    assert parsed[Keyword("book/id")] == "ws"
    events = parsed[Keyword("events")]
    assert len(events) == 2  # one source/ingested + one claim/proposed
    heads = [e[0] for e in events]
    assert Symbol("ingested", namespace="source") in heads
    assert Symbol("proposed", namespace="claim") in heads


def test_export_idempotent(tmp_path: Path) -> None:
    workspace = _seed_workspace(tmp_path)
    out = workspace / "analysis" / "ingest-trace.edn"
    export_trace(workspace, out)
    first = out.read_text(encoding="utf-8")
    export_trace(workspace, out)
    second = out.read_text(encoding="utf-8")
    assert first == second
```

- [ ] **Step 2: Run, expect FAIL** (module doesn't exist).

```bash
cd skills/book-knowledge && .venv/Scripts/python.exe -m pytest tests/test_export_symbolic_trace.py -v
```

- [ ] **Step 3: Write `export_symbolic_trace.py`.**

```python
# skills/book-knowledge/scripts/export_symbolic_trace.py
"""Export the workspace's ingestion history as a symbolic EDN event stream.

Reads:
- <workspace>/raw/manifests/*.json   → (source/ingested ...) events
- <workspace>/claims/ledger.jsonl    → (claim/proposed ...) events
- <workspace>/claims/events.jsonl    → (claim/<status> ...) transition events (optional)

Writes:
- <workspace>/analysis/ingest-trace.edn

The output is regenerable: re-running with the same inputs produces a
byte-identical file (events are sorted by timestamp, then by stable
secondary keys).
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path
from typing import Any

# Cross-project import of neurosym-forge's EDN tools
_FORGE_SCRIPTS = Path(__file__).resolve().parents[2] / "neurosym-forge"
sys.path.insert(0, str(_FORGE_SCRIPTS))
from scripts._edn_reader import Keyword, Symbol  # noqa: E402
from scripts._edn_writer import write_edn  # noqa: E402


def _parse_instant(value: str) -> dt.datetime:
    """Parse an ISO-8601 instant tolerant of trailing 'Z'."""
    normalized = value.replace("Z", "+00:00") if value.endswith("Z") else value
    return dt.datetime.fromisoformat(normalized)


def _infer_kind(manifest: dict) -> Symbol:
    """Map a manifest hint to an :kind value."""
    path = manifest.get("path", "")
    if path.endswith(".pdf"):
        return Keyword("pdf")
    if path.endswith(".md"):
        return Keyword("markdown")
    if path.endswith(".yaml") or path.endswith(".yml"):
        return Keyword("yaml")
    if "thesis" in manifest.get("doc_id", "").lower():
        return Keyword("thesis")
    return Keyword("unknown")


def _manifest_to_event(manifest: dict) -> tuple[Symbol, dict]:
    """Translate a raw/manifests/*.json record to a source/ingested event."""
    payload: dict = {
        Keyword("doc/id"): manifest["doc_id"],
        Keyword("ingested-at"): _parse_instant(manifest["ingested_at"]),
        Keyword("kind"): _infer_kind(manifest),
    }
    if "path" in manifest:
        payload[Keyword("path")] = manifest["path"]
    if "title" in manifest:
        payload[Keyword("title")] = manifest["title"]
    if "sha256" in manifest:
        payload[Keyword("sha256")] = manifest["sha256"]
    return Symbol("ingested", namespace="source"), payload


def _claim_to_proposed_event(claim: dict) -> tuple[Symbol, dict]:
    """Translate a ledger row to a claim/proposed event."""
    payload: dict = {
        Keyword("claim/id"): claim["claim_id"],
    }
    if claim.get("canonical_text"):
        payload[Keyword("text")] = claim["canonical_text"]
    if claim.get("source_spans"):
        payload[Keyword("source/spans")] = [
            {Keyword("doc/id"): s["doc_id"], Keyword("locator-text"): s["locator_text"]}
            for s in claim["source_spans"]
        ]
    if "confidence" in claim:
        payload[Keyword("confidence")] = claim["confidence"]
    if claim.get("created_at"):
        payload[Keyword("proposed-at")] = _parse_instant(claim["created_at"])
    return Symbol("proposed", namespace="claim"), payload


def _event_to_status_event(event: dict) -> tuple[Symbol, dict]:
    """Translate a claims/events.jsonl row to a claim/<status> transition event."""
    head = Symbol(event["to"], namespace="claim")
    payload: dict = {
        Keyword("claim/id"): event["claim_id"],
        Keyword("from"): Keyword(event["from"]),
        Keyword("to"): Keyword(event["to"]),
        Keyword("transitioned-at"): _parse_instant(event["timestamp"]),
    }
    if event.get("cause_ticket_id"):
        payload[Keyword("cause-ticket-id")] = event["cause_ticket_id"]
    if event.get("cause_class"):
        payload[Keyword("cause-class")] = event["cause_class"]
    if event.get("operator"):
        payload[Keyword("operator")] = event["operator"]
    return head, payload


def _event_sort_key(event_tuple: tuple[Symbol, dict]) -> tuple:
    """Order events by their primary timestamp, then by stable secondary keys."""
    head, payload = event_tuple
    instant = (
        payload.get(Keyword("ingested-at"))
        or payload.get(Keyword("proposed-at"))
        or payload.get(Keyword("transitioned-at"))
    )
    if instant is None:
        # Fall back to MAX so missing timestamps sink to the end deterministically
        instant = dt.datetime.max.replace(tzinfo=dt.timezone.utc)
    # Tie-breaker: head string then claim/doc id
    secondary = str(head)
    tertiary = str(payload.get(Keyword("claim/id")) or payload.get(Keyword("doc/id")) or "")
    return (instant, secondary, tertiary)


def export_trace(workspace: Path, out_path: Path) -> int:
    """Generate the EDN ingestion trace. Returns the event count."""
    events: list[tuple[Symbol, dict]] = []

    manifests_dir = workspace / "raw" / "manifests"
    if manifests_dir.is_dir():
        for manifest_path in sorted(manifests_dir.glob("*.json")):
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            events.append(_manifest_to_event(manifest))

    ledger_path = workspace / "claims" / "ledger.jsonl"
    if ledger_path.exists():
        seen_claims: set[str] = set()
        for line in ledger_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            cid = row.get("claim_id")
            if cid and cid not in seen_claims:
                seen_claims.add(cid)
                events.append(_claim_to_proposed_event(row))

    events_path = workspace / "claims" / "events.jsonl"
    if events_path.exists():
        for line in events_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            events.append(_event_to_status_event(json.loads(line)))

    events.sort(key=_event_sort_key)

    payload = {
        Keyword("version"): 1,
        Keyword("book/id"): workspace.name,
        Keyword("events"): [[head, body] for head, body in events],
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        write_edn(payload, pretty=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return len(events)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", required=True)
    ap.add_argument("--out", default=None,
                    help="defaults to <workspace>/analysis/ingest-trace.edn")
    args = ap.parse_args(argv)
    workspace = Path(args.workspace)
    out_path = Path(args.out) if args.out else workspace / "analysis" / "ingest-trace.edn"
    n = export_trace(workspace, out_path)
    print(f"exported {n} events → {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
```

- [ ] **Step 4: Run, expect PASS.**

```bash
cd skills/book-knowledge && .venv/Scripts/python.exe -m pytest tests/test_export_symbolic_trace.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit.**

```bash
git add skills/book-knowledge/scripts/export_symbolic_trace.py skills/book-knowledge/tests/test_export_symbolic_trace.py
git commit -m "book-knowledge: export_symbolic_trace exporter"
```

### Task 3.3: `load_symbolic_trace.py`

**Files:**
- Create: `skills/book-knowledge/scripts/load_symbolic_trace.py`
- Create: `skills/book-knowledge/tests/test_load_symbolic_trace.py`

- [ ] **Step 1: Write failing tests.**

```python
# skills/book-knowledge/tests/test_load_symbolic_trace.py
from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

import pytest

_FORGE_SCRIPTS = Path(__file__).resolve().parents[3] / "skills" / "neurosym-forge"
sys.path.insert(0, str(_FORGE_SCRIPTS))
from scripts._edn_reader import Keyword, Symbol  # noqa: E402

from scripts.export_symbolic_trace import export_trace
from scripts.load_symbolic_trace import load_trace


def _seed_workspace(root: Path) -> Path:
    import json
    workspace = root / "ws"
    (workspace / "raw" / "manifests").mkdir(parents=True)
    (workspace / "claims").mkdir()
    (workspace / "raw" / "manifests" / "alpha.json").write_text(json.dumps({
        "doc_id": "alpha",
        "ingested_at": "2026-05-12T16:13:51.630442Z",
        "path": "raw/alpha.pdf",
        "title": "Alpha source",
    }), encoding="utf-8")
    (workspace / "claims" / "ledger.jsonl").write_text(
        json.dumps({
            "claim_id": "clm-2026-000001",
            "canonical_text": "x",
            "status": "verified",
            "confidence": 0.9,
            "created_at": "2026-05-12T16:14:01Z",
            "source_spans": [],
        }) + "\n",
        encoding="utf-8",
    )
    return workspace


def test_load_returns_structured_dict(tmp_path: Path) -> None:
    workspace = _seed_workspace(tmp_path)
    out = workspace / "analysis" / "ingest-trace.edn"
    export_trace(workspace, out)
    loaded = load_trace(out)
    assert loaded["version"] == 1
    assert loaded["book_id"] == "ws"
    assert len(loaded["events"]) == 2
    e0 = loaded["events"][0]
    assert "head" in e0 and "payload" in e0
    assert e0["head"] == "source/ingested"


def test_loader_round_trip(tmp_path: Path) -> None:
    workspace = _seed_workspace(tmp_path)
    out = workspace / "analysis" / "ingest-trace.edn"
    export_trace(workspace, out)
    loaded = load_trace(out)
    # The loaded events should round-trip through write+read
    assert all(isinstance(e["head"], str) for e in loaded["events"])
    for event in loaded["events"]:
        if event["head"] == "source/ingested":
            assert isinstance(event["payload"]["ingested-at"], dt.datetime)
        elif event["head"] == "claim/proposed":
            assert "claim/id" in event["payload"]


def test_loader_validates_schema(tmp_path: Path) -> None:
    # Write an invalid trace
    bad = tmp_path / "bad.edn"
    bad.write_text("{:version 2 :book/id \"x\" :events []}", encoding="utf-8")
    with pytest.raises(ValueError, match=r"schema"):
        load_trace(bad)
```

- [ ] **Step 2: Run, expect FAIL.**

```bash
cd skills/book-knowledge && .venv/Scripts/python.exe -m pytest tests/test_load_symbolic_trace.py -v
```

- [ ] **Step 3: Write `load_symbolic_trace.py`.**

```python
# skills/book-knowledge/scripts/load_symbolic_trace.py
"""Load a symbolic ingestion trace from EDN into a structured Python dict.

The on-disk trace has the shape:

    {:version 1
     :book/id "..."
     :events [(head/sym {...payload}) ...]}

This loader normalises that into a plain Python dict:

    {
      "version": 1,
      "book_id": "...",
      "events": [
        {"head": "source/ingested",
         "payload": {"doc/id": "...", "ingested-at": datetime(...), ...}},
        ...
      ],
    }

Keyword keys in the payload are flattened to their string form ("doc/id"
without the leading colon) so downstream consumers can use plain dict
access. The schema at ingest-trace.schema.json is enforced.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import jsonschema

_FORGE_SCRIPTS = Path(__file__).resolve().parents[2] / "neurosym-forge"
sys.path.insert(0, str(_FORGE_SCRIPTS))
from scripts._edn_reader import Keyword, Symbol, read_edn  # noqa: E402

_SCHEMA_PATH = Path(__file__).resolve().parent.parent / "assets" / "ingest-trace.schema.json"


def _flatten_key(k: Any) -> str:
    if isinstance(k, Keyword):
        return str(k).lstrip(":")
    return str(k)


def _flatten_payload(payload: dict) -> dict:
    return {_flatten_key(k): v for k, v in payload.items()}


def load_trace(path: Path) -> dict:
    """Parse the EDN trace file at `path` and validate against the schema."""
    edn = read_edn(path.read_text(encoding="utf-8"))
    version = edn.get(Keyword("version"))
    book_id = edn.get(Keyword("book/id"))
    raw_events = edn.get(Keyword("events"), [])
    events = []
    for entry in raw_events:
        if not isinstance(entry, list) or len(entry) < 2:
            continue
        head, payload = entry[0], entry[1]
        head_str = str(head) if isinstance(head, Symbol) else str(head).lstrip(":")
        events.append({"head": head_str, "payload": _flatten_payload(payload)})
    result = {"version": version, "book_id": book_id, "events": events}

    schema = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
    try:
        jsonschema.validate(result, schema)
    except jsonschema.ValidationError as e:
        raise ValueError(f"trace fails schema validation: {e.message}") from e
    return result
```

- [ ] **Step 4: Run, expect PASS.**

```bash
cd skills/book-knowledge && .venv/Scripts/python.exe -m pytest tests/test_load_symbolic_trace.py -v
```

- [ ] **Step 5: Commit.**

```bash
git add skills/book-knowledge/scripts/load_symbolic_trace.py skills/book-knowledge/tests/test_load_symbolic_trace.py
git commit -m "book-knowledge: load_symbolic_trace + schema validation"
```

---

## Phase 4: Generate Bermuda's trace artifact

### Task 4.1: Run the exporter against the real Bermuda workspace and commit the result

**Files:**
- Create: `examples/bermuda-manual/analysis/ingest-trace.edn` (generated)

- [ ] **Step 1: Generate the trace.**

```bash
cd skills/book-knowledge && .venv/Scripts/python.exe -m scripts.export_symbolic_trace \
  --workspace ../../examples/bermuda-manual

ls ../../examples/bermuda-manual/analysis/ingest-trace.edn
```

Expected: output `exported N events → .../analysis/ingest-trace.edn` (N depends on the live ledger; should be ~47 = 1 manifest + 46 claims).

- [ ] **Step 2: Sanity-inspect the artifact.**

```bash
head -30 examples/bermuda-manual/analysis/ingest-trace.edn
```

Expected: starts with `{:version 1 :book/id "bermuda-manual" :events [...]}`. Contains `(source/ingested {...})` for the thesis manifest, then a series of `(claim/proposed {...})` for each claim.

- [ ] **Step 3: Confirm the artifact round-trips through the loader.**

```bash
cd skills/book-knowledge && .venv/Scripts/python.exe -c "
from pathlib import Path
from scripts.load_symbolic_trace import load_trace
loaded = load_trace(Path('../../examples/bermuda-manual/analysis/ingest-trace.edn'))
print(f'version: {loaded[\"version\"]}')
print(f'book_id: {loaded[\"book_id\"]}')
print(f'event count: {len(loaded[\"events\"])}')
print(f'head distribution:')
heads = {}
for e in loaded['events']:
    heads[e['head']] = heads.get(e['head'], 0) + 1
for h, n in sorted(heads.items()):
    print(f'  {h}: {n}')
"
```

Expected: prints version 1, book_id "bermuda-manual", a count around 47, and head distribution showing `source/ingested: 1` and `claim/proposed: 46` (give or take depending on ledger state).

- [ ] **Step 4: Commit.**

```bash
git add examples/bermuda-manual/analysis/ingest-trace.edn
git commit -m "examples/bermuda-manual: ingest-trace artifact"
```

---

## Phase 5: Rust verdict EDN emission

### Task 5.1: New template-shape test for verdict EDN

**Files:**
- Modify: `skills/neurosym-forge/tests/test_rust_template_shape.py`

- [ ] **Step 1: Append the failing test.**

```python
def test_ir_template_verdict_uses_edn_not_serde_json() -> None:
    text = _read("ir.rs.tmpl")
    # The return-trip verdict serialization must not use serde_json::to_string
    assert "serde_json::to_string" not in text, \
        "ir.rs.tmpl emit_verdict must use EDN emission, not serde_json::to_string"
```

- [ ] **Step 2: Run, expect FAIL.**

```bash
cd skills/neurosym-forge && .venv/Scripts/python.exe -m pytest tests/test_rust_template_shape.py::test_ir_template_verdict_uses_edn_not_serde_json -v
```

- [ ] **Step 3: Commit the failing test.**

```bash
git add skills/neurosym-forge/tests/test_rust_template_shape.py
git commit -m "neurosym-forge: template-shape test for verdict EDN emission (red)"
```

### Task 5.2: Implement the EDN verdict emitter in the template

**Files:**
- Modify: `skills/neurosym-forge/assets/project-template/rust-verifier/src/ir.rs.tmpl`

- [ ] **Step 1: Read the current `emit_verdict` in `ir.rs.tmpl`.**

```bash
grep -A 4 "pub fn emit_verdict" skills/neurosym-forge/assets/project-template/rust-verifier/src/ir.rs.tmpl
```

You should see something like:

```rust
pub fn emit_verdict(v: &Verdict) -> String {
    serde_json::to_string(v).unwrap_or_else(|_| "{\"status\":\"unknown\"}".to_string())
}
```

- [ ] **Step 2: Replace `emit_verdict` with a hand-rolled EDN writer.**

```rust
pub fn emit_verdict(v: &Verdict) -> String {
    let mut out = String::from("{:status :");
    out.push_str(&v.status);
    out.push_str(" :core [");
    for (i, claim_id) in v.core.iter().enumerate() {
        if i > 0 {
            out.push(' ');
        }
        out.push('"');
        out.push_str(&edn_escape(claim_id));
        out.push('"');
    }
    out.push_str("] :explanation \"");
    out.push_str(&edn_escape(&v.explanation));
    out.push_str("\"}");
    out
}

fn edn_escape(s: &str) -> String {
    s.replace('\\', "\\\\").replace('"', "\\\"")
}
```

- [ ] **Step 3: Run the template-shape test, expect PASS.**

```bash
cd skills/neurosym-forge && .venv/Scripts/python.exe -m pytest tests/test_rust_template_shape.py -v
```

- [ ] **Step 4: Run the full neurosym-forge suite.**

```bash
cd skills/neurosym-forge && .venv/Scripts/python.exe -m pytest tests/ -q
```

Expected: ~146 passing (no regressions).

- [ ] **Step 5: Commit.**

```bash
git add skills/neurosym-forge/assets/project-template/rust-verifier/src/ir.rs.tmpl
git commit -m "neurosym-forge: verdict EDN emission in ir.rs template"
```

### Task 5.3: Mirror into Bermuda's `ir.rs`

**Files:**
- Modify: `verifiers/bermuda/rust-verifier/src/ir.rs`

- [ ] **Step 1: Open `verifiers/bermuda/rust-verifier/src/ir.rs`.**

Find the current `emit_verdict` block. It should be identical to the pre-fix template (using `serde_json::to_string`).

- [ ] **Step 2: Replace it with the same EDN body** from Task 5.2 Step 2. Include the `edn_escape` helper.

- [ ] **Step 3: Confirm no other `serde_json::to_string` calls remain in `ir.rs`.**

```bash
grep -n "serde_json::to_string" verifiers/bermuda/rust-verifier/src/ir.rs
```

Expected: no matches.

- [ ] **Step 4: Commit.**

```bash
git add verifiers/bermuda/rust-verifier/src/ir.rs
git commit -m "verifiers/bermuda: verdict EDN emission in ir.rs (lockstep)"
```

---

## Phase 6: Smoke + PR

### Task 6.1: Full sweep

- [ ] **Step 1: Run all suites.**

```bash
cd skills/neurosym-forge && .venv/Scripts/python.exe -m pytest tests/ -q
cd ../book-qa && python -m pytest tests/ -q
cd ../book-knowledge && .venv/Scripts/python.exe -m pytest tests/ -q
cd ../../verifiers/bermuda && .venv/Scripts/python.exe -m pytest tests/ -q
```

Expected (record actual numbers):
- neurosym-forge: ~146 (123 + ~22 new from PR-2)
- book-qa: 47 unchanged
- book-knowledge: existing baseline + ~7 new (3 export + 3 load + 1 schema-related)
- verifiers/bermuda: 23 unchanged

- [ ] **Step 2: Smoke — scaffold a fresh project and confirm v0.4 PR-2 contract.**

```bash
cd skills/neurosym-forge && .venv/Scripts/python.exe -m scripts.scaffold_project \
  --name "PR2 smoke" --slug pr2_smoke --out /tmp/pr2_smoke
grep -c "emit_verdict" /tmp/pr2_smoke/rust-verifier/src/ir.rs
grep -c "serde_json::to_string" /tmp/pr2_smoke/rust-verifier/src/ir.rs
```

Expected: `emit_verdict` count ≥ 1; `serde_json::to_string` count = 0.

- [ ] **Step 3: Cleanup.**

```bash
rm -rf /tmp/pr2_smoke
```

### Task 6.2: Push + open PR

- [ ] **Step 1: Push.**

```bash
cd C:/Users/charl/code/russellian-book-suite-booklogic-pr2
git push -u origin spec/booklogic-pr2
```

- [ ] **Step 2: Open the PR.**

```bash
gh pr create --title "BookLogic v0.4 PR-2: ingest-trace exporter + EDN extensions + Rust verdict EDN" --body "$(cat <<'EOF'
## Summary

Lands the second sub-PR of the BookLogic v0.4 mission.

- **EDN reader extensions:** `Symbol` dataclass (bare identifiers `foo` / `foo/bar`); `#inst` tagged literal returns timezone-aware `datetime.datetime`; selective tag dispatch (other tags still raise)
- **EDN writer extensions:** Symbol and datetime emission with round-trip
- **`book-knowledge/scripts/export_symbolic_trace.py`:** reads `raw/manifests/*.json`, `claims/ledger.jsonl`, and optional `claims/events.jsonl`; writes regenerable `analysis/ingest-trace.edn`
- **`book-knowledge/scripts/load_symbolic_trace.py`:** mirror loader; validates against the new `ingest-trace.schema.json` (closed event-head set: `source/ingested`, `claim/proposed`, `claim/verified`, `claim/disputed`, `claim/superseded`, `claim/refuted`)
- **Bermuda artifact:** `examples/bermuda-manual/analysis/ingest-trace.edn` shipped as worked example
- **Rust verdict EDN emission:** `ir.rs::emit_verdict` no longer uses `serde_json::to_string`; emits hand-rolled EDN; CLJS reader on the return trip now gets keywords back
- **22+ new tests** across reader, writer, exporter, loader, template-shape

Spec: `docs/specs/2026-05-14-booklogic-v0.4-pr2-design.md`.
Plan: `docs/plans/2026-05-14-booklogic-v0.4-pr2.md`.

## Test plan

- [ ] `cd skills/neurosym-forge && .venv/Scripts/python.exe -m pytest tests/ -q` — ~146 passing
- [ ] `cd skills/book-knowledge && .venv/Scripts/python.exe -m pytest tests/ -q` — baseline + ~7 new
- [ ] `cd skills/book-qa && python -m pytest tests/ -q` — 47 unchanged
- [ ] `cd verifiers/bermuda && .venv/Scripts/python.exe -m pytest tests/ -q` — 23 unchanged
- [ ] `examples/bermuda-manual/analysis/ingest-trace.edn` parses cleanly via `load_trace`

## Out of scope

- BookLogic DSL forms (PR-3 + PR-4)
- Bermuda real Z3 run (PR-5)
- Atom-emitted events in the trace (verifier emits those at run time — PR-5's domain)
- Multi-book trace aggregation (v0.5)
EOF
)"
```

- [ ] **Step 3: Return PR URL.**

---

## Self-review

Walking the spec § "What ships" against this plan:

| Spec deliverable | Implementing tasks |
|---|---|
| D1 — Symbol + `#inst` in reader/writer | 1.1, 1.2, 2.1 |
| D2 — `export_symbolic_trace.py` | 3.2 |
| D3 — `load_symbolic_trace.py` | 3.3 |
| D4 — `ingest-trace.schema.json` | 3.1 |
| D5 — Rust verdict EDN emission | 5.2, 5.3 |
| D6 — Bermuda trace artifact | 4.1 |

All six deliverables have implementing tasks.

**Placeholder scan:** No "TBD" / "TODO" / "fill in" in any step.

**Type consistency:**
- `Symbol` and `Keyword` used identically across tasks 1.1, 1.2, 2.1, 3.2, 3.3, and Bermuda tests
- `export_trace(workspace: Path, out_path: Path) -> int` consistent across task 3.2 (definition) and 3.3 (test usage) and 4.1 (CLI)
- `load_trace(path: Path) -> dict` consistent across task 3.3 (definition), 3.3 tests, 4.1 verification step
- Event head strings match the schema `enum` in task 3.1
- `edn_escape` defined inside `ir.rs.tmpl` task 5.2 step 2 and mirrored verbatim into Bermuda's `ir.rs` task 5.3 step 2

**Effort:** Spec said ~2 days. Plan has 6 phases, ~14 tasks, ~22 new tests. Matches.

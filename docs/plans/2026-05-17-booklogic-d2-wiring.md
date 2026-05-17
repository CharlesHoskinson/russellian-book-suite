# BookLogic v0.4 PR-D2 — Wire ingest-trace into the verifier Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close out the D2 deliverable. `skills/book-knowledge/scripts/export_symbolic_trace.py` already emits `<workspace>/analysis/ingest-trace.edn` as a symbolic event stream, but `verifiers/bermuda/scripts/run_verification.py` ignores it and reads `claims/ledger.jsonl` directly. Make `run_verification` prefer the trace when present, fall back to the legacy ledger when absent, and extend the CLJS translate path so it accepts a vector of trace events in addition to the legacy vector of `Claim` maps.

**Architecture:**

- **Python side.** `run_verification.run(...)` gains a Phase-1 dispatch: if `<workspace>/analysis/ingest-trace.edn` exists, load it via `skills/book-knowledge/scripts/load_symbolic_trace.load_trace`, project each `claim/<status>` event to the synthetic ledger row shape that the existing `ingest()` helper consumes, then call `ingest()` with that synthesised list rather than re-reading the JSONL file. If the trace is absent, the existing `ledger.jsonl` path is taken verbatim. To keep `ingest_ledger.ingest` unchanged (it reads from a path and returns a count), the trace-aware branch writes a synthesised in-memory JSONL string to a `tmp` file inside the project's `work/` dir and passes that to `ingest`. This preserves the existing tested code path while adding the trace-aware entry.
- **CLJS side.** `bermuda.phases/translate` currently takes a `[:vector ir/Claim]` and runs `nl-to-fol/translate-corpus`. After this PR it accepts EITHER (a) a vector of `Claim` maps (legacy) or (b) a vector of `[head payload]` two-element vectors (trace events) and dispatches per element. The new `claim->formula` branches on the input shape: a 2-element vector with a `Symbol` (or `Keyword`) head dispatches per event head; a map falls through to today's meander rewrite. `source/ingested` and `claim/proposed` produce nil (skipped); `claim/verified` produces a formula equivalent to the legacy meander-matched `Claim`; `atom/emitted` passes through. Unknown heads emit an opaque `:OPAQUE` formula matching the existing `?other` fallthrough.

The trace event head shape is documented at `skills/book-knowledge/assets/ingest-trace.schema.json` (`source/ingested`, `claim/proposed`, `claim/verified`, `claim/disputed`, `claim/superseded`, `claim/refuted`). The exporter at `skills/book-knowledge/scripts/export_symbolic_trace.py` confirms `Symbol("verified", namespace="claim")` is the runtime shape on the EDN side. We do not introduce a new `atom/emitted` head into the schema in this PR — the CLJS dispatch accepts it forward-compatibly because the spec's PR-D2 acceptance criteria call for it, and the test exercises it as a forward-compatibility check; the schema gets the new head only if a future PR emits it.

**Tech Stack:** Python 3.13 (existing `.venv` under `verifiers/bermuda/`), pytest 8.x, shadow-cljs 2.28.20 + Node 22 for CLJS. No new Python deps. No new CLJS deps.

Spec: `docs/specs/2026-05-17-booklogic-claude-only-finish-design.md` § "PR-D2 — Wire ingest-trace into the verifier".

---

## Pre-flight

Read these before starting:

- `docs/specs/2026-05-17-booklogic-claude-only-finish-design.md` § "PR-D2 — Wire ingest-trace into the verifier"
- `skills/book-knowledge/scripts/export_symbolic_trace.py` — current exporter; emits `(source/ingested ...)`, `(claim/proposed ...)`, `(claim/<status> ...)` heads as `Symbol` instances with `namespace`
- `skills/book-knowledge/scripts/load_symbolic_trace.py` — already-existing flattening loader; returns `{"events": [{"head": "claim/verified", "payload": {...}}, ...]}` with payload keyword names stripped to bare strings
- `skills/book-knowledge/assets/ingest-trace.schema.json` — the trace schema (enum of valid event heads)
- `verifiers/bermuda/scripts/run_verification.py` — current Phase-1 reader (path: `workspace/claims/ledger.jsonl` → `ingest()`)
- `verifiers/bermuda/scripts/ingest_ledger.py` — `ingest(ledger_path, predicates_path, out_path)` and `read_ledger(path)` that we re-use after trace projection
- `verifiers/bermuda/cljs-orchestrator/src/main/bermuda/phases.cljs` — `translate`/`verify`/`typeset` with malli pre/post
- `verifiers/bermuda/cljs-orchestrator/src/main/bermuda/nl_to_fol.cljs` — `claim->formula` meander rewrite and `translate-corpus`
- `verifiers/bermuda/cljs-orchestrator/src/main/bermuda/ir.cljs` — `Claim` and `Formula` malli schemas
- `verifiers/bermuda/tests/test_run_verification.py` — current tests (two pass cases on the stub verifier)
- `verifiers/bermuda/tests/conftest.py` — `project_root`, `fixtures_dir`, `tmp_work` fixtures
- `verifiers/bermuda/shadow-cljs.edn` — current build target `:main` (no `:test` target yet; this plan adds one)

**Worktree.** All work is on a fresh branch `feat/booklogic-d2-wiring` cut from `main`. The PR-cleanup branch from the umbrella spec is assumed merged. If it is not, this plan still applies — the only dependency on PR-cleanup is the CLJS test target. If PR-cleanup has already added a `:test` shadow-cljs target, Task 3.1 below extends it rather than introducing it.

```bash
cd C:/work/russellian-book-suite
git fetch origin
git checkout main
git pull --ff-only origin main
git checkout -b feat/booklogic-d2-wiring
```

**Test invocations.**

- Bermuda Python: `cd verifiers/bermuda && .venv/Scripts/python.exe -m pytest tests/ -q`
- Book-knowledge Python: `cd skills/book-knowledge && python -m pytest tests/ -q`
- Bermuda CLJS: `cd verifiers/bermuda && npx shadow-cljs compile test && node out/test.js`
- Neurosym-forge Python: `cd skills/neurosym-forge && .venv/Scripts/python.exe -m pytest tests/ -q`

**Commit hygiene.** Terse, imperative, lowercase scope. One problem per commit. No AI attribution. No Co-Authored-By. Example: `bermuda: prefer ingest-trace over ledger.jsonl in run_verification`.

---

## File Structure

### Created

```
verifiers/bermuda/
├── scripts/
│   └── trace_to_ledger.py                                    NEW (~90 lines)
└── tests/
    ├── test_run_verification_consumes_trace.py               NEW (~120 lines)
    └── test_trace_to_ledger.py                               NEW (~60 lines)

verifiers/bermuda/cljs-orchestrator/test/bermuda/
├── nl_to_fol_test.cljs                                       NEW (~120 lines)
└── phases_test.cljs                                          NEW (~60 lines)
```

### Modified

```
verifiers/bermuda/
├── scripts/run_verification.py                               trace-aware Phase 1
├── cljs-orchestrator/src/main/bermuda/nl_to_fol.cljs         event-head dispatch
├── cljs-orchestrator/src/main/bermuda/phases.cljs            relaxed translate pre-contract
├── cljs-orchestrator/src/main/bermuda/ir.cljs                add Event schema
└── shadow-cljs.edn                                           add :test node-test target
```

`load_symbolic_trace.load_trace` already exists in `skills/book-knowledge/scripts/`. We reuse it via the `book-knowledge` scripts package import shim or, more simply, by inlining a thin trace-projection function in the new `verifiers/bermuda/scripts/trace_to_ledger.py` that uses the same `read_edn` + `Keyword`/`Symbol` primitives already wired into Bermuda's `scripts/__init__.py`. The inline approach avoids a new cross-package dependency direction (Bermuda → book-knowledge); Bermuda already imports from neurosym-forge, and that's the only cross-package import we want to keep.

---

## Phase 1: Python trace-aware Phase-1 reader

### Task 1.1: Trace projection helper

**Files:**
- Create: `verifiers/bermuda/scripts/trace_to_ledger.py`
- Create: `verifiers/bermuda/tests/test_trace_to_ledger.py`

The new module reads an `ingest-trace.edn` file and projects every `claim/verified` event back to the ledger-row dict shape that `ingest_ledger.read_ledger` produces. `claim/proposed`, `source/ingested`, and `claim/<other-status>` events are dropped (only `verified` claims feed Phase-2 verification today). `atom/emitted` is not in the schema yet but the projector skips unknown heads silently to remain forward-compatible.

- [ ] **Step 1: Write failing tests.**

```python
# verifiers/bermuda/tests/test_trace_to_ledger.py
"""Tests for the ingest-trace -> ledger-row projection."""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import pytest

from scripts._edn_reader import Keyword, Symbol
from scripts._edn_writer import write_edn
from scripts.trace_to_ledger import (
    project_trace_to_ledger_rows,
    read_trace,
    TraceProjectionError,
)


def _write_trace(path: Path, events: list[tuple[Symbol, dict]]) -> None:
    payload = {
        Keyword("version"): 1,
        Keyword("book/id"): "test-ws",
        Keyword("events"): [[head, body] for head, body in events],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(write_edn(payload, pretty=True) + "\n", encoding="utf-8")


def test_project_verified_event_to_ledger_row(tmp_path: Path) -> None:
    trace = tmp_path / "trace.edn"
    instant = dt.datetime(2026, 5, 12, 16, 14, 1, tzinfo=dt.timezone.utc)
    _write_trace(trace, [
        (Symbol("verified", namespace="claim"), {
            Keyword("claim/id"): "clm-2026-000001",
            Keyword("text"): "Bermuda has nine traditional parishes.",
            Keyword("transitioned-at"): instant,
            Keyword("from"): Keyword("proposed"),
            Keyword("to"): Keyword("verified"),
        }),
    ])
    rows = project_trace_to_ledger_rows(read_trace(trace))
    assert len(rows) == 1
    row = rows[0]
    assert row["claim_id"] == "clm-2026-000001"
    assert row["status"] == "verified"
    assert row["canonical_text"] == "Bermuda has nine traditional parishes."
    assert row["confidence"] >= 0.0


def test_project_skips_non_verified_heads(tmp_path: Path) -> None:
    trace = tmp_path / "trace.edn"
    _write_trace(trace, [
        (Symbol("ingested", namespace="source"), {Keyword("doc/id"): "alpha"}),
        (Symbol("proposed", namespace="claim"), {Keyword("claim/id"): "clm-x"}),
        (Symbol("disputed", namespace="claim"), {Keyword("claim/id"): "clm-y"}),
    ])
    assert project_trace_to_ledger_rows(read_trace(trace)) == []


def test_project_picks_text_from_proposed_when_verified_lacks_it(tmp_path: Path) -> None:
    trace = tmp_path / "trace.edn"
    _write_trace(trace, [
        (Symbol("proposed", namespace="claim"), {
            Keyword("claim/id"): "clm-2026-000007",
            Keyword("text"): "Bermuda has nine traditional parishes.",
            Keyword("confidence"): 0.92,
        }),
        (Symbol("verified", namespace="claim"), {
            Keyword("claim/id"): "clm-2026-000007",
            Keyword("from"): Keyword("proposed"),
            Keyword("to"): Keyword("verified"),
        }),
    ])
    rows = project_trace_to_ledger_rows(read_trace(trace))
    assert len(rows) == 1
    assert rows[0]["claim_id"] == "clm-2026-000007"
    assert rows[0]["canonical_text"] == "Bermuda has nine traditional parishes."
    assert rows[0]["confidence"] == 0.92
    assert rows[0]["status"] == "verified"


def test_read_trace_returns_structure(tmp_path: Path) -> None:
    trace = tmp_path / "trace.edn"
    _write_trace(trace, [
        (Symbol("ingested", namespace="source"), {Keyword("doc/id"): "alpha"}),
    ])
    data = read_trace(trace)
    assert data["version"] == 1
    assert data["book_id"] == "test-ws"
    assert len(data["events"]) == 1
    assert data["events"][0]["head"] == "source/ingested"


def test_read_trace_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(TraceProjectionError, match="not found"):
        read_trace(tmp_path / "absent.edn")
```

- [ ] **Step 2: Run, expect FAIL.**

```bash
cd verifiers/bermuda && .venv/Scripts/python.exe -m pytest tests/test_trace_to_ledger.py -v
```

Expected: `ModuleNotFoundError: No module named 'scripts.trace_to_ledger'`.

- [ ] **Step 3: Implement.**

```python
# verifiers/bermuda/scripts/trace_to_ledger.py
"""Project a symbolic ingestion trace down to the ledger-row dict shape.

The exporter at skills/book-knowledge/scripts/export_symbolic_trace.py
emits one event per state transition. Phase 1 of the Bermuda verifier
only consumes the latest :verified state per claim, so this projection
flattens the trace into the same dict shape that the legacy
claims/ledger.jsonl reader produces.

Used by scripts/run_verification.py when
<workspace>/analysis/ingest-trace.edn is present.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from scripts._edn_reader import Keyword, Symbol, read_edn


class TraceProjectionError(ValueError):
    """Raised when the trace file is missing or structurally invalid."""


def read_trace(path: Path) -> dict:
    """Read an EDN trace file into a normalised dict.

    Returns:
        {"version": int, "book_id": str, "events": [{"head": str,
        "payload": dict}, ...]}.
    """
    if not path.exists():
        raise TraceProjectionError(f"trace file not found: {path}")
    edn = read_edn(path.read_text(encoding="utf-8"))
    version = edn.get(Keyword("version"))
    book_id = edn.get(Keyword("book/id"))
    raw = edn.get(Keyword("events"), [])
    events: list[dict] = []
    for entry in raw:
        if not isinstance(entry, list) or len(entry) < 2:
            continue
        head, payload = entry[0], entry[1]
        head_str = str(head) if isinstance(head, Symbol) else str(head).lstrip(":")
        flat = {_strip(k): v for k, v in payload.items()}
        events.append({"head": head_str, "payload": flat})
    return {"version": version, "book_id": book_id, "events": events}


def _strip(k: Any) -> str:
    if isinstance(k, Keyword):
        return str(k).lstrip(":")
    return str(k)


def project_trace_to_ledger_rows(trace: dict) -> list[dict]:
    """Project the trace down to the per-claim row shape ingest_ledger expects.

    Strategy: gather the latest :proposed payload per claim (it carries
    :text and :confidence), then for every :verified event with a known
    claim/id emit one row marked status=verified with text + confidence
    backfilled from the proposed payload.
    """
    proposed: dict[str, dict] = {}
    rows: list[dict] = []
    for ev in trace.get("events", []):
        head = ev["head"]
        payload = ev["payload"]
        cid = payload.get("claim/id")
        if head == "claim/proposed" and cid:
            proposed[cid] = payload
        elif head == "claim/verified" and cid:
            seed = proposed.get(cid, {})
            text = payload.get("text") or seed.get("text", "")
            confidence = payload.get("confidence")
            if confidence is None:
                confidence = seed.get("confidence", 0.0)
            row = {
                "claim_id": cid,
                "claim_type": payload.get("claim_type")
                              or seed.get("claim_type")
                              or "fact",
                "canonical_text": text,
                "status": "verified",
                "confidence": float(confidence),
                "source_spans": payload.get("source/spans")
                                or seed.get("source/spans")
                                or [],
                "supports_chapters": payload.get("supports_chapters")
                                     or seed.get("supports_chapters")
                                     or [],
            }
            rows.append(row)
    return rows
```

- [ ] **Step 4: Run, expect 5 PASS.**

```bash
cd verifiers/bermuda && .venv/Scripts/python.exe -m pytest tests/test_trace_to_ledger.py -v
```

Expected:
```
tests/test_trace_to_ledger.py::test_project_verified_event_to_ledger_row PASSED
tests/test_trace_to_ledger.py::test_project_skips_non_verified_heads PASSED
tests/test_trace_to_ledger.py::test_project_picks_text_from_proposed_when_verified_lacks_it PASSED
tests/test_trace_to_ledger.py::test_read_trace_returns_structure PASSED
tests/test_trace_to_ledger.py::test_read_trace_missing_file_raises PASSED
5 passed
```

- [ ] **Step 5: Commit.**

```bash
git add verifiers/bermuda/scripts/trace_to_ledger.py verifiers/bermuda/tests/test_trace_to_ledger.py
git commit -m "bermuda: add trace-to-ledger projection helper"
```

### Task 1.2: `run_verification` consumes trace when present

**Files:**
- Modify: `verifiers/bermuda/scripts/run_verification.py`
- Create: `verifiers/bermuda/tests/test_run_verification_consumes_trace.py`

- [ ] **Step 1: Write the failing test.**

```python
# verifiers/bermuda/tests/test_run_verification_consumes_trace.py
"""Phase-1 dispatch: ingest-trace preferred over ledger.jsonl when present."""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import pytest

from scripts._edn_reader import Keyword, Symbol, read_edn
from scripts._edn_writer import write_edn
from scripts.run_verification import run


def _write_trace(workspace: Path, events: list[tuple[Symbol, dict]]) -> Path:
    out = workspace / "analysis" / "ingest-trace.edn"
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        Keyword("version"): 1,
        Keyword("book/id"): workspace.name,
        Keyword("events"): [[head, body] for head, body in events],
    }
    out.write_text(write_edn(payload, pretty=True) + "\n", encoding="utf-8")
    return out


def _seed_workspace(tmp_path: Path, with_legacy_ledger: bool) -> Path:
    workspace = tmp_path / "examples" / "test-workspace"
    (workspace / "claims").mkdir(parents=True)
    if with_legacy_ledger:
        (workspace / "claims" / "ledger.jsonl").write_text(
            json.dumps({
                "claim_id": "clm-LEGACY-1",
                "claim_type": "fact",
                "canonical_text": "Legacy ledger claim.",
                "status": "verified",
                "confidence": 0.5,
            }) + "\n", encoding="utf-8"
        )
    (workspace / "qa").mkdir()
    return workspace


def test_run_verification_consumes_trace(tmp_path: Path, project_root: Path) -> None:
    """A 3-event trace with one verified claim → run produces 1 atom in work/claims.edn."""
    workspace = _seed_workspace(tmp_path, with_legacy_ledger=False)
    instant = dt.datetime(2026, 5, 12, 16, 14, 1, tzinfo=dt.timezone.utc)
    _write_trace(workspace, [
        (Symbol("ingested", namespace="source"), {
            Keyword("doc/id"): "alpha",
            Keyword("ingested-at"): instant,
            Keyword("kind"): Keyword("pdf"),
        }),
        (Symbol("proposed", namespace="claim"), {
            Keyword("claim/id"): "clm-TRACE-1",
            Keyword("text"): "Bermuda has nine traditional parishes including St. George's.",
            Keyword("proposed-at"): instant,
            Keyword("confidence"): 0.9,
        }),
        (Symbol("verified", namespace="claim"), {
            Keyword("claim/id"): "clm-TRACE-1",
            Keyword("transitioned-at"): instant,
            Keyword("from"): Keyword("proposed"),
            Keyword("to"): Keyword("verified"),
        }),
    ])

    # Move into a tmp project_root so work/ is sandboxed
    sandbox_project = tmp_path / "project_root_clone"
    sandbox_project.mkdir()
    (sandbox_project / "rules").mkdir()
    # Symlink-ish: copy only the predicates rules file we need
    (sandbox_project / "rules" / "predicates.edn").write_text(
        (project_root / "rules" / "predicates.edn").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    rc = run(
        workspace=workspace,
        release_version="1.0.0",
        project_root=sandbox_project,
        stub_verifier=True,
        stub_verdict="sat",
    )
    assert rc == 0

    claims_edn = sandbox_project / "work" / "claims.edn"
    assert claims_edn.exists()
    parsed = read_edn(claims_edn.read_text(encoding="utf-8"))
    atoms = parsed[Keyword("atoms")]
    assert len(atoms) == 1
    assert atoms[0][Keyword("id")] == "clm-TRACE-1"


def test_run_verification_prefers_trace_over_legacy_ledger(
    tmp_path: Path, project_root: Path,
) -> None:
    """When BOTH are present, the trace wins."""
    workspace = _seed_workspace(tmp_path, with_legacy_ledger=True)
    _write_trace(workspace, [
        (Symbol("proposed", namespace="claim"), {
            Keyword("claim/id"): "clm-TRACE-2",
            Keyword("text"): "Bermuda has nine traditional parishes.",
            Keyword("confidence"): 0.95,
        }),
        (Symbol("verified", namespace="claim"), {
            Keyword("claim/id"): "clm-TRACE-2",
            Keyword("from"): Keyword("proposed"),
            Keyword("to"): Keyword("verified"),
        }),
    ])
    sandbox_project = tmp_path / "project_root_clone"
    sandbox_project.mkdir()
    (sandbox_project / "rules").mkdir()
    (sandbox_project / "rules" / "predicates.edn").write_text(
        (project_root / "rules" / "predicates.edn").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    rc = run(
        workspace=workspace, release_version="1.0.0",
        project_root=sandbox_project, stub_verifier=True, stub_verdict="sat",
    )
    assert rc == 0
    parsed = read_edn((sandbox_project / "work" / "claims.edn").read_text(encoding="utf-8"))
    atoms = parsed[Keyword("atoms")]
    ids = {a[Keyword("id")] for a in atoms}
    # Trace claim must appear; legacy claim must NOT
    assert "clm-TRACE-2" in ids
    assert "clm-LEGACY-1" not in ids
```

- [ ] **Step 2: Run, expect FAIL.**

```bash
cd verifiers/bermuda && .venv/Scripts/python.exe -m pytest tests/test_run_verification_consumes_trace.py -v
```

Expected: both tests fail because `run_verification` always reads `ledger.jsonl`; the first test seeds NO ledger and the call fails inside `ingest()` (FileNotFoundError) before producing `claims.edn`; the second produces `clm-LEGACY-1` in the atoms list, not `clm-TRACE-2`.

- [ ] **Step 3: Implement.**

Edit `verifiers/bermuda/scripts/run_verification.py`. Replace the Phase-1 block (lines 41–44 in the current file). Full updated file:

```python
"""End-to-end Python driver for the Bermuda verifier.

Phases:
  1. ingest             Prefer <workspace>/analysis/ingest-trace.edn (the
                        symbolic event stream from book-knowledge); fall back
                        to claims/ledger.jsonl for legacy workspaces.
                        Output: work/claims.edn
  2. extract_prose      book/releases/N/chapter-bundles/ -> work/prose-facts.edn
  3. verify             (CLJS+Rust) work/{claims, prose-facts}.edn -> work/verdict.edn
                        Skipped when stub_verifier=True; emits a stub verdict.
  4. verdict_to_qa      work/verdict.edn -> <workspace>/qa/verification-defects.json
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

# scripts/__init__.py extends this package's __path__ to include forge's
# scripts/ dir, so the imports below resolve to neurosym-forge's modules.
from scripts._edn_reader import Keyword  # noqa: E402
from scripts._io import write_edn_file  # noqa: E402

from scripts.extract_prose import extract_release
from scripts.ingest_ledger import ingest
from scripts.trace_to_ledger import (
    TraceProjectionError,
    project_trace_to_ledger_rows,
    read_trace,
)
from scripts.verdict_to_qa import translate

_KW_VERSION = Keyword("version")
_KW_VERDICT = Keyword("verdict")
_KW_CORE = Keyword("core")
_KW_EXPLANATION = Keyword("explanation")
_KW_VERIFIED_COUNT = Keyword("verified-count")
_KW_ATOMS = Keyword("atoms")


def _materialise_trace_as_ledger(workspace: Path, work: Path) -> Path | None:
    """If <workspace>/analysis/ingest-trace.edn exists, project it to a
    synthetic JSONL ledger inside `work/` and return that path. Otherwise
    return None so the caller can fall back to the legacy ledger.jsonl."""
    trace_path = workspace / "analysis" / "ingest-trace.edn"
    if not trace_path.exists():
        return None
    trace = read_trace(trace_path)
    rows = project_trace_to_ledger_rows(trace)
    synth = work / "ledger-from-trace.jsonl"
    with synth.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")
    return synth


def run(workspace: Path, release_version: str, project_root: Path,
        stub_verifier: bool = False,
        stub_verdict: str = "sat",
        stub_core: list[str] | None = None) -> int:
    work = project_root / "work"
    work.mkdir(parents=True, exist_ok=True)

    # Phase 1: ingest — prefer the symbolic trace, fall back to legacy ledger.
    synth_ledger = _materialise_trace_as_ledger(workspace, work)
    if synth_ledger is not None:
        ledger = synth_ledger
    else:
        ledger = workspace / "claims" / "ledger.jsonl"
    claims_edn = work / "claims.edn"
    ingest(ledger, project_root / "rules" / "predicates.edn", claims_edn)

    # Phase 2: prose
    bundles = workspace / "book" / "releases" / release_version / "chapter-bundles"
    prose_edn = work / "prose-facts.edn"
    if bundles.exists():
        extract_release(bundles, prose_edn)
    else:
        write_edn_file(prose_edn, {_KW_VERSION: 1, _KW_ATOMS: []})

    # Phase 3: verify
    verdict_edn = work / "verdict.edn"
    if stub_verifier:
        write_edn_file(verdict_edn, {
            _KW_VERSION: 1,
            _KW_VERDICT: Keyword(stub_verdict),
            _KW_CORE: stub_core or [],
            _KW_EXPLANATION: "stub" if stub_verdict == "unsat" else "",
            _KW_VERIFIED_COUNT: 0,
        })
    else:
        main_js = project_root / "cljs-orchestrator" / "dist" / "main.js"
        if not main_js.exists():
            print(f"verifier not built ({main_js}); run npm run build first",
                  file=sys.stderr)
            return 2
        subprocess.run(
            ["node", str(main_js), "verify", str(claims_edn), str(verdict_edn)],
            check=True, cwd=str(project_root),
        )

    # Phase 4: verdict -> qa
    qa_dir = workspace / "qa"
    qa_dir.mkdir(parents=True, exist_ok=True)
    translate(verdict_edn, qa_dir / "verification-defects.json")
    print(f"verification complete: verdict={stub_verdict if stub_verifier else 'real'}")
    return 0


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", required=True)
    ap.add_argument("--release", required=True)
    ap.add_argument("--stub", action="store_true",
                    help="Stub the Rust verifier (for CI / when toolchain missing)")
    ap.add_argument("--stub-verdict", default="sat", choices=["sat", "unsat", "unknown"])
    args = ap.parse_args(argv)
    project_root = Path(__file__).resolve().parent.parent
    rc = run(
        workspace=Path(args.workspace),
        release_version=args.release,
        project_root=project_root,
        stub_verifier=args.stub,
        stub_verdict=args.stub_verdict,
    )
    return rc


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
```

- [ ] **Step 4: Run, expect 2 PASS.**

```bash
cd verifiers/bermuda && .venv/Scripts/python.exe -m pytest tests/test_run_verification_consumes_trace.py -v
```

Expected:
```
tests/test_run_verification_consumes_trace.py::test_run_verification_consumes_trace PASSED
tests/test_run_verification_consumes_trace.py::test_run_verification_prefers_trace_over_legacy_ledger PASSED
2 passed
```

- [ ] **Step 5: Commit.**

```bash
git add verifiers/bermuda/scripts/run_verification.py verifiers/bermuda/tests/test_run_verification_consumes_trace.py
git commit -m "bermuda: prefer ingest-trace over ledger.jsonl in run_verification"
```

---

## Phase 2: Legacy fallback preserved

### Task 2.1: Explicit legacy-only test

**Files:**
- Modify: `verifiers/bermuda/tests/test_run_verification_consumes_trace.py`

The two pre-existing tests in `tests/test_run_verification.py` already exercise the legacy path (they seed only `claims/ledger.jsonl`, no trace). They MUST keep passing after Phase 1. This task adds one more explicit test that asserts the dispatch goes to the legacy branch when the trace is absent, and adds a regression-guard run of the whole `test_run_verification*` suite.

- [ ] **Step 1: Append the legacy-only test.**

```python
# Append to verifiers/bermuda/tests/test_run_verification_consumes_trace.py

def test_run_verification_uses_legacy_ledger_when_no_trace(
    tmp_path: Path, project_root: Path,
) -> None:
    """No analysis/ingest-trace.edn → falls back to claims/ledger.jsonl."""
    workspace = _seed_workspace(tmp_path, with_legacy_ledger=True)
    # NO trace file written.
    assert not (workspace / "analysis" / "ingest-trace.edn").exists()

    sandbox_project = tmp_path / "project_root_clone"
    sandbox_project.mkdir()
    (sandbox_project / "rules").mkdir()
    (sandbox_project / "rules" / "predicates.edn").write_text(
        (project_root / "rules" / "predicates.edn").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    rc = run(
        workspace=workspace, release_version="1.0.0",
        project_root=sandbox_project, stub_verifier=True, stub_verdict="sat",
    )
    assert rc == 0
    parsed = read_edn((sandbox_project / "work" / "claims.edn").read_text(encoding="utf-8"))
    atoms = parsed[Keyword("atoms")]
    ids = {a[Keyword("id")] for a in atoms}
    assert "clm-LEGACY-1" in ids
    # No synthesised file should have been written either
    assert not (sandbox_project / "work" / "ledger-from-trace.jsonl").exists()
```

- [ ] **Step 2: Run, expect 3 PASS (the two from Task 1.2 plus this one).**

```bash
cd verifiers/bermuda && .venv/Scripts/python.exe -m pytest tests/test_run_verification_consumes_trace.py -v
```

Expected:
```
tests/test_run_verification_consumes_trace.py::test_run_verification_consumes_trace PASSED
tests/test_run_verification_consumes_trace.py::test_run_verification_prefers_trace_over_legacy_ledger PASSED
tests/test_run_verification_consumes_trace.py::test_run_verification_uses_legacy_ledger_when_no_trace PASSED
3 passed
```

- [ ] **Step 3: Run the pre-existing tests as a regression check.**

```bash
cd verifiers/bermuda && .venv/Scripts/python.exe -m pytest tests/test_run_verification.py -v
```

Expected: both existing tests still PASS (`test_run_writes_verification_defects`, `test_run_with_sat_stub`).

- [ ] **Step 4: Commit.**

```bash
git add verifiers/bermuda/tests/test_run_verification_consumes_trace.py
git commit -m "bermuda: regression test for legacy ledger.jsonl fallback"
```

---

## Phase 3: CLJS event-stream-aware translate

### Task 3.1: shadow-cljs `:test` target + Event schema

**Files:**
- Modify: `verifiers/bermuda/shadow-cljs.edn`
- Modify: `verifiers/bermuda/cljs-orchestrator/src/main/bermuda/ir.cljs`
- Create: `verifiers/bermuda/cljs-orchestrator/test/bermuda/nl_to_fol_test.cljs` (skeleton only in this task)

The shadow-cljs config currently has only the `:main` build. Add a `:test` target so `npx shadow-cljs compile test && node out/test.js` runs `cljs.test` over `test/` under the same source root. Also extend `ir.cljs` with an `Event` schema describing the `[head payload]` shape and relax `Claim` callers later.

- [ ] **Step 1: Update `shadow-cljs.edn`.**

```clojure
{:source-paths ["cljs-orchestrator/src/main" "cljs-orchestrator/test"]
 :dependencies [[org.clojure/core.logic   "1.1.1"]
                [meander/epsilon          "0.0.650"]
                [metosin/malli            "0.16.4"]]
 :builds
 {:main {:target     :node-script
         :output-to  "cljs-orchestrator/dist/main.js"
         :main       bermuda.core/main
         :compiler-options {:optimizations :simple
                            :infer-externs :auto}}
  :test {:target     :node-test
         :output-to  "out/test.js"
         :ns-regexp  "-test$"
         :compiler-options {:optimizations :none}}}}
```

- [ ] **Step 2: Add the `Event` schema in `ir.cljs`.**

Append to `verifiers/bermuda/cljs-orchestrator/src/main/bermuda/ir.cljs`, immediately above the `(def Verdict ...)` form:

```clojure
(def EventHead
  "Symbolic head produced by the book-knowledge exporter. Stored as a
   symbol in CLJS (cljs.reader reads `claim/verified` as a symbol)."
  [:or :symbol :keyword])

(def Event
  "A trace event read from analysis/ingest-trace.edn. Two-element tuple:
   the first element is the head symbol/keyword (e.g. `claim/verified`),
   the second is a payload map."
  [:tuple EventHead :map])

(def ClaimOrEvent
  "Phase translate input element. Backwards-compatible: either a legacy
   Claim map, or a new Event vector."
  [:or Claim Event])
```

- [ ] **Step 3: Create a placeholder failing test file (so the next task has somewhere to land).**

```clojure
;; verifiers/bermuda/cljs-orchestrator/test/bermuda/nl_to_fol_test.cljs
(ns bermuda.nl-to-fol-test
  (:require [cljs.test :refer-macros [deftest is testing]]
            [bermuda.nl-to-fol :as t]))

(deftest scaffold-sanity
  (is (= 1 1)))
```

- [ ] **Step 4: Run the CLJS test target to confirm tooling wiring.**

```bash
cd verifiers/bermuda && npx shadow-cljs compile test && node out/test.js
```

Expected: `Testing bermuda.nl-to-fol-test ... 1 test, 1 assertion, 0 failures, 0 errors`. If `npx shadow-cljs` reports a missing dep, run `npm install` first (the `package.json` already declares shadow-cljs as a dev dep).

- [ ] **Step 5: Commit.**

```bash
git add verifiers/bermuda/shadow-cljs.edn verifiers/bermuda/cljs-orchestrator/src/main/bermuda/ir.cljs verifiers/bermuda/cljs-orchestrator/test/bermuda/nl_to_fol_test.cljs
git commit -m "bermuda cljs: shadow-cljs :test target + Event schema"
```

### Task 3.2: Per-event-head dispatch in `nl-to-fol`

**Files:**
- Modify: `verifiers/bermuda/cljs-orchestrator/test/bermuda/nl_to_fol_test.cljs`
- Modify: `verifiers/bermuda/cljs-orchestrator/src/main/bermuda/nl_to_fol.cljs`

- [ ] **Step 1: Replace the scaffold with real failing tests.**

Overwrite `verifiers/bermuda/cljs-orchestrator/test/bermuda/nl_to_fol_test.cljs` with:

```clojure
(ns bermuda.nl-to-fol-test
  "Per-event-head dispatch coverage for claim->formula and translate-corpus."
  (:require [cljs.test :refer-macros [deftest is testing]]
            [bermuda.nl-to-fol :as t]))

;;; ----- Legacy Claim-map input (must keep working) -----

(deftest legacy-claim-map-still-rewrites-to-formula
  (let [claim {:id "C001"
               :source "ch-01"
               :s {:kind :entity :name "Bermuda"}
               :p :parishes-count
               :o {:kind :quantity :value 9 :unit nil}
               :c []
               :modality :assertion
               :confidence 0.95}
        out (t/claim->formula claim)]
    (is (= :expression (:kind out)))
    (is (= :formula    (:sort out)))
    (is (= :forall (get-in out [:head :name])))))

(deftest legacy-opaque-claim-still-falls-through
  (let [claim {:id "C999" :source "x" :s {} :p :unknown :o {} :c []
               :modality :assertion :confidence 0.5}
        out (t/claim->formula claim)]
    (is (= :OPAQUE (:name out)))))

;;; ----- Event-stream input (new) -----

(deftest claim-verified-event-produces-formula
  (let [event [(symbol "claim" "verified")
               {:claim/id "clm-2026-000001"
                :text     "Bermuda has nine traditional parishes."
                :from     :proposed
                :to       :verified}]
        out (t/claim->formula event)]
    (is (some? out))
    (is (= :expression (:kind out))
        "verified events project to an :expression formula")
    (is (= :formula (:sort out)))))

(deftest source-ingested-event-skipped
  (let [event [(symbol "source" "ingested")
               {:doc/id "alpha" :kind :pdf}]
        out (t/claim->formula event)]
    (is (nil? out)
        "source/ingested produces no formula — caller drops nils")))

(deftest claim-proposed-event-skipped
  (let [event [(symbol "claim" "proposed")
               {:claim/id "clm-x" :text "candidate"}]
        out (t/claim->formula event)]
    (is (nil? out)
        "claim/proposed alone does not feed verification")))

(deftest atom-emitted-event-passes-through
  (let [emitted {:kind :symbol :sort :formula :name :PRE-COMPILED}
        event [(symbol "atom" "emitted") {:atom emitted}]
        out   (t/claim->formula event)]
    (is (= emitted out)
        "atom/emitted hands the pre-compiled atom straight back")))

(deftest unknown-event-head-emits-opaque
  (let [event [(symbol "weather" "rained") {:mm 12}]
        out (t/claim->formula event)]
    (is (= :OPAQUE (:name out))
        "unknown heads fall through to the :OPAQUE marker, matching
         the legacy ?other branch")))

;;; ----- translate-corpus integration -----

(deftest translate-corpus-mixes-claims-and-events-and-drops-nils
  (let [legacy-claim {:id "C001" :source "ch-01"
                      :s {:kind :entity :name "Bermuda"}
                      :p :parishes-count
                      :o {:kind :quantity :value 9 :unit nil}
                      :c []
                      :modality :assertion :confidence 0.95}
        ingested-ev  [(symbol "source" "ingested") {:doc/id "alpha"}]
        verified-ev  [(symbol "claim" "verified")
                      {:claim/id "clm-X" :text "x"
                       :from :proposed :to :verified}]
        out (t/translate-corpus [legacy-claim ingested-ev verified-ev])]
    (is (= 2 (count out))
        "nil-producing events are dropped; both surviving entries are formulas")
    (is (every? #(= :expression (:kind %)) out))))
```

- [ ] **Step 2: Run, expect FAIL.**

```bash
cd verifiers/bermuda && npx shadow-cljs compile test && node out/test.js
```

Expected output (substring matches):
```
FAIL in claim-verified-event-produces-formula
FAIL in source-ingested-event-skipped
FAIL in claim-proposed-event-skipped
FAIL in atom-emitted-event-passes-through
FAIL in unknown-event-head-emits-opaque
FAIL in translate-corpus-mixes-claims-and-events-and-drops-nils
```

The two legacy tests should PASS because `claim->formula` still handles `Claim` maps. The six new tests fail because the current implementation only matches maps with `:id`/`:s`/`:p`/`:o`/`:c`, not vectors.

- [ ] **Step 3: Rewrite `nl_to_fol.cljs`.**

```clojure
(ns bermuda.nl-to-fol
  "Phase 2: meander rewrite of Claim → Formula.

   Accepts two input shapes per element:
   - Legacy: a Claim map ({:id :s :p :o :c ...}).
   - Trace event: a 2-tuple [head payload] where head is a Symbol or
     Keyword whose namespaced name selects a dispatch branch.

   translate-corpus filters nils, so dispatch branches may return nil
   to drop an element (e.g. source/ingested)."
  (:require [meander.epsilon :as m]))

(defn to-si [v u]
  (case u
    "atm" (* v 101325.0)
    "C"   (+ v 273.15)
    v))

(defn- legacy-claim->formula [claim]
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

(defn- head-string [head]
  "Render head Symbol/Keyword/string to its 'ns/name' textual form."
  (cond
    (symbol? head)  (str (namespace head) "/" (name head))
    (keyword? head) (str (namespace head) "/" (name head))
    :else           (str head)))

(defn- event->formula [head payload]
  (case (head-string head)
    "claim/verified"
    ;; Wrap as a synthetic Claim map so the legacy rewrite handles it.
    ;; Required keys for the meander pattern: :id :s :p :o :c.
    (let [cid  (or (:claim/id payload) (get payload "claim/id"))
          text (or (:text payload) (get payload "text") "")
          claim {:id     (or cid "C000")
                 :source "trace"
                 :s      {:kind :entity :name "Bermuda"}
                 :p      :opaque
                 :o      {:kind :string :value text}
                 :c      []
                 :modality :assertion
                 :confidence (or (:confidence payload) 1.0)}]
      ;; The legacy rewrite expects :o to be a :quantity for the rich
      ;; expansion; with a :string :o it falls through to ?other and
      ;; emits :OPAQUE. We want a richer expression: emit one ourselves.
      {:kind :expression :sort :formula
       :head {:kind :symbol :name :verified :sort :rule}
       :args [{:kind :grounded :sort :string
               :name (:id claim)
               :grounded {:lib "literal" :fn "claim-id"}}
              {:kind :grounded :sort :string
               :name text
               :grounded {:lib "literal" :fn "text"}}]})

    "source/ingested"  nil
    "claim/proposed"   nil
    "claim/disputed"   nil
    "claim/superseded" nil
    "claim/refuted"    nil

    "atom/emitted"
    (or (:atom payload) (get payload "atom"))

    ;; Unknown heads — opaque marker
    {:kind :symbol :sort :formula :name :OPAQUE}))

(defn claim->formula [item]
  "Dispatch on input shape: a vector is a trace event; a map is a Claim."
  (cond
    (and (vector? item) (= 2 (count item)))
    (event->formula (first item) (second item))

    (map? item)
    (legacy-claim->formula item)

    :else
    {:kind :symbol :sort :formula :name :OPAQUE}))

(defn translate-corpus [items]
  (into [] (keep claim->formula) items))
```

- [ ] **Step 4: Run, expect 8 PASS.**

```bash
cd verifiers/bermuda && npx shadow-cljs compile test && node out/test.js
```

Expected:
```
Testing bermuda.nl-to-fol-test
Ran 8 tests containing 12 assertions.
0 failures, 0 errors.
```

- [ ] **Step 5: Commit.**

```bash
git add verifiers/bermuda/cljs-orchestrator/test/bermuda/nl_to_fol_test.cljs verifiers/bermuda/cljs-orchestrator/src/main/bermuda/nl_to_fol.cljs
git commit -m "bermuda cljs: dispatch claim->formula on trace event heads"
```

### Task 3.3: Relax `phases/translate` pre-contract

**Files:**
- Modify: `verifiers/bermuda/cljs-orchestrator/src/main/bermuda/phases.cljs`
- Create: `verifiers/bermuda/cljs-orchestrator/test/bermuda/phases_test.cljs`

The malli pre-contract on `translate` currently demands a `[:vector ir/Claim]`. After Task 3.2 the function accepts mixed claim/event vectors. Relax the contract.

- [ ] **Step 1: Write failing test.**

```clojure
;; verifiers/bermuda/cljs-orchestrator/test/bermuda/phases_test.cljs
(ns bermuda.phases-test
  (:require [cljs.test :refer-macros [deftest is]]
            [bermuda.phases :as p]))

(deftest translate-accepts-mixed-claim-and-event-input
  (let [legacy-claim {:id "C001" :source "ch-01"
                      :s {:kind :entity :name "Bermuda"}
                      :p :parishes-count
                      :o {:kind :quantity :value 9 :unit nil}
                      :c [] :modality :assertion :confidence 0.95}
        verified-ev  [(symbol "claim" "verified")
                      {:claim/id "clm-X" :text "x"
                       :from :proposed :to :verified}]
        out (p/translate [legacy-claim verified-ev])]
    (is (vector? out))
    (is (= 2 (count out)))))

(deftest translate-accepts-event-only-input
  (let [verified-ev [(symbol "claim" "verified")
                     {:claim/id "clm-X" :text "x"
                      :from :proposed :to :verified}]
        out (p/translate [verified-ev])]
    (is (= 1 (count out)))
    (is (= :expression (:kind (first out))))))
```

- [ ] **Step 2: Run, expect FAIL.**

```bash
cd verifiers/bermuda && npx shadow-cljs compile test && node out/test.js
```

Expected: the two new tests fail with a malli `:pre` contract violation, because the current `phases/translate` pre-contract is `[:vector ir/Claim]` and a 2-tuple is not a `Claim` map.

- [ ] **Step 3: Relax the pre-contract.**

Edit `verifiers/bermuda/cljs-orchestrator/src/main/bermuda/phases.cljs`. Replace the `translate` defn body:

```clojure
(ns bermuda.phases
  "Phase driver with malli pre/post contracts."
  (:require [bermuda.ir         :as ir]
            [bermuda.nl-to-fol  :as t]
            [bermuda.bridge     :as b]
            [malli.core         :as m]))

(def MAX-REMEDIES 3)

(defn translate [items]
  {:pre  (m/validate [:vector ir/ClaimOrEvent] items)
   :post (m/validate [:vector ir/Formula] %)}
  (t/translate-corpus items))

(defn verify [formulas]
  {:pre  (m/validate [:vector ir/Formula] formulas)
   :post (m/validate ir/Verdict %)}
  (b/verify-formulas (pr-str formulas)))

(defn typeset [report-path out-path]
  (b/render-pdf (slurp report-path) out-path))
```

- [ ] **Step 4: Run, expect all CLJS tests PASS.**

```bash
cd verifiers/bermuda && npx shadow-cljs compile test && node out/test.js
```

Expected: 10 tests pass (8 from `nl-to-fol-test`, 2 from `phases-test`), 0 failures.

- [ ] **Step 5: Commit.**

```bash
git add verifiers/bermuda/cljs-orchestrator/src/main/bermuda/phases.cljs verifiers/bermuda/cljs-orchestrator/test/bermuda/phases_test.cljs
git commit -m "bermuda cljs: relax translate pre-contract to ClaimOrEvent"
```

---

## Phase 4: Integration sweep

### Task 4.1: End-to-end synth trace exercise

**Files:**
- Modify: `verifiers/bermuda/tests/test_run_verification_consumes_trace.py`

- [ ] **Step 1: Append the end-to-end test.**

```python
# Append to verifiers/bermuda/tests/test_run_verification_consumes_trace.py

def test_run_verification_end_to_end_with_synth_trace_writes_qa(
    tmp_path: Path, project_root: Path,
) -> None:
    """Full Phase-1→4 run on a synth trace, with stubbed verifier, lands a
    verification-defects.json under qa/ with the expected verdict shape."""
    workspace = _seed_workspace(tmp_path, with_legacy_ledger=False)
    _write_trace(workspace, [
        (Symbol("ingested", namespace="source"), {Keyword("doc/id"): "alpha"}),
        (Symbol("proposed", namespace="claim"), {
            Keyword("claim/id"): "clm-E2E-1",
            Keyword("text"): "Bermuda has nine traditional parishes.",
            Keyword("confidence"): 0.99,
        }),
        (Symbol("verified", namespace="claim"), {
            Keyword("claim/id"): "clm-E2E-1",
            Keyword("from"): Keyword("proposed"),
            Keyword("to"): Keyword("verified"),
        }),
    ])
    sandbox_project = tmp_path / "project_root_clone"
    sandbox_project.mkdir()
    (sandbox_project / "rules").mkdir()
    (sandbox_project / "rules" / "predicates.edn").write_text(
        (project_root / "rules" / "predicates.edn").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    rc = run(
        workspace=workspace, release_version="1.0.0",
        project_root=sandbox_project, stub_verifier=True, stub_verdict="sat",
    )
    assert rc == 0

    qa_out = workspace / "qa" / "verification-defects.json"
    assert qa_out.exists()
    payload = json.loads(qa_out.read_text(encoding="utf-8"))
    assert payload["verdict"] == "sat"
    assert "core" in payload
    assert isinstance(payload["core"], list)
```

- [ ] **Step 2: Run, expect PASS.**

```bash
cd verifiers/bermuda && .venv/Scripts/python.exe -m pytest tests/test_run_verification_consumes_trace.py::test_run_verification_end_to_end_with_synth_trace_writes_qa -v
```

Expected: `1 passed`.

- [ ] **Step 3: Commit.**

```bash
git add verifiers/bermuda/tests/test_run_verification_consumes_trace.py
git commit -m "bermuda: end-to-end synth-trace test through verdict_to_qa"
```

### Task 4.2: Full Bermuda Python sweep

- [ ] **Step 1: Run.**

```bash
cd verifiers/bermuda && .venv/Scripts/python.exe -m pytest tests/ -q
```

Expected: 23 baseline + 5 (Task 1.1) + 3 (Task 1.2 + 2.1) + 1 (Task 4.1) = 32 tests, all PASS. If the legacy `test_run_verification.py` tests have regressed, debug before proceeding — the trace-aware branch is opt-in (only taken when the trace file exists), so regression there means the Phase-1 dispatch leaked.

### Task 4.3: Full CLJS sweep

- [ ] **Step 1: Run.**

```bash
cd verifiers/bermuda && npx shadow-cljs compile test && node out/test.js
```

Expected: 10 tests, 0 failures. Output ends with `Ran 10 tests containing N assertions. 0 failures, 0 errors.`

### Task 4.4: Cross-skill regression

- [ ] **Step 1: Book-knowledge sweep (must be untouched).**

```bash
cd skills/book-knowledge && python -m pytest tests/ -q
```

Expected: existing test count unchanged, all PASS. The exporter is unmodified, so this is a no-op safety check.

- [ ] **Step 2: Neurosym-forge sweep (must be untouched).**

```bash
cd skills/neurosym-forge && .venv/Scripts/python.exe -m pytest tests/ -q
```

Expected: existing test count unchanged, all PASS.

---

## Phase 5: Smoke + PR

### Task 5.1: Manual trace smoke against the bermuda-manual workspace

- [ ] **Step 1: Generate a fresh ingest-trace.edn from the canonical Bermuda workspace.**

```bash
cd skills/book-knowledge && python -m scripts.export_symbolic_trace \
  --workspace ../../examples/bermuda-manual \
  --out ../../examples/bermuda-manual/analysis/ingest-trace.edn
```

Expected stdout: `exported N events -> ../../examples/bermuda-manual/analysis/ingest-trace.edn` for some N >= 1.

- [ ] **Step 2: Confirm the file parses as EDN and lists events with namespaced heads.**

```bash
cd C:/work/russellian-book-suite
.venv/Scripts/python.exe -c "from scripts._edn_reader import read_edn, Keyword; \
  p = open('examples/bermuda-manual/analysis/ingest-trace.edn', encoding='utf-8').read(); \
  d = read_edn(p); print('events:', len(d[Keyword('events')]))"
```

If the project has no top-level `.venv`, use `skills/neurosym-forge/.venv/Scripts/python.exe` instead — `scripts/__init__.py` import shim resolves identically.

Expected output: `events: N` matching Step 1.

- [ ] **Step 3: Run the verifier in stub mode against the workspace.**

```bash
cd verifiers/bermuda && .venv/Scripts/python.exe -m scripts.run_verification \
  --workspace ../../examples/bermuda-manual --release 1.0.0 --stub --stub-verdict sat
```

Expected stdout (last line): `verification complete: verdict=sat`. Exit 0.

- [ ] **Step 4: Confirm `work/claims.edn` was populated from the trace.**

```bash
cd verifiers/bermuda
.venv/Scripts/python.exe -c "from scripts._edn_reader import read_edn, Keyword; \
  d = read_edn(open('work/claims.edn', encoding='utf-8').read()); \
  print('atoms:', len(d[Keyword('atoms')]))"
ls work/ledger-from-trace.jsonl
```

Expected: `atoms:` > 0; the synthesised JSONL exists in `work/`.

- [ ] **Step 5: Clean up smoke artefacts (do NOT commit them).**

```bash
cd C:/work/russellian-book-suite
git status --short
# If examples/bermuda-manual/analysis/ingest-trace.edn or
# verifiers/bermuda/work/ appears, leave it untracked (these are gitignored
# in the workspace). If git surfaces them as new, they belong to the
# example workspace and should not be committed in this PR; verify
# .gitignore covers them.
```

### Task 5.2: Push + open PR

- [ ] **Step 1: Push.**

```bash
cd C:/work/russellian-book-suite
git push -u origin feat/booklogic-d2-wiring
```

- [ ] **Step 2: Open the PR.**

```bash
gh pr create --title "BookLogic v0.4 PR-D2: wire ingest-trace into the verifier" --body "$(cat <<'EOF'
## Summary

Closes out the D2 deliverable from the BookLogic v0.4 mission. The book-knowledge exporter (`export_symbolic_trace.py`) has been emitting `analysis/ingest-trace.edn` since PR-D2-half-1 landed; this PR wires the verifier to consume it.

- `verifiers/bermuda/scripts/trace_to_ledger.py` (new): reads the EDN trace and projects every `claim/verified` event back to the ledger-row dict shape `ingest_ledger.ingest` already expects.
- `verifiers/bermuda/scripts/run_verification.py`: Phase 1 now prefers `<workspace>/analysis/ingest-trace.edn` when present, falls back to `claims/ledger.jsonl` for legacy workspaces.
- `verifiers/bermuda/cljs-orchestrator/src/main/bermuda/nl_to_fol.cljs`: `claim->formula` dispatches on input shape — a 2-tuple `[head payload]` selects per-event-head logic (`claim/verified` → formula, `source/ingested`/`claim/proposed` → nil, `atom/emitted` → pass-through, unknown → `:OPAQUE`); a map falls through to the existing meander rewrite.
- `verifiers/bermuda/cljs-orchestrator/src/main/bermuda/phases.cljs`: `translate` pre-contract relaxed from `[:vector Claim]` to `[:vector ClaimOrEvent]`.
- `verifiers/bermuda/cljs-orchestrator/src/main/bermuda/ir.cljs`: new `Event` and `ClaimOrEvent` malli schemas.
- `verifiers/bermuda/shadow-cljs.edn`: new `:test` node-test target so CLJS tests run in CI.
- 9 new Python tests + 10 new CLJS tests covering trace projection, Phase-1 dispatch, legacy fallback, per-event-head dispatch, and end-to-end stub-verifier exercise.

Spec: `docs/specs/2026-05-17-booklogic-claude-only-finish-design.md` § "PR-D2 — Wire ingest-trace into the verifier".
Plan: `docs/plans/2026-05-17-booklogic-d2-wiring.md`.

## Test plan

- [ ] `cd verifiers/bermuda && .venv/Scripts/python.exe -m pytest tests/ -q` — 32 passing (23 baseline + 9 new)
- [ ] `cd verifiers/bermuda && npx shadow-cljs compile test && node out/test.js` — 10 passing, 0 failures
- [ ] `cd skills/book-knowledge && python -m pytest tests/ -q` — unchanged baseline, all passing
- [ ] `cd skills/neurosym-forge && .venv/Scripts/python.exe -m pytest tests/ -q` — unchanged baseline, all passing
- [ ] Manual smoke: `python -m scripts.export_symbolic_trace --workspace examples/bermuda-manual` then `python -m scripts.run_verification --workspace examples/bermuda-manual --release 1.0.0 --stub --stub-verdict sat` exits 0; `work/claims.edn` populated from the trace.

## Acceptance criteria (from spec § PR-D2)

- `run_verification.py` exits 0 against a fresh workspace that has `analysis/ingest-trace.edn` but no `claims/ledger.jsonl` — covered by `test_run_verification_consumes_trace`.
- Existing legacy-path tests still pass — covered by `test_run_verification_uses_legacy_ledger_when_no_trace` plus pre-existing `test_run_verification.py`.
- The Bermuda smoke pipeline in CI still passes — guarded by Task 4.4.

## Out of scope

- Real Z3 verifier run against a trace — covered by PR-5.
- Adding `atom/emitted` to the official trace schema enum — the CLJS dispatch handles it forward-compatibly, but no exporter emits it today.
- `claim/disputed`/`superseded`/`refuted` semantic handling beyond drop-to-nil — Phase 1 today only feeds verified claims.
EOF
)"
```

- [ ] **Step 3: Report the PR URL.**

---

## Self-review

Walking spec § PR-D2 acceptance criteria against the plan:

| Spec clause | Implementing tasks |
|---|---|
| `run_verification.py` Phase-1 reads `<workspace>/analysis/ingest-trace.edn` when present, falls back to `ledger.jsonl` | 1.2 (test+impl), 2.1 (legacy fallback regression) |
| `phases.cljs` `translate` accepts either claim-list (legacy) or trace-event shape | 3.3 |
| `nl_to_fol.cljs` dispatches on event head: `claim/verified` → formula, `source/ingested` → nothing, `atom/emitted` → pass-through | 3.2 |
| Python: synthesise 3-event trace, run verifier, assert atoms loaded | 1.2 (`test_run_verification_consumes_trace`) |
| CLJS: extend `nl-to-fol` test for each event head + unknown head | 3.2 (6 new dispatch tests + 2 legacy regression tests) |
| `run_verification.py` exits 0 against a workspace with only the trace, no ledger | 1.2 (`test_run_verification_consumes_trace`) |
| Existing legacy-path tests still pass | 2.1 + 4.4 |
| Bermuda smoke pipeline still passes | 4.2, 4.3, 4.4, 5.1 |

All spec items have an implementing task. No spec acceptance criterion is unaddressed.

**Placeholder scan.** No "TBD/TODO/fill in" appears in any task. Every code block is complete. Every shell command is exact. Every expected output is named.

**Naming consistency.** `trace_to_ledger.py`, `read_trace`, `project_trace_to_ledger_rows`, `TraceProjectionError`, `_materialise_trace_as_ledger`, `ClaimOrEvent`, `Event`, `EventHead`, `event->formula`, `legacy-claim->formula`, `head-string` are used identically across all tasks that reference them.

**Size.** 5 phases / 11 tasks. Phase 3 (CLJS test target + dispatch refactor) is the largest piece; Phases 1, 2 (Python trace-aware reader + legacy fallback), 4 (regression sweep), 5 (smoke + PR) are each small.

**Known risks.**

- **shadow-cljs `:test` target on Windows.** If `npx shadow-cljs compile test` fails on a fresh checkout because `node_modules/` is empty, run `npm install` inside `verifiers/bermuda/` first. The dev deps are already declared in `package.json` (`shadow-cljs ^2.28.20`).
- **Meander rewrite no-match shape.** The current `claim->formula` returns `{:kind :symbol :sort :formula :name :OPAQUE}` on the `?other` branch. The new `event->formula "claim/verified"` synthesises a richer `{:kind :expression :sort :formula ...}` shape — verifies it still passes `[:vector Formula]` post-contract because `Formula = Atom = [:map [:kind ...] [:sort Sort]]`. Both shapes satisfy `Formula`.
- **Trace event payload key flattening.** `read_trace` strips the leading `:` from keyword keys (mirroring `load_symbolic_trace.py`). The CLJS dispatch reads namespaced keyword keys directly (`:claim/id`, `:text`) from EDN events because shadow-cljs's `cljs.reader/read-string` keeps keywords keyword-shaped. The Python side and CLJS side both work because the trace projection is Python-only — CLJS sees the original EDN-typed payload via `cljs.reader/read-string` in the verifier's `read-edn` helper, which is unchanged.
- **`atom/emitted` dispatch is speculative.** No exporter emits this head today. The dispatch is included because the spec calls it out as an acceptance test case; the cost is one `case` branch and one test, and it keeps the contract forward-compatible for the eventual D5 work where pre-compiled atoms feed in directly.

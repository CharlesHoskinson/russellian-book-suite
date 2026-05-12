# Bundle C — Closed-Loop Ledger Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert the russellian-book-suite claim ledger from a write-only artifact into a self-correcting epistemic state via abductive counter-claims, Bayesian belief propagation over PROV-O, and book-qa writeback to ledger state.

**Architecture:** Four loosely coupled additions across three existing skills. book-knowledge owns the ledger and gains propagation + counter-claim + apply-writeback; book-qa proposes ledger transitions from defect tickets; book-compose loads counter-claims as must-address contract entries and excludes refuted claims from default slices. No new skills. Spec at `docs/specs/2026-05-11-bundle-c-closed-loop-ledger-design.md`.

**Tech Stack:** Python 3.13, jsonschema, rdflib, pyshacl, pytest. No new external dependencies. Workspace layout and entry-point patterns inherit from existing book-knowledge SKILL.md.

---

## Pre-flight

Read these before starting any task:
- `skills/book-knowledge/SKILL.md`
- `skills/book-knowledge/scripts/claim_validator.py` (schema + state machine)
- `skills/book-knowledge/scripts/ledger.py` (append + transition helpers)
- `skills/book-knowledge/scripts/project_graph.py` (TriG projector)
- `skills/book-knowledge/scripts/run_competency_queries.py` (query runner)
- `skills/book-knowledge/assets/claim-record.schema.json`
- `skills/book-knowledge/assets/queries/*.rq` (existing competency queries)
- `skills/book-qa/SKILL.md` (defect taxonomy D1–D12)
- `docs/specs/2026-05-11-bundle-c-closed-loop-ledger-design.md` (the design this plan implements)

**Reconciliation note.** The existing schema has a `confidence` field (0.0–1.0) set at extraction time. Per the spec, this is *not* the same as `p_prior`. Treat `confidence` as the extractor's self-reported confidence at ingest; leave its semantics unchanged. Bundle C adds new fields `p_prior`, `p_posterior`, `counter_claim_ids`, and `load_bearing` alongside `confidence`.

**State machine.** Current transitions in `claim_validator.VALID_TRANSITIONS`:
```python
"proposed":   {"verified", "disputed", "superseded"}
"verified":   {"disputed", "superseded"}
"disputed":   {"verified", "superseded"}
"superseded": set()
```
Bundle C extends to:
```python
"proposed":   {"verified", "disputed", "superseded"}
"verified":   {"disputed", "superseded"}
"disputed":   {"verified", "superseded", "refuted"}
"superseded": set()
"refuted":    set()
```
Existing transitions stay; `refuted` is reachable only from `disputed` and is terminal.

**Commit hygiene.** Each task ends with a commit. Conventional-commit prefixes (`feat:`, `test:`, `refactor:`) are fine but not required — terse human style per repo CLAUDE.md. No AI attribution.

**Test invocation.** All commands assume CWD is the relevant skill directory (`skills/book-knowledge/` or `skills/book-qa/`) and a `.venv` exists per SKILL.md. Use `.venv\Scripts\python.exe` on Windows, `.venv/bin/python` on POSIX.

**Where tests contain `...`.** A few tests in this plan (Tasks 2.9, 3.6, 3.7, 4.6) leave fixture setup as `...` because the exact contract-loader signature, ledger-slice function name, and Sentinel call site live in book-compose / book-qa scripts whose interfaces I could not read remotely. The engineer must read the matching script and fill in the fixture using the existing test style in that skill — the assertion lines and the production-code changes are concrete.

---

## File Structure

### book-knowledge — created

```
skills/book-knowledge/
├── scripts/
│   ├── propagate_belief.py             # Phase 1
│   ├── generate_counter_claims.py      # Phase 2
│   ├── apply_writeback.py              # Phase 3
│   └── counter_claims.py               # Phase 2 — schema + I/O helper
├── assets/
│   ├── counter-claim.schema.json       # Phase 2
│   ├── events.schema.json              # Phase 3
│   └── queries/
│       ├── coverage/                   # Phase 2 — existing files move here
│       ├── consistency/                # Phase 2 — contradiction_scan.rq moves here
│       └── defeasible/                 # Phase 2
│           ├── rebuttal-presence.rq
│           ├── contested-rebuttal-window.rq
│           ├── posterior-floor.rq
│           └── _meta.yaml              # per-query severity + exceptions
└── tests/
    ├── test_propagate_belief.py        # Phase 1
    ├── test_generate_counter_claims.py # Phase 2
    ├── test_apply_writeback.py         # Phase 3
    ├── test_defeasible_queries.py      # Phase 2
    ├── test_counter_claims_schema.py   # Phase 2
    └── test_events_log.py              # Phase 3
```

### book-knowledge — modified

- `scripts/claim_validator.py` — add `refuted` state + new schema fields
- `scripts/ledger.py` — `transition_status` writes to `claims/events.jsonl`
- `scripts/run_competency_queries.py` — load directory-classed queries with metadata
- `assets/claim-record.schema.json` — add fields
- `SKILL.md` — document new scripts and `claims/events.jsonl`, `claims/snapshots/`, `claims/counter-claims.jsonl`, `claims/proposed-transitions.jsonl`, `claims/address-checks/`

### book-qa — created

```
skills/book-qa/
├── scripts/propose_writeback.py        # Phase 3
└── tests/test_propose_writeback.py     # Phase 3
```

### book-qa — modified

- `SKILL.md` — document new `propose_writeback.py` script and outputs

### book-compose — modified

- `scripts/load_contract.py` (or wherever contracts are read; engineer locates) — read `counter-claims.jsonl` and emit must-address entries
- New: `scripts/check_address.py` — two-stage address detection (verbatim + LLM verifier)
- New: `tests/test_check_address.py`
- Ledger-slice loader — exclude `refuted` and (configurably) `disputed` by default; honor `force_include_refuted`

---

# PHASE 1 — Belief propagation (~3 days)

Goal: add `p_prior` and `p_posterior` fields, projected from ledger + PROV-O graph. No reads from these fields anywhere else yet — Phase 1 ships as a no-op for existing books.

## Task 1.1: Extend claim schema with new fields

**Files:**
- Modify: `skills/book-knowledge/assets/claim-record.schema.json`
- Modify: `skills/book-knowledge/scripts/claim_validator.py:11-18` (VALID_TRANSITIONS)
- Test: `skills/book-knowledge/tests/test_claim_validator.py` (add cases; file already exists)

- [ ] **Step 1: Write the failing tests**

In `tests/test_claim_validator.py`, append:

```python
import json
import pytest
from pathlib import Path

from scripts.claim_validator import (
    validate_claim, assert_transition_allowed, ClaimValidationError,
)

BASE = {
    "claim_id": "clm-2026-000001",
    "canonical_text": "Test claim text long enough.",
    "status": "verified",
    "claim_type": "fact",
    "confidence": 0.7,
    "source_spans": [{"doc_id": "d1", "locator_text": "evidence here"}],
    "created_at": "2026-05-11T00:00:00Z",
}

def test_refuted_status_accepted():
    rec = {**BASE, "status": "refuted"}
    validate_claim(rec)

def test_p_prior_and_p_posterior_accepted():
    rec = {**BASE, "p_prior": 0.7, "p_posterior": 0.82}
    validate_claim(rec)

def test_load_bearing_accepted():
    rec = {**BASE, "load_bearing": True}
    validate_claim(rec)

def test_counter_claim_ids_accepted():
    rec = {**BASE, "counter_claim_ids": ["cc-0001-abcdef", "cc-0001-fedcba"]}
    validate_claim(rec)

def test_p_posterior_out_of_range_rejected():
    rec = {**BASE, "p_posterior": 1.5}
    with pytest.raises(ClaimValidationError):
        validate_claim(rec)

def test_disputed_to_refuted_allowed():
    assert_transition_allowed("disputed", "refuted")  # must not raise

def test_verified_to_refuted_rejected():
    with pytest.raises(ClaimValidationError):
        assert_transition_allowed("verified", "refuted")

def test_refuted_is_terminal():
    with pytest.raises(ClaimValidationError):
        assert_transition_allowed("refuted", "verified")
    with pytest.raises(ClaimValidationError):
        assert_transition_allowed("refuted", "disputed")
```

- [ ] **Step 2: Run tests to verify they fail**

```
.venv\Scripts\python.exe -m pytest tests/test_claim_validator.py -v -k "refuted or p_prior or p_posterior or load_bearing or counter_claim"
```
Expected: FAILures referring to schema validation errors and missing `refuted` in VALID_TRANSITIONS.

- [ ] **Step 3: Update schema**

In `assets/claim-record.schema.json`, change the `status` enum:
```json
"status": {"enum": ["proposed", "verified", "disputed", "superseded", "refuted"]},
```
Add to `properties` (insert before `"source_spans"` for readability):
```json
"p_prior":          {"type": "number", "minimum": 0.0, "maximum": 1.0},
"p_posterior":      {"type": "number", "minimum": 0.0, "maximum": 1.0},
"load_bearing":     {"type": "boolean", "default": false},
"counter_claim_ids":{"type": "array", "items": {"type": "string", "pattern": "^cc-[0-9]{4}-[0-9a-f]{6}$"}},
```
Leave `additionalProperties: false` in place.

- [ ] **Step 4: Update state machine**

In `scripts/claim_validator.py`, replace `VALID_TRANSITIONS`:
```python
VALID_TRANSITIONS = {
    "proposed":   {"verified", "disputed", "superseded"},
    "verified":   {"disputed", "superseded"},
    "disputed":   {"verified", "superseded", "refuted"},
    "superseded": set(),
    "refuted":    set(),
}
```

- [ ] **Step 5: Run tests to verify they pass**

```
.venv\Scripts\python.exe -m pytest tests/test_claim_validator.py -v
```
Expected: PASS for all existing and new tests.

- [ ] **Step 6: Commit**

```bash
git add skills/book-knowledge/assets/claim-record.schema.json \
        skills/book-knowledge/scripts/claim_validator.py \
        skills/book-knowledge/tests/test_claim_validator.py
git commit -m "Add refuted state and p_prior/p_posterior/load_bearing/counter_claim_ids to claim schema"
```

---

## Task 1.2: Build PROV-O derivation graph reader

**Files:**
- Create: `skills/book-knowledge/scripts/belief_graph.py`
- Test: `skills/book-knowledge/tests/test_belief_graph.py`

This module is the read side: it turns the projected `graph/dataset.trig` plus `ledger.jsonl` into an in-memory `BeliefGraph` suitable for propagation. Keeping it separate from `propagate_belief.py` keeps the propagation math independently testable.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_belief_graph.py
from pathlib import Path
import json

from scripts.belief_graph import BeliefGraph, load_belief_graph
from scripts.workspace import init_workspace


def _seed(tmp_path: Path) -> Path:
    layout = init_workspace(tmp_path)
    claims = [
        {"claim_id": "clm-2026-000001", "canonical_text": "Claim A core.",
         "status": "verified", "claim_type": "fact", "confidence": 0.7,
         "source_spans": [{"doc_id": "src1", "locator_text": "A evidence"}],
         "created_at": "2026-05-11T00:00:00Z"},
        {"claim_id": "clm-2026-000002", "canonical_text": "Claim B derived.",
         "status": "verified", "claim_type": "fact", "confidence": 0.6,
         "source_spans": [{"doc_id": "src2", "locator_text": "B evidence"}],
         "derived_from": ["clm-2026-000001"],
         "created_at": "2026-05-11T00:00:00Z"},
    ]
    with layout.ledger.open("w", encoding="utf-8") as fh:
        for c in claims:
            fh.write(json.dumps(c) + "\n")
    return layout.root


def test_load_belief_graph_picks_up_derivation_edges(tmp_path):
    root = _seed(tmp_path)
    bg = load_belief_graph(root)
    assert "clm-2026-000001" in bg.nodes
    assert "clm-2026-000002" in bg.nodes
    assert ("clm-2026-000001", "clm-2026-000002") in bg.derivation_edges


def test_node_carries_status_and_sources(tmp_path):
    root = _seed(tmp_path)
    bg = load_belief_graph(root)
    n = bg.nodes["clm-2026-000001"]
    assert n.status == "verified"
    assert n.sources == ["src1"]
```

- [ ] **Step 2: Run test to verify it fails**

```
.venv\Scripts\python.exe -m pytest tests/test_belief_graph.py -v
```
Expected: FAIL — module does not exist.

- [ ] **Step 3: Implement `belief_graph.py`**

```python
"""Reads ledger.jsonl + source manifests and emits an in-memory belief graph."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from .workspace import find_workspace_root, WorkspaceLayout


@dataclass
class BeliefNode:
    claim_id: str
    status: str
    sources: list[str] = field(default_factory=list)
    p_prior: float | None = None
    p_posterior: float | None = None
    counter_claim_ids: list[str] = field(default_factory=list)
    load_bearing: bool = False


@dataclass
class BeliefGraph:
    nodes: dict[str, BeliefNode] = field(default_factory=dict)
    derivation_edges: set[tuple[str, str]] = field(default_factory=set)  # (parent, child)


def _latest_per_claim(records: list[dict]) -> dict[str, dict]:
    latest: dict[str, dict] = {}
    for r in records:
        latest[r["claim_id"]] = r
    return latest


def load_belief_graph(workspace_root: Path) -> BeliefGraph:
    layout = WorkspaceLayout.for_root(workspace_root)
    records = []
    if layout.ledger.exists():
        for line in layout.ledger.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                records.append(json.loads(line))
    latest = _latest_per_claim(records)
    g = BeliefGraph()
    for cid, rec in latest.items():
        g.nodes[cid] = BeliefNode(
            claim_id=cid,
            status=rec["status"],
            sources=[s["doc_id"] for s in rec.get("source_spans", [])],
            p_prior=rec.get("p_prior"),
            p_posterior=rec.get("p_posterior"),
            counter_claim_ids=list(rec.get("counter_claim_ids", [])),
            load_bearing=bool(rec.get("load_bearing", False)),
        )
        for parent in rec.get("derived_from", []):
            g.derivation_edges.add((parent, cid))
    return g
```

> If `WorkspaceLayout.for_root` does not exist, look at how `workspace.py` exposes layout construction and adapt. The existing `init_workspace` returns a layout — use that pattern.

- [ ] **Step 4: Run tests**

```
.venv\Scripts\python.exe -m pytest tests/test_belief_graph.py -v
```
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add skills/book-knowledge/scripts/belief_graph.py \
        skills/book-knowledge/tests/test_belief_graph.py
git commit -m "Add BeliefGraph reader over ledger and derivation edges"
```

---

## Task 1.3: Implement prior-from-status helper

**Files:**
- Modify: `skills/book-knowledge/scripts/belief_graph.py`
- Modify: `skills/book-knowledge/tests/test_belief_graph.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_belief_graph.py`:
```python
from scripts.belief_graph import prior_for_status

def test_prior_for_status_defaults():
    assert prior_for_status("verified")   == 0.7
    assert prior_for_status("proposed")   == 0.5
    assert prior_for_status("disputed")   == 0.2
    assert prior_for_status("refuted")    == 0.05
    assert prior_for_status("superseded") == 0.5

def test_prior_for_status_unknown_raises():
    import pytest
    with pytest.raises(ValueError):
        prior_for_status("anything-else")
```

- [ ] **Step 2: Run, expect fail**

```
.venv\Scripts\python.exe -m pytest tests/test_belief_graph.py::test_prior_for_status_defaults -v
```

- [ ] **Step 3: Implement**

Append to `scripts/belief_graph.py`:
```python
PRIOR_BY_STATUS = {
    "verified":   0.70,
    "proposed":   0.50,
    "disputed":   0.20,
    "refuted":    0.05,
    "superseded": 0.50,
}

def prior_for_status(status: str) -> float:
    try:
        return PRIOR_BY_STATUS[status]
    except KeyError as e:
        raise ValueError(f"unknown status: {status!r}") from e
```

- [ ] **Step 4: Run, expect pass**

- [ ] **Step 5: Commit**

```bash
git commit -am "Add prior_for_status helper"
```

---

## Task 1.4: Implement source-trust loader

**Files:**
- Modify: `skills/book-knowledge/scripts/belief_graph.py`
- Modify: `skills/book-knowledge/tests/test_belief_graph.py`

Source manifests under `raw/manifests/` may carry a `trust: float` field (Bundle C adds it). Missing field = 1.0.

- [ ] **Step 1: Failing test**

```python
def test_source_trust_defaults_to_one(tmp_path):
    root = _seed(tmp_path)
    from scripts.belief_graph import load_source_trust
    trust = load_source_trust(root)
    assert trust.get("src1", 1.0) == 1.0
    assert trust.get("missing-doc", 1.0) == 1.0

def test_source_trust_reads_manifest_field(tmp_path):
    root = _seed(tmp_path)
    manifest_dir = root / "raw" / "manifests"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    (manifest_dir / "src1.json").write_text(
        '{"doc_id": "src1", "trust": 0.6}', encoding="utf-8"
    )
    from scripts.belief_graph import load_source_trust
    trust = load_source_trust(root)
    assert trust["src1"] == 0.6
```

- [ ] **Step 2: Run, expect fail**

- [ ] **Step 3: Implement**

Append to `belief_graph.py`:
```python
def load_source_trust(workspace_root: Path) -> dict[str, float]:
    layout = WorkspaceLayout.for_root(workspace_root)
    manifest_dir = layout.root / "raw" / "manifests"
    out: dict[str, float] = {}
    if not manifest_dir.exists():
        return out
    for path in manifest_dir.glob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        doc_id = data.get("doc_id")
        if doc_id:
            out[doc_id] = float(data.get("trust", 1.0))
    return out
```

- [ ] **Step 4: Run, expect pass**

- [ ] **Step 5: Commit**

```bash
git commit -am "Add load_source_trust reader"
```

---

## Task 1.5: Implement core propagation math

**Files:**
- Create: `skills/book-knowledge/scripts/propagate_belief.py`
- Test: `skills/book-knowledge/tests/test_propagate_belief.py`

This task implements the pure-function `propagate(...)` that takes a `BeliefGraph` and a trust dict and returns posteriors. No I/O.

- [ ] **Step 1: Failing test**

```python
# tests/test_propagate_belief.py
import math
from scripts.belief_graph import BeliefGraph, BeliefNode
from scripts.propagate_belief import propagate, COUNTER_OPEN_DAMP, COUNTER_ADDRESSED_DAMP


def _g_single(status="verified", sources=("src1",), p_prior=None):
    g = BeliefGraph()
    g.nodes["clm-x"] = BeliefNode(
        claim_id="clm-x", status=status, sources=list(sources), p_prior=p_prior,
    )
    return g


def test_single_claim_uses_prior_unchanged():
    g = _g_single(status="verified")
    trust = {"src1": 1.0}
    posts = propagate(g, trust, counter_claims=[])
    assert math.isclose(posts["clm-x"], 0.70, rel_tol=1e-6)


def test_two_independent_sources_corroborate():
    g = BeliefGraph()
    g.nodes["clm-y"] = BeliefNode(
        claim_id="clm-y", status="verified", sources=["s1", "s2"],
    )
    trust = {"s1": 1.0, "s2": 1.0}
    posts = propagate(g, trust, counter_claims=[])
    # 1 - (1-0.7)*(1-0.7) = 1 - 0.09 = 0.91
    assert math.isclose(posts["clm-y"], 0.91, rel_tol=1e-6)


def test_clamped_to_max():
    g = BeliefGraph()
    g.nodes["clm-z"] = BeliefNode(
        claim_id="clm-z", status="verified", sources=[f"s{i}" for i in range(20)],
    )
    trust = {f"s{i}": 1.0 for i in range(20)}
    posts = propagate(g, trust, counter_claims=[])
    assert posts["clm-z"] == 0.95  # clamped


def test_low_trust_source_reduces_evidence():
    g = _g_single(sources=["s1"])
    trust = {"s1": 0.5}
    posts = propagate(g, trust, counter_claims=[])
    # With trust=0.5, effective evidence = 0.7 * 0.5 = 0.35
    assert math.isclose(posts["clm-x"], 0.35, rel_tol=1e-6)


def test_open_counter_claim_damps():
    g = _g_single(status="verified", sources=["s1"])
    g.nodes["clm-x"].counter_claim_ids = ["cc-1"]
    trust = {"s1": 1.0}
    counter_claims = [{"id": "cc-1", "target_claim_id": "clm-x", "status": "open"}]
    posts = propagate(g, trust, counter_claims=counter_claims)
    assert math.isclose(posts["clm-x"], 0.70 * COUNTER_OPEN_DAMP, rel_tol=1e-6)


def test_addressed_counter_claim_damps_more_than_open():
    g_open = _g_single(); g_open.nodes["clm-x"].counter_claim_ids = ["cc-1"]
    g_addr = _g_single(); g_addr.nodes["clm-x"].counter_claim_ids = ["cc-1"]
    trust = {"src1": 1.0}
    posts_open = propagate(g_open, trust,
        counter_claims=[{"id": "cc-1", "target_claim_id": "clm-x", "status": "open"}])
    posts_addr = propagate(g_addr, trust,
        counter_claims=[{"id": "cc-1", "target_claim_id": "clm-x", "status": "addressed"}])
    assert posts_addr["clm-x"] < posts_open["clm-x"]  # addressed = stronger damp
    assert math.isclose(posts_addr["clm-x"] / posts_open["clm-x"],
                        COUNTER_ADDRESSED_DAMP / COUNTER_OPEN_DAMP, rel_tol=1e-6)
```

- [ ] **Step 2: Run, expect fail**

```
.venv\Scripts\python.exe -m pytest tests/test_propagate_belief.py -v
```

- [ ] **Step 3: Implement `propagate_belief.py` core**

```python
"""Bayesian belief propagation over the claim ledger's derivation graph."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .belief_graph import BeliefGraph, prior_for_status

POSTERIOR_FLOOR = 0.05
POSTERIOR_CEIL = 0.95
COUNTER_OPEN_DAMP = 0.95       # per spec — open rivals weigh less than addressed
COUNTER_ADDRESSED_DAMP = 0.85
MAX_ITERATIONS = 20
CONVERGENCE_EPSILON = 1e-4


def _evidence_combine(sources: list[str], trust: dict[str, float],
                      base_prior: float) -> float:
    """1 - prod(1 - p_i*trust_i) across sources. Single-source returns prior*trust."""
    if not sources:
        return base_prior
    failure = 1.0
    for s in sources:
        t = trust.get(s, 1.0)
        failure *= (1.0 - base_prior * t)
    return 1.0 - failure


def _apply_counter_damping(p: float, counter_claims_for_node: list[dict]) -> float:
    for cc in counter_claims_for_node:
        status = cc.get("status", "open")
        if status == "addressed":
            p *= COUNTER_ADDRESSED_DAMP
        elif status == "open":
            p *= COUNTER_OPEN_DAMP
        # dismissed counter-claims do not damp
    return p


def _clamp(p: float) -> float:
    return max(POSTERIOR_FLOOR, min(POSTERIOR_CEIL, p))


def propagate(graph: BeliefGraph, trust: dict[str, float],
              counter_claims: Iterable[dict]) -> dict[str, float]:
    cc_by_target: dict[str, list[dict]] = {}
    for cc in counter_claims:
        cc_by_target.setdefault(cc["target_claim_id"], []).append(cc)
    # Initialize from p_prior if set, else from status.
    p: dict[str, float] = {}
    for cid, node in graph.nodes.items():
        p[cid] = node.p_prior if node.p_prior is not None else prior_for_status(node.status)
    # Topological-ish fixed-point: cap at MAX_ITERATIONS.
    for _ in range(MAX_ITERATIONS):
        new_p: dict[str, float] = {}
        for cid, node in graph.nodes.items():
            base = node.p_prior if node.p_prior is not None else prior_for_status(node.status)
            evidence = _evidence_combine(node.sources, trust, base)
            evidence = _apply_counter_damping(evidence, cc_by_target.get(cid, []))
            new_p[cid] = _clamp(evidence)
        delta = max(abs(new_p[c] - p[c]) for c in p) if p else 0.0
        p = new_p
        if delta < CONVERGENCE_EPSILON:
            break
    return p
```

- [ ] **Step 4: Run, expect pass**

```
.venv\Scripts\python.exe -m pytest tests/test_propagate_belief.py -v
```

- [ ] **Step 5: Commit**

```bash
git add skills/book-knowledge/scripts/propagate_belief.py \
        skills/book-knowledge/tests/test_propagate_belief.py
git commit -m "Add pure-function propagate over BeliefGraph"
```

---

## Task 1.6: Snapshot writer

**Files:**
- Modify: `skills/book-knowledge/scripts/propagate_belief.py`
- Modify: `skills/book-knowledge/tests/test_propagate_belief.py`

- [ ] **Step 1: Failing test**

```python
import json
from pathlib import Path
from scripts.workspace import init_workspace
from scripts.propagate_belief import write_snapshot


def test_write_snapshot_creates_iso_named_file(tmp_path):
    layout = init_workspace(tmp_path)
    layout.ledger.write_text(
        json.dumps({"claim_id": "clm-2026-000001", "canonical_text": "Hi.",
                    "status": "verified", "claim_type": "fact", "confidence": 0.7,
                    "source_spans": [{"doc_id": "d", "locator_text": "abcd"}],
                    "created_at": "2026-05-11T00:00:00Z"}) + "\n",
        encoding="utf-8",
    )
    path = write_snapshot(tmp_path)
    assert path.exists()
    assert path.parent == layout.root / "claims" / "snapshots"
    assert path.name.endswith(".jsonl")
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert records[0]["claim_id"] == "clm-2026-000001"
```

- [ ] **Step 2: Run, expect fail**

- [ ] **Step 3: Implement**

Append to `propagate_belief.py`:
```python
from datetime import datetime, timezone
from pathlib import Path
import shutil

from .workspace import WorkspaceLayout


def write_snapshot(workspace_root: Path) -> Path:
    layout = WorkspaceLayout.for_root(workspace_root)
    snap_dir = layout.root / "claims" / "snapshots"
    snap_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dest = snap_dir / f"{stamp}.jsonl"
    if layout.ledger.exists():
        shutil.copy2(layout.ledger, dest)
    else:
        dest.write_text("", encoding="utf-8")
    return dest
```

- [ ] **Step 4: Run, expect pass**

- [ ] **Step 5: Commit**

```bash
git commit -am "Add propagate_belief snapshot writer"
```

---

## Task 1.7: Posterior writeback to ledger

**Files:**
- Modify: `skills/book-knowledge/scripts/propagate_belief.py`
- Modify: `skills/book-knowledge/tests/test_propagate_belief.py`

After computing posteriors, append a new ledger record per affected claim that carries the updated `p_prior` and `p_posterior`. This preserves append-only semantics rather than rewriting prior records.

- [ ] **Step 1: Failing test**

```python
def test_write_posteriors_appends_records(tmp_path):
    from scripts.propagate_belief import write_posteriors
    layout = init_workspace(tmp_path)
    base = {"claim_id": "clm-2026-000001", "canonical_text": "Hi text.",
            "status": "verified", "claim_type": "fact", "confidence": 0.7,
            "source_spans": [{"doc_id": "d", "locator_text": "abcd"}],
            "created_at": "2026-05-11T00:00:00Z"}
    layout.ledger.write_text(json.dumps(base) + "\n", encoding="utf-8")
    write_posteriors(tmp_path, {"clm-2026-000001": 0.82}, generated_by_run="run-x")
    records = [json.loads(l) for l in layout.ledger.read_text(encoding="utf-8").splitlines()]
    assert len(records) == 2
    assert records[1]["claim_id"] == "clm-2026-000001"
    assert records[1]["p_posterior"] == 0.82
    assert records[1]["p_prior"] == 0.7  # carried from prior_for_status("verified")
    assert records[1]["generated_by_run"] == "run-x"
```

- [ ] **Step 2: Run, expect fail**

- [ ] **Step 3: Implement**

Append to `propagate_belief.py`:
```python
from .belief_graph import load_belief_graph, prior_for_status


def write_posteriors(workspace_root: Path, posteriors: dict[str, float],
                     generated_by_run: str) -> int:
    layout = WorkspaceLayout.for_root(workspace_root)
    bg = load_belief_graph(workspace_root)
    written = 0
    with layout.ledger.open("a", encoding="utf-8") as fh:
        for cid, post in posteriors.items():
            node = bg.nodes.get(cid)
            if node is None:
                continue
            prior = node.p_prior if node.p_prior is not None else prior_for_status(node.status)
            # Build a minimal new record by copying the latest existing one's required fields.
            latest = _latest_record_for(layout, cid)
            if latest is None:
                continue
            new = dict(latest)
            new["p_prior"] = prior
            new["p_posterior"] = post
            new["generated_by_run"] = generated_by_run
            fh.write(json.dumps(new, sort_keys=True) + "\n")
            written += 1
    return written


def _latest_record_for(layout: WorkspaceLayout, claim_id: str) -> dict | None:
    found = None
    if not layout.ledger.exists():
        return None
    for line in layout.ledger.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rec = json.loads(line)
        if rec["claim_id"] == claim_id:
            found = rec
    return found
```

Add at top of file:
```python
import json
```

- [ ] **Step 4: Run, expect pass**

- [ ] **Step 5: Commit**

```bash
git commit -am "Append posterior records to ledger preserving append-only semantics"
```

---

## Task 1.8: Markdown report writer + entrypoint

**Files:**
- Modify: `skills/book-knowledge/scripts/propagate_belief.py`
- Modify: `skills/book-knowledge/tests/test_propagate_belief.py`

- [ ] **Step 1: Failing test**

```python
def test_run_entrypoint_writes_report_and_snapshot(tmp_path):
    from scripts.propagate_belief import run
    layout = init_workspace(tmp_path)
    layout.ledger.write_text(json.dumps({
        "claim_id": "clm-2026-000001", "canonical_text": "Hi text.",
        "status": "verified", "claim_type": "fact", "confidence": 0.7,
        "source_spans": [{"doc_id": "d", "locator_text": "abcd"}],
        "created_at": "2026-05-11T00:00:00Z"}) + "\n", encoding="utf-8")
    run_id = run(tmp_path, run_id="run-2026-05-11-01")
    report = layout.root / "graph" / "reports" / f"belief-propagation-{run_id}.md"
    assert report.exists()
    text = report.read_text(encoding="utf-8")
    assert "clm-2026-000001" in text
    assert "histogram" in text.lower()
    snapshots = list((layout.root / "claims" / "snapshots").glob("*.jsonl"))
    assert len(snapshots) == 1
```

- [ ] **Step 2: Run, expect fail**

- [ ] **Step 3: Implement entrypoint**

Append to `propagate_belief.py`:
```python
def _histogram(values: list[float], bins: int = 10) -> list[tuple[float, float, int]]:
    if not values:
        return []
    edges = [i / bins for i in range(bins + 1)]
    counts = [0] * bins
    for v in values:
        idx = min(int(v * bins), bins - 1)
        counts[idx] += 1
    return [(edges[i], edges[i + 1], counts[i]) for i in range(bins)]


def write_report(workspace_root: Path, run_id: str,
                 before: dict[str, float], after: dict[str, float]) -> Path:
    layout = WorkspaceLayout.for_root(workspace_root)
    out_dir = layout.root / "graph" / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"belief-propagation-{run_id}.md"
    deltas = sorted(
        ((cid, before.get(cid, 0.0), after[cid], after[cid] - before.get(cid, 0.0))
         for cid in after),
        key=lambda r: abs(r[3]), reverse=True,
    )
    lines = [f"# Belief propagation report — {run_id}\n",
             f"Total claims: {len(after)}",
             "\n## Top 20 absolute deltas\n",
             "| claim_id | before | after | delta |", "|---|---|---|---|"]
    for cid, b, a, d in deltas[:20]:
        lines.append(f"| {cid} | {b:.3f} | {a:.3f} | {d:+.3f} |")
    lines.append("\n## Posterior histogram\n")
    lines.append("| bin | count |")
    lines.append("|---|---|")
    for lo, hi, count in _histogram(list(after.values())):
        lines.append(f"| [{lo:.2f}, {hi:.2f}) | {count} |")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def run(workspace_root: Path, run_id: str | None = None) -> str:
    if run_id is None:
        run_id = datetime.now(timezone.utc).strftime("run-%Y%m%dT%H%M%SZ")
    write_snapshot(workspace_root)
    bg = load_belief_graph(workspace_root)
    trust = load_source_trust(workspace_root)
    cc_path = WorkspaceLayout.for_root(workspace_root).root / "claims" / "counter-claims.jsonl"
    counter_claims = []
    if cc_path.exists():
        for line in cc_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                counter_claims.append(json.loads(line))
    before = {cid: (n.p_posterior if n.p_posterior is not None
                    else (n.p_prior if n.p_prior is not None else prior_for_status(n.status)))
              for cid, n in bg.nodes.items()}
    after = propagate(bg, trust, counter_claims)
    write_posteriors(workspace_root, after, generated_by_run=run_id)
    write_report(workspace_root, run_id, before, after)
    return run_id


if __name__ == "__main__":
    import sys
    run(Path(sys.argv[1]))
```

Add at top: `from .belief_graph import load_source_trust`.

- [ ] **Step 4: Run, expect pass**

- [ ] **Step 5: Commit**

```bash
git commit -am "Add propagate_belief.run entrypoint with report and CLI"
```

---

## Task 1.9: Documentation pass

**Files:**
- Modify: `skills/book-knowledge/SKILL.md`

- [ ] **Step 1: Edit SKILL.md**

Under the **Workspace layout** code block, add the new artifacts:
```
  claims/
    ledger.jsonl  conflicts.jsonl  verification/
    snapshots/                                # NEW — Bundle C
    counter-claims.jsonl                      # NEW — Bundle C
    address-checks/                           # NEW — Bundle C
    proposed-transitions.jsonl                # NEW — Bundle C
    events.jsonl                              # NEW — Bundle C
```

Under **Components** → **Claim ledger:**, add a new bullet:
```
- `propagate_belief.py` — Bayesian belief propagation over PROV-O; writes p_posterior records, snapshot, report
```

Under **Usage**, append:
```
.venv\Scripts\python.exe -m scripts.propagate_belief <workspace>
```

- [ ] **Step 2: Commit**

```bash
git add skills/book-knowledge/SKILL.md
git commit -m "Document propagate_belief in book-knowledge SKILL"
```

---

# PHASE 2 — Counter-claims and defeasible coverage (~4 days)

Goal: load-bearing claims carry abductive rivals; rivals become must-address in contracts; defeasible SPARQL coverage queries land as non-blocking warnings.

## Task 2.1: Counter-claim schema + I/O

**Files:**
- Create: `skills/book-knowledge/assets/counter-claim.schema.json`
- Create: `skills/book-knowledge/scripts/counter_claims.py`
- Test: `skills/book-knowledge/tests/test_counter_claims_schema.py`

- [ ] **Step 1: Failing test**

```python
# tests/test_counter_claims_schema.py
import json
from pathlib import Path
import pytest
from scripts.counter_claims import (
    validate_counter_claim, append_counter_claim, read_counter_claims,
    CounterClaimError,
)
from scripts.workspace import init_workspace

BASE = {
    "id": "cc-0001-abcdef",
    "target_claim_id": "clm-2026-000001",
    "text": "Some rival hypothesis stated as one sentence.",
    "disagreement_vector": "scope",
    "status": "open",
    "provenance": {"generator": "abduction-v1", "prompt_sha256": "0"*64},
    "created_at": "2026-05-11T00:00:00Z",
    "addressed_in_chapter": None,
}

def test_valid_record_accepts():
    validate_counter_claim(BASE)

def test_invalid_status_rejected():
    with pytest.raises(CounterClaimError):
        validate_counter_claim({**BASE, "status": "approved"})

def test_invalid_disagreement_vector_rejected():
    with pytest.raises(CounterClaimError):
        validate_counter_claim({**BASE, "disagreement_vector": "vibes"})

def test_id_pattern_enforced():
    with pytest.raises(CounterClaimError):
        validate_counter_claim({**BASE, "id": "cc-0001-XYZ"})

def test_append_and_read(tmp_path):
    layout = init_workspace(tmp_path)
    append_counter_claim(tmp_path, BASE)
    items = read_counter_claims(tmp_path)
    assert len(items) == 1
    assert items[0]["id"] == "cc-0001-abcdef"
```

- [ ] **Step 2: Run, expect fail**

- [ ] **Step 3: Write the schema**

`assets/counter-claim.schema.json`:
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "counter-claim",
  "type": "object",
  "required": ["id", "target_claim_id", "text", "disagreement_vector",
               "status", "provenance", "created_at"],
  "properties": {
    "id":                    {"type": "string", "pattern": "^cc-[0-9]{4}-[0-9a-f]{6}$"},
    "target_claim_id":       {"type": "string", "pattern": "^clm-[0-9]{4}-[0-9]{6}$"},
    "text":                  {"type": "string", "minLength": 12},
    "disagreement_vector":   {"enum": ["mechanism", "measurement", "scope", "time_period", "population"]},
    "status":                {"enum": ["open", "addressed", "dismissed"]},
    "provenance":            {
      "type": "object",
      "required": ["generator", "prompt_sha256"],
      "properties": {
        "generator":     {"type": "string"},
        "prompt_sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"}
      },
      "additionalProperties": false
    },
    "created_at":            {"type": "string", "format": "date-time"},
    "addressed_in_chapter":  {"type": ["string", "null"]}
  },
  "additionalProperties": false
}
```

- [ ] **Step 4: Implement `counter_claims.py`**

```python
"""Counter-claim records — append-only parallel ledger keyed by cc-XXXX-XXXXXX."""
from __future__ import annotations

import json
from pathlib import Path

import jsonschema

from .workspace import WorkspaceLayout

ASSETS = Path(__file__).resolve().parent.parent / "assets"
SCHEMA = json.loads((ASSETS / "counter-claim.schema.json").read_text(encoding="utf-8"))


class CounterClaimError(Exception):
    pass


def validate_counter_claim(record: dict) -> None:
    try:
        jsonschema.validate(record, SCHEMA)
    except jsonschema.ValidationError as e:
        raise CounterClaimError(str(e)) from e


def _path(workspace_root: Path) -> Path:
    return WorkspaceLayout.for_root(workspace_root).root / "claims" / "counter-claims.jsonl"


def append_counter_claim(workspace_root: Path, record: dict) -> None:
    validate_counter_claim(record)
    path = _path(workspace_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, sort_keys=True) + "\n")


def read_counter_claims(workspace_root: Path) -> list[dict]:
    path = _path(workspace_root)
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out


def next_counter_claim_id(workspace_root: Path) -> str:
    """Generate cc-YYYY-NNNNNN; NN is hex random for collision tolerance."""
    import secrets
    from datetime import datetime, timezone
    year = datetime.now(timezone.utc).year
    return f"cc-{year}-{secrets.token_hex(3)}"
```

- [ ] **Step 5: Run, expect pass**

- [ ] **Step 6: Commit**

```bash
git add skills/book-knowledge/assets/counter-claim.schema.json \
        skills/book-knowledge/scripts/counter_claims.py \
        skills/book-knowledge/tests/test_counter_claims_schema.py
git commit -m "Add counter-claim schema and append/read helpers"
```

---

## Task 2.2: Abductive counter-claim generator (LLM call)

**Files:**
- Create: `skills/book-knowledge/scripts/generate_counter_claims.py`
- Test: `skills/book-knowledge/tests/test_generate_counter_claims.py`

The actual LLM call goes through Claude Code's Skill-managed agent infra, which means we shell out via the same `Agent` invocation pattern other skills use. For the test, parameterize the LLM client behind a callable. Live testing happens in Phase 4.

- [ ] **Step 1: Failing test**

```python
# tests/test_generate_counter_claims.py
import json
from pathlib import Path
from scripts.workspace import init_workspace
from scripts.generate_counter_claims import generate_for_claim, prompt_for_claim


def fake_llm(prompt: str) -> str:
    return json.dumps([
        {"text": "Ferry consolidation reversed since 2020.",
         "disagreement_vector": "scope"},
        {"text": "The cited 2019 study used a flawed denominator.",
         "disagreement_vector": "measurement"},
    ])


def test_prompt_for_claim_contains_claim_text():
    claim = {"claim_id": "clm-2026-000001",
             "canonical_text": "Bermuda's ferry network expanded since 2020."}
    p = prompt_for_claim(claim)
    assert "Bermuda's ferry network expanded since 2020." in p
    assert "rival" in p.lower()
    assert "disagreement" in p.lower()


def test_generate_for_claim_writes_records(tmp_path):
    layout = init_workspace(tmp_path)
    target = {"claim_id": "clm-2026-000001",
              "canonical_text": "Bermuda's ferry network expanded since 2020.",
              "status": "verified", "claim_type": "fact", "confidence": 0.8,
              "source_spans": [{"doc_id": "d", "locator_text": "abcd"}],
              "created_at": "2026-05-11T00:00:00Z",
              "load_bearing": True}
    layout.ledger.write_text(json.dumps(target) + "\n", encoding="utf-8")
    ids = generate_for_claim(tmp_path, target["claim_id"], llm_call=fake_llm)
    assert len(ids) == 2
    cc_path = layout.root / "claims" / "counter-claims.jsonl"
    items = [json.loads(l) for l in cc_path.read_text(encoding="utf-8").splitlines()]
    assert {it["target_claim_id"] for it in items} == {"clm-2026-000001"}
    assert {it["disagreement_vector"] for it in items} == {"scope", "measurement"}
```

- [ ] **Step 2: Run, expect fail**

- [ ] **Step 3: Implement**

```python
"""Abductive counter-claim generation for load-bearing claims."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable

from .counter_claims import append_counter_claim, next_counter_claim_id
from .ledger import read_claims
from .workspace import WorkspaceLayout

PROMPT_TEMPLATE = """\
Given a claim from a non-fiction book's ledger, generate the 2-3 strongest rival
hypotheses that, if true, would falsify or weaken the claim. Each rival must be:
- A single declarative sentence (no questions, no hedges, no lists).
- Tagged with exactly one disagreement vector from: mechanism, measurement,
  scope, time_period, population.

Claim text:
{claim_text}

Return JSON only, an array of objects with keys "text" and "disagreement_vector".
No prose outside the JSON.
"""


def prompt_for_claim(claim: dict) -> str:
    return PROMPT_TEMPLATE.format(claim_text=claim["canonical_text"])


def _latest_claim_record(workspace_root: Path, claim_id: str) -> dict | None:
    for r in read_claims(WorkspaceLayout.for_root(workspace_root)):
        if r["claim_id"] == claim_id:
            latest = r
    return locals().get("latest")


def generate_for_claim(workspace_root: Path, claim_id: str,
                       llm_call: Callable[[str], str]) -> list[str]:
    target = _latest_claim_record(workspace_root, claim_id)
    if target is None:
        raise ValueError(f"claim not found: {claim_id}")
    prompt = prompt_for_claim(target)
    raw = llm_call(prompt)
    rivals = json.loads(raw)
    prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    new_ids: list[str] = []
    for rival in rivals:
        cc_id = next_counter_claim_id(workspace_root)
        rec = {
            "id": cc_id,
            "target_claim_id": claim_id,
            "text": rival["text"],
            "disagreement_vector": rival["disagreement_vector"],
            "status": "open",
            "provenance": {"generator": "abduction-v1", "prompt_sha256": prompt_hash},
            "created_at": now,
            "addressed_in_chapter": None,
        }
        append_counter_claim(workspace_root, rec)
        new_ids.append(cc_id)
    return new_ids


def generate_for_all_load_bearing(workspace_root: Path,
                                  llm_call: Callable[[str], str]) -> dict[str, list[str]]:
    layout = WorkspaceLayout.for_root(workspace_root)
    latest: dict[str, dict] = {}
    for r in read_claims(layout):
        latest[r["claim_id"]] = r
    out: dict[str, list[str]] = {}
    for cid, rec in latest.items():
        if rec.get("load_bearing"):
            existing = set(rec.get("counter_claim_ids", []))
            if existing:
                continue  # idempotent — skip if already generated
            out[cid] = generate_for_claim(workspace_root, cid, llm_call)
    return out
```

- [ ] **Step 4: Run, expect pass**

- [ ] **Step 5: Commit**

```bash
git add skills/book-knowledge/scripts/generate_counter_claims.py \
        skills/book-knowledge/tests/test_generate_counter_claims.py
git commit -m "Add abductive counter-claim generator with prompt template and fake-LLM tests"
```

---

## Task 2.3: Update claim record with counter_claim_ids after generation

**Files:**
- Modify: `skills/book-knowledge/scripts/generate_counter_claims.py`
- Modify: `skills/book-knowledge/tests/test_generate_counter_claims.py`

- [ ] **Step 1: Failing test**

```python
def test_generate_for_claim_appends_ids_to_target(tmp_path):
    layout = init_workspace(tmp_path)
    target = {"claim_id": "clm-2026-000001",
              "canonical_text": "X happens since 2020.",
              "status": "verified", "claim_type": "fact", "confidence": 0.8,
              "source_spans": [{"doc_id": "d", "locator_text": "abcd"}],
              "created_at": "2026-05-11T00:00:00Z",
              "load_bearing": True}
    layout.ledger.write_text(json.dumps(target) + "\n", encoding="utf-8")
    new_ids = generate_for_claim(tmp_path, target["claim_id"], llm_call=fake_llm)
    # Reload the ledger — the latest record for the claim should carry the new IDs.
    records = [json.loads(l) for l in layout.ledger.read_text(encoding="utf-8").splitlines()]
    latest = [r for r in records if r["claim_id"] == "clm-2026-000001"][-1]
    assert latest.get("counter_claim_ids") == new_ids
```

- [ ] **Step 2: Run, expect fail**

- [ ] **Step 3: Implement append-to-target**

Inside `generate_for_claim`, after the rivals loop, before `return new_ids`:
```python
    # Append an updated claim record carrying the new counter_claim_ids.
    layout = WorkspaceLayout.for_root(workspace_root)
    updated = dict(target)
    existing = list(updated.get("counter_claim_ids", []))
    updated["counter_claim_ids"] = existing + new_ids
    with layout.ledger.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(updated, sort_keys=True) + "\n")
```

- [ ] **Step 4: Run, expect pass**

- [ ] **Step 5: Commit**

```bash
git commit -am "Append updated claim record carrying generated counter_claim_ids"
```

---

## Task 2.4: Address-detection (verbatim + LLM verifier) in book-compose

**Files:**
- Create: `skills/book-compose/scripts/check_address.py`
- Test: `skills/book-compose/tests/test_check_address.py`

- [ ] **Step 1: Failing test**

```python
# tests/test_check_address.py
import json
from pathlib import Path
from scripts.check_address import check_address


def stub_verifier(chapter: str, rival_text: str) -> dict:
    if "ferry consolidation" in chapter.lower():
        return {"addressed": True,
                "supporting_paragraph": "Yet the ferry network has consolidated."}
    return {"addressed": False, "supporting_paragraph": None}


def test_verbatim_path(tmp_path):
    chapter = "Bermuda ferries fact: Ferry consolidation reversed since 2020. More text."
    rival = {"id": "cc-1", "text": "Ferry consolidation reversed since 2020."}
    result = check_address(chapter, rival, verifier=stub_verifier, cache_dir=tmp_path)
    assert result["addressed"] is True
    assert result["mechanism"] == "verbatim"


def test_llm_verifier_path(tmp_path):
    chapter = "Yet the ferry network has consolidated — schedules dropped by half."
    rival = {"id": "cc-1", "text": "Bermuda's ferry network has consolidated rather than expanded."}
    result = check_address(chapter, rival, verifier=stub_verifier, cache_dir=tmp_path)
    assert result["addressed"] is True
    assert result["mechanism"] == "llm"


def test_cache_avoids_verifier_recall(tmp_path):
    chapter = "Yet the ferry network has consolidated — schedules dropped by half."
    rival = {"id": "cc-1", "text": "Bermuda's ferry network has consolidated rather than expanded."}
    calls = {"n": 0}
    def counting(chap, txt):
        calls["n"] += 1
        return stub_verifier(chap, txt)
    check_address(chapter, rival, verifier=counting, cache_dir=tmp_path)
    check_address(chapter, rival, verifier=counting, cache_dir=tmp_path)
    assert calls["n"] == 1
```

- [ ] **Step 2: Run, expect fail**

- [ ] **Step 3: Implement**

```python
"""Two-stage address check: verbatim fast path then cached LLM verifier."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Callable


def _cache_key(chapter: str, rival_text: str) -> str:
    h = hashlib.sha256()
    h.update(chapter.encode("utf-8"))
    h.update(b"||")
    h.update(rival_text.encode("utf-8"))
    return h.hexdigest()


def check_address(chapter_text: str, rival: dict,
                  verifier: Callable[[str, str], dict],
                  cache_dir: Path) -> dict:
    """Returns {"addressed": bool, "mechanism": "verbatim"|"llm"|"none",
    "supporting_paragraph": str|None}."""
    rival_text = rival["text"]
    if rival_text.strip() in chapter_text:
        return {"addressed": True, "mechanism": "verbatim",
                "supporting_paragraph": rival_text.strip()}
    cache_dir.mkdir(parents=True, exist_ok=True)
    key = _cache_key(chapter_text, rival_text)
    cache_file = cache_dir / f"{key}.json"
    if cache_file.exists():
        cached = json.loads(cache_file.read_text(encoding="utf-8"))
        return {**cached, "mechanism": "llm"}
    verdict = verifier(chapter_text, rival_text)
    cache_file.write_text(json.dumps(verdict), encoding="utf-8")
    return {"addressed": bool(verdict["addressed"]),
            "mechanism": "llm",
            "supporting_paragraph": verdict.get("supporting_paragraph")}
```

- [ ] **Step 4: Run, expect pass**

- [ ] **Step 5: Commit**

```bash
git add skills/book-compose/scripts/check_address.py \
        skills/book-compose/tests/test_check_address.py
git commit -m "Add two-stage address check (verbatim + cached LLM verifier)"
```

---

## Task 2.5: Promote address verdicts back to counter-claim status

**Files:**
- Create: `skills/book-knowledge/scripts/promote_addressed.py`
- Test: `skills/book-knowledge/tests/test_promote_addressed.py`

A separate script run after book-compose drafts a chapter: read the chapter's check_address results, update each counter-claim's status to `addressed` (or leave `open`).

- [ ] **Step 1: Failing test**

```python
# tests/test_promote_addressed.py
import json
from scripts.workspace import init_workspace
from scripts.counter_claims import append_counter_claim
from scripts.promote_addressed import promote_addressed


def _seed_cc(tmp_path):
    init_workspace(tmp_path)
    append_counter_claim(tmp_path, {
        "id": "cc-2026-abcdef", "target_claim_id": "clm-2026-000001",
        "text": "Ferry network has consolidated.", "disagreement_vector": "scope",
        "status": "open",
        "provenance": {"generator": "abduction-v1", "prompt_sha256": "0"*64},
        "created_at": "2026-05-11T00:00:00Z", "addressed_in_chapter": None,
    })


def test_promotes_open_to_addressed(tmp_path):
    _seed_cc(tmp_path)
    promote_addressed(tmp_path, chapter_id="ch07", addressed_ids=["cc-2026-abcdef"])
    from scripts.counter_claims import read_counter_claims
    items = read_counter_claims(tmp_path)
    latest = [r for r in items if r["id"] == "cc-2026-abcdef"][-1]
    assert latest["status"] == "addressed"
    assert latest["addressed_in_chapter"] == "ch07"
```

- [ ] **Step 2: Run, expect fail**

- [ ] **Step 3: Implement**

```python
"""Promote counter-claims from 'open' to 'addressed' based on check_address verdicts."""
from __future__ import annotations

from pathlib import Path

from .counter_claims import append_counter_claim, read_counter_claims


def _latest_per_id(items: list[dict]) -> dict[str, dict]:
    latest: dict[str, dict] = {}
    for r in items:
        latest[r["id"]] = r
    return latest


def promote_addressed(workspace_root: Path, chapter_id: str,
                      addressed_ids: list[str]) -> int:
    items = read_counter_claims(workspace_root)
    latest = _latest_per_id(items)
    promoted = 0
    for cc_id in addressed_ids:
        rec = latest.get(cc_id)
        if rec is None or rec["status"] == "addressed":
            continue
        new = dict(rec)
        new["status"] = "addressed"
        new["addressed_in_chapter"] = chapter_id
        append_counter_claim(workspace_root, new)
        promoted += 1
    return promoted
```

- [ ] **Step 4: Run, expect pass**

- [ ] **Step 5: Commit**

```bash
git add skills/book-knowledge/scripts/promote_addressed.py \
        skills/book-knowledge/tests/test_promote_addressed.py
git commit -m "Promote counter-claims to addressed after chapter draft check"
```

---

## Task 2.6: Move existing queries into coverage/, contradiction into consistency/

**Files:**
- Move: `skills/book-knowledge/assets/queries/*.rq` → `assets/queries/coverage/` (except `contradiction_scan.rq` → `consistency/`)
- Create: `skills/book-knowledge/assets/queries/defeasible/_meta.yaml`
- Modify: `skills/book-knowledge/scripts/run_competency_queries.py`
- Test: `skills/book-knowledge/tests/test_run_competency_queries.py` (or wherever existing tests live)

- [ ] **Step 1: Inventory existing tests**

Read `tests/test_run_competency_queries.py` (or grep for it) to find which query files existing tests reference by path. They likely reference flat paths — those tests must continue passing after the move.

- [ ] **Step 2: Move files**

```bash
mkdir -p skills/book-knowledge/assets/queries/coverage
mkdir -p skills/book-knowledge/assets/queries/consistency
mkdir -p skills/book-knowledge/assets/queries/defeasible

git mv skills/book-knowledge/assets/queries/chapter_evidence_coverage.rq    skills/book-knowledge/assets/queries/coverage/
git mv skills/book-knowledge/assets/queries/unsupported_claims.rq           skills/book-knowledge/assets/queries/coverage/
git mv skills/book-knowledge/assets/queries/orphan_wiki_pages.rq            skills/book-knowledge/assets/queries/coverage/
git mv skills/book-knowledge/assets/queries/stale_after_source_refresh.rq   skills/book-knowledge/assets/queries/coverage/
git mv skills/book-knowledge/assets/queries/contradiction_scan.rq           skills/book-knowledge/assets/queries/consistency/
```

- [ ] **Step 3: Update `run_competency_queries.py`**

Change the file-discovery to walk subdirectories and tag each query with its directory class. Treat top-level `.rq` files (none should remain) as `coverage` for back-compat. Sketch:

```python
QUERY_CLASSES = ("coverage", "consistency", "defeasible")

def discover_queries(assets_root: Path) -> list[tuple[str, str, Path]]:
    """Returns (class, name, path) for every .rq under assets/queries/."""
    base = assets_root / "queries"
    out: list[tuple[str, str, Path]] = []
    for cls in QUERY_CLASSES:
        cls_dir = base / cls
        if not cls_dir.exists():
            continue
        for f in sorted(cls_dir.glob("*.rq")):
            out.append((cls, f.stem, f))
    # Back-compat: flat .rq files at the top of queries/.
    for f in sorted(base.glob("*.rq")):
        out.append(("coverage", f.stem, f))
    return out
```

Update the script's main runner to invoke each query and emit results keyed by class. Existing report output should be preserved.

- [ ] **Step 4: Add tests for the new structure**

```python
def test_discover_queries_picks_up_subdirs():
    from scripts.run_competency_queries import discover_queries
    from pathlib import Path
    ASSETS = Path(__file__).resolve().parent.parent / "assets"
    found = discover_queries(ASSETS)
    classes = {c for c, _, _ in found}
    assert "coverage" in classes
    assert "consistency" in classes
    # defeasible may be empty pre-2.7; skip that assertion until 2.7 lands.
    names_in_coverage = {n for c, n, _ in found if c == "coverage"}
    assert "chapter_evidence_coverage" in names_in_coverage
```

- [ ] **Step 5: Run full book-knowledge test suite**

```
.venv\Scripts\python.exe -m pytest tests/ -v
```
Expected: all tests pass (existing + new).

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "Organize SPARQL queries into coverage/consistency/defeasible directories"
```

---

## Task 2.7: Ship three defeasible queries with metadata

**Files:**
- Create: `skills/book-knowledge/assets/queries/defeasible/rebuttal-presence.rq`
- Create: `skills/book-knowledge/assets/queries/defeasible/contested-rebuttal-window.rq`
- Create: `skills/book-knowledge/assets/queries/defeasible/posterior-floor.rq`
- Create: `skills/book-knowledge/assets/queries/defeasible/_meta.yaml`
- Test: `skills/book-knowledge/tests/test_defeasible_queries.py`

The three queries enforce: every load-bearing cited claim has at least one addressed counter-claim (unless `axiom: true`); every disputed claim has a rebuttal within 300 words of its citation (unless chapter declares `accepts_unrebutted: true`); every cited claim has `p_posterior >= 0.4` (unless contract pins via `pin_low_confidence: true`).

The book-knowledge graph projector must include `p_posterior` and counter-claim `cc:rebuts` edges for these queries to fire. That requires a small extension to `project_graph.py`. Do that here.

- [ ] **Step 1: Failing test for graph projection of p_posterior**

```python
# tests/test_project_graph_posterior.py
import json
from rdflib import URIRef
from scripts.workspace import init_workspace
from scripts.project_graph import project_graph

def test_p_posterior_appears_in_graph(tmp_path):
    layout = init_workspace(tmp_path)
    layout.ledger.write_text(json.dumps({
        "claim_id": "clm-2026-000001", "canonical_text": "Hi.",
        "status": "verified", "claim_type": "fact", "confidence": 0.7,
        "p_posterior": 0.42,
        "source_spans": [{"doc_id": "d", "locator_text": "abcd"}],
        "created_at": "2026-05-11T00:00:00Z",
    }) + "\n", encoding="utf-8")
    out = project_graph(layout)
    text = out.read_text(encoding="utf-8")
    assert "p_posterior" in text or "0.42" in text
```

- [ ] **Step 2: Run, expect fail**

- [ ] **Step 3: Extend `project_graph.py`**

In the projection loop, add triples for `p_posterior` and `cc:rebuts` (counter-claim edges). Specifically: per-claim, if `p_posterior` is present, emit `<claim> tbf:pPosterior <decimal>`. Per counter-claim in `counter-claims.jsonl`, emit `<cc> a tbf:CounterClaim ; tbf:rebuts <target_claim>`.

Concretely add (mirror existing emit style):
```python
if "p_posterior" in r:
    ds.add((_claim_uri(r["claim_id"]),
            TBF.pPosterior,
            Literal(float(r["p_posterior"]), datatype=XSD.decimal)))
```

For counter-claims, read `claims/counter-claims.jsonl` if it exists, and emit:
```python
for cc in counter_claim_records:
    cc_uri = URIRef(f"{BASE}counter-claims/{quote(cc['id'])}")
    ds.add((cc_uri, RDF.type, TBF.CounterClaim))
    ds.add((cc_uri, TBF.rebuts, _claim_uri(cc["target_claim_id"])))
    ds.add((cc_uri, TBF.ccStatus, Literal(cc["status"])))
```

- [ ] **Step 4: Run, expect pass**

- [ ] **Step 5: Write the three defeasible queries**

`rebuttal-presence.rq`:
```sparql
PREFIX tbf: <https://example.org/book-knowledge#>
SELECT ?claim WHERE {
  ?claim a tbf:Claim ;
         tbf:loadBearing true ;
         tbf:supportsChapter ?chapter .
  FILTER NOT EXISTS {
    ?cc tbf:rebuts ?claim ;
        tbf:ccStatus "addressed" .
  }
  FILTER NOT EXISTS {
    ?claim tbf:axiom true .
  }
}
```

`contested-rebuttal-window.rq`:
```sparql
PREFIX tbf: <https://example.org/book-knowledge#>
SELECT ?claim ?chapter WHERE {
  ?claim a tbf:Claim ;
         tbf:status "disputed" ;
         tbf:supportsChapter ?chapter .
  FILTER NOT EXISTS {
    ?claim tbf:rebuttalWindowOk ?chapter .
  }
}
```
(`tbf:rebuttalWindowOk` is asserted by a separate post-render check in book-compose; emitting it is out of scope here. The query will fail by default until that asserter lands; that is intentional — non-blocking until Phase 4.)

`posterior-floor.rq`:
```sparql
PREFIX tbf: <https://example.org/book-knowledge#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
SELECT ?claim ?p WHERE {
  ?claim a tbf:Claim ;
         tbf:pPosterior ?p ;
         tbf:supportsChapter ?chapter .
  FILTER (?p < 0.4)
  FILTER NOT EXISTS {
    ?claim tbf:pinLowConfidence true .
  }
}
```

- [ ] **Step 6: Write `_meta.yaml`**

```yaml
rebuttal-presence:
  severity: critical
  default_satisfied: true
  exception_queries: []
contested-rebuttal-window:
  severity: important
  default_satisfied: true
  exception_queries: []
posterior-floor:
  severity: critical
  default_satisfied: true
  exception_queries: []
```

- [ ] **Step 7: Add tests**

```python
def test_defeasible_meta_yaml_loads():
    import yaml
    from pathlib import Path
    p = Path(__file__).resolve().parent.parent / "assets" / "queries" / "defeasible" / "_meta.yaml"
    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    assert "rebuttal-presence" in data
    assert data["rebuttal-presence"]["severity"] in ("critical", "important", "minor")

def test_defeasible_queries_parse():
    from pathlib import Path
    from rdflib.plugins.sparql import prepareQuery
    qdir = Path(__file__).resolve().parent.parent / "assets" / "queries" / "defeasible"
    for q in qdir.glob("*.rq"):
        prepareQuery(q.read_text(encoding="utf-8"))  # raises on syntax error
```

- [ ] **Step 8: Run, expect pass**

- [ ] **Step 9: Commit**

```bash
git add -A
git commit -m "Ship rebuttal-presence, contested-rebuttal-window, posterior-floor defeasible queries"
```

---

## Task 2.8: Defeasible query runner with non-blocking warnings

**Files:**
- Modify: `skills/book-knowledge/scripts/run_competency_queries.py`
- Modify: `skills/book-knowledge/tests/test_run_competency_queries.py`

The runner must (a) execute defeasible queries, (b) check exception queries before declaring failure, (c) emit warnings (not hard-fail) until Phase 4 flips the switch.

- [ ] **Step 1: Failing test**

```python
def test_defeasible_query_emits_warning_not_failure(tmp_path):
    from scripts.workspace import init_workspace
    from scripts.run_competency_queries import run_all
    layout = init_workspace(tmp_path)
    # Seed a load-bearing claim with no counter-claims → rebuttal-presence fires.
    import json
    layout.ledger.write_text(json.dumps({
        "claim_id": "clm-2026-000001", "canonical_text": "Bermuda fact.",
        "status": "verified", "claim_type": "fact", "confidence": 0.8,
        "source_spans": [{"doc_id": "d", "locator_text": "abcd"}],
        "created_at": "2026-05-11T00:00:00Z",
        "load_bearing": True, "supports_chapters": ["ch07"]
    }) + "\n", encoding="utf-8")
    # Project the graph first.
    from scripts.project_graph import project_graph
    project_graph(layout)
    result = run_all(tmp_path)
    assert result["exit_code"] == 0  # warnings, not failure
    assert any(w["query"] == "rebuttal-presence" for w in result["warnings"])
```

- [ ] **Step 2: Run, expect fail**

- [ ] **Step 3: Implement defeasible classification**

Adjust `run_all` (or whatever the existing entry is) so that:
- coverage and consistency queries continue to hard-fail.
- defeasible queries fire as warnings; the `_meta.yaml` `severity` is recorded but does not yet escalate to failure. This becomes blocking in Phase 4 by changing one default.

Add a `BLOCKING_DEFEASIBLE` constant at the top of the module, default `False`. When True, severity=critical defeasible queries that fire (and whose exception queries return empty) escalate to failure.

- [ ] **Step 4: Run, expect pass**

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "Run defeasible queries as warnings; gate behind BLOCKING_DEFEASIBLE flag"
```

---

## Task 2.9: book-compose contract loader reads counter-claims as must-address

**Files:**
- Modify: `skills/book-compose/scripts/load_contract.py` (engineer locates exact file)
- Modify: corresponding test in `skills/book-compose/tests/`

The engineer must first locate the contract loader. `grep -rn "must_include\|must-include\|acceptance_tests" skills/book-compose/scripts/` is a good starting query.

- [ ] **Step 1: Locate contract loader**

Run:
```
grep -rn "contract" skills/book-compose/scripts/ | head -20
```
Identify the function that parses contract YAML and emits the chapter's draft brief.

- [ ] **Step 2: Failing test**

In the matching test file, add:
```python
def test_contract_loader_emits_must_address_from_counter_claims(tmp_path):
    # Set up a workspace, ledger with a load-bearing claim, counter-claims.jsonl,
    # and a contract that references the claim.
    # Assert that the loader returns must_address entries for each open
    # counter-claim whose target is cited by the chapter.
    ...
```
(Fill in concrete fixtures matching the existing test style.)

- [ ] **Step 3: Implement**

In the contract loader, after parsing the YAML, read `counter-claims.jsonl` and emit:
```python
must_address = [
    {"counter_claim_id": cc["id"], "text": cc["text"],
     "target_claim_id": cc["target_claim_id"]}
    for cc in read_counter_claims(workspace_root)
    if cc["status"] == "open"
    and cc["target_claim_id"] in chapter_referenced_claim_ids
]
```
Attach `must_address` to the brief that book-compose hands to the chapter-draft agent.

- [ ] **Step 4: Run tests in book-compose**

```
.venv\Scripts\python.exe -m pytest tests/ -v
```

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "Contract loader emits must_address entries from open counter-claims"
```

---

## Task 2.10: Documentation pass for Phase 2

**Files:**
- Modify: `skills/book-knowledge/SKILL.md`
- Modify: `skills/book-compose/SKILL.md` (only if it documents contracts)

- [ ] **Step 1: Edit book-knowledge SKILL.md**

Under **Components** → **Claim ledger:**, add:
```
- `counter_claims.py` — schema + I/O for counter-claims.jsonl
- `generate_counter_claims.py` — abductive counter-claim generator
- `promote_addressed.py` — promote counter-claims to addressed
```

Under **Components** → **RDF graph, SHACL, SPARQL:**, change:
```
- `run_competency_queries.py` — runs queries from coverage/, consistency/, and defeasible/
```

Under **Usage**, append:
```
.venv\Scripts\python.exe -m scripts.generate_counter_claims <workspace>
```

- [ ] **Step 2: Commit**

```bash
git add skills/book-knowledge/SKILL.md skills/book-compose/SKILL.md
git commit -m "Document counter-claim helpers and defeasible query classes"
```

---

# PHASE 3 — Writeback adapter (~4 days)

Goal: book-qa proposes ledger transitions from defect tickets; book-knowledge applies them; the ledger now closes its loop.

## Task 3.1: events.jsonl writer

**Files:**
- Create: `skills/book-knowledge/scripts/events_log.py`
- Create: `skills/book-knowledge/assets/events.schema.json`
- Test: `skills/book-knowledge/tests/test_events_log.py`

- [ ] **Step 1: Failing test**

```python
# tests/test_events_log.py
import json
from scripts.workspace import init_workspace
from scripts.events_log import append_event, read_events, EventError
import pytest

def test_append_event(tmp_path):
    init_workspace(tmp_path)
    append_event(tmp_path, {
        "timestamp": "2026-05-11T00:00:00Z",
        "claim_id": "clm-2026-000001",
        "from": "verified", "to": "disputed",
        "cause_ticket_id": "ch07-D11-04",
        "cause_class": "unsupported_claim",
        "operator": "charles@host",
    })
    events = read_events(tmp_path)
    assert events[0]["to"] == "disputed"

def test_invalid_state_rejected(tmp_path):
    init_workspace(tmp_path)
    with pytest.raises(EventError):
        append_event(tmp_path, {
            "timestamp": "2026-05-11T00:00:00Z",
            "claim_id": "clm-2026-000001",
            "from": "verified", "to": "not-a-state",
            "cause_ticket_id": "x", "cause_class": "y", "operator": "z",
        })
```

- [ ] **Step 2: Run, expect fail**

- [ ] **Step 3: Schema**

`assets/events.schema.json`:
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "ledger-event",
  "type": "object",
  "required": ["timestamp","claim_id","from","to","cause_ticket_id","cause_class","operator"],
  "properties": {
    "timestamp":       {"type":"string","format":"date-time"},
    "claim_id":        {"type":"string","pattern":"^clm-[0-9]{4}-[0-9]{6}$"},
    "from":            {"enum":["proposed","verified","disputed","superseded","refuted"]},
    "to":              {"enum":["proposed","verified","disputed","superseded","refuted"]},
    "cause_ticket_id": {"type":"string"},
    "cause_class":     {"type":"string"},
    "operator":        {"type":"string"}
  },
  "additionalProperties": false
}
```

- [ ] **Step 4: Implement**

```python
"""Append-only state-transition log for the claim ledger."""
from __future__ import annotations
import json
from pathlib import Path
import jsonschema

from .workspace import WorkspaceLayout

ASSETS = Path(__file__).resolve().parent.parent / "assets"
SCHEMA = json.loads((ASSETS / "events.schema.json").read_text(encoding="utf-8"))


class EventError(Exception):
    pass


def _path(root: Path) -> Path:
    return WorkspaceLayout.for_root(root).root / "claims" / "events.jsonl"


def append_event(workspace_root: Path, event: dict) -> None:
    try:
        jsonschema.validate(event, SCHEMA)
    except jsonschema.ValidationError as e:
        raise EventError(str(e)) from e
    p = _path(workspace_root)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, sort_keys=True) + "\n")


def read_events(workspace_root: Path) -> list[dict]:
    p = _path(workspace_root)
    if not p.exists():
        return []
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]
```

- [ ] **Step 5: Run, expect pass**

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "Add events.jsonl schema and append/read helpers"
```

---

## Task 3.2: ledger.transition_status writes an event

**Files:**
- Modify: `skills/book-knowledge/scripts/ledger.py`
- Modify: `skills/book-knowledge/tests/test_ledger.py`

- [ ] **Step 1: Failing test**

```python
def test_transition_status_writes_event(tmp_path):
    from scripts.workspace import init_workspace
    from scripts.ledger import append_claim, transition_status
    from scripts.events_log import read_events
    init_workspace(tmp_path)
    base = {"claim_id": "clm-2026-000001", "canonical_text": "Hi text.",
            "status": "verified", "claim_type": "fact", "confidence": 0.7,
            "source_spans": [{"doc_id": "d", "locator_text": "abcd"}],
            "created_at": "2026-05-11T00:00:00Z"}
    append_claim(tmp_path, base)
    transition_status(tmp_path, "clm-2026-000001", "disputed",
                      cause_ticket_id="ch07-D11-04",
                      cause_class="unsupported_claim",
                      operator="charles@host")
    events = read_events(tmp_path)
    assert events[0]["from"] == "verified"
    assert events[0]["to"] == "disputed"
    assert events[0]["cause_ticket_id"] == "ch07-D11-04"
```

- [ ] **Step 2: Run, expect fail**

- [ ] **Step 3: Modify `transition_status`**

Extend the signature:
```python
def transition_status(layout: WorkspaceLayout | Path, claim_id: str, new_status: str,
                      cause_ticket_id: str = "manual",
                      cause_class: str = "manual",
                      operator: str = "unknown",
                      note: str = "") -> dict:
```
After validating the transition and writing the new claim record, append an event via `events_log.append_event`. Also reset `p_prior` to `prior_for_status(new_status)` in the new record so propagation picks it up.

If the existing tests pass a positional `layout` object, retain the `WorkspaceLayout` overload but also accept a `Path` for new callers. (Use `isinstance(layout_or_root, Path)` to branch.)

- [ ] **Step 4: Run, expect pass (existing tests + new test)**

- [ ] **Step 5: Commit**

```bash
git commit -am "Emit events on transition_status and reset p_prior on status change"
```

---

## Task 3.3: Define ticket → transition mapping

**Files:**
- Create: `skills/book-qa/scripts/transition_rules.py`
- Test: `skills/book-qa/tests/test_transition_rules.py`

- [ ] **Step 1: Failing test**

```python
# tests/test_transition_rules.py
from scripts.transition_rules import map_ticket_to_proposed_transition


def _ticket(class_, **kw):
    return {"class": class_, "id": kw.pop("id", "tkt-1"), **kw}


def test_unsupported_claim_maps_to_disputed():
    t = _ticket("unsupported_claim", claim_id="clm-2026-000001",
                claim_current_status="verified")
    out = map_ticket_to_proposed_transition(t)
    assert out["from"] == "verified"
    assert out["to"] == "disputed"


def test_refuted_by_new_source_maps_to_refuted():
    t = _ticket("refuted_by_new_source", claim_id="clm-2026-000001",
                claim_current_status="disputed")
    out = map_ticket_to_proposed_transition(t)
    assert out["from"] == "disputed"
    assert out["to"] == "refuted"


def test_addressed_rival_returns_counter_claim_action():
    t = _ticket("addressed_rival", counter_claim_id="cc-2026-abcdef",
                chapter_id="ch07")
    out = map_ticket_to_proposed_transition(t)
    assert out["kind"] == "counter_claim"
    assert out["counter_claim_id"] == "cc-2026-abcdef"
    assert out["new_status"] == "addressed"


def test_unknown_class_returns_none():
    assert map_ticket_to_proposed_transition({"class": "unknown"}) is None


def test_unsupported_on_already_disputed_skips():
    t = _ticket("unsupported_claim", claim_id="clm-2026-000001",
                claim_current_status="disputed")
    assert map_ticket_to_proposed_transition(t) is None  # already disputed; no-op
```

- [ ] **Step 2: Run, expect fail**

- [ ] **Step 3: Implement**

```python
"""Pure mapping from QA defect ticket → proposed ledger transition."""


def map_ticket_to_proposed_transition(ticket: dict) -> dict | None:
    cls = ticket.get("class")
    if cls == "unsupported_claim":
        if ticket.get("claim_current_status") != "verified":
            return None
        return {"kind": "claim", "claim_id": ticket["claim_id"],
                "from": "verified", "to": "disputed",
                "cause_ticket_id": ticket["id"], "cause_class": cls}
    if cls == "refuted_by_new_source":
        if ticket.get("claim_current_status") != "disputed":
            return None
        return {"kind": "claim", "claim_id": ticket["claim_id"],
                "from": "disputed", "to": "refuted",
                "cause_ticket_id": ticket["id"], "cause_class": cls}
    if cls == "addressed_rival":
        return {"kind": "counter_claim",
                "counter_claim_id": ticket["counter_claim_id"],
                "new_status": "addressed",
                "chapter_id": ticket.get("chapter_id"),
                "cause_ticket_id": ticket["id"], "cause_class": cls}
    return None
```

- [ ] **Step 4: Run, expect pass**

- [ ] **Step 5: Commit**

```bash
git add skills/book-qa/scripts/transition_rules.py \
        skills/book-qa/tests/test_transition_rules.py
git commit -m "Add ticket-to-proposed-transition mapping rules"
```

---

## Task 3.4: propose_writeback.py entrypoint

**Files:**
- Create: `skills/book-qa/scripts/propose_writeback.py`
- Test: `skills/book-qa/tests/test_propose_writeback.py`

- [ ] **Step 1: Failing test**

```python
# tests/test_propose_writeback.py
import json
from pathlib import Path
from scripts.propose_writeback import propose_writeback


def test_writes_proposed_transitions_and_md(tmp_path):
    ws = tmp_path / "ws"
    (ws / "qa").mkdir(parents=True)
    (ws / "claims").mkdir(parents=True)
    (ws / "qa" / "lint-findings.json").write_text(json.dumps({"tickets": [
        {"id": "ch07-D11-04", "class": "unsupported_claim",
         "claim_id": "clm-2026-000001", "claim_current_status": "verified",
         "severity": "critical"}
    ]}), encoding="utf-8")
    (ws / "qa" / "swarm-findings.json").write_text(json.dumps({"tickets": [
        {"id": "ch07-C12-02", "class": "addressed_rival",
         "counter_claim_id": "cc-2026-abcdef", "chapter_id": "ch07",
         "severity": "important"}
    ]}), encoding="utf-8")
    out = propose_writeback(ws, version="v5")
    proposed = (ws / "claims" / "proposed-transitions.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(proposed) == 2
    md = (ws / "qa" / "ledger-writeback-v5.md").read_text(encoding="utf-8")
    assert "clm-2026-000001" in md
    assert "cc-2026-abcdef" in md
```

- [ ] **Step 2: Run, expect fail**

- [ ] **Step 3: Implement**

```python
"""Read QA tickets, propose ledger transitions; write to claims/ and qa/ reports."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Iterable

from .transition_rules import map_ticket_to_proposed_transition


def _load_tickets(qa_dir: Path) -> list[dict]:
    tickets: list[dict] = []
    for name in ("lint-findings.json", "swarm-findings.json"):
        p = qa_dir / name
        if not p.exists():
            continue
        payload = json.loads(p.read_text(encoding="utf-8"))
        tickets.extend(payload.get("tickets", []))
    return tickets


def propose_writeback(workspace_root: Path, version: str) -> Path:
    qa_dir = workspace_root / "qa"
    claims_dir = workspace_root / "claims"
    claims_dir.mkdir(parents=True, exist_ok=True)
    tickets = _load_tickets(qa_dir)
    proposed: list[dict] = []
    for t in tickets:
        m = map_ticket_to_proposed_transition(t)
        if m is not None:
            m["severity"] = t.get("severity", "important")
            proposed.append(m)
    out_jsonl = claims_dir / "proposed-transitions.jsonl"
    with out_jsonl.open("w", encoding="utf-8") as fh:
        for p in proposed:
            fh.write(json.dumps(p, sort_keys=True) + "\n")
    md_lines = [f"# Ledger writeback proposals — {version}", "",
                f"Total: {len(proposed)} proposed transition(s).", ""]
    md_lines.append("| kind | target | from→to / new_status | ticket | severity |")
    md_lines.append("|---|---|---|---|---|")
    for p in proposed:
        if p["kind"] == "claim":
            md_lines.append(f"| claim | {p['claim_id']} | {p['from']}→{p['to']} | {p['cause_ticket_id']} | {p['severity']} |")
        else:
            md_lines.append(f"| counter_claim | {p['counter_claim_id']} | →{p['new_status']} | {p['cause_ticket_id']} | {p['severity']} |")
    out_md = qa_dir / f"ledger-writeback-{version}.md"
    out_md.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    return out_md
```

- [ ] **Step 4: Run, expect pass**

- [ ] **Step 5: Commit**

```bash
git add skills/book-qa/scripts/propose_writeback.py \
        skills/book-qa/tests/test_propose_writeback.py
git commit -m "Add propose_writeback entrypoint emitting proposed-transitions and md report"
```

---

## Task 3.5: apply_writeback.py in book-knowledge

**Files:**
- Create: `skills/book-knowledge/scripts/apply_writeback.py`
- Test: `skills/book-knowledge/tests/test_apply_writeback.py`

- [ ] **Step 1: Failing test**

```python
# tests/test_apply_writeback.py
import json
import getpass
from pathlib import Path
from scripts.workspace import init_workspace
from scripts.ledger import append_claim
from scripts.counter_claims import append_counter_claim
from scripts.apply_writeback import apply_writeback
from scripts.events_log import read_events
from scripts.counter_claims import read_counter_claims


def test_apply_writeback_propose_only_default(tmp_path):
    layout = init_workspace(tmp_path)
    append_claim(tmp_path, {"claim_id": "clm-2026-000001", "canonical_text": "Hi text.",
                            "status": "verified", "claim_type": "fact", "confidence": 0.7,
                            "source_spans": [{"doc_id":"d","locator_text":"abcd"}],
                            "created_at": "2026-05-11T00:00:00Z"})
    (tmp_path / "claims" / "proposed-transitions.jsonl").write_text(json.dumps({
        "kind": "claim", "claim_id": "clm-2026-000001",
        "from": "verified", "to": "disputed",
        "cause_ticket_id": "tkt-1", "cause_class": "unsupported_claim",
        "severity": "critical"
    }) + "\n", encoding="utf-8")
    summary = apply_writeback(tmp_path, auto_apply=False)
    # Propose-only: nothing applied.
    assert summary["applied"] == 0
    assert summary["proposed"] == 1
    assert read_events(tmp_path) == []


def test_apply_writeback_auto_apply_critical(tmp_path):
    layout = init_workspace(tmp_path)
    append_claim(tmp_path, {"claim_id": "clm-2026-000001", "canonical_text": "Hi text.",
                            "status": "verified", "claim_type": "fact", "confidence": 0.7,
                            "source_spans": [{"doc_id":"d","locator_text":"abcd"}],
                            "created_at": "2026-05-11T00:00:00Z"})
    (tmp_path / "claims" / "proposed-transitions.jsonl").write_text(json.dumps({
        "kind": "claim", "claim_id": "clm-2026-000001",
        "from": "verified", "to": "disputed",
        "cause_ticket_id": "tkt-1", "cause_class": "unsupported_claim",
        "severity": "critical"
    }) + "\n", encoding="utf-8")
    summary = apply_writeback(tmp_path, auto_apply=True)
    assert summary["applied"] == 1
    events = read_events(tmp_path)
    assert events[-1]["to"] == "disputed"


def test_apply_writeback_skips_non_critical_in_auto(tmp_path):
    layout = init_workspace(tmp_path)
    append_claim(tmp_path, {"claim_id": "clm-2026-000001", "canonical_text": "Hi text.",
                            "status": "verified", "claim_type": "fact", "confidence": 0.7,
                            "source_spans": [{"doc_id":"d","locator_text":"abcd"}],
                            "created_at": "2026-05-11T00:00:00Z"})
    (tmp_path / "claims" / "proposed-transitions.jsonl").write_text(json.dumps({
        "kind": "claim", "claim_id": "clm-2026-000001",
        "from": "verified", "to": "disputed",
        "cause_ticket_id": "tkt-1", "cause_class": "unsupported_claim",
        "severity": "important"
    }) + "\n", encoding="utf-8")
    summary = apply_writeback(tmp_path, auto_apply=True)
    assert summary["applied"] == 0  # only critical auto-applies
```

- [ ] **Step 2: Run, expect fail**

- [ ] **Step 3: Implement**

```python
"""Apply proposed transitions emitted by book-qa propose_writeback."""
from __future__ import annotations
import getpass
import json
from datetime import datetime, timezone
from pathlib import Path

from .ledger import transition_status
from .counter_claims import append_counter_claim, read_counter_claims
from .workspace import WorkspaceLayout


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _operator() -> str:
    try:
        user = getpass.getuser()
    except Exception:
        user = "unknown"
    return f"{user}@apply_writeback"


def apply_writeback(workspace_root: Path, auto_apply: bool = False) -> dict:
    layout = WorkspaceLayout.for_root(workspace_root)
    pt = layout.root / "claims" / "proposed-transitions.jsonl"
    if not pt.exists():
        return {"proposed": 0, "applied": 0}
    proposed: list[dict] = []
    for line in pt.read_text(encoding="utf-8").splitlines():
        if line.strip():
            proposed.append(json.loads(line))
    applied = 0
    op = _operator()
    for p in proposed:
        if not auto_apply:
            continue
        # Auto-apply rule: claim transitions of severity=critical from
        # deterministic ticket classes (D11 = unsupported_claim).
        if p["kind"] == "claim":
            if p.get("severity") != "critical":
                continue
            if p.get("cause_class") != "unsupported_claim":
                continue
            transition_status(
                workspace_root, p["claim_id"], p["to"],
                cause_ticket_id=p["cause_ticket_id"],
                cause_class=p["cause_class"],
                operator=op,
            )
            applied += 1
        elif p["kind"] == "counter_claim":
            existing = [c for c in read_counter_claims(workspace_root)
                        if c["id"] == p["counter_claim_id"]]
            if not existing:
                continue
            new = dict(existing[-1])
            new["status"] = p["new_status"]
            new["addressed_in_chapter"] = p.get("chapter_id")
            append_counter_claim(workspace_root, new)
            applied += 1
    return {"proposed": len(proposed), "applied": applied}
```

- [ ] **Step 4: Run, expect pass**

- [ ] **Step 5: Commit**

```bash
git add skills/book-knowledge/scripts/apply_writeback.py \
        skills/book-knowledge/tests/test_apply_writeback.py
git commit -m "Add apply_writeback with propose-only default and auto-apply for critical D11"
```

---

## Task 3.6: book-compose excludes refuted (and optionally disputed) from default slice

**Files:**
- Modify: book-compose's ledger-slice loader (engineer locates)
- Modify: corresponding test

- [ ] **Step 1: Locate ledger slice**

```
grep -rn "verified\|status" skills/book-compose/scripts/ | grep -i "claim\|ledger" | head
```
Identify the function that selects which claims feed a chapter draft.

- [ ] **Step 2: Failing test**

```python
def test_slice_excludes_refuted_by_default(tmp_path):
    # Seed ledger with a verified claim and a refuted claim, both referenced by chapter ch07.
    # Call the slice function; assert refuted is absent.
    ...

def test_slice_includes_refuted_when_pinned(tmp_path):
    # Seed same; contract says force_include_refuted: [clm-2026-000002].
    # Assert refuted claim is present.
    ...
```

- [ ] **Step 3: Implement**

In the slice function:
```python
def slice_for_chapter(workspace_root, chapter_id, contract):
    all_records = _latest_per_claim(read_claims(...))
    force_include = set(contract.get("force_include_refuted", []))
    out = []
    for r in all_records.values():
        if chapter_id not in r.get("supports_chapters", []):
            continue
        if r["status"] == "refuted" and r["claim_id"] not in force_include:
            continue
        # Optionally drop disputed unless contract explicitly accepts:
        if r["status"] == "disputed" and not contract.get("accept_disputed", False):
            continue
        out.append(r)
    return out
```

- [ ] **Step 4: Run book-compose tests**

```
.venv\Scripts\python.exe -m pytest tests/ -v
```

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "Exclude refuted (and by default disputed) claims from chapter slice; honor force_include_refuted"
```

---

## Task 3.7: Wire propose_writeback into book-qa Sentinel stage

**Files:**
- Modify: book-qa's Sentinel script (locate via SKILL.md: `scripts/sentinel.py`)
- Modify: book-qa tests

- [ ] **Step 1: Locate**

```
grep -rn "sentinel" skills/book-qa/scripts/ | head
```

- [ ] **Step 2: Failing test**

Add a test that runs the Sentinel step on a fixture and asserts the post-Sentinel state includes `claims/proposed-transitions.jsonl` and `qa/ledger-writeback-<version>.md`.

- [ ] **Step 3: Implement**

After the Sentinel aggregation step, call:
```python
from .propose_writeback import propose_writeback
propose_writeback(workspace_root, version=current_version)
```

- [ ] **Step 4: Run**

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "Sentinel calls propose_writeback after aggregation"
```

---

## Task 3.8: Documentation pass for Phase 3

**Files:**
- Modify: `skills/book-knowledge/SKILL.md`
- Modify: `skills/book-qa/SKILL.md`

- [ ] **Step 1: book-knowledge SKILL.md**

Under **Components** → **Claim ledger:**, add:
```
- `apply_writeback.py` — applies QA-proposed ledger transitions; default propose-only, --auto-apply for critical D11
- `events_log.py` — append-only state-transition log (claims/events.jsonl)
```

Under **Release gate:**, append:
```
After writeback proposals from book-qa, run:
  .venv\Scripts\python.exe -m scripts.apply_writeback <workspace> --auto-apply
to commit deterministic critical transitions; review qa/ledger-writeback-<version>.md before applying others.
```

- [ ] **Step 2: book-qa SKILL.md**

Add under the architecture diagram, after step 3 (Sentinel):
```
After Sentinel: propose_writeback.py emits claims/proposed-transitions.jsonl
and qa/ledger-writeback-<version>.md. book-knowledge.apply_writeback applies them.
```

- [ ] **Step 3: Commit**

```bash
git add skills/book-knowledge/SKILL.md skills/book-qa/SKILL.md
git commit -m "Document writeback adapter across book-knowledge and book-qa"
```

---

# PHASE 4 — Bermuda re-build, tune, promote (~2 days)

Goal: prove out Bundle C end-to-end on the Bermuda manuscript and flip defeasible queries from warning to hard-gate.

## Task 4.1: Tag bermuda load-bearing claims

**Files:**
- Modify: `examples/bermuda-manual/claims/ledger.jsonl` (one-shot edit)

- [ ] **Step 1: Identify load-bearing claims**

Read each `chapters/contracts/ch-NN.yaml` for the Bermuda book; record which claims each contract names as load-bearing in its prose-must-cite list. For Phase 4 simplicity, treat any claim cited by two or more chapter contracts as load-bearing.

- [ ] **Step 2: One-shot script**

Create `tools/tag_load_bearing.py` (this is a one-shot tool, not a long-lived skill script):
```python
"""One-shot: mark claims as load_bearing=true based on cross-chapter citations."""
import json, sys
from pathlib import Path

ws = Path(sys.argv[1])
ledger = ws / "claims" / "ledger.jsonl"
records = [json.loads(l) for l in ledger.read_text(encoding="utf-8").splitlines() if l.strip()]
# Tally chapter references per claim.
from collections import Counter
counts: Counter[str] = Counter()
for r in records:
    for ch in r.get("supports_chapters", []):
        counts[r["claim_id"]] += 1
# Append load_bearing=true records for claims cited >= 2 chapters.
load_bearing = {cid for cid, n in counts.items() if n >= 2}
# Append updated records.
latest = {r["claim_id"]: r for r in records}
with ledger.open("a", encoding="utf-8") as fh:
    for cid in load_bearing:
        if not latest[cid].get("load_bearing"):
            updated = dict(latest[cid])
            updated["load_bearing"] = True
            fh.write(json.dumps(updated, sort_keys=True) + "\n")
print(f"tagged {len(load_bearing)} claims as load_bearing")
```

- [ ] **Step 3: Run**

```
python tools/tag_load_bearing.py examples/bermuda-manual
```

- [ ] **Step 4: Commit (one-shot tool + ledger update)**

```bash
git add tools/tag_load_bearing.py examples/bermuda-manual/claims/ledger.jsonl
git commit -m "Tag bermuda load-bearing claims (>=2 chapter citations)"
```

---

## Task 4.2: Generate counter-claims for bermuda

**Files:**
- Run: `skills/book-knowledge/scripts/generate_counter_claims.py` against the Bermuda workspace using the real LLM call

- [ ] **Step 1: Wire up the live LLM call**

The skill's existing pattern for LLM calls is via Claude Code's `Skill` / `Agent` invocation. For this one run, write a tiny adapter `tools/run_counter_claim_gen.py` that uses whatever Claude Code agent dispatch path the other skills use to call the model. (Engineer reads `skills/book-knowledge/scripts/` for any LLM-invocation pattern that already exists; if none does, this run uses a manual paste-through: write each prompt to a file under `/tmp/cc-prompts/<claim_id>.txt`, run Claude Code on each, paste JSON back to a parallel `<claim_id>.json`, and write a small reader that calls `generate_for_claim(..., llm_call=lambda p: Path(f"/tmp/cc-prompts/{claim_id}.json").read_text())`.)

- [ ] **Step 2: Run generation**

```
.venv\Scripts\python.exe tools/run_counter_claim_gen.py examples/bermuda-manual
```

- [ ] **Step 3: Inspect output**

```
wc -l examples/bermuda-manual/claims/counter-claims.jsonl
```
Expected: 2–3 records per load-bearing claim.

- [ ] **Step 4: Commit**

```bash
git add tools/run_counter_claim_gen.py examples/bermuda-manual/claims/counter-claims.jsonl
git commit -m "Generate abductive counter-claims for bermuda load-bearing claims"
```

---

## Task 4.3: Run belief propagation and inspect histogram

**Files:**
- Run: `.venv\Scripts\python.exe -m scripts.propagate_belief examples/bermuda-manual`

- [ ] **Step 1: Run**

```
.venv\Scripts\python.exe -m scripts.propagate_belief examples/bermuda-manual
```

- [ ] **Step 2: Inspect the report**

Open the latest `examples/bermuda-manual/graph/reports/belief-propagation-*.md`. Look at:
- The top-20 deltas — are any claims dropping below 0.4 unexpectedly?
- The histogram — is the distribution clustering at the floor 0.05 or ceil 0.95? If so, the damping factors need tuning.

- [ ] **Step 3: Tune (if needed)**

If load-bearing claims with several open counter-claims drop too far, increase `COUNTER_OPEN_DAMP` toward 0.97. If addressed counter-claims do not damp enough, lower `COUNTER_ADDRESSED_DAMP` toward 0.80. Commit the tuned constants with a `tune:` prefix in the commit message and a one-liner explaining the chosen values.

```bash
git commit -am "Tune counter-claim damping after bermuda re-run (open=0.97, addressed=0.83)"
```

---

## Task 4.4: Rebuild Bermuda and observe must-address coverage

**Files:**
- Run: book-compose's full build pipeline on `examples/bermuda-manual`

- [ ] **Step 1: Build**

```
.venv\Scripts\python.exe -m scripts.build_book examples/bermuda-manual --version v6
```
(Exact command depends on book-compose's CLI; engineer locates.)

- [ ] **Step 2: Verify must-address surfaced**

Each chapter brief used during draft must include `must_address` entries for the open counter-claims of cited load-bearing claims. The chapter draft pipeline should log these. Check `examples/bermuda-manual/reports/V6.md` (or equivalent) for a per-chapter summary of addressed-vs-open counter-claims.

- [ ] **Step 3: Verify writeback proposals exist**

After QA stage:
```
ls examples/bermuda-manual/claims/proposed-transitions.jsonl
ls examples/bermuda-manual/qa/ledger-writeback-v6.md
```

- [ ] **Step 4: Commit any updated reports**

```bash
git add examples/bermuda-manual/reports/V6.md \
        examples/bermuda-manual/qa/ledger-writeback-v6.md \
        examples/bermuda-manual/qa/swarm-findings.md
git commit -m "Bermuda v6 build with Bundle C enabled"
```

---

## Task 4.5: Promote defeasible queries to hard-gate

**Files:**
- Modify: `skills/book-knowledge/scripts/run_competency_queries.py`
- Modify: `skills/book-knowledge/tests/test_run_competency_queries.py`

- [ ] **Step 1: Failing test**

```python
def test_blocking_defeasible_flag_escalates_critical(tmp_path):
    from scripts.workspace import init_workspace
    from scripts.run_competency_queries import run_all
    import scripts.run_competency_queries as mod
    layout = init_workspace(tmp_path)
    # Seed a state that fires rebuttal-presence (load-bearing claim, no addressed cc).
    ...
    mod.BLOCKING_DEFEASIBLE = True
    result = run_all(tmp_path)
    assert result["exit_code"] != 0
    assert any(f["query"] == "rebuttal-presence" for f in result["failures"])
```

- [ ] **Step 2: Run, expect fail**

- [ ] **Step 3: Flip the default**

In `run_competency_queries.py`, change:
```python
BLOCKING_DEFEASIBLE = False
```
to:
```python
BLOCKING_DEFEASIBLE = True
```
Confirm `run_all` consults this flag and escalates `severity: critical` defeasible fires to failures, while `severity: important` remains warnings.

- [ ] **Step 4: Run, expect pass**

- [ ] **Step 5: Commit**

```bash
git commit -am "Promote defeasible queries to hard-gate (BLOCKING_DEFEASIBLE=True)"
```

---

## Task 4.6: Add acceptance-test integration test

**Files:**
- Create: `skills/book-knowledge/tests/test_bundle_c_integration.py`

This is the end-to-end test that closes the loop on the spec's acceptance criteria.

- [ ] **Step 1: Write integration test**

```python
"""End-to-end: plant a bad claim, run QA, apply writeback, rebuild, observe exclusion."""
import json
from pathlib import Path

from scripts.workspace import init_workspace
from scripts.ledger import append_claim
from scripts.counter_claims import append_counter_claim
from scripts.apply_writeback import apply_writeback


def test_bad_claim_progression(tmp_path):
    init_workspace(tmp_path)
    append_claim(tmp_path, {
        "claim_id": "clm-2026-000001",
        "canonical_text": "A claim that the QA will later find unsupported.",
        "status": "verified", "claim_type": "fact", "confidence": 0.8,
        "source_spans": [{"doc_id": "d", "locator_text": "ZZZZ"}],
        "supports_chapters": ["ch01"],
        "load_bearing": True,
        "created_at": "2026-05-11T00:00:00Z",
    })
    # Round 1: book-qa produces an unsupported_claim ticket.
    (tmp_path / "qa").mkdir(parents=True, exist_ok=True)
    (tmp_path / "qa" / "lint-findings.json").write_text(json.dumps({"tickets": [
        {"id": "ch01-D11-01", "class": "unsupported_claim",
         "claim_id": "clm-2026-000001", "claim_current_status": "verified",
         "severity": "critical"}
    ]}), encoding="utf-8")
    from scripts.propose_writeback import propose_writeback as pw  # imported from book-qa path; adjust import as needed
    # In practice, run via subprocess into the book-qa skill; here we shim with a direct call.
    # ... (engineer chooses whether to subprocess or import-shim).

    apply_writeback(tmp_path, auto_apply=True)
    # Round 2: same QA finding now upgrades disputed → refuted.
    (tmp_path / "qa" / "lint-findings.json").write_text(json.dumps({"tickets": [
        {"id": "ch01-D11-02", "class": "refuted_by_new_source",
         "claim_id": "clm-2026-000001", "claim_current_status": "disputed",
         "severity": "critical"}
    ]}), encoding="utf-8")
    # ... propose, apply ...
    apply_writeback(tmp_path, auto_apply=True)

    # Final state: claim is refuted.
    from scripts.belief_graph import load_belief_graph
    bg = load_belief_graph(tmp_path)
    assert bg.nodes["clm-2026-000001"].status == "refuted"
```

- [ ] **Step 2: Run, expect pass after wiring the subprocess / import shim**

- [ ] **Step 3: Commit**

```bash
git add skills/book-knowledge/tests/test_bundle_c_integration.py
git commit -m "Add Bundle C end-to-end integration test (verified → disputed → refuted)"
```

---

# Self-review checklist

The engineer working this plan should run this after Phase 4:

- [ ] All eight spec acceptance criteria observable on the bermuda v6 build report.
- [ ] No test in any of the three modified skills was marked `xfail` or skipped to land Bundle C.
- [ ] `git log --oneline --since=2026-05-11` shows roughly 30–40 commits with terse messages, no AI attribution.
- [ ] Regression: rebuilding bermuda without invoking any Bundle C entrypoint (skip `propagate_belief`, `generate_counter_claims`, `apply_writeback`; leave the new queries in `defeasible/` since they are warning-only at first) produces the same QA D1–D8 result as v5. Note: the PDF will diff if any chapter prose has changed for non-Bundle-C reasons; check QA exit code and D1–D8 ticket count, not byte-identity.
- [ ] `apply_writeback.py` mutates `claims/` only when `--auto-apply` is passed or after explicit operator confirmation in interactive mode.
- [ ] Counter-claims for any single load-bearing claim cap at 3.

---

# Open-question deferrals

Items raised during planning but kept out of scope:

- **OpenStreetMap-style trust scoring per source.** Spec uses a flat `trust: float` in source manifests; if you need provenance per-paragraph rather than per-source, that is a separate change.
- **Counter-claim regeneration on claim revision.** Currently a counter-claim is invalidated by claim version hash; the *regeneration* trigger is operator-driven. An automatic regen-on-edit hook is straightforward but deferred.
- **UI for proposed-transition review.** CLI/markdown only for v1.

Spec is at `docs/specs/2026-05-11-bundle-c-closed-loop-ledger-design.md`. Open questions and risks recorded there are not duplicated here.

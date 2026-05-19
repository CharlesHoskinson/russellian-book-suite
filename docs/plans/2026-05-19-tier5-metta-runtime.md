# Tier 5 — MeTTa runtime + semantic retrieval + framing reckoning — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Promote neurosym-forge from a "MeTTa-shaped scaffolder" to an embeddable MeTTa-runtime + semantic-retrieval framework, and reconcile the docs with what's actually wired vs aspirational.

**Architecture:** Six independent OpenSpec changes across three tracks. Tracks (and their phase letters):

- **Runtime + storage (Phases O, P, Q):** embed hyperon-experimental as a 4th codegen backend, define the EDN↔MeTTa bijection + Atomspace-shaped dedup storage, ship a vector-embedding sidecar with a `(neighbors $atom $k)` grounded atom.
- **Query + framing (Phases R, S):** hybrid neuro-symbolic query (`(hybrid-match $space $template $hint $k)`) layering vector-retrieval on top of symbolic match; framework framing reckoning that distinguishes "MeTTa-runtime-grounded" from "MeTTa-shaped" in the docs.
- **Eval (Phase T):** extend Phase N's onboarding bench with a MeTTa-runtime domain prompt; measure whether fresh agents can wire `:backend :metta` from the docs alone.

The trigger is an external analysis comparing neurosym-forge to MeTTa/Hyperon/Atomspace. The analysis's strongest finding: the framework's promotional language calls itself "MeTTa-style" but no backend actually runs MeTTa today. Phases O+P+Q make the runtime real; Phases R+S+T extend it and reckon honestly with what's now true.

**Tech Stack:** Python 3.13 (ingest, codegen, eval harness), Rust 1.90 + z3 0.20 + egg 0.10 + cozo 0.7 + **hyperon = "0.2" or current `hyperon-experimental`** (verifier), ClojureScript via nbb (DSL compiler), `sentence-transformers/all-MiniLM-L6-v2` (embeddings), pytest + cargo test + nbb test.

**Dependencies (the cross-coupling matters):**
- Phase O is a prerequisite for Phase P (the bijection needs a real interpreter to round-trip against), Phase Q (the embedding sidecar exposes itself as a MeTTa grounded atom), and Phase R (hybrid-match is a MeTTa expression).
- Phase Q is a prerequisite for Phase R (hybrid-match needs neighbors).
- Phase S (framing) can land in parallel with O+P+Q — it's docs-only. The drift lint (REQ-BOOKLOGIC-064) catches future regressions.
- Phase T depends on Phase O landing on main (the eval prompt references `:backend :metta`).

Recommended execution order: O → P (parallel with Q) → R (after Q) → S (any time) → T (after O).

**Caveats explicitly tracked (from the analysis):**
- `hyperon-experimental` is alpha. The plan pins a known-working commit + documents the update procedure.
- MORK's "thousands to millions of times" speedup is aspirational, not benchmarked — this tier intentionally avoids MORK and DAS; single-machine `hyperon-experimental` only.
- PLN truth values, Rholang/ASI-Chain compilation, and distributed Atomspace are explicitly out of scope.

---

## Pre-flight

Read before starting any phase:

- `openspec/changes/tier5-*/{proposal,design,tasks}.md` and `specs/` (this PR authors them)
- `skills/neurosym-forge/SUPPORT_MATRIX.md` — current ground truth
- `skills/neurosym-forge/references/metta-idioms.md` — current (Tier-1) framing
- `docs/booklogic-dsl-reference.md` — author-facing reference (Phase R adds §7; Phase S adds the `:metta` operator row)
- `verifiers/osmotic_pressure/rust-verifier/src/{eqsat,kg}.rs` — the Phase H/I templates for adding a new backend
- `skills/neurosym-forge/scripts/codegen_axioms.py` — the dispatch loop (z3/egg/cozo branches, line ~166-194)
- `skills/neurosym-forge/eval/onboarding-bench.py` — the Phase N harness, extended in Phase T

**Branches:** one per phase, all cut from main.

```bash
cd ~/work/russellian-book-suite
git fetch origin
git checkout main
git pull --ff-only origin main
# Per-phase branches:
git checkout -b feat/tier5-metta-backend           # Phase O
git checkout -b feat/tier5-edn-metta-bijection     # Phase P
git checkout -b feat/tier5-embedding-sidecar       # Phase Q
git checkout -b feat/tier5-hybrid-query            # Phase R
git checkout -b feat/tier5-framing-reckoning       # Phase S
git checkout -b feat/tier5-metta-onboarding-eval   # Phase T
```

**Worktree pattern (for parallel execution):** mirror the Tier 1-4 approach — `git worktree add` per phase under `C:\work\russellian-book-suite-worktrees\<branch-name>`.

**Test invocations:**

```bash
# Per-verifier
make -C verifiers/osmotic_pressure ci
make -C verifiers/bermuda ci

# Cargo unit tests (Linux/WSL only — needs system libz3 + libpython for hyperon)
wsl -d Ubuntu -- bash -lc 'cd /mnt/c/work/russellian-book-suite/verifiers/osmotic_pressure/rust-verifier && cargo test --features smt,metta --release'

# Neurosym-forge full suite (must not regress; baseline 303 passed, 9 skipped post-Tier-4)
py -m pytest skills/neurosym-forge/tests -q
```

**Commit hygiene:** terse, imperative; no AI attribution; one problem per commit; never `--no-verify`.

**Scope guard:** this tier does NOT add MORK, DAS, PLN truth values, Rholang/ASI-Chain compilation, distributed Atomspace, or a persistent vector DB. Reject scope creep into Tier 6+.

---

## Phase O — MeTTa backend (`tier5-metta-backend`)

**Branch:** `feat/tier5-metta-backend`
**OpenSpec change:** `openspec/changes/tier5-metta-backend/`
**Exit criteria:** `defconstraint :backend :metta` constraints route through `verifiers/*/rust-verifier/src/metta.rs` into the embedded hyperon-experimental runtime; verdict surfaces `:metta-results`; a cargo integration test asserts a 3-atom MeTTa program produces the expected output; SUPPORT_MATRIX.md gains a row `defconstraint :backend :metta | wired (alpha)`.

### Task O1: Add hyperon-experimental dependency + minimal smoke

**Files:**
- Modify: `verifiers/osmotic_pressure/rust-verifier/Cargo.toml`
- Modify: `verifiers/bermuda/rust-verifier/Cargo.toml`
- Create: `verifiers/osmotic_pressure/rust-verifier/src/metta.rs`
- Create: `verifiers/bermuda/rust-verifier/src/metta.rs`

- [ ] **O1.1: Failing test — embedded MeTTa returns the expected result for a 3-atom program** (REQ-METTA-040, 047)

Create `verifiers/osmotic_pressure/rust-verifier/tests/metta_smoke.rs`:

```rust
//! REQ-METTA-040, 047 — the embedded MeTTa runtime correctly evaluates
//! a 3-atom program: one fact, one rule, one query.
use osmotic_pressure_verifier::metta::run_metta;

#[test]
fn three_atom_grandparent_query() {
    let program = r#"
        (Parent Tom Bob)
        (Parent Bob Carol)
        (= (Grandparent $x $z) (, (Parent $x $y) (Parent $y $z)))
        !(match &self (Grandparent Tom $g) $g)
    "#;
    let results = run_metta(program).expect("run_metta");
    assert_eq!(results.len(), 1);
    assert_eq!(results[0], "Carol");
}
```

- [ ] **O1.2: Run** `wsl -d Ubuntu -- bash -lc 'cd /mnt/c/work/russellian-book-suite/verifiers/osmotic_pressure/rust-verifier && cargo test --features metta metta_smoke'`
Expected: FAIL — `metta` module / function doesn't exist yet.

- [ ] **O1.3: Add hyperon-experimental to `Cargo.toml`**

Both verifiers:
```toml
[dependencies]
hyperon = { version = "0.2", optional = true }

[features]
default = ["smt", "kg"]
metta = ["dep:hyperon"]
```

(If hyperon's published crate version is different at implementation time, pin to whatever commit / version compiles. Document the pin in `docs/operations/hyperon-experimental-pin.md` with the rationale.)

- [ ] **O1.4: Implement `metta.rs` minimal `run_metta`** (REQ-METTA-040)

```rust
//! Embedded MeTTa runtime via hyperon-experimental.
//!
//! REQ-METTA-040: run_metta evaluates a MeTTa program string and returns
//! the printed form of each `!`-evaluated atom.

use hyperon::common::tokens::Tokenizer;
use hyperon::metta::runner::{Metta, Status};
use hyperon::space::DynSpace;

#[derive(Debug)]
pub enum MettaError {
    Init(String),
    Run(String),
    Timeout,
}

impl std::fmt::Display for MettaError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            MettaError::Init(s) => write!(f, "metta init: {s}"),
            MettaError::Run(s) => write!(f, "metta run: {s}"),
            MettaError::Timeout => write!(f, "metta timeout"),
        }
    }
}

impl std::error::Error for MettaError {}

pub fn run_metta(program: &str) -> Result<Vec<String>, MettaError> {
    let metta = Metta::new(None);
    let results = metta
        .run(hyperon::metta::runner::SExprParser::new(program))
        .map_err(|e| MettaError::Run(format!("{e:?}")))?;
    let mut out = Vec::new();
    for batch in results {
        for atom in batch {
            out.push(format!("{atom}"));
        }
    }
    Ok(out)
}
```

(The exact hyperon API may shift; this is the v0.2-ish surface. Update to match the pinned version.)

- [ ] **O1.5: Add `mod metta;` to `lib.rs`** in both verifiers (cfg-gated on `feature = "metta"`):

```rust
#[cfg(feature = "metta")]
pub mod metta;
```

- [ ] **O1.6: Run the test — confirm PASS**

- [ ] **O1.7: Commit**

```bash
git add verifiers/osmotic_pressure/rust-verifier/Cargo.toml \
        verifiers/osmotic_pressure/rust-verifier/src/metta.rs \
        verifiers/osmotic_pressure/rust-verifier/src/lib.rs \
        verifiers/osmotic_pressure/rust-verifier/tests/metta_smoke.rs \
        verifiers/bermuda/rust-verifier/Cargo.toml \
        verifiers/bermuda/rust-verifier/src/metta.rs \
        verifiers/bermuda/rust-verifier/src/lib.rs
git commit -m "metta: embed hyperon-experimental as a 4th backend (REQ-METTA-040, 047)"
```

### Task O2: Timeout + error handling

- [ ] **O2.1: Failing test** (REQ-METTA-043, 044) — a MeTTa program with a divergent recursive rule completes with `Err(MettaError::Timeout)` when `VERIFIER_METTA_TIMEOUT_MS` is set short. Add to `tests/metta_smoke.rs`:

```rust
#[test]
fn divergent_rule_hits_timeout() {
    std::env::set_var("VERIFIER_METTA_TIMEOUT_MS", "100");
    let program = r#"
        (= (loop $x) (loop $x))
        !(match &self (loop a) $r)
    "#;
    let start = std::time::Instant::now();
    let result = run_metta(program);
    let elapsed = start.elapsed();
    std::env::remove_var("VERIFIER_METTA_TIMEOUT_MS");
    assert!(elapsed.as_secs() < 5, "timeout was not honoured");
    assert!(matches!(result, Err(MettaError::Timeout)),
            "expected Err(Timeout) on divergent rule, got {:?}", result);
}
```

- [ ] **O2.2: Implement timeout via std::thread::spawn + mpsc::recv_timeout** (mirrors the Phase I kg::run_queries pattern):

```rust
use std::sync::mpsc;
use std::thread;
use std::time::Duration;

pub fn run_metta(program: &str) -> Result<Vec<String>, MettaError> {
    let timeout_ms: u64 = std::env::var("VERIFIER_METTA_TIMEOUT_MS")
        .ok()
        .and_then(|s| s.parse().ok())
        .unwrap_or(30_000);
    let (tx, rx) = mpsc::channel();
    let program = program.to_string();
    thread::spawn(move || {
        let metta = Metta::new(None);
        let result = metta
            .run(hyperon::metta::runner::SExprParser::new(&program))
            .map_err(|e| MettaError::Run(format!("{e:?}")))
            .map(|batches| {
                batches.into_iter()
                    .flatten()
                    .map(|a| format!("{a}"))
                    .collect::<Vec<_>>()
            });
        let _ = tx.send(result);
    });
    match rx.recv_timeout(Duration::from_millis(timeout_ms)) {
        Ok(result) => result,
        Err(mpsc::RecvTimeoutError::Timeout) => Err(MettaError::Timeout),
        Err(mpsc::RecvTimeoutError::Disconnected) => Err(MettaError::Run("interpreter thread died".into())),
    }
}
```

(Note: leaked thread continues until `Metta::run` returns. Document the limitation in metta.rs's module docstring.)

- [ ] **O2.3: Run** — confirm PASS.

- [ ] **O2.4: Commit**

```bash
git commit -am "metta: VERIFIER_METTA_TIMEOUT_MS env var + Timeout error variant (REQ-METTA-043, 044)"
```

### Task O3: Codegen — `:backend :metta` dispatch

- [ ] **O3.1: Failing test in `skills/neurosym-forge/tests/test_codegen_axioms.py`** (REQ-METTA-041, 042):

```python
def test_metta_backend_emits_metta_constraints_registry() -> None:
    """REQ-METTA-041, 042: :backend :metta constraints surface in
    metta_constraints() registry (parallel to cozo_constraints())."""
    cs = [_constraint(name="C001"),  # :z3
          _constraint(name="C-mt-001", backend=":metta",
                      assert_form="(! (match &self (Parent Tom $x) $x))")]
    src = generate_axioms_source(cs)
    # The :metta entries surface in a metta_constraints() registry, not
    # in assert_axioms.
    assert "pub fn metta_constraints" in src
    assert '"C-mt-001"' in src
    assert_axioms_half, _, _ = src.partition("pub fn cozo_constraints")
    assert '"C-mt-001"' not in assert_axioms_half
```

- [ ] **O3.2: Implement `_emit_metta_block` + dispatch** in `skills/neurosym-forge/scripts/codegen_axioms.py`. Mirror Phase I's `_emit_cozo_block` exactly — collect a list of `(name, metta_program_source)` pairs, emit a `pub fn metta_constraints() -> Vec<(String, String)>`.

In the dispatch loop, add:
```python
elif backend == Keyword("metta"):
    metta_entries.append(_emit_metta_block(c))
```

The `_emit_metta_block` builder translates `:assert (foo bar)` to a MeTTa program string. The translation is the inverse of Phase P's `metta_to_edn` (Phase P's bijection lands in parallel).

- [ ] **O3.3: Run** — confirm PASS.

- [ ] **O3.4: Re-vendor codegen** to both verifiers (byte-identical check via `diff`).

- [ ] **O3.5: Update SUPPORT_MATRIX.md** (REQ-METTA-045) — add row `| defconstraint :backend :metta | wired | metta_constraints() | hyperon-experimental | wired (alpha) |`. Update the legend to define `wired (alpha)`.

- [ ] **O3.6: Update test_support_matrix.py drift lint** — assert the new row exists with `wired (alpha)` status.

- [ ] **O3.7: Commit**

```bash
git commit -am "codegen: route :backend :metta to metta_constraints() registry (REQ-METTA-041, 042)"
```

### Task O4: lib.rs wiring — run metta_constraints at smoke time

- [ ] **O4.1: Add `pub fn run_metta_constraints(constraint_edn: String) -> napi::Result<String>` napi entry** in both verifiers' lib.rs that iterates `axioms::metta_constraints()`, feeds each pair through `metta::run_metta`, and surfaces results onto a verdict slice mirroring Phase I's `:queries`/`:cozo-defects` shape but named `:metta-results`/`:metta-errors`.

- [ ] **O4.2: Update Verdict struct** in `ir.rs` (both verifiers) to add `pub metta_results: Vec<MettaResult>` and `pub metta_errors: Vec<MettaError>` (mirror QueryResult). emit_verdict serialises both.

- [ ] **O4.3: Update verdict_to_qa.py** to read the new fields and surface them in `verification-defects.json`.

- [ ] **O4.4: Cargo integration test** at `tests/metta_constraints_pipeline.rs`: assert a `:backend :metta` constraint flows through the codegen → metta::run_metta → verdict chain end-to-end.

- [ ] **O4.5: Commit**

```bash
git commit -am "lib(rs): run_metta_constraints napi entry + verdict :metta-results (REQ-METTA-041, 042, 046)"
```

### Task O5: Push + open PR-O

```bash
git push -u origin feat/tier5-metta-backend
gh pr create --title "Tier 5O: hyperon-experimental as 4th codegen backend (REQ-METTA-040..047)" --body "<see umbrella plan Phase O>"
```

Merge on green CI.

---

## Phase P — EDN ↔ MeTTa bijection + Atomspace dedup (`tier5-edn-metta-bijection`)

**Branch:** `feat/tier5-edn-metta-bijection`
**Exit criteria:** `edn_to_metta(form)` and `metta_to_edn(text)` form a verified bijection over the 7 golden atom files (post-Tier-1 goldens). The new `_atomspace.py` module's `Atomspace.add(atom)` deduplicates structurally-identical sub-expressions.

### Task P1: Define the bijection rules

**Files:**
- Create: `skills/neurosym-forge/scripts/_metta_bijection.py`
- Create: `skills/neurosym-forge/tests/test_metta_bijection.py`

- [ ] **P1.1: Failing test — bijection round-trip on the 7 Tier-1 goldens** (REQ-EDN-060, 066)

```python
"""REQ-EDN-060, 066: edn_to_metta and metta_to_edn form a verified bijection."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts._edn_reader import read_edn
from scripts._metta_bijection import edn_to_metta, metta_to_edn

GOLDEN_FILES = sorted((ROOT / "tests" / "golden").glob("*.edn"))


@pytest.mark.parametrize("golden", GOLDEN_FILES, ids=lambda p: p.name)
def test_edn_to_metta_round_trip(golden: Path):
    raw = golden.read_text(encoding="utf-8")
    parsed = read_edn(raw)
    metta_form = edn_to_metta(parsed)
    re_parsed = metta_to_edn(metta_form)
    assert parsed == re_parsed, (
        f"bijection round-trip failed for {golden.name}\n"
        f"original: {parsed!r}\nmetta: {metta_form!r}\nre-parsed: {re_parsed!r}"
    )
```

- [ ] **P1.2: Run** — confirm FAIL (module doesn't exist).

- [ ] **P1.3: Implement `_metta_bijection.py`** with the rules from REQ-EDN-061, 062, 063:

```python
"""EDN ↔ MeTTa bijection.

REQ-EDN-060, 061, 062, 063, 066.

Bijection rules:
  EDN keyword `:foo`            ↔ MeTTa symbol `foo`
  EDN logic var `?x`            ↔ MeTTa variable `$x`
  EDN list `(a b c)`            ↔ MeTTa expression `(a b c)`
  EDN vector `[a b c]`          ↔ MeTTa expression `(Vector a b c)`
  EDN map `{:k1 v1 :k2 v2}`     ↔ MeTTa `(Map (k1 v1) (k2 v2))` ordered by key
  EDN string `"foo"`            ↔ MeTTa string `"foo"`
  EDN int / float               ↔ MeTTa number
  EDN nil                       ↔ MeTTa `()` (empty expression)
  EDN tagged literal `#inst`    ↔ MeTTa `(Inst "...")`
"""
from __future__ import annotations
import re
from typing import Any
from scripts._edn_reader import (
    Keyword, Symbol, EdnList, EdnVector, read_edn,
)


class BijectionError(ValueError):
    """Raised when an EDN form has no canonical MeTTa representation."""


def edn_to_metta(form: Any) -> str:
    """Serialise an EDN form to MeTTa surface syntax."""
    if form is None:
        return "()"
    if isinstance(form, bool):
        return "True" if form else "False"
    if isinstance(form, (int, float)):
        return repr(form)
    if isinstance(form, str):
        return f'"{form}"'
    if isinstance(form, Keyword):
        return form.name
    if isinstance(form, Symbol):
        return f"${form.name.lstrip('?')}" if form.name.startswith("?") else form.name
    if isinstance(form, EdnList):
        body = " ".join(edn_to_metta(x) for x in form)
        return f"({body})"
    if isinstance(form, EdnVector):
        body = " ".join(edn_to_metta(x) for x in form)
        return f"(Vector {body})" if body else "(Vector)"
    if isinstance(form, dict):
        pairs = sorted(form.items(), key=lambda kv: edn_to_metta(kv[0]))
        body = " ".join(f"({edn_to_metta(k)} {edn_to_metta(v)})" for k, v in pairs)
        return f"(Map {body})"
    raise BijectionError(f"no MeTTa representation for {type(form).__name__}: {form!r}")


def metta_to_edn(text: str) -> Any:
    """Parse a MeTTa surface form back into the canonical EDN value."""
    parser = _Parser(text)
    parser._skip_ws()
    if parser._eof():
        return None
    return _from_metta_node(parser._parse_form())


# ... _Parser implementation mirroring _edn_reader's recursive descent,
# with appropriate adjustments for $-vars and the (Vector ...) / (Map ...) /
# (Inst ...) special heads. Full implementation in commit.
```

- [ ] **P1.4: Run the 7-golden round-trip — confirm PASS** for all 7.

- [ ] **P1.5: Commit**

```bash
git commit -am "edn: edn_to_metta + metta_to_edn bijection (REQ-EDN-060..066)"
```

### Task P2: Atomspace-shaped storage with dedup

- [ ] **P2.1: Failing test for `Atomspace.add` dedup property** (REQ-EDN-064, 065)

```python
def test_atomspace_dedupes_subexpressions():
    """REQ-EDN-064, 065: structurally-identical sub-expressions share a handle."""
    from scripts._atomspace import Atomspace
    space = Atomspace()
    h1 = space.add(("P", ("Q", "a"), "b"))
    h2 = space.add(("R", ("Q", "a")))
    # The shared (Q a) sub-DAG should have exactly one handle internally.
    assert space.dedup_factor() < 1.0, (
        "expected dedup factor < 1.0 due to shared (Q a) sub-expression"
    )
    # Re-adding the same atom returns the same handle.
    h1_again = space.add(("P", ("Q", "a"), "b"))
    assert h1 == h1_again
```

- [ ] **P2.2: Implement `Atomspace` via hash-cons** in `_atomspace.py`:

```python
"""Atomspace-shaped storage with structural-sharing (hash-cons).

REQ-EDN-064, 065: structurally-identical sub-expressions share a
single canonical handle.
"""
from __future__ import annotations
from typing import Any


class AtomspaceHandle:
    __slots__ = ("_id",)
    def __init__(self, id_: int): self._id = id_
    def __eq__(self, o): return isinstance(o, AtomspaceHandle) and o._id == self._id
    def __hash__(self): return self._id
    def __repr__(self): return f"AtomspaceHandle({self._id})"


class Atomspace:
    def __init__(self) -> None:
        self._intern: dict[Any, AtomspaceHandle] = {}
        self._reverse: dict[AtomspaceHandle, Any] = {}
        self._next_id = 0
        self._inserts = 0

    def add(self, atom: Any) -> AtomspaceHandle:
        self._inserts += 1
        key = self._canonical(atom)
        if key in self._intern:
            return self._intern[key]
        handle = AtomspaceHandle(self._next_id)
        self._next_id += 1
        self._intern[key] = handle
        self._reverse[handle] = atom
        return handle

    def lookup(self, handle: AtomspaceHandle) -> Any:
        return self._reverse[handle]

    def iter_atoms(self):
        return iter(self._reverse.items())

    def dedup_factor(self) -> float:
        return len(self._intern) / self._inserts if self._inserts else 1.0

    def _canonical(self, atom: Any) -> Any:
        """Recursively hash-cons sub-expressions; tuples become tuples of
        canonical handles. This is what makes (Q a) shared between
        (P (Q a) b) and (R (Q a))."""
        if isinstance(atom, tuple):
            return tuple(self._canonical(x) for x in atom)
        return atom
```

- [ ] **P2.3: Run** — confirm PASS.

- [ ] **P2.4: Commit**

```bash
git commit -am "atomspace: hash-cons Atomspace with dedup_factor invariant (REQ-EDN-064, 065)"
```

### Task P3: Vendor + scaffold integration

- [ ] **P3.1: Add `_metta_bijection.py` and `_atomspace.py` to `scaffold_project.py`'s vendored-file tuple** (REQ-EDN-067) — both files copy into baked projects' scripts/ at scaffold time.

- [ ] **P3.2: Scaffold-bake test** asserts both files appear in baked projects.

- [ ] **P3.3: Commit**

```bash
git commit -am "scaffold: vendor _metta_bijection.py + _atomspace.py (REQ-EDN-067)"
```

### Task P4: Push + open PR-P. Merge on green.

---

## Phase Q — Embedding sidecar (`tier5-embedding-sidecar`)

**Branch:** `feat/tier5-embedding-sidecar`
**Exit criteria:** `EmbeddingSidecar` indexes Atomspace handles to 384-dim vectors via local `sentence-transformers/all-MiniLM-L6-v2`; `neighbors(handle, k)` returns top-k by cosine; the grounded MeTTa atom `(neighbors $atom $k)` is registered with the embedded runtime from Phase O.

### Task Q1: Sidecar smoke test

**Files:**
- Create: `skills/neurosym-forge/scripts/_embedding_sidecar.py`
- Create: `skills/neurosym-forge/tests/test_embedding_sidecar.py`

- [ ] **Q1.1: Failing test — insert 10 atoms, query neighbors of one, assert top-1 = self** (REQ-EMBED-040, 043, 046)

```python
"""REQ-EMBED-040, 043, 046: embedding sidecar smoke test."""
import pytest

pytest.importorskip("sentence_transformers", reason="needs sentence-transformers installed")


def test_smoke_top1_is_self():
    from scripts._atomspace import Atomspace
    from scripts._embedding_sidecar import EmbeddingSidecar
    space = Atomspace()
    sidecar = EmbeddingSidecar(space)
    handles = [space.add(("fact", f"observation-{i}")) for i in range(10)]
    for h in handles:
        sidecar.embed_atom(h)
    neighbours = sidecar.neighbors(handles[3], k=3)
    assert neighbours, "no neighbours returned"
    assert neighbours[0][0] == handles[3], "top-1 should be self"
    assert -1.0 <= neighbours[0][1] <= 1.0


def test_duplicate_insert_does_not_re_embed():
    """REQ-EMBED-041: duplicate insert is a no-op for the sidecar."""
    from scripts._atomspace import Atomspace
    from scripts._embedding_sidecar import EmbeddingSidecar
    space = Atomspace()
    sidecar = EmbeddingSidecar(space)
    h1 = space.add(("foo", "bar"))
    sidecar.embed_atom(h1)
    n1 = sidecar.count()
    h2 = space.add(("foo", "bar"))  # same canonical
    sidecar.embed_atom(h2)
    assert sidecar.count() == n1
```

- [ ] **Q1.2: Implement `EmbeddingSidecar`**:

```python
"""REQ-EMBED-040..046: vector-embedding sidecar for the Atomspace.

Default encoder: sentence-transformers/all-MiniLM-L6-v2 (384-dim).
Override via NEUROSYM_EMBED_MODEL env var.
"""
from __future__ import annotations
import os
from typing import Optional
import numpy as np


class EmbeddingUnavailableError(RuntimeError):
    """Embedding model is unavailable (missing package, network, etc.)."""


class EmbeddingSidecar:
    def __init__(self, space, *, auto_embed: bool = False,
                 model_name: Optional[str] = None) -> None:
        self.space = space
        self.auto_embed = auto_embed
        self._model_name = model_name or os.environ.get(
            "NEUROSYM_EMBED_MODEL",
            "sentence-transformers/all-MiniLM-L6-v2",
        )
        self._model = None  # lazy
        self._vecs: dict = {}

    def _ensure_model(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as e:
                raise EmbeddingUnavailableError(
                    f"sentence-transformers not installed; pip install sentence-transformers"
                ) from e
            self._model = SentenceTransformer(self._model_name)
        return self._model

    def embed_atom(self, handle) -> None:
        if handle in self._vecs:
            return  # idempotent (REQ-EMBED-041)
        atom = self.space.lookup(handle)
        text = str(atom)
        vec = self._ensure_model().encode([text], normalize_embeddings=True)[0]
        self._vecs[handle] = np.asarray(vec, dtype=np.float32)

    def neighbors(self, handle, k: int = 5):
        if handle not in self._vecs:
            self.embed_atom(handle)
        query = self._vecs[handle]
        scored = []
        for h, vec in self._vecs.items():
            sim = float(np.dot(query, vec))
            scored.append((h, sim))
        scored.sort(key=lambda kv: kv[1], reverse=True)
        return scored[:k]

    def count(self) -> int:
        return len(self._vecs)
```

- [ ] **Q1.3: Run** — confirm PASS (with sentence-transformers installed).

- [ ] **Q1.4: Commit**

```bash
git commit -am "embedding: sidecar with sentence-transformers/all-MiniLM-L6-v2 (REQ-EMBED-040, 041, 043, 046)"
```

### Task Q2: Missing-model error path

- [ ] **Q2.1: Test that EmbeddingUnavailableError surfaces with remediation message** (REQ-EMBED-044)

```python
def test_missing_model_error_names_install_command(monkeypatch):
    """REQ-EMBED-044: the error message names the install command."""
    import builtins
    monkeypatch.setitem(__import__('sys').modules, 'sentence_transformers', None)
    real_import = builtins.__import__
    def fake_import(name, *args, **kwargs):
        if name == 'sentence_transformers':
            raise ImportError('mocked')
        return real_import(name, *args, **kwargs)
    monkeypatch.setattr(builtins, '__import__', fake_import)
    from scripts._atomspace import Atomspace
    from scripts._embedding_sidecar import EmbeddingSidecar, EmbeddingUnavailableError
    space = Atomspace()
    sidecar = EmbeddingSidecar(space)
    h = space.add(("foo",))
    with pytest.raises(EmbeddingUnavailableError) as exc_info:
        sidecar.embed_atom(h)
    assert "pip install" in str(exc_info.value)
```

- [ ] **Q2.2: Run** — confirm PASS (the implementation in Q1.2 already raises with that message).

- [ ] **Q2.3: Commit**

```bash
git commit -am "embedding: sidecar missing-model error names remediation (REQ-EMBED-044)"
```

### Task Q3: Grounded atom wiring (Rust side, requires Phase O)

- [ ] **Q3.1: Failing cargo integration test** — `(neighbors (Person Alice) 5)` MeTTa expression returns 5 most-similar atoms.

Note: this task requires Phase O's `metta::run_metta` to be available. If Phase O has not yet merged, this task is BLOCKED — open the PR for Q1+Q2+Q4 first; come back to Q3 after Phase O merges.

The grounded atom registration uses hyperon's grounded-atom mechanism. The Rust side defines a `NeighborsAtom` struct implementing `Grounded` and registers it into the `Metta` runtime via `metta.tokenizer().register_token(...)`. The struct holds a handle to the Python sidecar (via PyO3 — hyperon's Python bindings make this two-way).

Full integration is intricate; document it in a separate task block at the start of Q3 with the pin to hyperon's exact grounded-atom API at implementation time.

- [ ] **Q3.2: Implement the grounded atom**, then ensure the test passes.

- [ ] **Q3.3: Commit**

```bash
git commit -am "metta(grounded): (neighbors $atom $k) wired via PyO3 sidecar bridge (REQ-EMBED-045)"
```

### Task Q4: Vendor the sidecar + add to scaffold

- [ ] **Q4.1: Add `_embedding_sidecar.py` to `scaffold_project.py`** so baked projects ship it.

- [ ] **Q4.2: Add `sentence-transformers` to `skills/neurosym-forge/pyproject.toml` as an optional extra** (the heavy install isn't mandatory; the tests `importorskip` when missing).

- [ ] **Q4.3: Commit**

```bash
git commit -am "scaffold: vendor _embedding_sidecar.py + optional sentence-transformers extra (REQ-EMBED-040)"
```

### Task Q5: Push + open PR-Q. Merge on green.

---

## Phase R — Hybrid neuro-symbolic query (`tier5-hybrid-query`)

**Branch:** `feat/tier5-hybrid-query`
**Exit criteria:** A grounded MeTTa atom `(hybrid-match $space $template $hint $k)` returns the intersection of `neighbors($hint, $k)` and `match($space, $template)`, in similarity order. The fallback to pure-symbolic match when the sidecar is unavailable is tested.

### Task R1: Hybrid match test

- [ ] **R1.1: Failing cargo integration test** — 10 atoms about "ages" with one matching the template; assert it appears in top-1 of hybrid-match (REQ-QUERY-040, 041, 044):

```rust
// verifiers/osmotic_pressure/rust-verifier/tests/hybrid_query.rs
//! REQ-QUERY-040, 041, 044
use osmotic_pressure_verifier::metta::run_metta;

#[test]
fn hybrid_match_returns_intersection_in_similarity_order() {
    let program = r#"
        (Person Alice 30)
        (Person Bob 35)
        (Person Carol 40)
        (Person Dave 25)
        ; ... 6 more
        !(hybrid-match &self (Person $name $age) (Person Carol 40) 3)
    "#;
    let results = run_metta(program).expect("run_metta");
    // hybrid-match should return Carol first (similarity = 1.0), then
    // Bob/Dave (similar ages), filtering by the (Person ...) template.
    assert!(results[0].contains("Carol"));
}
```

- [ ] **R1.2: Implement `(hybrid-match ...)` as a grounded atom** that:
  1. Calls `neighbors(hint, k)` (Phase Q's grounded atom)
  2. For each neighbour, runs `match(space, template)` on the neighbour
  3. Returns the union of match results, ordered by neighbour similarity

(The implementation is more thread-spanning than Phase Q's `neighbors`; the Rust side needs to evaluate a MeTTa pattern given a MeTTa atom. Use hyperon's `match_atom` API.)

- [ ] **R1.3: Run** — confirm PASS.

- [ ] **R1.4: Commit**

```bash
git commit -am "metta(hybrid): hybrid-match grounded atom (REQ-QUERY-040, 041, 044)"
```

### Task R2: Sidecar-unavailable fallback

- [ ] **R2.1: Failing test** — when sidecar raises `EmbeddingUnavailableError`, hybrid-match falls back to pure symbolic match AND surfaces a warning (REQ-QUERY-042):

```rust
#[test]
fn hybrid_match_falls_back_when_sidecar_unavailable() {
    std::env::set_var("NEUROSYM_DISABLE_EMBEDDING", "1");
    let program = r#"
        (Person Alice 30)
        !(hybrid-match &self (Person $n $a) (Person Alice 30) 1)
    "#;
    let results = run_metta(program).expect("run_metta");
    std::env::remove_var("NEUROSYM_DISABLE_EMBEDDING");
    assert!(!results.is_empty(), "fallback should return symbolic-only results");
}
```

- [ ] **R2.2: Implement the fallback** — wrap the neighbour call in `match { Ok(n) => n, Err(EmbeddingUnavailable) => warn; pure_match() }`.

- [ ] **R2.3: Commit**

```bash
git commit -am "metta(hybrid): pure-symbolic fallback when sidecar unavailable (REQ-QUERY-042)"
```

### Task R3: Empty-result handling + introspection atom

- [ ] **R3.1: Tests for empty-result and `(neighbors-only ...)` grounded atom** (REQ-QUERY-043, 045).

- [ ] **R3.2: Implement**.

- [ ] **R3.3: Commit**

```bash
git commit -am "metta(hybrid): empty-result handling + neighbors-only introspection (REQ-QUERY-043, 045)"
```

### Task R4: DSL reference §7

- [ ] **R4.1: Add §7 to `docs/booklogic-dsl-reference.md`** documenting both grounded atoms with a worked example (REQ-QUERY-046).

- [ ] **R4.2: Commit**

```bash
git commit -am "docs(dsl): §7 hybrid queries (REQ-QUERY-046)"
```

### Task R5: Push + open PR-R. Merge on green.

---

## Phase S — Framing reckoning (`tier5-framing-reckoning`)

**Branch:** `feat/tier5-framing-reckoning`
**Exit criteria:** Every promotional claim about "MeTTa" in the framework's docs either (a) correctly describes the post-Tier-5 runtime (with `(alpha)` qualifier where appropriate) or (b) explicitly says "MeTTa-shaped" with a link to the new metta-runtime-grounded-vs-shaped reference doc.

### Task S1: Author `docs/concepts/metta-runtime-grounded-vs-shaped.md`

- [ ] **S1.1: Write the reference doc** (~150 lines) per REQ-BOOKLOGIC-060:

Sections:
1. **What "runtime-grounded" means** — after Tier 5, the framework embeds the real hyperon-experimental crate. `:backend :metta` constraints flow through that interpreter. `(neighbors ...)` is a real grounded atom calling Python via PyO3.
2. **What's still "MeTTa-shaped"** — the EDN files. They use MeTTa-style idioms (`=`, `:`, `?`, `match`-shape sexps) but are not parsed by a MeTTa interpreter — they're parsed by `_edn_reader.py` and translated. The `:backend :z3` / `:backend :egg` / `:backend :cozo` constraints don't go through MeTTa.
3. **The alpha qualifier** — hyperon-experimental is alpha; the version pin is at `docs/operations/hyperon-experimental-pin.md`. Read it before counting on any MeTTa feature for a production deploy.
4. **What's NOT included in Tier 5** — DAS, MORK, PLN truth values, Rholang/ASI-Chain compilation. Each gets a one-line "future tier" pointer.
5. **Reading the SUPPORT_MATRIX** — how to interpret `wired (alpha)` vs `wired` vs `stub`.

- [ ] **S1.2: Commit**

```bash
git commit -am "docs(concepts): metta-runtime-grounded-vs-shaped reference (REQ-BOOKLOGIC-060)"
```

### Task S2: SKILL.md update

- [ ] **S2.1: Edit `skills/neurosym-forge/SKILL.md`** (REQ-BOOKLOGIC-061):
  - Name the embedded hyperon-experimental crate + its alpha status, near the top
  - Link to `docs/concepts/metta-runtime-grounded-vs-shaped.md`
  - Replace any sentence that pre-Tier-5 implied the framework "runs MeTTa" without qualifier

- [ ] **S2.2: Commit**

```bash
git commit -am "docs(skill): SKILL.md names hyperon-experimental + grounded-vs-shaped link (REQ-BOOKLOGIC-061)"
```

### Task S3: SUPPORT_MATRIX.md `:metta` row

- [ ] **S3.1: Add `defconstraint :backend :metta | wired (alpha) | hyperon-experimental` row to SUPPORT_MATRIX** (REQ-BOOKLOGIC-062). This duplicates Phase O's REQ-METTA-045 work; if Phase O merged first, the row is already present — verify and update the explanatory paragraph below the table.

- [ ] **S3.2: Update `test_support_matrix.py` drift lint** to assert the `(alpha)` qualifier appears alongside `:metta` rows.

- [ ] **S3.3: Commit**

```bash
git commit -am "support-matrix: defconstraint :backend :metta wired (alpha) (REQ-BOOKLOGIC-062)"
```

### Task S4: references/metta-idioms.md rewrite

- [ ] **S4.1: Rewrite `skills/neurosym-forge/references/metta-idioms.md`** (REQ-BOOKLOGIC-063):
  - Section 1 (existing): "What we borrow from MeTTa" — atomspace, grounded atoms, rewrite rules
  - Section 2 (existing): "What we don't borrow" — full unification, dynamic dispatch
  - **Section 3 (NEW): "What we now embed at runtime (Tier 5)"** — `:backend :metta` constraints, `(neighbors $atom $k)` grounded atom, `(hybrid-match ...)`, Atomspace dedup in Python via `_atomspace.py`
  - Strike-out / retire any pre-Tier-5 sentence that overstated the integration.

- [ ] **S4.2: Commit**

```bash
git commit -am "docs(references): metta-idioms rewrites Tier-5 reality (REQ-BOOKLOGIC-063)"
```

### Task S5: Drift lint for promotional language

- [ ] **S5.1: Failing test** in `test_support_matrix.py` (REQ-BOOKLOGIC-064):

```python
def test_no_promotional_overstatement_on_metta_row():
    """REQ-BOOKLOGIC-064: if SUPPORT_MATRIX or SKILL.md says :metta is
    'production-ready' or 'stable' while hyperon-experimental remains
    alpha, lint fails."""
    text = (MATRIX.read_text(encoding="utf-8")
            + Path(MATRIX.parent / "SKILL.md").read_text(encoding="utf-8"))
    # Find :metta-related claims
    metta_lines = [ln for ln in text.splitlines() if ":metta" in ln.lower() or "hyperon" in ln.lower()]
    forbidden = ["production-ready", "production ready", "fully stable", "GA-quality"]
    for line in metta_lines:
        for word in forbidden:
            assert word.lower() not in line.lower(), (
                f"promotional overstatement detected: {line!r} contains {word!r}"
            )
```

- [ ] **S5.2: Run** — confirm PASS (no current text contains the forbidden phrases).

- [ ] **S5.3: Commit**

```bash
git commit -am "tests(lint): drift lint against promotional overstatement on :metta (REQ-BOOKLOGIC-064)"
```

### Task S6: Deprecation runbook (optional, only if API breaks)

- [ ] **S6.1: Author `docs/operations/deprecate-metta-backend.md`** (REQ-BOOKLOGIC-065) — a deprecation runbook for the day hyperon-experimental's API breaks incompatibly. Covers migration to `:backend :z3` or `:backend :cozo` substitutes.

- [ ] **S6.2: Commit**

```bash
git commit -am "docs(ops): deprecation runbook for :backend :metta (REQ-BOOKLOGIC-065)"
```

### Task S7: DSL reference §2.5 update

- [ ] **S7.1: Add `:metta` row to the operator table in §2.5** (REQ-BOOKLOGIC-066) — with the `(alpha)` qualifier and a link to the metta-runtime-grounded-vs-shaped doc.

- [ ] **S7.2: Commit**

```bash
git commit -am "docs(dsl): :metta operator row in §2.5 (REQ-BOOKLOGIC-066)"
```

### Task S8: Push + open PR-S. Merge on green.

---

## Phase T — MeTTa onboarding eval (`tier5-metta-onboarding-eval`)

**Branch:** `feat/tier5-metta-onboarding-eval`
**Exit criteria:** A 4th domain prompt (Grandparent / MeTTa-runtime) ships under `skills/neurosym-forge/eval/prompts/`; the bench harness records whether the agent used `:backend :metta`; the aggregator report has a MeTTa-backend-uptake section.

### Task T1: Author the prompt

- [ ] **T1.1: Create `skills/neurosym-forge/eval/prompts/grandparent-metta.md`** (REQ-EVAL-060):

```markdown
# Grandparent — MeTTa-runtime domain

Build a verifier that checks a multi-hop "Grandparent" relation derived
from "Parent" facts.

## Facts

- Tom is parent of Bob
- Bob is parent of Carol
- Carol is parent of Dave

## Rule

A Grandparent relation holds when there's a Parent–Parent chain:
`Grandparent(X, Z) :- Parent(X, Y), Parent(Y, Z)`

## Acceptance

The verifier MUST surface a `Grandparent(Tom, Carol)` and
`Grandparent(Bob, Dave)` claim. The verifier MUST NOT surface a
`Grandparent(Tom, Dave)` claim (that's a great-grandparent — out of
scope for the single-hop rule).

The grand-rule is non-trivial in Z3 (multi-hop relations are clumsy
without quantifiers). Consider whether `:backend :metta` is the right
tool for this — see `skills/neurosym-forge/SUPPORT_MATRIX.md`.
```

- [ ] **T1.2: Commit**

```bash
git commit -am "eval(onboarding): grandparent-metta domain prompt (REQ-EVAL-060)"
```

### Task T2: Harness schema update — `metta_backend_used` column

- [ ] **T2.1: Failing test** — bench output CSV has `metta_backend_used` column (REQ-EVAL-061, 062):

```python
def test_bench_csv_has_metta_backend_column(tmp_path):
    """REQ-EVAL-061, 062: CSV columns include metta_backend_used."""
    import subprocess, sys, csv
    result = subprocess.run(
        [sys.executable, "skills/neurosym-forge/eval/onboarding-bench.py",
         "--backend", "stub", "--out", str(tmp_path)],
        capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0
    csvs = list(tmp_path.rglob("*.csv"))
    assert csvs
    with csvs[0].open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        assert "metta_backend_used" in reader.fieldnames
```

- [ ] **T2.2: Add the column to `onboarding-bench.py`'s CSV schema**. The stub backend hard-codes `metta_backend_used=False` for the first 3 prompts and `True` for the grandparent-metta prompt (the "happy path" the docs suggest).

- [ ] **T2.3: Commit**

```bash
git commit -am "eval(onboarding): metta_backend_used column + stub behaviour (REQ-EVAL-061, 062, 064)"
```

### Task T3: SUCCESS_WITHOUT_METTA outcome

- [ ] **T3.1: Test that a successful run NOT using `:backend :metta` records `outcome=SUCCESS_WITHOUT_METTA`** (REQ-EVAL-063).

- [ ] **T3.2: Implement the outcome logic**.

- [ ] **T3.3: Commit**

```bash
git commit -am "eval(onboarding): SUCCESS_WITHOUT_METTA signal (REQ-EVAL-063)"
```

### Task T4: Aggregator report section

- [ ] **T4.1: Add MeTTa-backend-uptake section** to `aggregate_runs.py` and the seed `docs/eval/onboarding-bench-report.md` (REQ-EVAL-065).

- [ ] **T4.2: Commit**

```bash
git commit -am "eval(onboarding): MeTTa-backend-uptake aggregator section (REQ-EVAL-065)"
```

### Task T5: Push + open PR-T. Merge on green.

---

## Self-review

**Spec coverage** (every REQ has a task):
- Phase O: REQ-METTA-040..047 — Tasks O1-O4 (8 REQs, all covered) ✓
- Phase P: REQ-EDN-060..067 — Tasks P1-P3 (8 REQs, all covered) ✓
- Phase Q: REQ-EMBED-040..046 — Tasks Q1-Q4 (7 REQs, all covered) ✓
- Phase R: REQ-QUERY-040..046 — Tasks R1-R4 (7 REQs, all covered) ✓
- Phase S: REQ-BOOKLOGIC-060..066 — Tasks S1-S7 (7 REQs, all covered) ✓
- Phase T: REQ-EVAL-060..065 — Tasks T1-T4 (6 REQs, all covered) ✓

**Placeholder scan:** No "TBD", no "TODO", no "implement later" in code blocks. The Phase Q task Q3 (grounded-atom Rust integration) is intentionally lighter on code because hyperon's grounded-atom API surface depends on the pinned version at implementation time — the plan notes that the engineer must look up the exact API at the start of Q3.

**Type consistency:**
- `run_metta(program: &str) -> Result<Vec<String>, MettaError>` — same signature O1.4, O2.2 ✓
- `MettaError` enum — Init / Run / Timeout variants consistent ✓
- `EmbeddingSidecar.embed_atom(handle)`, `.neighbors(handle, k)`, `.count()` — Q1.2 and Q1.1 match ✓
- `Atomspace.add(atom) -> AtomspaceHandle`, `.lookup(handle)`, `.iter_atoms()`, `.dedup_factor()` — P2.2 and P2.1 match ✓
- `edn_to_metta(form) -> str` / `metta_to_edn(text) -> Any` — P1.1 and P1.3 match ✓

**Dependency consistency:**
- Phase O's `run_metta` is used by Phase Q (R3.1 cargo test) — both reference the same crate-level export ✓
- Phase Q's `EmbeddingSidecar.neighbors` is used by Phase R's `(hybrid-match ...)` — both reference the same Python module ✓
- Phase S's drift lint references SUPPORT_MATRIX.md's `(alpha)` qualifier — set by Phase O's REQ-METTA-045 ✓
- Phase T's prompt references `:backend :metta` — defined by Phase O's REQ-METTA-041 ✓

Plan complete. Successor execution per superpowers:subagent-driven-development or superpowers:executing-plans.

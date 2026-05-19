# Tier 5 — Scale + LLM extractors + Author ergonomics — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the seven concrete gaps the framework actually has after Tier 1-4: untested at real-corpus scale, hand-authored lift regex, no cross-chapter constraints, unused `:confidence` field, no manuscript-visible defect surfacing, no semantic similarity over claims, 1146-line DSL reference with no interactive entry point.

**Architecture:** Seven independent OpenSpec changes across three tracks. Tracks (and their phase letters):

- **Scale + extraction (Phases O, P, Q):** prove the framework runs at 1000+ claims via a 4th verifier; replace hand-regex with `:backend :llm` lift extractors; ship a vector-embedding sidecar with `similar_claims(claim_id, k)` — no MeTTa runtime dependency.
- **Coverage + accuracy (Phases R, S):** `defconstraint :scope :corpus` so cross-chapter consistency constraints can be written; propagate the `:confidence` field already on every atom into the verdict scoring + advisory-downgrade discipline.
- **Author surface (Phases T, U):** publication bridge that emits `manuscript-annotations.json` + a markdown→HTML overlay renderer; interactive `forge` CLI for `add-constraint`, `suggest-lifts`, `explain-defect`, `similar`, `render`.

This Tier replaces the closed PR #89 (MeTTa runtime) which solved problems the framework didn't have. The replacement focuses on what 5+ session of Tier 1-4 work surfaced as genuine ergonomic + empirical gaps.

**Tech Stack:** Python 3.13 (ingest, codegen, CLI, renderer), Rust 1.90 + z3 0.20 + egg 0.10 + cozo 0.7 (verifier), ClojureScript via nbb (DSL compiler), `sentence-transformers/all-MiniLM-L6-v2` (embeddings), OpenAI/Anthropic/`ollama` (LLM extractors — provider-pluggable), `click` (CLI), pytest + cargo test + nbb test.

**Dependencies (the cross-coupling matters):**

- Phase O (scale test) can begin immediately — no other phase is a prerequisite. It will SURFACE gaps that the other phases address.
- Phase Q (semantic retrieval) is a prerequisite for Phase R's `:semantic-neighbours` verdict field AND Phase T's "see also" feature AND Phase U's `forge similar`.
- Phase P (LLM extractors) is a prerequisite for Phase U's `forge suggest-lifts`.
- Phase R (cross-chapter) is independent — extends Phase J's codegen but doesn't conflict with O/P/Q/S/T.
- Phase S (confidence) is independent — modifies verdict shape but doesn't conflict structurally.
- Phase T (publication) consumes Phase S's defect-confidence + Phase Q's semantic-neighbours.
- Phase U (CLI) consumes Phase P's LLM provider + Phase Q's index + Phase T's renderer.

Recommended execution order: O (in parallel with) P + Q → R + S → T → U.

**Caveats:**
- The LLM-extractors path (Phase P) introduces external API dependencies. Caching + offline-stub-responder pattern keeps CI deterministic; production runs need API keys.
- The semantic retrieval (Phase Q) requires `sentence-transformers` (heavy install, ~500MB including the model). Declared as an optional extra; graceful degradation when missing.
- The 4th verifier's domain (Phase O) is recommended to be the ADSC clinical report (~4816 lines, ~OneDrive/Desktop/stemCells/). Alternatives: EpochPoET LaTeX paper, sevenlayer ZK book. Pick one and commit to it.

---

## Pre-flight

Read before starting any phase:

- `openspec/changes/tier5-*/{proposal,design,tasks}.md` + `specs/` (this PR authors them)
- `docs/booklogic-dsl-reference.md` — author-facing reference; Phases R, S, T, U all extend it
- `verifiers/osmotic_pressure/scripts/ingest_ledger.py` — `_apply_predicates` is the regex-lift evaluator Phase P alternates
- `skills/neurosym-forge/scripts/codegen_axioms.py` — Phase R extends the `axioms_for_subject` / `axioms_shared` pattern with `axioms_corpus`
- `verifiers/bermuda/scripts/verdict_to_qa.py` — Phase S/T extend the verdict-to-defect translation
- `skills/neurosym-forge/scripts/scaffold_project.py` — Phase U extends the CLI entry point pattern
- `docs/eval/2026-05-18-third-verifier-build-log.md` — the discipline Phase O scales up

**Branches:** one per phase, cut from main.

```bash
cd ~/work/russellian-book-suite
git fetch origin
git checkout main
git pull --ff-only origin main
# Per-phase branches when starting:
git checkout -b feat/tier5-scale-corpus
git checkout -b feat/tier5-llm-extractors
git checkout -b feat/tier5-semantic-retrieval
git checkout -b feat/tier5-cross-chapter
git checkout -b feat/tier5-confidence-propagation
git checkout -b feat/tier5-publication-bridge
git checkout -b feat/tier5-author-cli
```

**Worktree pattern:** mirror Tier 1-4 — `git worktree add` per phase under `C:\work\russellian-book-suite-worktrees\<branch-name>`.

**Test invocations:**

```bash
# Per-verifier
make -C verifiers/osmotic_pressure ci
make -C verifiers/bermuda ci
make -C verifiers/epidemiology ci
# After Phase O, also:
make -C verifiers/adsc-clinical ci   # or whichever 4th corpus was chosen

# Neurosym-forge full suite (must not regress; baseline 303 post-Tier-4)
py -m pytest skills/neurosym-forge/tests -q
```

**Commit hygiene:** terse, imperative; no AI attribution; one problem per commit; never `--no-verify`.

**Scope guard:** this Tier does NOT pivot the framework to MeTTa, does NOT introduce a chain-of-thought reasoning engine, does NOT add agent-driven autonomous fact-checking. Each of those is genuinely interesting and out of scope.

---

## Phase O — Scale corpus (`tier5-scale-corpus`)

**Branch:** `feat/tier5-scale-corpus`
**OpenSpec change:** `openspec/changes/tier5-scale-corpus/`
**Exit criteria:** A 4th verifier at `verifiers/adsc-clinical/` (or chosen corpus) passes `make ci` end-to-end with 1000+ ingested claims; a build-log + scale-eval report document where the framework breaks and where it holds.

### Task O1: Pick the corpus, scaffold the project

**Files:**
- Create: `verifiers/adsc-clinical/` (or chosen corpus) — standard scaffold output

- [ ] **O1.1: Domain choice** — see `openspec/changes/tier5-scale-corpus/design.md` for the comparison. Recommendation: ADSC clinical report. The corpus has trial-claim shape ("trial X, n=Y, primary endpoint Z achieved p<0.001"), which exercises Phase R's cross-chapter consistency AND Phase S's confidence propagation natively.

- [ ] **O1.2: Scaffold**

```bash
py -m scripts.scaffold_project --name "ADSC Clinical Verifier" \
  --slug adsc_clinical \
  --out verifiers/adsc-clinical \
  --has-book-knowledge-bridge
```

- [ ] **O1.3: Commit**

```bash
git add verifiers/adsc-clinical/
git commit -m "scaffold(adsc-clinical): 4th verifier project for Tier 5 scale eval"
```

### Task O2: Ingest the corpus

- [ ] **O2.1: Run book-knowledge against the source markdown** — this produces the `claims.jsonl` ledger.

```bash
py -m book_knowledge.ingest_markdown \
  --in ~/OneDrive/Desktop/stemCells/ADSC_Complete_Report.md \
  --out verifiers/adsc-clinical/fixtures/claims_clean.jsonl
```

(If book-knowledge isn't installed in this verifier's env, install per `skills/book-knowledge/SKILL.md`. If the markdown ingest produces atypical structure, document in the build-log.)

- [ ] **O2.2: Assert ingest size**

```bash
wc -l verifiers/adsc-clinical/fixtures/claims_clean.jsonl
# Expected: ≥ 1000 lines (REQ-CORPUS-041)
```

- [ ] **O2.3: Commit**

```bash
git commit -am "adsc-clinical: ingest ADSC report → claims_clean.jsonl"
```

### Task O3: Author the BookLogic source

- [ ] **O3.1: Sorts** at `verifiers/adsc-clinical/rules/booklogic/sorts.edn`:

```edn
{:forms [(defsort :trial)
         (defsort :treatment)
         (defsort :patient-population)]}
```

- [ ] **O3.2: Predicates** at `verifiers/adsc-clinical/rules/booklogic/predicates.edn`:

```edn
{:forms [(defpredicate :trial-n            [:trial] :int)
         (defpredicate :trial-p-value      [:trial] :real)
         (defpredicate :treatment-efficacy [:treatment] :real)
         (defpredicate :follow-up-months   [:trial] :real)
         (defpredicate :primary-endpoint-met [:trial] :bool)
         (defpredicate :adverse-event-rate [:treatment] :real)
         (defpredicate :dose-mg            [:treatment] :real)
         (defpredicate :patient-count      [:patient-population] :int)]}
```

(8 predicates ≥ REQ-CORPUS-041's threshold.)

- [ ] **O3.3: Lifts** at `verifiers/adsc-clinical/rules/booklogic/lifts.edn` — regex per predicate. Start with hand-authored regex; Phase P will offer `:backend :llm` as an alternative.

- [ ] **O3.4: Constraints** at `verifiers/adsc-clinical/rules/booklogic/constraints.edn` — at least 3 within-trial constraints (e.g., `(>= :trial-n 10)` minimum sample size) and at least 1 cross-trial corpus-scope (deferred to Phase R if `:scope :corpus` not yet shipped — note in build-log).

- [ ] **O3.5: Run `make extract` to confirm the by-predicate distribution covers 8+ predicates** (REQ-CORPUS-041).

- [ ] **O3.6: Commit**

```bash
git commit -am "adsc-clinical: BookLogic source (sorts/predicates/lifts/constraints)"
```

### Task O4: Fixtures

- [ ] **O4.1: `fixtures/claims_clean.jsonl`** — already in place from O2.
- [ ] **O4.2: `fixtures/claims_doctored_low_n.jsonl`** — same trials but with `n=5` (below minimum). Should produce `:unsat` with the low-n defect.
- [ ] **O4.3: `fixtures/claims_doctored_p_value_mismatch.jsonl`** — trial reports `p<0.05` in one section, `p<0.5` in another. Should produce a corpus-scope `:unsat` (or be deferred to Phase R for cross-chapter).
- [ ] **O4.4: `fixtures/claims_doctored_adverse_rate_above_efficacy.jsonl`** — treatment-efficacy lower than adverse-event-rate (treatment doing more harm than good). Should produce `:unsat` with the efficacy-vs-harm defect.

- [ ] **O4.5: Commit**

```bash
git commit -am "adsc-clinical: 1 clean + 3 doctored fixtures"
```

### Task O5: Build-log + scale-eval report

- [ ] **O5.1: Author `docs/eval/2026-05-19-scale-corpus-build-log.md`** AS YOU BUILD. Every framework gap surfaces here:

```markdown
## Gap: <one-line summary>
**When encountered:** Task O2.1 ran ingest_markdown
**What broke:** book-knowledge regex didn't handle multi-line trial blocks
**Tier closing this gap:** Tier 5 Phase P (LLM extractors) OR future book-knowledge work
**Workaround used:** Manual extraction for trials in sections 7-9
**Status:** DEFERRED to Phase P merge
```

- [ ] **O5.2: Run profile** of `make ci` with `time` + `/usr/bin/time -v` (or psutil-based wrapper). Capture: claims-per-minute throughput, peak RSS, wall time per phase.

- [ ] **O5.3: Author `docs/eval/2026-05-19-scale-eval-report.md`** synthesising: throughput numbers, defect-detection rate on the 3 doctored fixtures, false-positive count on clean fixture, where the framework's scaling profile breaks first (compile, ingest, codegen, smt, verdict).

- [ ] **O5.4: Commit**

```bash
git add docs/eval/2026-05-19-scale-corpus-build-log.md \
        docs/eval/2026-05-19-scale-eval-report.md
git commit -m "docs(eval): scale-corpus build-log + scale-eval report (REQ-CORPUS-043, 046)"
```

### Task O6: Push + open PR-O. Merge on green.

---

## Phase P — LLM extractors (`tier5-llm-extractors`)

**Branch:** `feat/tier5-llm-extractors`
**Exit criteria:** A `deflift` form with `:backend :llm` calls an LLM provider, validates the proposed atom against `booklogic-schema.edn`, and emits a structured atom or a `:llm-lift-rejected` defect. SUPPORT_MATRIX gains a `deflift :backend :llm | wired (alpha)` row.

### Task P1: Provider interface + stub responder

**Files:**
- Create: `skills/neurosym-forge/scripts/_llm_lift.py`
- Create: `skills/neurosym-forge/tests/test_llm_lift.py`

- [ ] **P1.1: Failing test for the provider interface + stub backend** (REQ-LLMLIFT-041, 048):

```python
"""REQ-LLMLIFT-041, 048: provider interface + offline stub."""
from __future__ import annotations
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts._llm_lift import LLMLiftProvider, StubLift


def test_stub_provider_returns_expected_atom():
    provider = StubLift(canned_response='{"predicate": ":trial-n", "subject": ":t1", "value": 42}')
    atom = provider.extract(
        claim_id="c-001",
        canonical_text="trial enrolled 42 patients",
        emit_template="(fact ?claim-id :trial :trial-n (parse-int ?v))",
    )
    assert atom["predicate"] == ":trial-n"
    assert atom["value"] == 42
```

- [ ] **P1.2: Implement `_llm_lift.py`** with the abstract base + 4 concrete providers (OpenAI, Anthropic, Local-via-ollama, Stub):

```python
"""REQ-LLMLIFT-040..048: LLM-backed lift providers.

Four concrete implementations:
  OpenAILift    — uses openai SDK; needs OPENAI_API_KEY
  AnthropicLift — uses anthropic SDK; needs ANTHROPIC_API_KEY
  LocalLift     — POSTs to a local Ollama HTTP endpoint at OLLAMA_URL (default http://localhost:11434)
  StubLift      — returns a canned JSON; offline, deterministic, used in CI

The provider class is selected by NEUROSYM_LLM_PROVIDER env var. Default
in test mode: 'stub'. Default in production: 'openai'.
"""
from __future__ import annotations
import json
import os
import sqlite3
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class LLMLiftError(RuntimeError):
    """Raised when an LLM lift attempt fails."""


class LLMLiftProvider(ABC):
    @abstractmethod
    def extract(self, *, claim_id: str, canonical_text: str,
                emit_template: str) -> dict[str, Any] | None:
        ...


class StubLift(LLMLiftProvider):
    def __init__(self, canned_response: str = "{}") -> None:
        self._response = canned_response

    def extract(self, *, claim_id, canonical_text, emit_template):
        return json.loads(self._response)


class OpenAILift(LLMLiftProvider):
    def __init__(self, model: str = "gpt-4o-mini") -> None:
        self.model = model

    def extract(self, *, claim_id, canonical_text, emit_template):
        try:
            import openai
        except ImportError as e:
            raise LLMLiftError(
                "openai package not installed; pip install openai"
            ) from e
        client = openai.OpenAI()  # uses OPENAI_API_KEY env var
        prompt = self._build_prompt(canonical_text, emit_template)
        timeout_ms = int(os.environ.get("VERIFIER_LLM_TIMEOUT_MS", "30000"))
        # Hard-cap response length to keep parsing reliable
        response = client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            timeout=timeout_ms / 1000.0,
        )
        return json.loads(response.choices[0].message.content)

    def _build_prompt(self, text: str, template: str) -> str:
        return (
            f"Extract a typed atom from this text matching the template.\n"
            f"Template: {template}\n"
            f"Text: {text}\n"
            f"Respond with JSON: {{\"predicate\": \":NAME\", \"subject\": \":S\", "
            f"\"value\": <typed-value>}}. JSON only."
        )


class AnthropicLift(LLMLiftProvider):
    # Same shape as OpenAILift with anthropic SDK; uses ANTHROPIC_API_KEY.
    def __init__(self, model: str = "claude-haiku-4-5") -> None:
        self.model = model

    def extract(self, *, claim_id, canonical_text, emit_template):
        try:
            import anthropic
        except ImportError as e:
            raise LLMLiftError(
                "anthropic package not installed; pip install anthropic"
            ) from e
        client = anthropic.Anthropic()
        timeout_ms = int(os.environ.get("VERIFIER_LLM_TIMEOUT_MS", "30000"))
        prompt = (
            f"Extract a typed atom from this text matching the template.\n"
            f"Template: {emit_template}\nText: {canonical_text}\n"
            f"Respond with JSON only."
        )
        msg = client.messages.create(
            model=self.model,
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
            timeout=timeout_ms / 1000.0,
        )
        return json.loads(msg.content[0].text)


class LocalLift(LLMLiftProvider):
    # POSTs to a local Ollama HTTP endpoint.
    def __init__(self, model: str = "llama3:8b") -> None:
        self.model = model
        self.base_url = os.environ.get("OLLAMA_URL", "http://localhost:11434")

    def extract(self, *, claim_id, canonical_text, emit_template):
        import urllib.request
        prompt = (
            f"Extract a typed atom from this text matching the template.\n"
            f"Template: {emit_template}\nText: {canonical_text}\n"
            f"JSON only."
        )
        body = json.dumps({
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
        }).encode()
        timeout = int(os.environ.get("VERIFIER_LLM_TIMEOUT_MS", "30000")) / 1000.0
        req = urllib.request.Request(
            f"{self.base_url}/api/generate", data=body,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                payload = json.loads(resp.read())
        except urllib.error.URLError as e:
            raise LLMLiftError(f"ollama unreachable at {self.base_url}: {e}") from e
        return json.loads(payload["response"])


def get_provider() -> LLMLiftProvider:
    """Factory: read NEUROSYM_LLM_PROVIDER and return the right backend."""
    name = os.environ.get("NEUROSYM_LLM_PROVIDER", "stub").lower()
    return {
        "stub": StubLift(),
        "openai": OpenAILift(),
        "anthropic": AnthropicLift(),
        "local": LocalLift(),
    }[name]
```

- [ ] **P1.3: Run** the test — confirm PASS.

- [ ] **P1.4: Commit**

```bash
git commit -am "llm-lift: provider interface + Stub/OpenAI/Anthropic/Local backends (REQ-LLMLIFT-040, 041, 048)"
```

### Task P2: Schema validation

- [ ] **P2.1: Failing test for schema validation** (REQ-LLMLIFT-042, 043):

```python
def test_proposal_validated_against_schema(tmp_path):
    schema = tmp_path / "booklogic-schema.edn"
    schema.write_text(
        '{:version 1 :sorts [:trial] '
        ':predicates {:trial-n {:arg-sorts [:trial] :return :int}}}',
        encoding="utf-8",
    )
    from scripts._llm_lift import validate_proposal, LLMLiftRejected
    # Valid proposal
    atom = validate_proposal(schema, {"predicate": ":trial-n", "subject": ":t1", "value": 42})
    assert atom["predicate"] == ":trial-n"
    # Unknown predicate
    with pytest.raises(LLMLiftRejected):
        validate_proposal(schema, {"predicate": ":bogus", "subject": ":t1", "value": 42})
    # Wrong value sort (int predicate getting a float)
    with pytest.raises(LLMLiftRejected):
        validate_proposal(schema, {"predicate": ":trial-n", "subject": ":t1", "value": 42.5})
```

- [ ] **P2.2: Implement `validate_proposal(schema_path, proposal_dict)`** in `_llm_lift.py`:

```python
class LLMLiftRejected(ValueError):
    """Raised when the LLM's proposal fails schema validation."""


def validate_proposal(schema_path: Path, proposal: dict) -> dict:
    from scripts._io import read_edn_file
    from scripts._edn_reader import Keyword
    schema = read_edn_file(schema_path)
    predicates = schema.get(Keyword("predicates"), {})
    pred = proposal.get("predicate", "")
    pred_kw = Keyword(pred.lstrip(":")) if isinstance(pred, str) else pred
    if pred_kw not in predicates:
        raise LLMLiftRejected(
            f"unknown predicate {pred!r}; known: {sorted(map(str, predicates))}"
        )
    spec = predicates[pred_kw]
    expected_return = spec.get(Keyword("return"))
    value = proposal.get("value")
    return_kw = expected_return.name if hasattr(expected_return, "name") else expected_return
    if return_kw == "int" and not isinstance(value, int):
        raise LLMLiftRejected(f"predicate {pred!r} expects :int, got {type(value).__name__}")
    if return_kw == "real" and not isinstance(value, (int, float)):
        raise LLMLiftRejected(f"predicate {pred!r} expects :real, got {type(value).__name__}")
    if return_kw == "bool" and not isinstance(value, bool):
        raise LLMLiftRejected(f"predicate {pred!r} expects :bool, got {type(value).__name__}")
    return proposal
```

- [ ] **P2.3: Run** — confirm PASS.

- [ ] **P2.4: Commit**

```bash
git commit -am "llm-lift: schema validation for LLM proposals (REQ-LLMLIFT-042, 043)"
```

### Task P3: SQLite cache

- [ ] **P3.1: Failing test for cache idempotence** (REQ-LLMLIFT-045):

```python
def test_cache_returns_same_atom_on_repeat(tmp_path, monkeypatch):
    monkeypatch.setenv("NEUROSYM_LLM_CACHE", "1")
    monkeypatch.setenv("NEUROSYM_LLM_CACHE_PATH", str(tmp_path / "cache.db"))
    from scripts._llm_lift import cached_extract, StubLift
    provider = StubLift(canned_response='{"predicate": ":foo", "subject": ":s", "value": 1}')
    a1 = cached_extract(provider, claim_id="c1", canonical_text="x", emit_template="t")
    a2 = cached_extract(provider, claim_id="c1", canonical_text="x", emit_template="t")
    assert a1 == a2
    # Verify the second call was a cache hit
    import sqlite3
    db = sqlite3.connect(tmp_path / "cache.db")
    rows = list(db.execute("SELECT hit_count FROM cache_stats WHERE claim_id = 'c1'"))
    db.close()
    assert rows and rows[0][0] >= 1
```

- [ ] **P3.2: Implement `cached_extract`** + the SQLite schema (text-keyed cache, hit_count column for stats).

- [ ] **P3.3: Run** — confirm PASS.

- [ ] **P3.4: Commit**

```bash
git commit -am "llm-lift: SQLite cache + hit-count stats (REQ-LLMLIFT-045)"
```

### Task P4: ingest_ledger.py integration

- [ ] **P4.1: Modify `_apply_predicates`** in both `verifiers/osmotic_pressure/scripts/ingest_ledger.py` and `verifiers/bermuda/scripts/ingest_ledger.py` (and the new `adsc-clinical/scripts/ingest_ledger.py` from Phase O) to check the lift's `:backend` field. When `:backend :llm`, route to `_llm_lift.cached_extract` instead of `re.search`.

- [ ] **P4.2: Failing test** that an `:backend :llm` lift produces a defect when the stub returns a schema-invalid proposal, instead of silently OPAQUE:

```python
def test_llm_lift_reject_surfaces_as_defect(tmp_path):
    # Stub returns a predicate name not in the schema
    monkeypatch.setenv("NEUROSYM_LLM_PROVIDER", "stub")
    # ... (full test exercising ingest → defect path)
```

- [ ] **P4.3: Implement** the routing + defect emission.

- [ ] **P4.4: Commit**

```bash
git commit -am "ingest: :backend :llm routes to LLM provider with schema validation (REQ-LLMLIFT-040..044)"
```

### Task P5: SUPPORT_MATRIX update + drift lint

- [ ] **P5.1: Add row** to `skills/neurosym-forge/SUPPORT_MATRIX.md`:

```markdown
| `deflift :backend :llm` | wired (alpha) | scripts/_llm_lift.py | n/a |
```

- [ ] **P5.2: Update `test_support_matrix.py`** drift lint to assert the alpha qualifier.

- [ ] **P5.3: Commit**

```bash
git commit -am "support-matrix: deflift :backend :llm wired (alpha) (REQ-LLMLIFT-047)"
```

### Task P6: Push + open PR-P. Merge on green.

---

## Phase Q — Semantic retrieval (`tier5-semantic-retrieval`)

**Branch:** `feat/tier5-semantic-retrieval`
**Exit criteria:** `_semantic_index.py` ships a `SemanticIndex` class that embeds claims with sentence-transformers, persists to `.npz`, and exposes `similar_claims(claim_id, k)`. Verdict gains `:semantic-neighbours` per defect.

### Task Q1: SemanticIndex smoke

**Files:**
- Create: `skills/neurosym-forge/scripts/_semantic_index.py`
- Create: `skills/neurosym-forge/tests/test_semantic_index.py`

- [ ] **Q1.1: Failing smoke test** (REQ-RETRIEVAL-040, 045):

```python
"""REQ-RETRIEVAL-040, 045: SemanticIndex smoke."""
import pytest

pytest.importorskip("sentence_transformers")


def test_insert_then_top_1_is_self(tmp_path):
    from scripts._semantic_index import SemanticIndex
    idx = SemanticIndex(cache_path=tmp_path / "idx.npz")
    for i in range(10):
        idx.embed_claim(claim_id=f"c-{i}", text=f"observation about disease {i}")
    neighbours = idx.similar_claims("c-3", k=3)
    assert neighbours[0][0] == "c-3"
    assert abs(neighbours[0][1] - 1.0) < 1e-5
    assert -1.0 <= neighbours[0][1] <= 1.0


def test_persistence_round_trip(tmp_path):
    from scripts._semantic_index import SemanticIndex
    cache = tmp_path / "idx.npz"
    idx1 = SemanticIndex(cache_path=cache)
    idx1.embed_claim(claim_id="c-1", text="hello")
    idx1.save()
    idx2 = SemanticIndex(cache_path=cache)
    idx2.load()
    n = idx2.similar_claims("c-1", k=1)
    assert n[0][0] == "c-1"
```

- [ ] **Q1.2: Implement `_semantic_index.py`**:

```python
"""REQ-RETRIEVAL-040..046: vector embedding sidecar.

Default encoder: sentence-transformers/all-MiniLM-L6-v2 (384-dim).
Persists to a single .npz keyed by claims.edn SHA-256 (cache-invalidates
on claim-set change).
"""
from __future__ import annotations
import os
import hashlib
from pathlib import Path
from typing import Optional
import numpy as np


class EmbeddingUnavailableError(RuntimeError):
    """Embedding model unavailable (missing package, no network for first download)."""


class SemanticIndex:
    def __init__(self, *, cache_path: Optional[Path] = None,
                 model_name: Optional[str] = None) -> None:
        self._cache_path = Path(cache_path) if cache_path else None
        self._model_name = model_name or os.environ.get(
            "NEUROSYM_EMBED_MODEL",
            "sentence-transformers/all-MiniLM-L6-v2",
        )
        self._model = None
        self._claim_ids: list[str] = []
        self._embeddings: list[np.ndarray] = []
        self._claims_sha: str = ""

    def _ensure_model(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as e:
                raise EmbeddingUnavailableError(
                    "sentence-transformers not installed; "
                    "pip install sentence-transformers"
                ) from e
            self._model = SentenceTransformer(self._model_name)
        return self._model

    def embed_claim(self, *, claim_id: str, text: str) -> None:
        if claim_id in self._claim_ids:
            return  # idempotent
        vec = self._ensure_model().encode([text], normalize_embeddings=True)[0]
        self._claim_ids.append(claim_id)
        self._embeddings.append(np.asarray(vec, dtype=np.float32))

    def similar_claims(self, claim_id: str, k: int = 5) -> list[tuple[str, float]]:
        if claim_id not in self._claim_ids:
            raise KeyError(f"claim_id {claim_id!r} not in index")
        i = self._claim_ids.index(claim_id)
        query = self._embeddings[i]
        scored = [(cid, float(np.dot(query, emb)))
                  for cid, emb in zip(self._claim_ids, self._embeddings)]
        scored.sort(key=lambda kv: kv[1], reverse=True)
        return scored[:k]

    def count(self) -> int:
        return len(self._claim_ids)

    def save(self) -> None:
        if not self._cache_path:
            return
        self._cache_path.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(
            self._cache_path,
            claim_ids=np.asarray(self._claim_ids, dtype=object),
            embeddings=np.vstack(self._embeddings) if self._embeddings
                       else np.zeros((0, 384), dtype=np.float32),
            claims_sha=np.asarray([self._claims_sha], dtype=object),
        )

    def load(self) -> None:
        if not self._cache_path or not self._cache_path.exists():
            return
        z = np.load(self._cache_path, allow_pickle=True)
        self._claim_ids = list(z["claim_ids"])
        self._embeddings = list(z["embeddings"])
        self._claims_sha = str(z["claims_sha"][0]) if "claims_sha" in z.files else ""

    def invalidate_if_claims_changed(self, claims_text: str) -> None:
        current_sha = hashlib.sha256(claims_text.encode("utf-8")).hexdigest()
        if self._claims_sha and self._claims_sha != current_sha:
            self._claim_ids = []
            self._embeddings = []
        self._claims_sha = current_sha
```

- [ ] **Q1.3: Run** — confirm PASS (with sentence-transformers installed).

- [ ] **Q1.4: Commit**

```bash
git commit -am "semantic: SemanticIndex with sentence-transformers + .npz persistence (REQ-RETRIEVAL-040, 041, 045)"
```

### Task Q2: Missing-model error

- [ ] **Q2.1: Test** (REQ-RETRIEVAL-042) — when sentence_transformers is missing, the error names the install command. (Pattern matches the Phase A test_extract_preview unavailable path.)

- [ ] **Q2.2: Confirm Q1.2's implementation already does this**. Verify in test.

- [ ] **Q2.3: Commit**

```bash
git commit -am "semantic: missing-model error names remediation (REQ-RETRIEVAL-042)"
```

### Task Q3: `make index-semantic` target

- [ ] **Q3.1: Add `index-semantic` target** to `verifiers/*/Makefile` + the scaffold template:

```makefile
index-semantic:
	@if [ -f work/claims.edn ]; then \
	  python scripts/build_semantic_index.py; \
	else \
	  echo "[index-semantic] no work/claims.edn; run make extract first"; \
	fi
```

- [ ] **Q3.2: Create `scripts/build_semantic_index.py`** that reads `claims.edn`, embeds each atom's `canonical_text`, saves to `work/semantic-index.npz`.

- [ ] **Q3.3: Commit**

```bash
git commit -am "make: index-semantic target via SemanticIndex (REQ-RETRIEVAL-043)"
```

### Task Q4: Verdict :semantic-neighbours field

- [ ] **Q4.1: Update Rust `Verdict` struct** in both verifiers' `ir.rs` to add `pub semantic_neighbours: Vec<NeighbourEntry>`.

- [ ] **Q4.2: Update `verdict_to_qa.py`** to attach the top-3 neighbours per defect (read from the .npz produced in Q3).

- [ ] **Q4.3: Commit**

```bash
git commit -am "verdict: :semantic-neighbours field per defect (REQ-RETRIEVAL-044)"
```

### Task Q5: Push + open PR-Q. Merge on green.

---

## Phase R — Cross-chapter (`tier5-cross-chapter`)

**Branch:** `feat/tier5-cross-chapter`
**Exit criteria:** `defconstraint :scope :corpus` constraints run over the union of all subjects' atoms; the verdict surfaces `:corpus-defects`.

### Task R1: `:scope :corpus` parsing + codegen

**Files:**
- Modify: `verifiers/*/cljs-orchestrator/src/main/*/booklogic.cljs`
- Modify: `skills/neurosym-forge/assets/project-template/cljs-orchestrator/.../booklogic.cljs.tmpl`
- Modify: `skills/neurosym-forge/scripts/codegen_axioms.py`
- Modify: `verifiers/*/scripts/_codegen_axioms_lib.py` (re-vendor)

- [ ] **R1.1: Failing test for the CLJS expand-defconstraint accepting `:scope :corpus`** (REQ-CORPUS-050):

```clojure
(deftest expand-defconstraint-scope-corpus
  (let [src {:sorts [(list 'defsort :trial)]
             :predicates [(list 'defpredicate :trial-n [:trial] :int)]
             :constraints [(list 'defconstraint :C001-cross
                                 :backend :z3
                                 :scope :corpus
                                 :assert '(approx= (:trial-n ?t1) (:trial-n ?t2) :tolerance 0)
                                 :on-unsat {:defect :D-Cross :severity :high :message "n mismatch"})]
             :lifts [] :rules [] :queries [] :remedies []}
        expanded (bl/expand src)
        c (first (:constraint-decls expanded))]
    (is (= :corpus (:scope c)))))
```

- [ ] **R1.2: Modify `expand-defconstraint`** in all three CLJS locations to accept the `:scope` option (default `:subject`).

- [ ] **R1.3: Failing test for codegen emission** of `axioms_corpus`:

```python
def test_corpus_scope_constraint_emits_axioms_corpus():
    constraint = read_edn(
        '{:id "C-corp" :backend :z3 :scope :corpus '
        ':assert (>= (:trial-n ?t) 10) '
        ':on-unsat {:defect :D :severity :high :message "x"}}'
    )
    src = generate_axioms_source([constraint])
    assert "pub fn axioms_corpus" in src
    assert '"C-corp"' in src  # emitted in axioms_corpus body, not axioms_for_subject
```

- [ ] **R1.4: Implement `:scope` dispatch** in codegen — `:subject` constraints flow into per-subject blocks (existing Phase J behaviour); `:corpus` constraints land in a new `axioms_corpus()` accessor body.

- [ ] **R1.5: Re-vendor codegen lib copies; diff to confirm byte-identity.**

- [ ] **R1.6: Commit**

```bash
git commit -am "codegen: emit axioms_corpus for :scope :corpus constraints (REQ-CORPUS-050, 051)"
```

### Task R2: Rust check_all calls axioms_corpus

- [ ] **R2.1: Modify `smt::check_all`** in both verifiers to: after running per-subject partitions, run a final `axioms_corpus` solver instance over the union of all subjects' atoms; record any `:unsat` as a corpus-scope defect.

- [ ] **R2.2: Cargo integration test** with a 2-trial fixture where the corpus-scope constraint requires `(>= :trial-n 10)`, one trial has n=15 (passes), the other has n=5 (fails); assert the corpus-defect surfaces.

- [ ] **R2.3: Commit**

```bash
git commit -am "smt: check_all runs axioms_corpus on union of subjects (REQ-CORPUS-052, 053)"
```

### Task R3: Verdict :corpus-defects

- [ ] **R3.1: Update Verdict struct** in `ir.rs` with `pub corpus_defects: Vec<CorpusDefect>` carrying the conflicting subjects in the explanation.

- [ ] **R3.2: Update `verdict_to_qa.py`** to read the new field.

- [ ] **R3.3: Commit**

```bash
git commit -am "verdict: :corpus-defects field surfaces cross-chapter failures (REQ-CORPUS-053)"
```

### Task R4: SUPPORT_MATRIX + DSL reference update

- [ ] **R4.1: Add a "Scope" subsection** to `docs/booklogic-dsl-reference.md` §2.5 — document `:scope :subject` (default) vs `:scope :corpus`.

- [ ] **R4.2: Update SUPPORT_MATRIX.md** legend section to define the scope modifier.

- [ ] **R4.3: Commit**

```bash
git commit -am "docs(dsl): :scope :corpus subsection in §2.5 (REQ-CORPUS-055)"
```

### Task R5: Push + open PR-R. Merge on green.

---

## Phase S — Confidence propagation (`tier5-confidence-propagation`)

**Branch:** `feat/tier5-confidence-propagation`
**Exit criteria:** Every defect carries a `:defect-confidence` float; low-confidence defects are downgraded to `:severity :advisory`; the verdict's top-level has `:verdict-confidence`.

### Task S1: Defect-confidence field

- [ ] **S1.1: Failing test** (REQ-CONFIDENCE-040, 041, 045):

```python
def test_defect_confidence_is_min_of_chain():
    """REQ-CONFIDENCE-040: defect-confidence = min of unsat-core atom confidences."""
    from scripts.verdict_to_qa import compute_defect_confidence
    chain_atoms = [
        {"id": "c-1", "confidence": 0.85},
        {"id": "c-2", "confidence": 0.62},
        {"id": "c-3", "confidence": 0.92},
    ]
    assert compute_defect_confidence(chain_atoms) == pytest.approx(0.62)


def test_low_confidence_defect_downgrades_to_advisory(monkeypatch):
    """REQ-CONFIDENCE-041: below threshold downgrades severity."""
    monkeypatch.setenv("VERIFIER_CONFIDENCE_THRESHOLD", "0.5")
    from scripts.verdict_to_qa import apply_confidence_downgrade
    defect_high = {"severity": "critical", "defect_confidence": 0.85}
    apply_confidence_downgrade(defect_high)
    assert defect_high["severity"] == "critical"
    defect_low = {"severity": "critical", "defect_confidence": 0.3}
    apply_confidence_downgrade(defect_low)
    assert defect_low["severity"] == "advisory"
```

- [ ] **S1.2: Implement `compute_defect_confidence` + `apply_confidence_downgrade`** in `verdict_to_qa.py` (both verifiers).

- [ ] **S1.3: Run** — confirm PASS.

- [ ] **S1.4: Commit**

```bash
git commit -am "verdict: :defect-confidence (min-of-chain) + advisory downgrade (REQ-CONFIDENCE-040, 041)"
```

### Task S2: Top-level :verdict-confidence

- [ ] **S2.1: Failing test** (REQ-CONFIDENCE-042) — verdict's top-level field = geometric mean of all defect confidences.

```python
def test_verdict_confidence_is_geometric_mean():
    from scripts.verdict_to_qa import compute_verdict_confidence
    defects = [{"defect_confidence": 0.8}, {"defect_confidence": 0.5}, {"defect_confidence": 0.9}]
    expected = (0.8 * 0.5 * 0.9) ** (1.0 / 3)
    assert compute_verdict_confidence(defects) == pytest.approx(expected, rel=1e-6)
```

- [ ] **S2.2: Implement**.

- [ ] **S2.3: Commit**

```bash
git commit -am "verdict: top-level :verdict-confidence as geometric mean (REQ-CONFIDENCE-042)"
```

### Task S3: Confidence validation at ingest

- [ ] **S3.1: Failing test** (REQ-CONFIDENCE-043) — out-of-range confidence raises clear error.

- [ ] **S3.2: Implement** validation in `ingest_ledger.py` (the field is already captured; just add the range check).

- [ ] **S3.3: Commit**

```bash
git commit -am "ingest: validate :confidence ∈ [0, 1] at ingest (REQ-CONFIDENCE-043)"
```

### Task S4: :advisory-defects array in QA output

- [ ] **S4.1: Modify `verdict_to_qa.py`** to split defects into `:critical-defects` (above threshold) and `:advisory-defects` (below) in the emitted JSON (REQ-CONFIDENCE-044).

- [ ] **S4.2: Commit**

```bash
git commit -am "verdict_to_qa: split into :critical-defects and :advisory-defects (REQ-CONFIDENCE-044)"
```

### Task S5: Push + open PR-S. Merge on green.

---

## Phase T — Publication bridge (`tier5-publication-bridge`)

**Branch:** `feat/tier5-publication-bridge`
**Exit criteria:** `verdict_to_qa.py` emits `manuscript-annotations.json`; `render_annotations.py` produces an annotated HTML overlay; `forge render` (or `make render`) invokes the chain.

### Task T1: manuscript-annotations.json schema

- [ ] **T1.1: Failing test** (REQ-PUB-040) — verdict_to_qa produces a JSON file with the right schema:

```python
def test_manuscript_annotations_schema(tmp_path):
    from scripts.verdict_to_qa import emit_manuscript_annotations
    verdict = {
        "status": "unsat",
        "defects": [
            {"claim_id": "c-001", "source_span": [120, 145],
             "severity": "critical", "message": "low n",
             "defect_confidence": 0.92},
        ],
    }
    out = tmp_path / "manuscript-annotations.json"
    emit_manuscript_annotations(verdict, source_path="report.md", out_path=out)
    import json
    data = json.loads(out.read_text())
    assert data["version"] == 1
    assert data["source_path"] == "report.md"
    assert len(data["annotations"]) == 1
    ann = data["annotations"][0]
    assert ann["claim_id"] == "c-001"
    assert ann["source_span"] == [120, 145]
```

- [ ] **T1.2: Implement `emit_manuscript_annotations`**.

- [ ] **T1.3: Commit**

```bash
git commit -am "pub: emit manuscript-annotations.json with versioned schema (REQ-PUB-040)"
```

### Task T2: Markdown → HTML overlay renderer

- [ ] **T2.1: Failing test** (REQ-PUB-041) — `render_annotations.py` produces HTML where each defect's source span is wrapped in `<mark>`:

```python
def test_render_overlays_marks(tmp_path):
    from scripts.render_annotations import render_html
    md = "The trial enrolled 42 patients with no adverse events."
    annotations = {
        "version": 1,
        "source_path": "src.md",
        "annotations": [
            {"claim_id": "c-001", "source_span": [4, 9],
             "severity": "critical", "message": "trial size below minimum",
             "defect_confidence": 0.9},
        ],
    }
    html = render_html(md, annotations)
    assert '<mark class="severity-critical"' in html
    assert "trial size below minimum" in html
    assert html.count("<mark") == 1
```

- [ ] **T2.2: Implement `render_html`** in `skills/neurosym-forge/scripts/render_annotations.py`.

- [ ] **T2.3: Commit**

```bash
git commit -am "pub: markdown→HTML overlay renderer with severity classes (REQ-PUB-041)"
```

### Task T3: Stale-span warning + skip

- [ ] **T3.1: Failing test** (REQ-PUB-043) — when source_span is out of bounds, renderer emits a warning and skips that annotation.

- [ ] **T3.2: Implement**.

- [ ] **T3.3: Commit**

```bash
git commit -am "pub: stale-span warning + skip (REQ-PUB-043)"
```

### Task T4: CLI entry point

- [ ] **T4.1: Add `make render` target** to each verifier's Makefile + scaffold template.

```makefile
render:
	python scripts/render_annotations.py \
	  --source $(MANUSCRIPT) \
	  --annotations work/manuscript-annotations.json \
	  --out-dir work/render
```

- [ ] **T4.2: Commit**

```bash
git commit -am "make: render target (REQ-PUB-044)"
```

### Task T5: defect-index.html + see-also from Phase Q

- [ ] **T5.1: Implement defect-index summary HTML** with clickable jumps + see-also links from Phase Q's semantic-neighbours (REQ-PUB-042, 045).

- [ ] **T5.2: Commit**

```bash
git commit -am "pub: defect-index.html + see-also semantic neighbours (REQ-PUB-042, 045)"
```

### Task T6: Push + open PR-T. Merge on green.

---

## Phase U — Author CLI (`tier5-author-cli`)

**Branch:** `feat/tier5-author-cli`
**Exit criteria:** `forge` CLI ships with subcommands `add-constraint`, `suggest-lifts`, `explain-defect`, `similar`, `render`. Each subcommand has a passing test against fixtures.

### Task U1: CLI skeleton

**Files:**
- Create: `skills/neurosym-forge/scripts/forge_cli.py`
- Modify: `skills/neurosym-forge/pyproject.toml` (entry point)
- Create: `skills/neurosym-forge/tests/test_forge_cli.py`

- [ ] **U1.1: Failing test for `forge --help`** (REQ-AUTHOR-040):

```python
def test_forge_help_lists_subcommands():
    import subprocess, sys
    result = subprocess.run(
        [sys.executable, "-m", "scripts.forge_cli", "--help"],
        capture_output=True, text=True, cwd="skills/neurosym-forge",
    )
    assert result.returncode == 0
    for sub in ("add-constraint", "suggest-lifts", "explain-defect", "similar", "render"):
        assert sub in result.stdout
```

- [ ] **U1.2: Implement `forge_cli.py` skeleton** with click:

```python
"""REQ-AUTHOR-040..046: interactive author CLI."""
from __future__ import annotations
import click


@click.group()
def cli():
    """Forge — author tooling for neurosym-forge verifiers."""


@cli.command("add-constraint")
@click.option("--id", "constraint_id", required=False)
@click.option("--backend", default=":z3")
@click.argument("project_root", type=click.Path(exists=True))
def add_constraint(constraint_id, backend, project_root):
    """Interactively add a defconstraint form."""
    # ... prompt-based flow per REQ-AUTHOR-041
    click.echo("add-constraint not yet wired")


# Stubs for suggest-lifts, explain-defect, similar, render — wired in later tasks


def main():
    cli()


if __name__ == "__main__":
    main()
```

- [ ] **U1.3: Add `forge` entry-point** to `pyproject.toml`:

```toml
[project.scripts]
forge = "scripts.forge_cli:main"
```

- [ ] **U1.4: Run** — confirm PASS.

- [ ] **U1.5: Commit**

```bash
git commit -am "cli: forge skeleton with 5 subcommands (REQ-AUTHOR-040)"
```

### Task U2: forge add-constraint

- [ ] **U2.1: Failing test** that runs `forge add-constraint` in non-interactive mode (`--non-interactive --id C-test --assert "(>= x 10)" --on-unsat-defect D-LowX --on-unsat-severity advisory`) and verifies the constraint lands in `rules/booklogic/constraints.edn`.

- [ ] **U2.2: Implement the non-interactive flow + interactive prompts** (REQ-AUTHOR-041).

- [ ] **U2.3: Commit**

```bash
git commit -am "cli(forge): add-constraint subcommand (REQ-AUTHOR-041)"
```

### Task U3: forge suggest-lifts

- [ ] **U3.1: Failing test** that suggest-lifts on a known unmatched claim returns candidate `deflift` forms.

- [ ] **U3.2: Implement** — call Phase P's `_llm_lift.get_provider().extract(...)`, type-check against schema, emit candidate `deflift` forms (REQ-AUTHOR-042).

- [ ] **U3.3: Commit**

```bash
git commit -am "cli(forge): suggest-lifts subcommand calling Phase P LLM provider (REQ-AUTHOR-042)"
```

### Task U4: forge explain-defect

- [ ] **U4.1: Failing test** that explain-defect against a fixture verdict prints the unsat-core chain + confidences + source span.

- [ ] **U4.2: Implement** (REQ-AUTHOR-043).

- [ ] **U4.3: Commit**

```bash
git commit -am "cli(forge): explain-defect subcommand (REQ-AUTHOR-043)"
```

### Task U5: forge similar + forge render

- [ ] **U5.1: Implement `forge similar`** wrapping Phase Q's `similar_claims` (REQ-AUTHOR-044).

- [ ] **U5.2: Implement `forge render`** wrapping Phase T's `render_annotations.py` (consistent invocation surface; the make target stays for non-CLI users).

- [ ] **U5.3: Commit**

```bash
git commit -am "cli(forge): similar + render subcommands (REQ-AUTHOR-044, plus Phase T integration)"
```

### Task U6: Error UX

- [ ] **U6.1: Failing test** that any forge subcommand failing produces a hand-readable error with `--debug` hint, not a stack trace (REQ-AUTHOR-045).

- [ ] **U6.2: Implement** error-decorator wrapping each subcommand.

- [ ] **U6.3: Commit**

```bash
git commit -am "cli(forge): hand-readable errors with --debug hint (REQ-AUTHOR-045)"
```

### Task U7: Push + open PR-U. Merge on green.

---

## Self-review

**Spec coverage** (every REQ has a task):
- Phase O: REQ-CORPUS-040..046 — Tasks O1-O5 (7 REQs, all covered) ✓
- Phase P: REQ-LLMLIFT-040..048 — Tasks P1-P5 (9 REQs, all covered) ✓
- Phase Q: REQ-RETRIEVAL-040..046 — Tasks Q1-Q4 (7 REQs, all covered) ✓
- Phase R: REQ-CORPUS-050..056 — Tasks R1-R4 (7 REQs, all covered) ✓
- Phase S: REQ-CONFIDENCE-040..045 — Tasks S1-S4 (6 REQs, all covered) ✓
- Phase T: REQ-PUB-040..046 — Tasks T1-T5 (7 REQs, all covered) ✓
- Phase U: REQ-AUTHOR-040..046 — Tasks U1-U6 (7 REQs, all covered) ✓

Total: 50 REQs across 7 phases.

**Placeholder scan:** No "TBD", no "TODO". Some tasks (e.g., R1.1's CLJS expand test) cite the existing CLJS test pattern via the worked code in REQ-CORPUS-050; engineers consult the existing `booklogic_test.cljs.tmpl` for the surrounding test infrastructure (`deftest`, `bl/expand`, etc.). That's a pointer, not a placeholder.

**Type consistency:**
- `LLMLiftProvider` + `extract(claim_id, canonical_text, emit_template)` signature — P1.1, P1.2, P3.2, U3.2 all consistent ✓
- `SemanticIndex` + `embed_claim(claim_id, text)` / `similar_claims(claim_id, k)` — Q1.1, Q1.2, U5.1, T5.1 all consistent ✓
- `:scope` modifier values `:subject` / `:corpus` — R1.1, R1.4, R2.1 consistent ✓
- `compute_defect_confidence(atoms) -> float` — S1.1, S1.2 consistent ✓
- `emit_manuscript_annotations(verdict, source_path, out_path)` — T1.1, T1.2 consistent ✓
- Verdict shape evolution: `:semantic-neighbours` (Phase Q), `:corpus-defects` (Phase R), `:defect-confidence` (Phase S), `:verdict-confidence` (Phase S), `:critical-defects` / `:advisory-defects` (Phase S split) — additive, no conflicts ✓

Plan complete. Successor execution per superpowers:subagent-driven-development or superpowers:executing-plans.

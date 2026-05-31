# syntopical-metabook v0.3 — Generalization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn `syntopical-metabook` into a general-purpose, domain-agnostic skill whose advertised surface matches what it does — wake the four dormant sub-workflows as CLI-reachable capabilities, strip every consensus-crypto reference, fix the two governance functional gaps (defconstraint support, staleness guard), and ship a QA plan plus a utility/value plan.

**Architecture:** A new `forge meta` click group mirrors the existing `forge govern` group, each subcommand a thin lazy-import wrapper over an existing sub-workflow entry point. `skill_api.py` grows to export all five capabilities (API 0.3). Governance gains a second rule source (`rules/constraints.edn`) feeding the unchanged stance-derivation engine, plus a shared staleness helper the three renderers consult. De-specialization is confined to docs and fixtures; the four sub-workflows are already domain-neutral.

**Tech Stack:** Python 3.11+, `click` (forge CLI), EDN (tolerant regex readers), pytest. No new third-party dependencies.

**Spec:** `docs/superpowers/specs/2026-05-31-syntopical-metabook-v0.3-generalization-design.md` (commit `f9b5f9f`, branch `feat/syntopical-metabook-v0.3-generalization`).

---

## Environment note for the executing engineer

In the authoring session the Read/Grep tools intermittently elided function bodies (showing `...`) for files under `skills/syntopical-metabook/`. **Before editing any existing file, re-read it in full** to confirm its current contents. `wc -l` line counts are reliable; verified counts: `expand_seeds.py` 97, `triage.py` 120, `rank_candidates.py` 96, `download_and_ingest.py` 129, `veto.py` ~40, `test_acquire_e2e.py` 97, `test_end_to_end.py` 156, `build_positions.py` 132, `render_per_rule.py` 91. The four sub-workflows are fully implemented and tested — not stubs.

## Paths and conventions

- Skill root: `skills/syntopical-metabook/` (abbreviated `SM/` below).
- Run the skill's tests from `SM/` with its venv: `./.venv/Scripts/python.exe -m pytest`.
- Forge CLI: `skills/neurosym-forge/scripts/forge_cli.py` (abbreviated `forge_cli.py`). Run its tests from `skills/neurosym-forge/`.
- All generated artifacts are byte-deterministic (no embedded timestamp in the body; provenance footer omits time). Preserve this in every writer.
- Commit messages: terse, no AI attribution.

## File structure

```
skills/syntopical-metabook/
├── scripts/
│   ├── _staleness.py                       NEW (PR 1) — shared mtime guard
│   ├── governance/
│   │   ├── build_positions.py              MODIFY (PR 1) — read rules/constraints.edn
│   │   ├── _constraints.py                 NEW (PR 1) — tolerant defconstraint reader
│   │   ├── render_per_rule.py              MODIFY (PR 1) — call staleness guard
│   │   ├── render_consensus_map.py         MODIFY (PR 1) — call staleness guard
│   │   └── render_adversarial.py           MODIFY (PR 1) — call staleness guard
│   ├── acquire/pipeline.py                 NEW (PR 3) — run_acquire orchestrator
│   └── synthesize/run_synthesize.py        NEW (PR 3) — run_synthesize orchestrator
├── skill_api.py                            MODIFY (PR 2 version, PR 3 exports)
├── SKILL.md                                MODIFY (PR 2)
├── references/
│   ├── governance-playbook.md              MODIFY (PR 2) — neutral examples
│   ├── acquire-playbook.md                 NEW (PR 3)
│   ├── synthesize-playbook.md              NEW (PR 3)
│   └── lens-and-gap-playbook.md            NEW (PR 3)
├── tests/
│   ├── unit/
│   │   ├── test_staleness.py               NEW (PR 1)
│   │   ├── test_constraints_reader.py      NEW (PR 1)
│   │   └── test_render_staleness.py        NEW (PR 1)
│   ├── integration/
│   │   ├── test_governance_defconstraint.py NEW (PR 1)
│   │   ├── test_acquire_orchestrator.py    NEW (PR 3)
│   │   └── test_synthesize_orchestrator.py NEW (PR 3)
│   ├── conformance/
│   │   ├── test_neutral_workspace.py       NEW (PR 1) — replaces epochpoet test
│   │   └── test_epochpoet_governance.py    DELETE (PR 1)
│   └── fixtures/workspaces/
│       ├── three-schools/                  RETHEME (PR 2) — neutral slugs
│       └── neutral-conformance/            NEW (PR 1) — schools + constraints + induced
└── docs/superpowers/plans/
    ├── 2026-05-31-syntopical-metabook-qa-plan.md       NEW (PR 4)
    └── 2026-05-31-syntopical-metabook-utility.md       NEW (PR 4)

skills/neurosym-forge/
├── scripts/forge_cli.py                    MODIFY (PR 3) — forge meta group
└── tests/test_forge_cli_meta.py            NEW (PR 3)
```

---

# PR 1 — Governance functional fixes (defconstraint + staleness + neutral conformance)

Lands the two functional gaps and a domain-neutral conformance canary that always runs. The neutral conformance workspace includes a `constraints.edn` so the new defconstraint path is exercised.

### Task 1: Shared staleness helper

**Files:**
- Create: `SM/scripts/_staleness.py`
- Test: `SM/tests/unit/test_staleness.py`

- [ ] **Step 1: Write the failing test**

```python
# SM/tests/unit/test_staleness.py
"""Staleness guard: positions.edn must be newer than its source ledgers."""
from __future__ import annotations
import os
import pytest
from scripts._staleness import StaleArtifactError, check_not_stale


def _touch(path, mtime):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("x", encoding="utf-8")
    os.utime(path, (mtime, mtime))


def test_passes_when_artifact_newer(tmp_path):
    src = tmp_path / "ledger.jsonl"
    art = tmp_path / "positions.edn"
    _touch(src, 1000)
    _touch(art, 2000)
    check_not_stale(art, [src])  # no raise


def test_raises_when_artifact_older(tmp_path):
    src = tmp_path / "ledger.jsonl"
    art = tmp_path / "positions.edn"
    _touch(src, 2000)
    _touch(art, 1000)
    with pytest.raises(StaleArtifactError, match="run `forge govern build`"):
        check_not_stale(art, [src])


def test_missing_sources_are_ignored(tmp_path):
    art = tmp_path / "positions.edn"
    _touch(art, 1000)
    check_not_stale(art, [tmp_path / "absent.jsonl"])  # no raise


def test_missing_artifact_raises(tmp_path):
    art = tmp_path / "positions.edn"
    with pytest.raises(StaleArtifactError, match="does not exist"):
        check_not_stale(art, [])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd SM && ./.venv/Scripts/python.exe -m pytest tests/unit/test_staleness.py -v`
Expected: FAIL — `ModuleNotFoundError: scripts._staleness`.

- [ ] **Step 3: Write minimal implementation**

```python
# SM/scripts/_staleness.py
"""Refuse to render from an artifact older than its source ledgers."""
from __future__ import annotations
from pathlib import Path


class StaleArtifactError(RuntimeError):
    """Raised when a generated artifact is older than a source it derives from."""


def check_not_stale(artifact: Path, sources: list[Path]) -> None:
    """Raise StaleArtifactError if `artifact` is missing or older than any
    existing path in `sources`. Missing sources are ignored."""
    artifact = Path(artifact)
    if not artifact.exists():
        raise StaleArtifactError(
            f"{artifact} does not exist. Run `forge govern build` first."
        )
    art_mtime = artifact.stat().st_mtime
    for src in sources:
        src = Path(src)
        if src.exists() and src.stat().st_mtime > art_mtime:
            raise StaleArtifactError(
                f"{artifact.name} is stale relative to {src.name}; "
                f"run `forge govern build` first."
            )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd SM && ./.venv/Scripts/python.exe -m pytest tests/unit/test_staleness.py -v`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add SM/scripts/_staleness.py SM/tests/unit/test_staleness.py
git commit -m "governance: shared staleness guard helper"
```

### Task 2: Wire staleness guard into the three renderers

**Files:**
- Modify: `SM/scripts/governance/render_per_rule.py` (function `render_per_rule`)
- Modify: `SM/scripts/governance/render_consensus_map.py` (function `render_consensus_map`)
- Modify: `SM/scripts/governance/render_adversarial.py` (function `render_adversarial`)
- Test: `SM/tests/unit/test_render_staleness.py`

The source ledgers a positions file derives from live at `<workspace>/knowledge/claims/ledger.jsonl`, `<workspace>/rules/booklogic/induced-theory.prov.edn`, and `<workspace>/rules/constraints.edn`. The renderers receive a `positions_path`; derive the workspace root as `positions_path.parents[1]` (positions.edn lives at `<ws>/syntopical/positions.edn`).

- [ ] **Step 1: Write the failing test**

```python
# SM/tests/unit/test_render_staleness.py
"""Renderers refuse a positions.edn older than its source ledgers."""
from __future__ import annotations
import os
import pytest
from scripts._staleness import StaleArtifactError
from scripts.governance._stance import Stance
from scripts.governance._positions_io import Position, write_positions
from scripts.governance.render_per_rule import render_per_rule


def _ws(tmp_path):
    ws = tmp_path / "ws"
    (ws / "syntopical").mkdir(parents=True)
    (ws / "knowledge" / "claims").mkdir(parents=True)
    return ws


def _pos():
    return Position(
        rule_id="r1", rule_form="", source="induced", school="school-a",
        stance=Stance.SUPPORTS, supporting_atoms=[], supporting_docs=[],
        contradicting_atoms=[], contradicting_docs=[],
        declared_by_charter=False, induction_prov="",
    )


def test_render_per_rule_refuses_stale(tmp_path):
    ws = _ws(tmp_path)
    positions = ws / "syntopical" / "positions.edn"
    write_positions(positions, [_pos()], generated_at="2026-05-31T00:00:00Z")
    ledger = ws / "knowledge" / "claims" / "ledger.jsonl"
    ledger.write_text("{}\n", encoding="utf-8")
    # make the ledger newer than positions
    os.utime(positions, (1000, 1000))
    os.utime(ledger, (2000, 2000))
    with pytest.raises(StaleArtifactError):
        render_per_rule(positions, ws / "syntopical" / "rules")


def test_render_per_rule_runs_when_fresh(tmp_path):
    ws = _ws(tmp_path)
    positions = ws / "syntopical" / "positions.edn"
    write_positions(positions, [_pos()], generated_at="2026-05-31T00:00:00Z")
    ledger = ws / "knowledge" / "claims" / "ledger.jsonl"
    ledger.write_text("{}\n", encoding="utf-8")
    os.utime(ledger, (1000, 1000))
    os.utime(positions, (2000, 2000))
    n = render_per_rule(positions, ws / "syntopical" / "rules")
    assert n == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd SM && ./.venv/Scripts/python.exe -m pytest tests/unit/test_render_staleness.py -v`
Expected: FAIL — `test_render_per_rule_refuses_stale` does not raise (no guard yet).

- [ ] **Step 3: Add the guard to each renderer**

In `render_per_rule.py`, add the import near the top:

```python
from .._staleness import check_not_stale
```

Then at the top of `render_per_rule(positions_path, out_dir)`, before `rows = read_positions(...)`:

```python
def render_per_rule(positions_path: Path, out_dir: Path) -> int:
    positions_path = Path(positions_path)
    ws = positions_path.parents[1]
    check_not_stale(positions_path, [
        ws / "knowledge" / "claims" / "ledger.jsonl",
        ws / "rules" / "booklogic" / "induced-theory.prov.edn",
        ws / "rules" / "constraints.edn",
    ])
    rows = read_positions(positions_path)
    # ... unchanged ...
```

Apply the identical import and the identical guard block (same three source paths) to the public entry function in `render_consensus_map.py` (`render_consensus_map(positions_path, out_dir)`) and `render_adversarial.py` (`render_adversarial(positions_path, out_path, config)`), each immediately before the existing `read_positions(...)` call.

- [ ] **Step 4: Run the full governance suite**

Run: `cd SM && ./.venv/Scripts/python.exe -m pytest tests/unit/test_render_staleness.py tests/unit/test_governance_per_rule.py tests/unit/test_governance_consensus.py tests/unit/test_governance_adversarial.py -v`
Expected: PASS. The pre-existing renderer tests write positions.edn last (so it is newest) and continue to pass; if any pre-existing test now fails on staleness, it is because its fixture writes a source after positions.edn — fix that test by writing positions.edn last, not by weakening the guard.

- [ ] **Step 5: Commit**

```bash
git add SM/scripts/governance/render_per_rule.py SM/scripts/governance/render_consensus_map.py SM/scripts/governance/render_adversarial.py SM/tests/unit/test_render_staleness.py
git commit -m "governance: renderers refuse stale positions.edn"
```

### Task 3: Confirm the defconstraint EDN shape

**Files:** (read-only investigation)
- Read: `forge_cli.py` function `_render_constraint` (around line 134) to see exactly what `forge add-constraint` writes.
- Read: any existing `rules/constraints.edn` in a real workspace (e.g. `/c/epochpoet/rules/constraints.edn` or `/c/epochpoet/rules/booklogic/constraints.edn`) if present.

- [ ] **Step 1: Capture the format**

Run:
```bash
sed -n '127,170p' skills/neurosym-forge/scripts/forge_cli.py
find /c/epochpoet -name 'constraints.edn' 2>/dev/null -exec sed -n '1,40p' {} \;
```

Record the actual keys of a `defconstraint` form. The reader in Task 4 must match them. The remainder of this plan assumes each constraint is an EDN map keyed by a constraint id with a `:derive-via` vector of claim-ids, e.g.:

```clojure
{:version 1
 :constraints
 {":C001-method-x" {:assert "(>= bond floor)"
                    :derive-via ["clm-2026-000001" "clm-2026-000002"]
                    :on-unsat-defect ":D1"}}}
```

If the real format differs (different key for the claim links, or a flat list instead of a map), adjust the regexes in Task 4 and the fixture in Task 5 to match the real shape before proceeding. Do not invent a format the toolchain does not emit.

- [ ] **Step 2: Commit (notes only, if any)**

No code change. If you discover the format differs from the assumption above, note it in the commit body of Task 4.

### Task 4: Tolerant defconstraint reader

**Files:**
- Create: `SM/scripts/governance/_constraints.py`
- Test: `SM/tests/unit/test_constraints_reader.py`

- [ ] **Step 1: Write the failing test**

```python
# SM/tests/unit/test_constraints_reader.py
"""Tolerant reader for rules/constraints.edn → per-rule support sets."""
from __future__ import annotations
import textwrap
from scripts.governance._constraints import load_constraints


def _write(p, text):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(textwrap.dedent(text), encoding="utf-8")
    return p


def test_load_constraints_pulls_id_and_claims(tmp_path):
    f = _write(tmp_path / "constraints.edn", """
        {:version 1
         :constraints
         {":C001-method-x" {:assert "(>= bond floor)"
                            :derive-via ["clm-2026-000001" "clm-2026-000002"]}
          ":C002-other"    {:assert "(= a b)"
                            :derive-via ["clm-2026-000004"]}}}
    """)
    out = load_constraints(f)
    assert set(out) == {":C001-method-x", ":C002-other"}
    assert out[":C001-method-x"]["atoms"] == ["clm-2026-000001", "clm-2026-000002"]
    assert out[":C002-other"]["atoms"] == ["clm-2026-000004"]


def test_missing_file_returns_empty(tmp_path):
    assert load_constraints(tmp_path / "absent.edn") == {}


def test_constraint_without_derive_via_has_empty_atoms(tmp_path):
    f = _write(tmp_path / "constraints.edn", """
        {:version 1 :constraints {":C003" {:assert "(p)"}}}
    """)
    out = load_constraints(f)
    assert out[":C003"]["atoms"] == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd SM && ./.venv/Scripts/python.exe -m pytest tests/unit/test_constraints_reader.py -v`
Expected: FAIL — `ModuleNotFoundError: scripts.governance._constraints`.

- [ ] **Step 3: Write minimal implementation**

Mirror the tolerant-regex style of `build_positions._load_prov_sidecar`. Adjust the `:derive-via` key here if Task 3 found a different key.

```python
# SM/scripts/governance/_constraints.py
"""Tolerant reader for rules/constraints.edn.

Pulls each constraint's id and its cited claim-ids (the :derive-via links).
Regex-based, matching the byte-shape `forge add-constraint` emits; not a
general EDN parser. Mirrors build_positions._load_prov_sidecar in style.
"""
from __future__ import annotations
import re
from pathlib import Path


def _str_vec(s: str) -> list[str]:
    return [m.strip('"') for m in re.findall(r'"[^"]*"', s)]


def load_constraints(path: Path) -> dict[str, dict]:
    """constraint-id → {"atoms": [claim-id, ...]}. Missing file → {}."""
    path = Path(path)
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8")
    out: dict[str, dict] = {}
    # Each entry: "<id>" { ... :derive-via [ ... ] ... }
    entry_re = re.compile(r'"(:[^"]+)"\s*\{(.*?)\}', re.DOTALL)
    for m in entry_re.finditer(text):
        cid, body = m.group(1), m.group(2)
        derive = re.search(r":derive-via\s*\[([^\]]*)\]", body)
        out[cid] = {"atoms": _str_vec(derive.group(1)) if derive else []}
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd SM && ./.venv/Scripts/python.exe -m pytest tests/unit/test_constraints_reader.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add SM/scripts/governance/_constraints.py SM/tests/unit/test_constraints_reader.py
git commit -m "governance: tolerant defconstraint reader"
```

### Task 5: Feed defconstraint rules into build_positions

**Files:**
- Modify: `SM/scripts/governance/build_positions.py` (function `build_positions`)
- Test: `SM/tests/integration/test_governance_defconstraint.py`

A defconstraint's support set is its cited claims' docs. Reuse the existing `_claim_doc_index` to map claim-ids → doc-ids, build a `RuleEvidence` per constraint, and emit positions with `source="defconstraint"`. Charter override still applies (`canonical_asserts`/`canonical_rejects` matching the constraint id).

- [ ] **Step 1: Write the failing test**

```python
# SM/tests/integration/test_governance_defconstraint.py
"""build_positions emits positions for defconstraint rules (no induced rules)."""
from __future__ import annotations
import shutil
from pathlib import Path
from scripts.governance.build_positions import build_positions
from scripts.governance._positions_io import read_positions
from scripts.governance._stance import Stance


def _seed(ws: Path):
    (ws / "syntopical" / "schools").mkdir(parents=True)
    (ws / "knowledge" / "claims").mkdir(parents=True)
    (ws / "rules").mkdir(parents=True)
    (ws / "syntopical" / "schools" / "school-a.edn").write_text(
        '{:version 1 :school :school-a :name "A" :charter "-" '
        ':members ["doc-a1" "doc-a2"] :canonical-asserts [] :canonical-rejects []}',
        encoding="utf-8")
    (ws / "knowledge" / "claims" / "ledger.jsonl").write_text(
        '{"claim_id":"clm-1","status":"verified","source_spans":[{"doc_id":"doc-a1"}]}\n'
        '{"claim_id":"clm-2","status":"verified","source_spans":[{"doc_id":"doc-a2"}]}\n',
        encoding="utf-8")
    (ws / "rules" / "constraints.edn").write_text(
        '{:version 1 :constraints '
        '{":C001-x" {:assert "(p)" :derive-via ["clm-1" "clm-2"]}}}',
        encoding="utf-8")


def test_defconstraint_emits_positions(tmp_path):
    ws = tmp_path / "ws"
    ws.mkdir()
    _seed(ws)
    build_positions(ws, generated_at="2026-05-31T00:00:00Z")
    rows = read_positions(ws / "syntopical" / "positions.edn")
    c = [r for r in rows if r.rule_id == ":C001-x"]
    assert len(c) == 1
    assert c[0].source == "defconstraint"
    assert c[0].school == "school-a"
    # two member docs support it → supports
    assert c[0].stance == Stance.SUPPORTS


def test_defconstraint_and_induced_coexist(tmp_path):
    ws = tmp_path / "ws"
    ws.mkdir()
    _seed(ws)
    (ws / "rules" / "booklogic").mkdir(parents=True)
    (ws / "rules" / "booklogic" / "induced-theory.prov.edn").write_text(
        '{:version 1 :rules {":induced/r-001" '
        '{:prov/derived-from-atoms ["clm-1"] '
        ':prov/source-documents ["doc-a1"] '
        ':prov/contradiction-atoms []}}}',
        encoding="utf-8")
    build_positions(ws, generated_at="2026-05-31T00:00:00Z")
    rows = read_positions(ws / "syntopical" / "positions.edn")
    sources = {r.source for r in rows}
    assert sources == {"defconstraint", "induced"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd SM && ./.venv/Scripts/python.exe -m pytest tests/integration/test_governance_defconstraint.py -v`
Expected: FAIL — only induced rules emitted; `:C001-x` absent.

- [ ] **Step 3: Implement**

In `build_positions.py`, add the import:

```python
from ._constraints import load_constraints
```

After the existing `prov = _load_prov_sidecar(...)` line, add:

```python
    constraints = load_constraints(workspace / "rules" / "constraints.edn")
```

Refactor the per-rule emit into a helper so induced and defconstraint rules share it. Replace the existing `for rule_id, prov_data in prov.items():` loop body's tail (the `for school in schools:` block) by extracting this helper above `build_positions`:

```python
def _emit_rows(rule_id, source, evidence, schools, config, induction_prov):
    rows = []
    for school in schools:
        stance = derive_stance(school, evidence, config)
        declared = (rule_id in school.canonical_asserts
                    or rule_id in school.canonical_rejects)
        rows.append(Position(
            rule_id=rule_id,
            rule_form="",
            source=source,
            school=school.slug,
            stance=stance,
            supporting_atoms=list(evidence.supporting_atoms),
            supporting_docs=list(evidence.supporting_docs),
            contradicting_atoms=list(evidence.contradicting_atoms),
            contradicting_docs=list(evidence.contradicting_docs),
            declared_by_charter=declared,
            induction_prov=induction_prov,
        ))
    return rows
```

Then in `build_positions`, the induced loop becomes:

```python
    positions: list[Position] = []
    for rule_id, prov_data in prov.items():
        supporting_docs = list(dict.fromkeys(prov_data["docs"]))
        contradicting_docs = list(dict.fromkeys(
            [d for atom in prov_data["contras"] for d in claim_docs.get(atom, [])]
        ))
        evidence = RuleEvidence(
            rule_id=rule_id,
            supporting_docs=supporting_docs,
            contradicting_docs=contradicting_docs,
            supporting_atoms=list(prov_data["atoms"]),
            contradicting_atoms=list(prov_data["contras"]),
        )
        positions += _emit_rows(
            rule_id, "induced", evidence, schools, config,
            f"induced-theory.prov.edn#{rule_id}")

    for cid, cdata in constraints.items():
        supporting_docs = list(dict.fromkeys(
            [d for atom in cdata["atoms"] for d in claim_docs.get(atom, [])]
        ))
        evidence = RuleEvidence(
            rule_id=cid,
            supporting_docs=supporting_docs,
            contradicting_docs=[],
            supporting_atoms=list(cdata["atoms"]),
            contradicting_atoms=[],
        )
        positions += _emit_rows(
            cid, "defconstraint", evidence, schools, config,
            f"constraints.edn#{cid}")
```

Leave the `write_positions(...)` tail unchanged. Update the module docstring line 8 to drop "(Phase 4 follow-up; optional)".

- [ ] **Step 4: Run tests**

Run: `cd SM && ./.venv/Scripts/python.exe -m pytest tests/integration/test_governance_defconstraint.py tests/integration/test_governance_three_schools.py -v`
Expected: PASS — both new defconstraint tests and the existing three-schools integration (induced path unchanged).

- [ ] **Step 5: Commit**

```bash
git add SM/scripts/governance/build_positions.py SM/tests/integration/test_governance_defconstraint.py
git commit -m "governance: build_positions reads rules/constraints.edn (defconstraint support)"
```

### Task 6: Neutral conformance workspace + test (replaces EpochPoET-bound test)

**Files:**
- Create: `SM/tests/fixtures/workspaces/neutral-conformance/syntopical/schools/school-a.edn`
- Create: `SM/tests/fixtures/workspaces/neutral-conformance/syntopical/schools/school-b.edn`
- Create: `SM/tests/fixtures/workspaces/neutral-conformance/syntopical/schools/self.edn`
- Create: `SM/tests/fixtures/workspaces/neutral-conformance/knowledge/claims/ledger.jsonl`
- Create: `SM/tests/fixtures/workspaces/neutral-conformance/rules/booklogic/induced-theory.prov.edn`
- Create: `SM/tests/fixtures/workspaces/neutral-conformance/rules/constraints.edn`
- Create: `SM/tests/conformance/test_neutral_workspace.py`
- Delete: `SM/tests/conformance/test_epochpoet_governance.py`

- [ ] **Step 1: Create the fixture files**

`school-a.edn`:
```clojure
{:version 1
 :school :school-a
 :name "School A"
 :charter "Prefers method X."
 :members ["doc-a1" "doc-a2"]
 :canonical-rejects []
 :canonical-asserts [":induced/r-001"]}
```

`school-b.edn`:
```clojure
{:version 1
 :school :school-b
 :name "School B"
 :charter "Rejects method X in favour of method Y."
 :members ["doc-b1"]
 :canonical-rejects [":induced/r-001"]
 :canonical-asserts []}
```

`self.edn`:
```clojure
{:version 1
 :school :self
 :name "Own work"
 :charter "Work by this book's author."
 :members ["self-work"]
 :canonical-rejects []
 :canonical-asserts []}
```

`knowledge/claims/ledger.jsonl`:
```jsonl
{"claim_id":"clm-1","canonical_text":"method X holds","status":"verified","source_spans":[{"doc_id":"doc-a1"}],"created_at":"2026-01-01T00:00:00+00:00"}
{"claim_id":"clm-2","canonical_text":"method X holds","status":"verified","source_spans":[{"doc_id":"doc-a2"}],"created_at":"2026-01-01T00:00:00+00:00"}
{"claim_id":"clm-3","canonical_text":"method X holds in own work","status":"verified","source_spans":[{"doc_id":"self-work"}],"created_at":"2026-01-01T00:00:00+00:00"}
{"claim_id":"clm-4","canonical_text":"method Y preferred","status":"verified","source_spans":[{"doc_id":"doc-b1"}],"created_at":"2026-01-01T00:00:00+00:00"}
```

`rules/booklogic/induced-theory.prov.edn`:
```clojure
{:version 1
 :rules {":induced/r-001" {:prov/derived-from-atoms ["clm-1" "clm-2" "clm-3"]
                           :prov/source-documents ["doc-a1" "doc-a2" "self-work"]
                           :prov/contradiction-atoms ["clm-4"]
                           :prov/status :active}}}
```

`rules/constraints.edn`:
```clojure
{:version 1
 :constraints
 {":C001-method-x" {:assert "(holds method-x)"
                    :derive-via ["clm-1" "clm-2"]}}}
```

- [ ] **Step 2: Write the conformance test**

```python
# SM/tests/conformance/test_neutral_workspace.py
"""Domain-neutral conformance canary — always runs (no external workspace).

Exercises both the induced-rule and defconstraint paths plus all renderers
against an in-repo workspace with curated schools.
"""
from __future__ import annotations
import shutil
from pathlib import Path
from scripts.governance.build_positions import build_positions
from scripts.governance.render_per_rule import render_per_rule
from scripts.governance.render_consensus_map import render_consensus_map
from scripts.governance.render_adversarial import render_adversarial
from scripts.governance._config import load_or_create_config
from scripts.governance._positions_io import read_positions
from scripts.governance._stance import Stance

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "workspaces" / "neutral-conformance"


def _ws(tmp_path):
    ws = tmp_path / "ws"
    shutil.copytree(FIXTURE, ws)
    return ws


def test_build_emits_both_sources(tmp_path):
    ws = _ws(tmp_path)
    build_positions(ws, generated_at="2026-05-31T00:00:00Z")
    rows = read_positions(ws / "syntopical" / "positions.edn")
    assert {r.source for r in rows} == {"induced", "defconstraint"}


def test_charter_override_and_atom_inference(tmp_path):
    ws = _ws(tmp_path)
    build_positions(ws, generated_at="2026-05-31T00:00:00Z")
    rows = read_positions(ws / "syntopical" / "positions.edn")
    induced = {r.school: r for r in rows if r.rule_id == ":induced/r-001"}
    assert induced["school-a"].stance == Stance.SUPPORTS      # charter assert
    assert induced["school-b"].stance == Stance.CONTRADICTS   # charter reject
    assert induced["self"].stance == Stance.SUPPORTS          # atoms (self-work)


def test_all_renderers_run(tmp_path):
    ws = _ws(tmp_path)
    build_positions(ws, generated_at="2026-05-31T00:00:00Z")
    pos = ws / "syntopical" / "positions.edn"
    assert render_per_rule(pos, ws / "syntopical" / "rules") >= 2
    render_consensus_map(pos, ws / "syntopical" / "figures")
    cfg = load_or_create_config(ws / "syntopical" / "governance-config.edn")
    render_adversarial(pos, ws / "syntopical" / "adversarial-review.md", cfg)
    assert (ws / "syntopical" / "figures" / "consensus-map.svg").exists()
    assert (ws / "syntopical" / "adversarial-review.md").exists()
```

Note: `self.edn`'s slug `self` must match the default `self_school` in `governance-config.edn`. If `_config.DEFAULTS["self_school"]` is `"my-own-work"`, either name the self school `my-own-work.edn`/`:my-own-work`, or add a `governance-config.edn` to the fixture setting `:self-school :self`. Verify `DEFAULTS` and pick one; the test above assumes the slug `self` is the configured self-school.

- [ ] **Step 3: Delete the EpochPoET-bound test**

```bash
git rm SM/tests/conformance/test_epochpoet_governance.py
```

- [ ] **Step 4: Run the conformance suite**

Run: `cd SM && ./.venv/Scripts/python.exe -m pytest tests/conformance/ -v`
Expected: PASS, 0 skipped (the canary now always runs).

- [ ] **Step 5: Commit**

```bash
git add SM/tests/fixtures/workspaces/neutral-conformance SM/tests/conformance/test_neutral_workspace.py
git commit -m "governance: domain-neutral conformance canary; drop EpochPoET-bound test"
```

### Task 7: PR 1 green check + open PR

- [ ] **Step 1: Run the full skill suite**

Run: `cd SM && ./.venv/Scripts/python.exe -m pytest -q`
Expected: all pass; skip count drops by 3 (conformance no longer skips).

- [ ] **Step 2: Push + PR**

```bash
git push -u origin feat/syntopical-metabook-v0.3-generalization
gh pr create --title "syntopical-metabook v0.3 PR 1 — defconstraint support + staleness guard + neutral conformance" --body "Adds rules/constraints.edn support to build_positions, a staleness guard on all renderers, and a domain-neutral conformance canary that always runs (replaces the EpochPoET-bound skipped test)."
```

---

# PR 2 — De-specialization (docs, version, fixtures)

No behavior change. Strips consensus-crypto references and syncs the documented surface with the code.

### Task 8: Re-theme the three-schools fixture

**Files:**
- Modify: `SM/tests/fixtures/workspaces/three-schools/syntopical/schools/praos.edn` → rename to `school-a.edn`
- Modify: `.../algorand.edn` → rename to `school-b.edn`
- Modify: `.../my-own-work.edn` → keep filename (matches default self-school) but neutralize charter
- Modify: `.../knowledge/claims/ledger.jsonl`
- Modify: `.../rules/booklogic/induced-theory.prov.edn`
- Modify: `SM/tests/integration/test_governance_three_schools.py` (slug assertions)

- [ ] **Step 1: Re-theme the school files**

```bash
cd SM/tests/fixtures/workspaces/three-schools/syntopical/schools
git mv praos.edn school-a.edn
git mv algorand.edn school-b.edn
```

`school-a.edn`:
```clojure
{:version 1
 :school :school-a
 :name "School A"
 :charter "Prefers method X."
 :members ["doc-a1" "doc-a2"]
 :canonical-rejects []
 :canonical-asserts [":method-x"]}
```

`school-b.edn`:
```clojure
{:version 1
 :school :school-b
 :name "School B"
 :charter "Rejects method X."
 :members ["doc-b1"]
 :canonical-rejects [":method-x"]
 :canonical-asserts []}
```

`my-own-work.edn`:
```clojure
{:version 1
 :school :my-own-work
 :name "Own work"
 :charter "Work by this book's author."
 :members ["self-work"]
 :canonical-rejects []
 :canonical-asserts []}
```

`knowledge/claims/ledger.jsonl`:
```jsonl
{"claim_id":"clm-2026-000001","canonical_text":"method X","status":"verified","claim_type":"design_decision","confidence":0.95,"source_spans":[{"doc_id":"doc-a1","locator_text":"method X holds"}],"created_at":"2026-01-01T00:00:00+00:00"}
{"claim_id":"clm-2026-000002","canonical_text":"method X","status":"verified","claim_type":"design_decision","confidence":0.95,"source_spans":[{"doc_id":"doc-a2","locator_text":"method X"}],"created_at":"2026-01-01T00:00:00+00:00"}
{"claim_id":"clm-2026-000003","canonical_text":"method X in own work","status":"verified","claim_type":"design_decision","confidence":0.9,"source_spans":[{"doc_id":"self-work","locator_text":"method X"}],"created_at":"2026-01-01T00:00:00+00:00"}
{"claim_id":"clm-2026-000004","canonical_text":"method Y","status":"verified","claim_type":"design_decision","confidence":0.9,"source_spans":[{"doc_id":"doc-b1","locator_text":"method Y"}],"created_at":"2026-01-01T00:00:00+00:00"}
```

`rules/booklogic/induced-theory.prov.edn` — replace doc-ids/atoms with neutral ones and the rule's charter keyword `:tau-leq-one` → `:method-x` if referenced; keep the structure:
```clojure
{:version 1
 :rules {":induced/r-001" {:prov/derived-from-atoms ["clm-2026-000001" "clm-2026-000002" "clm-2026-000003"]
                           :prov/source-documents ["doc-a1" "doc-a2" "self-work"]
                           :prov/contradiction-atoms ["clm-2026-000004"]
                           :prov/proposed-by {:lineage :llm}
                           :prov/validated-by []
                           :prov/entrenchment 0.85
                           :prov/status :active
                           :prov/llm-repair-calls 0
                           :prov/cost-usd 0.0}}}
```

- [ ] **Step 2: Update the integration test assertions**

Open `SM/tests/integration/test_governance_three_schools.py`. Replace every domain slug with the neutral set: `"praos"` → `"school-a"`, `"algorand"` → `"school-b"`, member doc-ids `praos2017`/`genesis2018` → `doc-a1`/`doc-a2`, `algorand2017` → `doc-b1`, `my-v2-spec` → `self-work`. Where the test asserts `set(by_school) == {"praos","algorand","my-own-work"}`, change to `{"school-a","school-b","my-own-work"}`. The charter-override test that expects `algorand` → CONTRADICTS becomes `school-b` → CONTRADICTS. Keep the structural assertions (row counts, idempotence) unchanged.

- [ ] **Step 3: Run the integration test**

Run: `cd SM && ./.venv/Scripts/python.exe -m pytest tests/integration/test_governance_three_schools.py -v`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add SM/tests/fixtures/workspaces/three-schools SM/tests/integration/test_governance_three_schools.py
git commit -m "test: re-theme three-schools fixture to neutral slugs"
```

### Task 9: Neutralize governance-playbook.md and document all govern subcommands

**Files:**
- Modify: `SM/references/governance-playbook.md`

- [ ] **Step 1: Rewrite the examples**

Replace the Praos/τ≤1 example block with a domain-neutral one and add the three undocumented subcommands. The full replacement body:

```markdown
# Governance playbook

The governance layer turns symbolic verdicts into literature-positioned
scholarship. Walk this once per book workspace.

## 1. Curate schools

Create `<workspace>/syntopical/schools/<slug>.edn` for each school of
thought your work engages with:

```clojure
{:version 1
 :school :school-a
 :name "School A"
 :charter "One-paragraph statement of what this school holds."
 :members ["doc-a1" "doc-a2"]
 :canonical-asserts [":some-rule-id"]
 :canonical-rejects [":another-rule-id"]}
```

`members` are `doc_id`s your book-knowledge ledger already knows about.
`canonical-asserts` / `canonical-rejects` are rule-id keywords; matching
them declares the school's position editorially, overriding atom-inferred
stance. Name your own work's school in `governance-config.edn`
(`:self-school`, default `:my-own-work`) so the adversarial review can find
positions you take against a cited school.

## 2. Build the positions ledger

```bash
forge govern build <workspace>
```

Writes `<workspace>/syntopical/positions.edn` — one row per `(rule, school)`
pair, covering both induced rules and `defconstraint` rules.

## 3. Render the reports

```bash
forge govern report      <workspace>   # syntopical/rules/<rule>.md
forge govern map         <workspace>   # syntopical/figures/consensus-map.{tex,svg}
forge govern review      <workspace>   # syntopical/adversarial-review.md
forge govern quarantine  <workspace>   # rules that failed forge induce --governance-gate
```

Renderers refuse to run on a `positions.edn` older than its source ledgers;
re-run `forge govern build` first.

## 4. Iterate

Edit schools, re-run `build`. The positions ledger is idempotent; running
twice produces byte-identical output.

## See also

- `references/acquire-playbook.md`, `synthesize-playbook.md`, `lens-and-gap-playbook.md`
- `docs/superpowers/specs/2026-05-31-syntopical-metabook-v0.3-generalization-design.md`
```

- [ ] **Step 2: Grep for residual domain terms**

Run: `grep -rniE 'praos|algorand|ouroboros|epochpoet|tau|τ' SM/references/ SM/SKILL.md`
Expected: no matches (the lens/acquire playbooks created in PR 3 must also stay clean).

- [ ] **Step 3: Commit**

```bash
git add SM/references/governance-playbook.md
git commit -m "docs: neutral governance playbook; document map/review/quarantine"
```

### Task 10: Sync SKILL.md (description, version, full surface)

**Files:**
- Modify: `SM/SKILL.md`

- [ ] **Step 1: Rewrite frontmatter + body**

Replace the file with:

```markdown
---
name: syntopical-metabook
description: General-purpose knowledge-curation layer for a book/knowledge workspace. Five capabilities — Acquire (grow the source set by citation-graph traversal and ingest via book-knowledge), Synthesize (topic maps, disputed questions, concept reconciliation over the claim ledger), Lens (project a per-chapter view book-compose reads), Gap (score thesis-node coverage and feed uncovered nodes back to acquisition), and Govern (partition rule/claim support by curated schools of thought; render reports, consensus map, adversarial review, induction gate). Use when the user wants to acquire or expand sources, synthesize a cross-source view, project a per-chapter lens, find coverage gaps, or position induced/asserted rules against schools of thought. The skill never touches the network directly (only via scrapling-fetch) and never mutates the canonical workspace (only via book-knowledge); it writes only under syntopical/.
license: MIT
metadata:
  author: charles-hoskinson
  version: 0.3.0
  category: writing
  workspace-aware: true
---

# syntopical-metabook

The world model above the book. Five capabilities over a workspace, each
reachable from the `forge` CLI and exported from `skill_api.py`.

## Capabilities

| Capability | CLI | Playbook |
|---|---|---|
| Acquire | `forge meta acquire` | `references/acquire-playbook.md` |
| Synthesize | `forge meta synthesize` | `references/synthesize-playbook.md` |
| Lens | `forge meta lens` | `references/lens-and-gap-playbook.md` |
| Gap | `forge meta gap` | `references/lens-and-gap-playbook.md` |
| Govern | `forge govern …` | `references/governance-playbook.md` |

The author loop: **Acquire → Synthesize → Gap → (feed back to Acquire) →
Lens → book-compose**, with **Govern** as the quality gate over induced and
asserted rules.

## Boundaries

- Reads: `raw/`, `wiki/`, `claims/`, `graph/`, `chapters/`, `rules/`, `syntopical/schools/`.
- Writes: `syntopical/` only.
- Network: only via `scrapling-fetch`. Never direct HTTP.
- Symbolic reasoning: only via `booklogic_adapter`. Never EDN logic in Python.

## Public surface

`skill_api.py` (`API_VERSION = (0, 3)`) exports:

- Acquire: `expand_seeds`, `rank`, `triage`, `apply_veto`, `download_and_ingest`, `run_acquire`
- Synthesize: `build_topic_map`, `build_disputed_questions`, `build_concept_reconciliation`, `run_synthesize`
- Lens: `project_lens`
- Gap: `build_coverage_report`, `seed_from_gap_report`
- Govern: `build_positions`, `render_per_rule`, `render_consensus_map`, `render_adversarial`, `governance_filter`, `GateDecision`
```

- [ ] **Step 2: Verify no domain terms remain**

Run: `grep -niE 'praos|algorand|ouroboros|epochpoet|chapter X|dormant|v0.1 scaffold' SM/SKILL.md`
Expected: no matches.

- [ ] **Step 3: Commit**

```bash
git add SM/SKILL.md
git commit -m "docs: general-purpose SKILL.md — five capabilities, version 0.3.0, full surface"
```

### Task 11: PR 2 green check + open PR

- [ ] **Step 1: Full suite**

Run: `cd SM && ./.venv/Scripts/python.exe -m pytest -q`
Expected: all pass.

- [ ] **Step 2: Push + PR**

```bash
git push
gh pr create --title "syntopical-metabook v0.3 PR 2 — de-specialization" --body "Neutral fixtures, neutral governance playbook, general-purpose SKILL.md (description + version 0.3.0 + documented full surface). No behavior change."
```

---

# PR 3 — Wake the sub-workflows (skill_api exports + forge meta CLI)

Exposes Acquire/Synthesize/Lens/Gap. Synthesize and Acquire get thin orchestrators that sequence existing entry points; Lens and Gap already have single entry points.

### Task 12: run_synthesize orchestrator

**Files:**
- Create: `SM/scripts/synthesize/run_synthesize.py`
- Test: `SM/tests/integration/test_synthesize_orchestrator.py`

The three synthesize builders have these signatures (confirm by re-reading the modules): `build_topic_map(workspace_root, chapter_id) -> Path`, `build_disputed_questions(workspace_root) -> list[Path]`, `build_concept_reconciliation(workspace_root) -> list[Path]`.

- [ ] **Step 1: Write the failing test**

```python
# SM/tests/integration/test_synthesize_orchestrator.py
"""run_synthesize sequences the three synthesize builders."""
from __future__ import annotations
from pathlib import Path
import scripts.synthesize.run_synthesize as rs


def test_run_synthesize_calls_all_three(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(rs, "build_topic_map",
                        lambda ws, ch: calls.append(("topic", ws, ch)) or (tmp_path / "topic-map.md"))
    monkeypatch.setattr(rs, "build_disputed_questions",
                        lambda ws: calls.append(("disputed", ws)) or [])
    monkeypatch.setattr(rs, "build_concept_reconciliation",
                        lambda ws: calls.append(("concepts", ws)) or [])
    out = rs.run_synthesize(tmp_path, "ch1")
    assert [c[0] for c in calls] == ["topic", "disputed", "concepts"]
    assert out["topic_map"] == tmp_path / "topic-map.md"
    assert out["disputed"] == []
    assert out["concepts"] == []
```

- [ ] **Step 2: Run to verify failure**

Run: `cd SM && ./.venv/Scripts/python.exe -m pytest tests/integration/test_synthesize_orchestrator.py -v`
Expected: FAIL — `ModuleNotFoundError: scripts.synthesize.run_synthesize`.

- [ ] **Step 3: Implement**

```python
# SM/scripts/synthesize/run_synthesize.py
"""Run the full synthesize pass: topic map + disputed questions + concepts."""
from __future__ import annotations
from pathlib import Path
from .topic_map import build_topic_map
from .disputed_questions import build_disputed_questions
from .concept_reconcile import build_concept_reconciliation


def run_synthesize(workspace_root: Path, chapter_id: str) -> dict:
    """Build all synthesize artifacts. Returns paths produced."""
    topic_map = build_topic_map(workspace_root, chapter_id)
    disputed = build_disputed_questions(workspace_root)
    concepts = build_concept_reconciliation(workspace_root)
    return {"topic_map": topic_map, "disputed": disputed, "concepts": concepts}
```

- [ ] **Step 4: Run test**

Run: `cd SM && ./.venv/Scripts/python.exe -m pytest tests/integration/test_synthesize_orchestrator.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add SM/scripts/synthesize/run_synthesize.py SM/tests/integration/test_synthesize_orchestrator.py
git commit -m "synthesize: run_synthesize orchestrator"
```

### Task 13: run_acquire orchestrator

**Files:**
- Create: `SM/scripts/acquire/pipeline.py`
- Test: `SM/tests/integration/test_acquire_orchestrator.py`

**Before writing:** re-read `tests/integration/test_acquire_e2e.py` (97 lines) — it composes `rank → triage → apply_veto → download_and_ingest` with stubs and is the source of truth for the call sequence and the stub shapes. The orchestrator below lifts that sequence and adds `expand_seeds` at the front. Confirm these signatures by re-reading the modules:
- `expand_seeds(seeds: list[str], depth: int = 2) -> list[PaperRef]` (`PaperRef(doc_id, title, source, cited_by_count, year)`)
- `Candidate(doc_id, title, abstract, year)`; `rank(query_text: str, candidates: list[Candidate]) -> list[ScoredCandidate]`
- `triage(scored, cfg: TriageConfig, workspace_root: Path, run_id: str) -> TriageResult`
- `apply_veto(tr: TriageResult, thesis_tree, candidate_lookup: dict, manifest_path: Path) -> TriageResult`
- `download_and_ingest(candidates: list[ScoredCandidate], workspace_root: Path) -> list[IngestOutcome]`

- [ ] **Step 1: Write the failing test (orchestration order, fully stubbed)**

```python
# SM/tests/integration/test_acquire_orchestrator.py
"""run_acquire sequences expand → rank → triage → veto → ingest."""
from __future__ import annotations
from pathlib import Path
import scripts.acquire.pipeline as pipe


def test_run_acquire_orchestration_order(monkeypatch, tmp_path):
    order = []
    monkeypatch.setattr(pipe, "expand_seeds",
                        lambda seeds, depth=2: order.append("expand") or [])
    monkeypatch.setattr(pipe, "rank",
                        lambda q, cands: order.append("rank") or [])
    monkeypatch.setattr(pipe, "triage",
                        lambda scored, cfg, ws, run_id: order.append("triage") or _FakeTriage())
    monkeypatch.setattr(pipe, "apply_veto",
                        lambda tr, tree, lookup, manifest: order.append("veto") or tr)
    monkeypatch.setattr(pipe, "download_and_ingest",
                        lambda cands, ws: order.append("ingest") or [])
    monkeypatch.setattr(pipe, "_load_thesis_tree", lambda ws, ch: {"nodes": []})
    out = pipe.run_acquire(tmp_path, chapter_id="ch1", seeds=["arxiv:1"],
                           query_text="q", depth=1)
    assert order == ["expand", "rank", "triage", "veto", "ingest"]
    assert out["ingested"] == []


class _FakeTriage:
    auto_approve = []
    manual_review = []
    reject = []
```

- [ ] **Step 2: Run to verify failure**

Run: `cd SM && ./.venv/Scripts/python.exe -m pytest tests/integration/test_acquire_orchestrator.py -v`
Expected: FAIL — `ModuleNotFoundError: scripts.acquire.pipeline`.

- [ ] **Step 3: Implement**

Re-read `triage.py` to confirm `TriageConfig`'s constructor and `TriageResult`'s field names (`auto_approve`/`manual_review`), and `veto.py` for `apply_veto`'s `candidate_lookup` shape. Adjust the field names below to match. The thesis-tree loader reads `chapters/<id>/thesis-tree.yaml` (same path the other sub-workflows use).

```python
# SM/scripts/acquire/pipeline.py
"""run_acquire — sequence the acquire entry points into one pass.

Composes the proven sequence from tests/integration/test_acquire_e2e.py
(rank → triage → veto → ingest) with expand_seeds at the front. Invents no
behavior; each step is an existing entry point.
"""
from __future__ import annotations
from pathlib import Path

import yaml

from .expand_seeds import expand_seeds, PaperRef
from .rank_candidates import Candidate, rank
from .triage import triage, TriageConfig
from .veto import apply_veto
from .download_and_ingest import download_and_ingest


def _load_thesis_tree(workspace_root: Path, chapter_id: str):
    p = Path(workspace_root) / "chapters" / chapter_id / "thesis-tree.yaml"
    if not p.exists():
        return {"nodes": []}
    return yaml.safe_load(p.read_text(encoding="utf-8")) or {"nodes": []}


def _to_candidate(ref: PaperRef) -> Candidate:
    return Candidate(doc_id=ref.doc_id, title=ref.title, abstract="", year=ref.year)


def run_acquire(workspace_root: Path, chapter_id: str, seeds: list[str],
                query_text: str, depth: int = 2, run_id: str = "acquire") -> dict:
    workspace_root = Path(workspace_root)
    refs = expand_seeds(seeds, depth=depth)
    candidates = [_to_candidate(r) for r in refs]
    scored = rank(query_text, candidates)
    cfg = TriageConfig()
    tr = triage(scored, cfg, workspace_root, run_id)
    thesis_tree = _load_thesis_tree(workspace_root, chapter_id)
    lookup = {c.doc_id: c for c in scored}
    manifest_path = workspace_root / "syntopical" / "acquisition" / "manifest.jsonl"
    tr = apply_veto(tr, thesis_tree, lookup, manifest_path)
    approved = list(getattr(tr, "auto_approve", []))
    ingested = download_and_ingest(approved, workspace_root)
    return {"triage": tr, "ingested": ingested}
```

If `TriageConfig()` requires arguments, pass the same defaults `test_acquire_e2e.py` uses. If `rank` is unavailable (optional `torch`/`sentence-transformers` absent), the call raises ImportError — that is acceptable; the CLI in Task 15 catches it and prints a clear "install acquire extras" message.

- [ ] **Step 4: Run test**

Run: `cd SM && ./.venv/Scripts/python.exe -m pytest tests/integration/test_acquire_orchestrator.py -v`
Expected: PASS (the test stubs every entry point, so no real network or ML runs). Also run the existing acquire suite to confirm no regression: `./.venv/Scripts/python.exe -m pytest tests/integration/test_acquire_e2e.py tests/unit/test_triage.py tests/unit/test_veto.py -v`.

- [ ] **Step 5: Commit**

```bash
git add SM/scripts/acquire/pipeline.py SM/tests/integration/test_acquire_orchestrator.py
git commit -m "acquire: run_acquire orchestrator"
```

### Task 14: Export the full surface from skill_api.py

**Files:**
- Modify: `SM/skill_api.py`
- Test: `SM/tests/unit/test_skill_api_surface.py`

- [ ] **Step 1: Write the failing test**

```python
# SM/tests/unit/test_skill_api_surface.py
"""skill_api exports all five capabilities at API 0.3."""
import skill_api


def test_api_version_is_0_3():
    assert skill_api.API_VERSION == (0, 3)


def test_exports_all_capabilities():
    for name in [
        "expand_seeds", "rank", "triage", "apply_veto", "download_and_ingest", "run_acquire",
        "build_topic_map", "build_disputed_questions", "build_concept_reconciliation", "run_synthesize",
        "project_lens",
        "build_coverage_report", "seed_from_gap_report",
        "build_positions", "render_per_rule", "render_consensus_map",
        "render_adversarial", "governance_filter", "GateDecision",
    ]:
        assert hasattr(skill_api, name), f"missing export: {name}"
```

- [ ] **Step 2: Run to verify failure**

Run: `cd SM && ./.venv/Scripts/python.exe -m pytest tests/unit/test_skill_api_surface.py -v`
Expected: FAIL — `API_VERSION == (0, 2)` and acquire/synthesize/lens/gap exports missing.

- [ ] **Step 3: Implement**

Replace `SM/skill_api.py` with:

```python
# skill_api.py
"""Public surface of the syntopical-metabook skill.

v0.3 exports all five capabilities: acquire, synthesize, lens, gap, govern.
"""
API_VERSION = (0, 3)

# Acquire
from scripts.acquire.expand_seeds import expand_seeds  # noqa: E402
from scripts.acquire.rank_candidates import rank  # noqa: E402
from scripts.acquire.triage import triage  # noqa: E402
from scripts.acquire.veto import apply_veto  # noqa: E402
from scripts.acquire.download_and_ingest import download_and_ingest  # noqa: E402
from scripts.acquire.pipeline import run_acquire  # noqa: E402

# Synthesize
from scripts.synthesize.topic_map import build_topic_map  # noqa: E402
from scripts.synthesize.disputed_questions import build_disputed_questions  # noqa: E402
from scripts.synthesize.concept_reconcile import build_concept_reconciliation  # noqa: E402
from scripts.synthesize.run_synthesize import run_synthesize  # noqa: E402

# Lens
from scripts.lens.project_lens import project_lens  # noqa: E402

# Gap
from scripts.gap.coverage_report import build_coverage_report  # noqa: E402
from scripts.gap.feed_acquire import seed_from_gap_report  # noqa: E402

# Govern
from scripts.governance.build_positions import build_positions  # noqa: E402
from scripts.governance.render_per_rule import render_per_rule  # noqa: E402
from scripts.governance.render_consensus_map import render_consensus_map  # noqa: E402
from scripts.governance.render_adversarial import render_adversarial  # noqa: E402
from scripts.governance.induction_gate import governance_filter, GateDecision  # noqa: E402

__all__ = [
    "API_VERSION",
    "expand_seeds", "rank", "triage", "apply_veto", "download_and_ingest", "run_acquire",
    "build_topic_map", "build_disputed_questions", "build_concept_reconciliation", "run_synthesize",
    "project_lens",
    "build_coverage_report", "seed_from_gap_report",
    "build_positions", "render_per_rule", "render_consensus_map",
    "render_adversarial", "governance_filter", "GateDecision",
]
```

Note: importing `rank` pulls `rank_candidates.py`, which may import `torch`/`sentence-transformers` lazily. Confirm the module-level import of `rank_candidates` does not hard-require those at import time (re-read the top of `rank_candidates.py`). If it does, move the heavy import inside `rank()` so `import skill_api` stays light; that is a legitimate small refactor for this task.

- [ ] **Step 4: Run test**

Run: `cd SM && ./.venv/Scripts/python.exe -m pytest tests/unit/test_skill_api_surface.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add SM/skill_api.py SM/tests/unit/test_skill_api_surface.py
git commit -m "skill_api: export all five capabilities (API 0.3)"
```

### Task 15: `forge meta` CLI group

**Files:**
- Modify: `skills/neurosym-forge/scripts/forge_cli.py` (append a `meta` group after the `govern` group, around line 1290+)
- Test: `skills/neurosym-forge/tests/test_forge_cli_meta.py`

Mirror the existing `govern` pattern: a `@cli.group()` plus a lazy-import helper and thin command wrappers.

- [ ] **Step 1: Write the failing test**

```python
# skills/neurosym-forge/tests/test_forge_cli_meta.py
"""forge meta subcommand group routing."""
from __future__ import annotations
import subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FORGE = ROOT / "neurosym-forge" / "scripts" / "forge_cli.py"


def _run(args):
    return subprocess.run([sys.executable, str(FORGE)] + args,
                          capture_output=True, text=True, check=False)


def test_meta_help_lists_subcommands():
    out = _run(["meta", "--help"])
    assert out.returncode == 0
    for sub in ("acquire", "synthesize", "lens", "gap"):
        assert sub in out.stdout


def test_meta_lens_requires_workspace():
    out = _run(["meta", "lens"])
    assert out.returncode != 0
```

- [ ] **Step 2: Run to verify failure**

Run: `cd skills/neurosym-forge && python -m pytest tests/test_forge_cli_meta.py -v`
Expected: FAIL — `meta` command not found.

- [ ] **Step 3: Implement — append to forge_cli.py**

After the last `@govern.command(...)` block:

```python
# ---------------------------------------------------------------------------
# `forge meta` group — wraps syntopical-metabook curation sub-workflows
# ---------------------------------------------------------------------------


@cli.group()
def meta() -> None:
    """syntopical-metabook curation: acquire, synthesize, lens, gap."""


def _import_metabook(attr: str):
    """Lazy-import a syntopical-metabook entry point; clean error if absent."""
    try:
        import importlib
        mod_map = {
            "run_acquire": "scripts.acquire.pipeline",
            "run_synthesize": "scripts.synthesize.run_synthesize",
            "project_lens": "scripts.lens.project_lens",
            "build_coverage_report": "scripts.gap.coverage_report",
        }
        module = importlib.import_module(mod_map[attr])
        return getattr(module, attr)
    except ImportError as e:
        raise click.ClickException(
            "syntopical-metabook skill not on sys.path. Install both skills in "
            "the same venv, or run from a workspace with PYTHONPATH set."
        ) from e


@meta.command("acquire")
@click.argument("workspace", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--chapter", "chapter_id", required=True, help="Chapter id (for thesis-tree veto).")
@click.option("--seed", "seeds", multiple=True, help="Seed paper id (repeatable).")
@click.option("--query", "query_text", default="", help="Query text for ranking.")
@click.option("--depth", default=2, type=int, help="Citation-graph traversal depth.")
@_handle
def meta_acquire(workspace: Path, chapter_id: str, seeds, query_text: str, depth: int) -> None:
    """Acquire and ingest sources by citation-graph traversal."""
    run_acquire = _import_metabook("run_acquire")
    try:
        out = run_acquire(workspace.resolve(), chapter_id=chapter_id,
                          seeds=list(seeds), query_text=query_text, depth=depth)
    except ImportError as e:
        raise click.ClickException(
            "acquire ranking needs the ML extras (torch, sentence-transformers). "
            "Install them or run the lighter sub-steps directly."
        ) from e
    click.echo(f"ingested {len(out['ingested'])} source(s)")


@meta.command("synthesize")
@click.argument("workspace", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--chapter", "chapter_id", required=True, help="Chapter id for the topic map.")
@_handle
def meta_synthesize(workspace: Path, chapter_id: str) -> None:
    """Build topic map, disputed questions, and concept reconciliation."""
    run_synthesize = _import_metabook("run_synthesize")
    out = run_synthesize(workspace.resolve(), chapter_id)
    click.echo(f"topic map: {out['topic_map']}; "
               f"{len(out['disputed'])} dispute file(s); "
               f"{len(out['concepts'])} concept file(s)")


@meta.command("lens")
@click.argument("workspace", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--chapter", "chapter_id", required=True, help="Chapter id to project.")
@_handle
def meta_lens(workspace: Path, chapter_id: str) -> None:
    """Project a per-chapter lens that book-compose reads."""
    project_lens = _import_metabook("project_lens")
    out = project_lens(workspace.resolve(), chapter_id)
    click.echo(f"wrote {out}")


@meta.command("gap")
@click.argument("workspace", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--chapter", "chapter_id", required=True, help="Chapter id to score.")
@click.option("--required-per-node", default=3, type=int, help="Claims needed per node for full coverage.")
@_handle
def meta_gap(workspace: Path, chapter_id: str, required_per_node: int) -> None:
    """Score thesis-node coverage and write a gap report."""
    build_coverage_report = _import_metabook("build_coverage_report")
    out = build_coverage_report(workspace.resolve(), chapter_id,
                                required_per_node=required_per_node)
    click.echo(f"wrote {out}")
```

- [ ] **Step 4: Run test**

Run: `cd skills/neurosym-forge && python -m pytest tests/test_forge_cli_meta.py -v`
Expected: PASS (2 passed). `meta lens` with no workspace exits non-zero (missing argument).

- [ ] **Step 5: Commit**

```bash
git add skills/neurosym-forge/scripts/forge_cli.py skills/neurosym-forge/tests/test_forge_cli_meta.py
git commit -m "forge: meta subcommand group (acquire, synthesize, lens, gap)"
```

### Task 16: Capability playbooks

**Files:**
- Create: `SM/references/acquire-playbook.md`
- Create: `SM/references/synthesize-playbook.md`
- Create: `SM/references/lens-and-gap-playbook.md`

- [ ] **Step 1: Write the three playbooks**

`acquire-playbook.md`:
```markdown
# Acquire playbook

Grow the source set by walking the citation graph outward from seeds, rank
and triage candidates, then ingest the keepers via book-knowledge.

```bash
forge meta acquire <workspace> --chapter <id> --seed arxiv:XXXX --seed doi:YYY --query "topic" --depth 2
```

Steps the orchestrator runs (each an exported entry point you can call directly):
1. `expand_seeds(seeds, depth)` — citation-graph traversal via scrapling-fetch.
2. `rank(query_text, candidates)` — relevance ranking (needs the ML extras).
3. `triage(...)` — partition into auto-approve / manual-review / reject.
4. `apply_veto(...)` — demote candidates unreachable from the thesis tree.
5. `download_and_ingest(...)` — fetch PDFs and stage via book-knowledge.

Artifacts: `syntopical/acquisition/{manifest.jsonl, triage-<run>.md, pending-seeds.txt}`.
Gap reports append uncovered-node statements to `pending-seeds.txt`; feed them
back with another `forge meta acquire` run.

ML extras: ranking imports torch + sentence-transformers. Without them, run
`expand_seeds` / `triage` directly and skip ranking.
```

`synthesize-playbook.md`:
```markdown
# Synthesize playbook

Build the cross-source view over the verified claim ledger.

```bash
forge meta synthesize <workspace> --chapter <id>
```

Produces:
- `syntopical/topic-map.md` — concepts grouped by thesis top-level node.
- `syntopical/disputed-questions/<topic>.md` — claims that conflict, by topic.
- `syntopical/concepts/<slug>.md` — concept reconciliation with surface-form alternates.

Symbolic reasoning (concept clustering, dispute detection) runs through
`booklogic_adapter`; set `SYNTOPICAL_NO_BOOKLOGIC=1` to use the in-memory
fallback. Output is byte-deterministic — re-running yields identical files.
```

`lens-and-gap-playbook.md`:
```markdown
# Lens and Gap playbook

## Lens

Project a per-chapter view that book-compose reads when drafting.

```bash
forge meta lens <workspace> --chapter <id>
```

Writes `syntopical/lenses/<id>.md` with YAML frontmatter and four sections in
strict order — Topics, Disputed Questions, Concept Reconciliation, Coverage.
`book-compose.read_lens()` parses these; do not reorder them.

## Gap

Score how well verified claims cover each thesis node.

```bash
forge meta gap <workspace> --chapter <id> --required-per-node 3
```

Writes `syntopical/reports/gaps-<id>-<ts>.md` (rows with coverage < 1.0) and,
via `seed_from_gap_report`, appends uncovered-node statements to
`syntopical/acquisition/pending-seeds.txt` for the next acquire run.
```

- [ ] **Step 2: Verify clean of domain terms**

Run: `grep -rniE 'praos|algorand|ouroboros|epochpoet|tau|τ' SM/references/`
Expected: no matches.

- [ ] **Step 3: Commit**

```bash
git add SM/references/acquire-playbook.md SM/references/synthesize-playbook.md SM/references/lens-and-gap-playbook.md
git commit -m "docs: acquire/synthesize/lens-and-gap playbooks"
```

### Task 17: PR 3 green check + open PR

- [ ] **Step 1: Full suites**

Run: `cd SM && ./.venv/Scripts/python.exe -m pytest -q` then `cd skills/neurosym-forge && python -m pytest -q`
Expected: both green.

- [ ] **Step 2: Push + PR**

```bash
git push
gh pr create --title "syntopical-metabook v0.3 PR 3 — wake sub-workflows (forge meta)" --body "Exports all five capabilities from skill_api (API 0.3), adds the forge meta CLI group (acquire/synthesize/lens/gap) mirroring forge govern, and ships per-capability playbooks. forge govern is unchanged."
```

---

# PR 4 — QA plan + utility/value plan documents

Two standalone documents. No code.

### Task 18: QA plan document

**Files:**
- Create: `docs/superpowers/plans/2026-05-31-syntopical-metabook-qa-plan.md`

- [ ] **Step 1: Write the QA plan**

The document must contain these sections with concrete content (not headers alone):

1. **Test layers per capability** — a table: capability × {unit, integration, conformance} listing the actual test files that cover each cell, and naming any empty cells as gaps to fill.
2. **Invariants enforced as tests:**
   - *Determinism/idempotence:* every writer (positions.edn, topic-map, concepts, disputes, lens, gap reports, governance renders) produces byte-identical output on a second run. List the existing idempotence tests and add a note for any writer lacking one.
   - *Boundary — writes confined to `syntopical/`:* describe a test that snapshots the workspace tree before/after each capability and asserts no file outside `syntopical/` (and the book-knowledge-mediated `raw/`/`claims/` for acquire) changed.
   - *Boundary — no direct HTTP:* describe a static test that greps the `scripts/` tree for forbidden imports (`requests`, `httpx`, `urllib.request`, `aiohttp`) outside the scrapling-fetch boundary and fails if any appear.
   - *Staleness:* the renderers refuse a stale positions.edn (PR 1 tests).
3. **CI matrix entry** — the exact `make`/pytest invocation for the skill suite, the install+import smoke leg (`import skill_api`), and a statement that the conformance canary runs on every checkout (no skips). Cross-reference the suite-wide CI skill matrix (the repo's existing P2-matrix coverage legs).
4. **Network-path manual smoke checklist** — the one path CI cannot exercise (`forge meta acquire` over live scrapling-fetch): a numbered manual procedure with a tiny real seed, expected manifest growth, and a teardown step.
5. **Coverage gates** — the bar each capability clears before its CLI command is "shipped": unit + integration green, conformance green where applicable, idempotence asserted, boundary tests green.

- [ ] **Step 2: Self-check the QA plan against reality**

Run: `cd SM && ./.venv/Scripts/python.exe -m pytest --collect-only -q | tail -20` and confirm every test file the QA plan names actually exists. Fix any mismatch in the document.

- [ ] **Step 3: Commit**

```bash
git add docs/superpowers/plans/2026-05-31-syntopical-metabook-qa-plan.md
git commit -m "docs: syntopical-metabook QA plan"
```

### Task 19: Utility / value plan document

**Files:**
- Create: `docs/superpowers/plans/2026-05-31-syntopical-metabook-utility.md`

- [ ] **Step 1: Write the utility plan**

Sections with concrete content:

1. **Who uses it and why** — the author building a book in the suite; one line of value per capability.
2. **The end-to-end author loop** — an ASCII flow of Acquire → Synthesize → Gap → Lens → book-compose with Govern as the gate, annotated with the workspace artifact each stage produces/consumes (`syntopical/acquisition/`, `topic-map.md`, `reports/gaps-*.md`, `lenses/<ch>.md`, `positions.edn`).
3. **Position in the suite** — a dependency sketch: syntopical-metabook sits above book-knowledge (facts) and neurosym-forge (rules), feeds book-compose (drafting); what it owns that no sibling does (the syntopical layer + schools-of-thought governance).
4. **"Use when…" scenarios** — one concrete trigger per capability, matching the rewritten SKILL.md `description` (e.g. "the chapter cites three sources but the thesis has six unsupported nodes → `forge meta gap` then `acquire`").
5. **Value summary** — what shipping v0.3 unlocked: an honest description, five CLI-reachable capabilities, governance that runs on real workspaces (defconstraint), and an always-on conformance canary.

- [ ] **Step 2: Commit**

```bash
git add docs/superpowers/plans/2026-05-31-syntopical-metabook-utility.md
git commit -m "docs: syntopical-metabook utility/value plan"
```

### Task 20: PR 4 + close-out

- [ ] **Step 1: Push + PR**

```bash
git push
gh pr create --title "syntopical-metabook v0.3 PR 4 — QA plan + utility plan" --body "Standalone QA plan (layered coverage, invariants-as-tests, CI matrix, manual network smoke, coverage gates) and utility/value plan (author loop, suite position, use-when scenarios)."
```

- [ ] **Step 2: Final full-suite check**

Run: `cd SM && ./.venv/Scripts/python.exe -m pytest -q` and `cd skills/neurosym-forge && python -m pytest -q`
Expected: both green; 0 unexpected skips.

---

## Self-Review

**Spec coverage (against `2026-05-31-syntopical-metabook-v0.3-generalization-design.md`):**

- §3 five-capability surface — Tasks 12–16 (orchestrators, exports, CLI, playbooks) ✓
- §4.1 SKILL.md description/version/body — Task 10 ✓
- §4.2 neutral governance playbook + map/review/quarantine documented — Task 9 ✓
- §4.3 re-themed fixture — Task 8; neutral conformance workspace replacing EpochPoET test — Task 6 ✓
- §5.1 defconstraint support — Tasks 3–5 ✓
- §5.2 staleness guard — Tasks 1–2 ✓
- §5.3 `:extends` non-change — no task needed (explicit non-change) ✓
- §6.1 skill_api exports (API 0.3) — Task 14 ✓
- §6.2 `forge meta` group, `forge govern` kept — Task 15 ✓
- §6.3 sub-workflow arg contracts — Task 15 options ✓
- §7 boundaries enforced as tests — specified in the QA plan, Task 18 (boundary tests described for the implementer to author) ✓
- §9.1 QA plan — Task 18 ✓
- §9.2 utility plan — Task 19 ✓
- §10 testing layers — Tasks across all PRs; conformance always-on (Task 6) ✓
- §11 PR sequence (4 PRs) — PRs 1–4 ✓

**Gap noted:** §7 says boundary invariants are "promoted to enforced tests." This plan *specifies* those boundary tests in the QA plan (Task 18) rather than authoring them as code tasks, to keep PR 4 documentation-only per §11. If you want the boundary tests as running code in this cycle, add them as tasks to PR 3 (a `tests/unit/test_boundaries.py` with the no-HTTP-import grep and a write-confinement check). Recommended: author them in PR 3; the QA plan then references real tests, not described ones. **Decision for the executor:** promote the two boundary tests into PR 3 as a Task 16b if time permits; otherwise they remain QA-plan specifications.

**Placeholder scan:** No "TBD"/"implement later". The `forge meta acquire` and `run_acquire` tasks carry real code with explicit "re-read and confirm signatures" steps — these are verification steps, not placeholders, and are required because of the authoring-session read glitch.

**Type consistency:** `Position` fields match `_positions_io.py`. `RuleEvidence` constructor matches `_stance.py`. `check_not_stale(artifact, sources)` signature consistent across Tasks 1–2. `run_acquire`/`run_synthesize` return dicts with the keys the CLI (Task 15) reads (`ingested`, `topic_map`/`disputed`/`concepts`). `_import_metabook(attr)` maps every attr the CLI calls.

**Known risk:** Three details depend on source the authoring session could not fully read — `TriageConfig`/`TriageResult` field names (Task 13), the exact `:derive-via` key in `constraints.edn` (Task 3), and whether `rank_candidates.py` hard-imports ML at module load (Task 14). Each has an explicit re-read/confirm step before its code is written. These are the only places the executor must reconcile against live source.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-05-31-syntopical-metabook-v0.3-generalization.md`. Two execution options:

**1. Subagent-Driven (recommended)** — fresh subagent per task, two-stage review between tasks, fast iteration.

**2. Inline Execution** — execute tasks in this session with checkpoints for review.

Which approach?

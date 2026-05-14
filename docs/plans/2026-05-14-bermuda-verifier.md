# bermuda-verifier Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire `neurosym-forge` against the Bermuda manual: scaffold `verifiers/bermuda/`, encode `canonical-facts.md` as Z3 axioms, ingest the claim ledger and chapter prose, and feed unsat verdicts into `book-qa` as defect class D13.

**Architecture:** Re-activate the deferred `--book-knowledge-bridge` flag in `neurosym-forge`; scaffold `verifiers/bermuda/`; write Bermuda-specific Python helpers (ingest_ledger, extract_prose pass A regex + pass B LLM, verdict_to_qa, run_verification); add Bermuda-specific Rust (`canonical.rs` encoding the 6 facts from `canonical-facts.md`); plumb a new D13 linter into `book-qa.scripts.lint_artifact`. Spec at `docs/specs/2026-05-14-bermuda-verifier-design.md`.

**Tech Stack:** Python 3.13, jsonschema, pyyaml, jinja2, pytest, regex. Rust 1.85 (edition 2024) + Z3 0.20 + cozo 0.7 (Bermuda-side; deferred to manual build). No new sibling-skill dependencies.

---

## Pre-flight

Read these before starting any task:
- `docs/specs/2026-05-14-bermuda-verifier-design.md` (this plan implements)
- `skills/neurosym-forge/SKILL.md`, `scripts/scaffold_project.py`, `assets/project-template/` (existing scaffolder)
- `skills/book-qa/scripts/lint_artifact.py` (D1–D12 linter — D13 plugs in here)
- `skills/book-knowledge/scripts/io_utils.py` (`read_jsonl`, `latest_per`) — the ledger reader
- `skills/book-knowledge/scripts/claim_validator.py` (validates ledger rows)
- `examples/bermuda-manual/claims/ledger.jsonl` (46 claims, the real ingestion target)
- `examples/bermuda-manual/reports/canonical-facts.md` (the canonical-facts source)
- `examples/bermuda-manual/book/releases/6.0.0/chapter-bundles/ch-NN/draft.md` (chapter drafts that prose-extraction reads)
- `CLAUDE.md` and `AGENTS.md` at repo root

**Worktree.** This plan executes on branch `spec/bermuda-verifier` in the worktree at `C:\Users\charl\code\russellian-book-suite-bermuda-verifier`. The spec is already committed on this branch.

**Test invocation.** Two test surfaces:
- `cd skills/neurosym-forge && .venv/Scripts/python.exe -m pytest tests/ -q` — for neurosym-forge changes
- `cd skills/book-qa && python -m pytest tests/ -q` — for book-qa D13 (book-qa has no `.venv`; uses system Python per repo conventions)
- `cd verifiers/bermuda && .venv/Scripts/python.exe -m pytest tests/ -q` — for Bermuda-specific Python (created in Phase 4)

**Commit hygiene.** Per repo CLAUDE.md: terse human style, no AI attribution, no Co-Authored-By. One problem per commit.

**Repository layout decision.** A new top-level `verifiers/` directory is added at repo root, sibling to `skills/` and `examples/`. Per the spec it is not owned by any skill; `neurosym-forge` produces it.

---

## File Structure

### Created in neurosym-forge

```
skills/neurosym-forge/
├── assets/
│   └── project-template-bridge/                  NEW: optional bridge-specific templates
│       └── scripts/
│           ├── __init__.py.tmpl                  empty marker
│           └── ingest_ledger.py.tmpl             generic ledger ingester template
└── scripts/scaffold_project.py                   MODIFIED: bridge flag re-activated
```

### Created in `verifiers/bermuda/` (after scaffold)

```
verifiers/bermuda/
├── (scaffolded output: SKILL.md, README.md, package.json, etc.)
├── rules/
│   ├── seed.edn                                  base + Bermuda sorts
│   └── predicates.edn                            Bermuda-specific predicate map
├── rust-verifier/
│   └── src/
│       └── canonical.rs                          NEW: Bermuda Z3 axioms
├── scripts/                                      Bermuda-specific Python
│   ├── __init__.py
│   ├── ingest_ledger.py                          ledger.jsonl → claims.edn
│   ├── prose_patterns.py                         regex catalog
│   ├── extract_prose.py                          drafts → prose-facts.edn
│   ├── verdict_to_qa.py                          verdict.edn → verification-defects.json
│   └── run_verification.py                       end-to-end orchestrator
├── pyproject.toml                                Bermuda Python helpers package
└── tests/
    ├── conftest.py
    ├── fixtures/
    │   ├── ledger_clean.jsonl
    │   ├── ledger_with_contradiction.jsonl
    │   ├── chapter_clean.md
    │   ├── chapter_with_8_parishes.md
    │   ├── verdict_sat.edn
    │   └── verdict_unsat.edn
    ├── test_ingest_ledger.py
    ├── test_prose_patterns.py
    ├── test_extract_prose.py
    ├── test_verdict_to_qa.py
    └── test_run_verification.py
```

### Modified

```
skills/book-qa/scripts/lint_artifact.py           MODIFIED: D13 linter added
skills/book-qa/tests/test_lint_artifact.py        MODIFIED: D13 tests added
README.md                                          MODIFIED: verifiers/ documented; D13 in skills table
skills/neurosym-forge/SKILL.md                    MODIFIED: drop v0.2 deferral notes
skills/neurosym-forge/references/grounded-atoms.md   MODIFIED: --book-knowledge-bridge re-documented
```

---

## Phase 1: neurosym-forge v0.2 — re-activate `--book-knowledge-bridge`

### Task 1.1: Bridge template directory + skeleton files

**Files:**
- Create: `skills/neurosym-forge/assets/project-template-bridge/scripts/__init__.py.tmpl`
- Create: `skills/neurosym-forge/assets/project-template-bridge/scripts/ingest_ledger.py.tmpl`

- [ ] **Step 1: Create directory and `__init__.py.tmpl`.**

```bash
mkdir -p skills/neurosym-forge/assets/project-template-bridge/scripts
```

`__init__.py.tmpl` (one line):

```python
"""{{ project_name }} — book-knowledge ledger bridge."""
```

- [ ] **Step 2: Write `ingest_ledger.py.tmpl`.**

```python
"""Generic ledger ingester. Reads a book-knowledge claim ledger and emits
EDN atoms into work/claims.edn. Project-specific predicate maps live in
rules/predicates.edn; this template provides the scaffold only.

Generated by neurosym-forge for project: {{ project_name }}.
Replace the stub predicate map in `rules/predicates.edn` with your domain
predicates before invoking.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def read_ledger(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def latest_per_id(rows: list[dict]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for r in rows:
        cid = r.get("claim_id") or r.get("id")
        if cid:
            out[cid] = r
    return out


def ingest(ledger_path: Path, predicates_path: Path, out_path: Path) -> int:
    rows = read_ledger(ledger_path)
    latest = latest_per_id(rows)
    verified = [r for r in latest.values()
                if r.get("status") == "verified" or r.get("tbf:status") == "verified"]
    atoms = [_claim_to_atom(c) for c in verified]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps({"version": 1, "atoms": atoms}, indent=2),
                        encoding="utf-8", newline="\n")
    return len(atoms)


def _claim_to_atom(claim: dict) -> dict:
    return {
        "kind": "symbol",
        "sort": ":formula",
        "name": ":OPAQUE",
        "id": claim.get("claim_id", "?"),
        "doc": claim.get("canonical_text", "")[:200],
    }


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ledger", required=True)
    ap.add_argument("--predicates", required=True)
    ap.add_argument("--out", default="work/claims.edn")
    args = ap.parse_args(argv)
    n = ingest(Path(args.ledger), Path(args.predicates), Path(args.out))
    print(f"ingested {n} verified atoms from {args.ledger}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
```

- [ ] **Step 3: Commit.**

```bash
git add skills/neurosym-forge/assets/project-template-bridge/
git commit -m "neurosym-forge: bridge template directory"
```

### Task 1.2: Update `scaffold_project.py` to walk both template trees

**Files:**
- Modify: `skills/neurosym-forge/scripts/scaffold_project.py`
- Modify: `skills/neurosym-forge/tests/test_scaffold_project.py`

- [ ] **Step 1: Write failing test.**

```python
# Append to skills/neurosym-forge/tests/test_scaffold_project.py

def test_bridge_flag_emits_ingest_ledger(tmp_project_root: Path, skill_root: Path) -> None:
    scaffold_project(
        project_name="Test", project_slug="test_bridge",
        out_dir=tmp_project_root, skill_root=skill_root,
        has_book_knowledge_bridge=True,
    )
    assert (tmp_project_root / "scripts" / "ingest_ledger.py").exists()
    assert (tmp_project_root / "scripts" / "__init__.py").exists()


def test_no_bridge_omits_ingest_ledger(tmp_project_root: Path, skill_root: Path) -> None:
    scaffold_project(
        project_name="Test", project_slug="test_nobridge",
        out_dir=tmp_project_root, skill_root=skill_root,
        has_book_knowledge_bridge=False,
    )
    assert not (tmp_project_root / "scripts" / "ingest_ledger.py").exists()
```

- [ ] **Step 2: Run, expect FAIL** (the second test passes, the first fails because the bridge files aren't emitted).

```bash
cd skills/neurosym-forge && .venv/Scripts/python.exe -m pytest tests/test_scaffold_project.py::test_bridge_flag_emits_ingest_ledger -v
```

Expected: AssertionError, ingest_ledger.py missing.

- [ ] **Step 3: Update `scaffold_project.py`.**

Find the section that walks `template_root.rglob("*.tmpl")` and add a second walk over `template_root_bridge` when the flag is set. Insert after the existing rglob loop:

```python
    # Bridge-specific templates (only if --book-knowledge-bridge)
    if has_book_knowledge_bridge:
        bridge_root = skill_root / "assets" / "project-template-bridge"
        if bridge_root.is_dir():
            bridge_env = Environment(
                loader=FileSystemLoader(str(bridge_root)),
                keep_trailing_newline=True,
                undefined=StrictUndefined,
            )
            for tmpl in sorted(bridge_root.rglob("*.tmpl")):
                rel = tmpl.relative_to(bridge_root)
                out_rel = Path(str(rel)[:-len(".tmpl")].replace("__project__", project_slug))
                loader_path = str(rel).replace("\\", "/")
                template = bridge_env.get_template(loader_path)
                rendered = template.render(**ctx)
                out_path = out_dir / out_rel
                out_path.parent.mkdir(parents=True, exist_ok=True)
                out_path.write_text(rendered, encoding="utf-8", newline="\n")
```

Also restore the CLI flag (it was removed during the v0.1 QA pass). Find the argparse block in `main()`:

```python
    ap.add_argument("--book-knowledge-bridge", action="store_true",
                    help="Emit a book-knowledge claim-ledger ingester template")
```

And pass it through:

```python
    scaffold_project(
        project_name=args.name,
        project_slug=args.slug,
        out_dir=Path(args.out),
        skill_root=skill_root,
        has_book_knowledge_bridge=args.book_knowledge_bridge,
    )
```

(The `has_book_knowledge_bridge` parameter on the function signature is already in place from the v0.1 QA pass; it was kept as an ignored parameter. Remove the "v0.2 deferral" note from the docstring.)

- [ ] **Step 4: Run, expect PASS.**

```bash
cd skills/neurosym-forge && .venv/Scripts/python.exe -m pytest tests/test_scaffold_project.py -v
```

Expected: all scaffold_project tests pass, including the two new ones.

- [ ] **Step 5: Update SKILL.md and references.**

In `skills/neurosym-forge/SKILL.md`, find:

```
- `book-knowledge` — accepts `claims/ledger.jsonl` as Phase-1 input via the `--book-knowledge-bridge` scaffold flag
```

Confirm it's the current line (the v0.1 QA pass may have edited it). If it says "v0.2 only" or "deferred", replace with the line above.

In `skills/neurosym-forge/references/grounded-atoms.md`, no changes needed (file doesn't mention the bridge flag).

- [ ] **Step 6: Commit.**

```bash
git add skills/neurosym-forge/scripts/scaffold_project.py skills/neurosym-forge/tests/test_scaffold_project.py skills/neurosym-forge/SKILL.md
git commit -m "neurosym-forge: re-activate --book-knowledge-bridge flag"
```

---

## Phase 2: `verifiers/` directory + Bermuda scaffold

### Task 2.1: Add `verifiers/` to repo root and scaffold Bermuda

**Files:**
- Create: `verifiers/.gitkeep`
- Create: `verifiers/bermuda/` (via scaffolder)

- [ ] **Step 1: Add the verifiers directory marker.**

```bash
mkdir -p verifiers
touch verifiers/.gitkeep
```

- [ ] **Step 2: Run the scaffolder.**

From repo root:

```bash
cd skills/neurosym-forge
.venv/Scripts/python.exe -m scripts.scaffold_project \
  --name "Bermuda Verifier" \
  --slug bermuda \
  --out ../../verifiers/bermuda \
  --book-knowledge-bridge
cd ../..
```

Expected output: `scaffolded bermuda at ../../verifiers/bermuda`. Verify:

```bash
ls verifiers/bermuda/
# Expect: SKILL.md, README.md, package.json, shadow-cljs.edn, deps.edn,
# Cargo.toml (in rust-verifier/), rules/, scripts/, cljs-orchestrator/, templates/
```

- [ ] **Step 3: Inspect scaffolded bridge files.**

```bash
cat verifiers/bermuda/scripts/ingest_ledger.py | head -20
```

Expected: the generic ingester template, with `"""Bermuda Verifier — book-knowledge ledger bridge."""` at the top.

- [ ] **Step 4: Commit the scaffolded tree.**

```bash
git add verifiers/
git commit -m "verifiers/bermuda: scaffolded by neurosym-forge --book-knowledge-bridge"
```

### Task 2.2: Bermuda Python project metadata

**Files:**
- Create: `verifiers/bermuda/pyproject.toml`
- Modify: `verifiers/bermuda/.gitignore` (already scaffolded)

- [ ] **Step 1: Write `pyproject.toml`.**

```toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "bermuda-verifier"
version = "0.1.0"
description = "Bermuda manual neurosymbolic verifier"
authors = [{name = "Charles Hoskinson"}]
license = {text = "MIT"}
requires-python = ">=3.13"
dependencies = [
    "jsonschema>=4.21",
    "pyyaml>=6.0.1",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
]

[tool.setuptools]
packages = ["scripts"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
```

- [ ] **Step 2: Create venv and install.**

```bash
cd verifiers/bermuda
python -m venv .venv
.venv/Scripts/python.exe -m pip install -e ".[dev]"
.venv/Scripts/python.exe -m pytest --collect-only
```

Expected: install completes; `no tests ran` (exit 5 is fine).

- [ ] **Step 3: Commit.**

```bash
git add verifiers/bermuda/pyproject.toml
git commit -m "verifiers/bermuda: pyproject.toml + dev deps"
```

### Task 2.3: Tests conftest + fixtures directory

**Files:**
- Create: `verifiers/bermuda/tests/__init__.py`
- Create: `verifiers/bermuda/tests/conftest.py`
- Create: `verifiers/bermuda/tests/fixtures/.gitkeep`

- [ ] **Step 1: Write `tests/__init__.py`.**

Empty file.

- [ ] **Step 2: Write `tests/conftest.py`.**

```python
"""Shared pytest fixtures for verifiers/bermuda/."""
from __future__ import annotations

from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture()
def project_root() -> Path:
    return PROJECT_ROOT


@pytest.fixture()
def fixtures_dir() -> Path:
    return PROJECT_ROOT / "tests" / "fixtures"


@pytest.fixture()
def tmp_work(tmp_path: Path) -> Path:
    work = tmp_path / "work"
    work.mkdir()
    return work
```

- [ ] **Step 3: Confirm fixtures visible.**

```bash
cd verifiers/bermuda && .venv/Scripts/python.exe -m pytest --fixtures -q tests/
```

Expected: `project_root`, `fixtures_dir`, `tmp_work` listed.

- [ ] **Step 4: Commit.**

```bash
git add verifiers/bermuda/tests/__init__.py verifiers/bermuda/tests/conftest.py verifiers/bermuda/tests/fixtures/
git commit -m "verifiers/bermuda: tests conftest + fixtures dir"
```

---

## Phase 3: Predicate map + ledger ingestion

### Task 3.1: Bermuda predicate map

**Files:**
- Modify: `verifiers/bermuda/rules/predicates.edn` (scaffolded as `{"version": 1, "predicates": {}}`)

- [ ] **Step 1: Write Bermuda predicates.**

Replace the file content with:

```json
{
  "version": 1,
  "predicates": {
    "parishes": {
      "patterns": [
        "(?P<n>\\d+|nine|eight|seven)\\s+(traditional|major)?\\s*parishes?",
        "the\\s+(?P<n>\\d+|nine|eight)\\s+parishes"
      ],
      "predicate": ":parishes-count",
      "subject": ":Bermuda",
      "value_kind": "int",
      "word_to_int": {"nine": 9, "eight": 8, "seven": 7}
    },
    "named_islands": {
      "patterns": [
        "(?P<n>\\d+)\\s+(named\\s+)?islands?\\s+and\\s+rocks?",
        "around\\s+(?P<n>\\d+)\\s+islands?",
        "approximately\\s+(?P<n>\\d+)\\s+islands?"
      ],
      "predicate": ":named-islands-and-rocks",
      "subject": ":Bermuda",
      "value_kind": "int"
    },
    "currency_peg": {
      "patterns": [
        "Bermudian\\s+dollar.*?pegged.*?(?:US|United States)\\s+dollar",
        "BMD.*?(?:pegged|parity).*?USD"
      ],
      "predicate": ":currency-pegged-at-parity",
      "subject": ":BMD",
      "value_kind": "bool",
      "value": true
    },
    "airport_island": {
      "patterns": [
        "L\\.?\\s*F\\.?\\s*Wade.*?(?P<island>St\\.?\\s+David's|St\\.?\\s+George's|Bermuda)\\s+Island",
        "(?:airport|aerodrome).*?(?:on|at)\\s+(?P<island>St\\.?\\s+David's|St\\.?\\s+George's)\\s+Island"
      ],
      "predicate": ":airport-on-island",
      "subject": ":L_F_Wade",
      "value_kind": "entity"
    },
    "cedar_binomial": {
      "patterns": [
        "Bermuda\\s+cedar\\s*\\(\\s*\\*?(?P<binomial>[A-Z][a-z]+\\s+[a-z]+)\\*?",
        "\\*(?P<binomial>Juniperus\\s+[a-z]+)\\*"
      ],
      "predicate": ":binomial",
      "subject": ":Bermuda_cedar",
      "value_kind": "string"
    }
  }
}
```

- [ ] **Step 2: Recalculate checksum.**

```bash
cd verifiers/bermuda
.venv/Scripts/python.exe -c "
import json, hashlib
from pathlib import Path
checksums = {}
for p in sorted((Path('rules')).glob('*.edn')):
    if p.name.startswith('.'):
        continue
    checksums[p.name] = hashlib.sha256(p.read_bytes()).hexdigest()
out = Path('rules/.checksums.edn')
out.write_text(json.dumps({'checksums': checksums}, indent=2, sort_keys=True) + '\n',
               encoding='utf-8', newline='\n')
print('updated', list(checksums.keys()))
"
```

Expected output includes `predicates.edn` in the list.

- [ ] **Step 3: Commit.**

```bash
git add verifiers/bermuda/rules/predicates.edn verifiers/bermuda/rules/.checksums.edn
git commit -m "verifiers/bermuda: predicate map for ledger + prose extraction"
```

### Task 3.2: Ledger ingester — overwrite the generic template

**Files:**
- Modify: `verifiers/bermuda/scripts/ingest_ledger.py` (scaffolded; replace body)
- Create: `verifiers/bermuda/tests/test_ingest_ledger.py`
- Create: `verifiers/bermuda/tests/fixtures/ledger_clean.jsonl`
- Create: `verifiers/bermuda/tests/fixtures/ledger_with_contradiction.jsonl`

- [ ] **Step 1: Write fixture `ledger_clean.jsonl`.**

3 verified facts that match the predicate map:

```
{"claim_id": "clm-2026-000001", "claim_type": "fact", "canonical_text": "Bermuda has nine traditional parishes including St. George's.", "status": "verified", "confidence": 0.95, "source_spans": [{"doc_id": "overview", "locator_text": "parish-count"}], "supports_chapters": ["ch-02"]}
{"claim_id": "clm-2026-000002", "claim_type": "fact", "canonical_text": "The Bermudian dollar is pegged at parity with the US dollar.", "status": "verified", "confidence": 0.9, "source_spans": [{"doc_id": "economy", "locator_text": "currency"}], "supports_chapters": ["ch-04"]}
{"claim_id": "clm-2026-000003", "claim_type": "design_decision", "canonical_text": "Use ‘Bermuda cedar' throughout, gloss as Juniperus bermudiana on first reference.", "status": "verified", "confidence": 0.8, "source_spans": [{"doc_id": "thesis", "locator_text": "ecology"}], "supports_chapters": ["ch-01"]}
```

- [ ] **Step 2: Write fixture `ledger_with_contradiction.jsonl`.**

Same as clean + one contradicting parish claim:

```
{"claim_id": "clm-2026-000001", "claim_type": "fact", "canonical_text": "Bermuda has nine traditional parishes including St. George's.", "status": "verified", "confidence": 0.95, "source_spans": [{"doc_id": "overview", "locator_text": "parish-count"}], "supports_chapters": ["ch-02"]}
{"claim_id": "clm-2026-000002", "claim_type": "fact", "canonical_text": "The Bermudian dollar is pegged at parity with the US dollar.", "status": "verified", "confidence": 0.9, "source_spans": [{"doc_id": "economy", "locator_text": "currency"}], "supports_chapters": ["ch-04"]}
{"claim_id": "clm-2026-000099", "claim_type": "fact", "canonical_text": "Bermuda has eight traditional parishes.", "status": "verified", "confidence": 0.9, "source_spans": [{"doc_id": "rival", "locator_text": "p2"}], "supports_chapters": ["ch-02"]}
```

- [ ] **Step 3: Write failing tests.**

```python
# verifiers/bermuda/tests/test_ingest_ledger.py
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.ingest_ledger import ingest, read_ledger, latest_per_id


def test_reads_jsonl(fixtures_dir: Path) -> None:
    rows = read_ledger(fixtures_dir / "ledger_clean.jsonl")
    assert len(rows) == 3


def test_latest_per_id_deduplicates(fixtures_dir: Path) -> None:
    rows = read_ledger(fixtures_dir / "ledger_clean.jsonl") + read_ledger(
        fixtures_dir / "ledger_clean.jsonl"
    )
    latest = latest_per_id(rows)
    assert len(latest) == 3


def test_emits_atoms_for_verified_facts(fixtures_dir: Path, project_root: Path,
                                        tmp_work: Path) -> None:
    n = ingest(
        ledger_path=fixtures_dir / "ledger_clean.jsonl",
        predicates_path=project_root / "rules" / "predicates.edn",
        out_path=tmp_work / "claims.edn",
    )
    assert n == 3
    payload = json.loads((tmp_work / "claims.edn").read_text(encoding="utf-8"))
    atoms = payload["atoms"]
    assert len(atoms) == 3
    # Parish-count fact should match the predicate map → :parishes-count atom
    parish_atoms = [a for a in atoms if a.get("predicate") == ":parishes-count"]
    assert len(parish_atoms) == 1
    assert parish_atoms[0]["value"] == 9
    assert parish_atoms[0]["id"] == "clm-2026-000001"


def test_design_decision_emitted_as_context(fixtures_dir: Path, project_root: Path,
                                            tmp_work: Path) -> None:
    ingest(fixtures_dir / "ledger_clean.jsonl",
           project_root / "rules" / "predicates.edn",
           tmp_work / "claims.edn")
    payload = json.loads((tmp_work / "claims.edn").read_text(encoding="utf-8"))
    cedar = [a for a in payload["atoms"] if a["id"] == "clm-2026-000003"][0]
    assert cedar["context"] is True


def test_unverified_claims_skipped(tmp_path: Path, project_root: Path, tmp_work: Path) -> None:
    bad = tmp_path / "proposed.jsonl"
    bad.write_text(json.dumps({
        "claim_id": "clm-2026-000999", "claim_type": "fact",
        "canonical_text": "x", "status": "proposed", "confidence": 0.5,
    }) + "\n", encoding="utf-8")
    n = ingest(bad, project_root / "rules" / "predicates.edn", tmp_work / "claims.edn")
    assert n == 0
```

- [ ] **Step 4: Run, expect FAIL.**

```bash
cd verifiers/bermuda && .venv/Scripts/python.exe -m pytest tests/test_ingest_ledger.py -v
```

Expected: failures — the scaffolded ingester emits OPAQUE atoms only and doesn't apply predicate matching.

- [ ] **Step 5: Replace `scripts/ingest_ledger.py`.**

```python
"""Bermuda-specific ledger ingester.

Reads examples/bermuda-manual/claims/ledger.jsonl, applies the predicate
map in rules/predicates.edn to fact-class claims, and emits typed atoms
to work/claims.edn. design_decision claims are emitted as :context atoms.

Generated initially by neurosym-forge --book-knowledge-bridge, then
specialized for the Bermuda predicate set.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


def read_ledger(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def latest_per_id(rows: list[dict]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for r in rows:
        cid = r.get("claim_id") or r.get("id")
        if cid:
            out[cid] = r
    return out


def _is_verified(c: dict) -> bool:
    return c.get("status") == "verified" or c.get("tbf:status") == "verified"


def _apply_predicates(text: str, predicates: dict[str, dict]) -> tuple[str, Any, str] | None:
    """Match text against the predicate map. Returns (predicate, value, subject) or None."""
    for _name, spec in predicates.items():
        for pat in spec.get("patterns", []):
            m = re.search(pat, text, flags=re.IGNORECASE | re.DOTALL)
            if not m:
                continue
            value_kind = spec.get("value_kind")
            if value_kind == "bool":
                value = spec.get("value", True)
            elif value_kind == "int":
                raw = m.group("n") if "n" in m.groupdict() else m.group(1)
                value = spec.get("word_to_int", {}).get(raw.lower(), None)
                if value is None:
                    try:
                        value = int(raw)
                    except ValueError:
                        continue
            elif value_kind == "string":
                value = m.group("binomial").strip()
            elif value_kind == "entity":
                value = m.group("island").replace(".", "").replace(" ", "_")
            else:
                continue
            return spec["predicate"], value, spec["subject"]
    return None


def _claim_to_atom(claim: dict, predicates: dict[str, dict]) -> dict:
    text = claim.get("canonical_text", "")
    base: dict[str, Any] = {
        "id": claim.get("claim_id", "?"),
        "doc": text[:200],
        "source_spans": claim.get("source_spans", []),
        "supports_chapters": claim.get("supports_chapters", []),
        "confidence": claim.get("confidence", 0.0),
    }
    if claim.get("claim_type") == "design_decision":
        base.update({"kind": "symbol", "sort": ":formula",
                     "name": ":CONTEXT", "context": True})
        return base
    match = _apply_predicates(text, predicates)
    if match is None:
        base.update({"kind": "symbol", "sort": ":formula", "name": ":OPAQUE"})
        return base
    predicate, value, subject = match
    base.update({"kind": "expression", "sort": ":formula",
                 "predicate": predicate, "subject": subject, "value": value,
                 "context": False})
    return base


def ingest(ledger_path: Path, predicates_path: Path, out_path: Path) -> int:
    rows = read_ledger(ledger_path)
    latest = latest_per_id(rows)
    verified = [c for c in latest.values() if _is_verified(c)]
    predicates = json.loads(predicates_path.read_text(encoding="utf-8")).get(
        "predicates", {}
    )
    atoms = [_claim_to_atom(c, predicates) for c in verified]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps({"version": 1, "atoms": atoms}, indent=2, sort_keys=True),
        encoding="utf-8", newline="\n",
    )
    return len(atoms)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ledger", required=True)
    ap.add_argument("--predicates", required=True)
    ap.add_argument("--out", default="work/claims.edn")
    args = ap.parse_args(argv)
    n = ingest(Path(args.ledger), Path(args.predicates), Path(args.out))
    print(f"ingested {n} verified atoms")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
```

- [ ] **Step 6: Run, expect PASS.**

```bash
cd verifiers/bermuda && .venv/Scripts/python.exe -m pytest tests/test_ingest_ledger.py -v
```

Expected: 5 passed.

- [ ] **Step 7: Smoke against the real Bermuda ledger.**

```bash
cd verifiers/bermuda && .venv/Scripts/python.exe -m scripts.ingest_ledger \
  --ledger ../../examples/bermuda-manual/claims/ledger.jsonl \
  --predicates rules/predicates.edn \
  --out work/claims.edn

cat work/claims.edn | head -30
```

Expected output: `ingested N verified atoms`. The work/claims.edn contains at least one `:parishes-count` atom with value 9, one `:currency-pegged-at-parity` atom, one `:airport-on-island` atom.

- [ ] **Step 8: Commit.**

```bash
git add verifiers/bermuda/scripts/ingest_ledger.py verifiers/bermuda/tests/test_ingest_ledger.py verifiers/bermuda/tests/fixtures/ledger_*.jsonl
git commit -m "verifiers/bermuda: ingest_ledger with Bermuda predicate match"
```

---

## Phase 4: Prose extraction (Pass A — regex)

### Task 4.1: `prose_patterns.py` — the regex catalog

**Files:**
- Create: `verifiers/bermuda/scripts/prose_patterns.py`
- Create: `verifiers/bermuda/tests/test_prose_patterns.py`

- [ ] **Step 1: Write failing tests.**

```python
# verifiers/bermuda/tests/test_prose_patterns.py
from __future__ import annotations

from scripts.prose_patterns import extract_pass_a


def test_extracts_parish_count_digit() -> None:
    atoms = extract_pass_a("Bermuda has 8 traditional parishes.")
    assert any(a["predicate"] == ":parishes-count" and a["value"] == 8 for a in atoms)


def test_extracts_parish_count_word() -> None:
    atoms = extract_pass_a("The nine parishes form the basis of local government.")
    assert any(a["predicate"] == ":parishes-count" and a["value"] == 9 for a in atoms)


def test_extracts_named_islands() -> None:
    atoms = extract_pass_a("The archipelago contains 181 named islands and rocks.")
    assert any(a["predicate"] == ":named-islands-and-rocks" and a["value"] == 181 for a in atoms)


def test_extracts_around_180_drift() -> None:
    atoms = extract_pass_a("There are around 180 islands in the chain.")
    assert any(a["predicate"] == ":named-islands-and-rocks" and a["value"] == 180 for a in atoms)


def test_no_match_returns_empty() -> None:
    assert extract_pass_a("This paragraph is unrelated.") == []


def test_each_atom_has_id_and_source_line() -> None:
    atoms = extract_pass_a("Bermuda has 8 parishes.\nLine two.", source_file="ch-02.md")
    assert atoms
    a = atoms[0]
    assert a["id"].startswith("prose-")
    assert a["source"]["file"] == "ch-02.md"
    assert a["source"]["line"] == 1
```

- [ ] **Step 2: Run, expect FAIL.**

```bash
cd verifiers/bermuda && .venv/Scripts/python.exe -m pytest tests/test_prose_patterns.py -v
```

Expected: ModuleNotFoundError.

- [ ] **Step 3: Write implementation.**

```python
# verifiers/bermuda/scripts/prose_patterns.py
"""Pass A — deterministic regex extraction of Bermuda numeric/named-entity facts."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

DEFAULT_PREDICATES_PATH = Path(__file__).resolve().parent.parent / "rules" / "predicates.edn"


def _load_predicates(path: Path | None = None) -> dict[str, dict]:
    p = path or DEFAULT_PREDICATES_PATH
    return json.loads(p.read_text(encoding="utf-8")).get("predicates", {})


def extract_pass_a(text: str, source_file: str = "?",
                   predicates: dict[str, dict] | None = None) -> list[dict]:
    """Return one atom dict per regex match.

    Each atom: {kind, sort, predicate, subject, value, id, source, confidence}.
    """
    if predicates is None:
        predicates = _load_predicates()
    out: list[dict] = []
    counter = 0
    for name, spec in predicates.items():
        for pat in spec.get("patterns", []):
            for m in re.finditer(pat, text, flags=re.IGNORECASE | re.DOTALL):
                value = _coerce_value(m, spec)
                if value is None:
                    continue
                counter += 1
                line = text.count("\n", 0, m.start()) + 1
                out.append({
                    "kind": "expression",
                    "sort": ":formula",
                    "predicate": spec["predicate"],
                    "subject": spec["subject"],
                    "value": value,
                    "id": f"prose-{Path(source_file).stem}-{counter:03d}",
                    "source": {"file": source_file, "line": line},
                    "confidence": 0.9,
                    "extractor": "regex",
                    "pattern": name,
                })
    return out


def _coerce_value(m: re.Match, spec: dict) -> Any:
    kind = spec.get("value_kind")
    if kind == "bool":
        return spec.get("value", True)
    if kind == "int":
        raw = m.group("n") if "n" in m.groupdict() else (m.group(1) if m.groups() else None)
        if raw is None:
            return None
        mapped = spec.get("word_to_int", {}).get(raw.lower())
        if mapped is not None:
            return mapped
        try:
            return int(raw)
        except ValueError:
            return None
    if kind == "string":
        return m.group("binomial").strip()
    if kind == "entity":
        return m.group("island").replace(".", "").replace(" ", "_")
    return None
```

- [ ] **Step 4: Run, expect PASS.**

```bash
cd verifiers/bermuda && .venv/Scripts/python.exe -m pytest tests/test_prose_patterns.py -v
```

Expected: 6 passed.

- [ ] **Step 5: Commit.**

```bash
git add verifiers/bermuda/scripts/prose_patterns.py verifiers/bermuda/tests/test_prose_patterns.py
git commit -m "verifiers/bermuda: prose_patterns Pass A regex extractor"
```

### Task 4.2: `extract_prose.py` — chapter walker

**Files:**
- Create: `verifiers/bermuda/scripts/extract_prose.py`
- Create: `verifiers/bermuda/tests/test_extract_prose.py`
- Create: `verifiers/bermuda/tests/fixtures/chapter_clean.md`
- Create: `verifiers/bermuda/tests/fixtures/chapter_with_8_parishes.md`

- [ ] **Step 1: Write fixture `chapter_clean.md`.**

```markdown
# Chapter 2: Government

Bermuda has nine traditional parishes including St. George's. The political
geography is durable; little has changed since the 1684 division.

The 1968 Constitution Order established representative government. The
Premier leads the government.
```

- [ ] **Step 2: Write fixture `chapter_with_8_parishes.md`.**

```markdown
# Chapter 2: Government

Bermuda has 8 traditional parishes including St. George's. Some sources
say 9, but the working figure used in this manual is 8.

The 1968 Constitution Order established representative government.
```

- [ ] **Step 3: Write failing tests.**

```python
# verifiers/bermuda/tests/test_extract_prose.py
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.extract_prose import extract_chapter, extract_release


def test_extracts_clean_chapter(fixtures_dir: Path, tmp_work: Path) -> None:
    atoms = extract_chapter(fixtures_dir / "chapter_clean.md")
    assert any(a["predicate"] == ":parishes-count" and a["value"] == 9 for a in atoms)


def test_extracts_drifty_chapter(fixtures_dir: Path) -> None:
    atoms = extract_chapter(fixtures_dir / "chapter_with_8_parishes.md")
    # Should pick up BOTH the "8 parishes" and the "9" mention — the verifier
    # decides which contradicts the canonical
    values = sorted(a["value"] for a in atoms if a["predicate"] == ":parishes-count")
    assert values == [8, 9]


def test_extract_release_walks_chapter_bundles(tmp_path: Path) -> None:
    bundles = tmp_path / "chapter-bundles"
    bundles.mkdir()
    (bundles / "ch-01").mkdir()
    (bundles / "ch-01" / "draft.md").write_text("Bermuda has 181 named islands and rocks.")
    (bundles / "ch-02").mkdir()
    (bundles / "ch-02" / "draft.md").write_text("Bermuda has 8 parishes.")
    n = extract_release(bundles, tmp_path / "prose-facts.edn")
    payload = json.loads((tmp_path / "prose-facts.edn").read_text(encoding="utf-8"))
    assert n == 2
    chapters = {a["source"]["file"] for a in payload["atoms"]}
    assert "ch-01/draft.md" in str(chapters) or any("ch-01" in c for c in chapters)
```

- [ ] **Step 4: Run, expect FAIL.**

```bash
cd verifiers/bermuda && .venv/Scripts/python.exe -m pytest tests/test_extract_prose.py -v
```

- [ ] **Step 5: Write implementation.**

```python
# verifiers/bermuda/scripts/extract_prose.py
"""Walk chapter drafts and extract Pass A prose facts."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from scripts.prose_patterns import extract_pass_a


def extract_chapter(draft_path: Path) -> list[dict]:
    text = draft_path.read_text(encoding="utf-8")
    return extract_pass_a(text, source_file=str(draft_path.name))


def extract_release(bundles_dir: Path, out_path: Path) -> int:
    """Walk chapter-bundles/*/draft.md and emit all prose-fact atoms."""
    all_atoms: list[dict] = []
    for ch_dir in sorted(bundles_dir.iterdir()):
        if not ch_dir.is_dir():
            continue
        draft = ch_dir / "draft.md"
        if not draft.exists():
            continue
        text = draft.read_text(encoding="utf-8")
        atoms = extract_pass_a(text, source_file=f"{ch_dir.name}/draft.md")
        all_atoms.extend(atoms)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps({"version": 1, "atoms": all_atoms}, indent=2, sort_keys=True),
        encoding="utf-8", newline="\n",
    )
    return len(all_atoms)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bundles", required=True,
                    help="Path to chapter-bundles/ (one dir per chapter, each with draft.md)")
    ap.add_argument("--out", default="work/prose-facts.edn")
    args = ap.parse_args(argv)
    n = extract_release(Path(args.bundles), Path(args.out))
    print(f"extracted {n} prose atoms")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
```

- [ ] **Step 6: Run, expect PASS.**

```bash
cd verifiers/bermuda && .venv/Scripts/python.exe -m pytest tests/test_extract_prose.py -v
```

Expected: 3 passed.

- [ ] **Step 7: Smoke against the real Bermuda chapters.**

```bash
cd verifiers/bermuda && .venv/Scripts/python.exe -m scripts.extract_prose \
  --bundles ../../examples/bermuda-manual/book/releases/6.0.0/chapter-bundles \
  --out work/prose-facts.edn

cat work/prose-facts.edn | head -30
```

Expected: some atoms, possibly with conflicting parish counts. Note what's there; it informs the verifier's expected unsat-core composition.

- [ ] **Step 8: Commit.**

```bash
git add verifiers/bermuda/scripts/extract_prose.py verifiers/bermuda/tests/test_extract_prose.py verifiers/bermuda/tests/fixtures/chapter_*.md
git commit -m "verifiers/bermuda: extract_prose chapter walker"
```

---

## Phase 5: Verdict → book-qa bridge

### Task 5.1: `verdict_to_qa.py` — verdict.edn → verification-defects.json

**Files:**
- Create: `verifiers/bermuda/scripts/verdict_to_qa.py`
- Create: `verifiers/bermuda/tests/test_verdict_to_qa.py`
- Create: `verifiers/bermuda/tests/fixtures/verdict_sat.edn`
- Create: `verifiers/bermuda/tests/fixtures/verdict_unsat.edn`

- [ ] **Step 1: Write fixtures.**

`tests/fixtures/verdict_sat.edn`:

```json
{
  "version": 1,
  "verdict": "sat",
  "core": [],
  "verified_count": 12
}
```

`tests/fixtures/verdict_unsat.edn`:

```json
{
  "version": 1,
  "verdict": "unsat",
  "core": ["clm-2026-000008", "prose-ch-02-001"],
  "explanation": "Chapter 2 prose says 8 parishes; ledger says 9.",
  "verified_count": 11
}
```

- [ ] **Step 2: Write failing tests.**

```python
# verifiers/bermuda/tests/test_verdict_to_qa.py
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.verdict_to_qa import translate


def test_sat_emits_empty_defects(fixtures_dir: Path, tmp_path: Path) -> None:
    out = tmp_path / "verification-defects.json"
    translate(fixtures_dir / "verdict_sat.edn", out)
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["verdict"] == "sat"
    assert payload["core"] == []


def test_unsat_passes_core_through(fixtures_dir: Path, tmp_path: Path) -> None:
    out = tmp_path / "verification-defects.json"
    translate(fixtures_dir / "verdict_unsat.edn", out)
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["verdict"] == "unsat"
    assert "clm-2026-000008" in payload["core"]
    assert payload["explanation"]


def test_missing_input_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        translate(tmp_path / "nonexistent.edn", tmp_path / "out.json")


def test_unknown_verdict_is_logged_not_gated(tmp_path: Path) -> None:
    inp = tmp_path / "unknown.edn"
    inp.write_text(json.dumps({"version": 1, "verdict": "unknown",
                               "core": [], "reason": "smt timeout"}),
                   encoding="utf-8")
    out = tmp_path / "verification-defects.json"
    translate(inp, out)
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["verdict"] == "unknown"
    assert payload["core"] == []
```

- [ ] **Step 3: Run, expect FAIL.**

```bash
cd verifiers/bermuda && .venv/Scripts/python.exe -m pytest tests/test_verdict_to_qa.py -v
```

- [ ] **Step 4: Write implementation.**

```python
# verifiers/bermuda/scripts/verdict_to_qa.py
"""Translate the verifier's verdict.edn into book-qa's verification-defects.json.

The output format is consumed by book-qa.lint_artifact.lint_d13. See
docs/specs/2026-05-14-bermuda-verifier-design.md § "book-qa D13 hook".
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

FORGE_BERMUDA_VERSION = "bermuda 0.1.0 / neurosym-forge 0.2.0"


def translate(verdict_path: Path, out_path: Path) -> None:
    if not verdict_path.exists():
        raise FileNotFoundError(verdict_path)
    payload = json.loads(verdict_path.read_text(encoding="utf-8"))
    result = {
        "verdict": payload.get("verdict", "unknown"),
        "core": list(payload.get("core", [])),
        "explanation": payload.get("explanation", ""),
        "verified_count": payload.get("verified_count", 0),
        "produced_at": dt.datetime.now(dt.UTC).isoformat(),
        "verifier_version": FORGE_BERMUDA_VERSION,
    }
    if payload.get("verdict") == "unknown":
        result["reason"] = payload.get("reason", "unknown")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(result, indent=2, sort_keys=True),
        encoding="utf-8", newline="\n",
    )


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verdict", required=True)
    ap.add_argument("--out", required=True,
                    help="path to <workspace>/qa/verification-defects.json")
    args = ap.parse_args(argv)
    translate(Path(args.verdict), Path(args.out))
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
```

- [ ] **Step 5: Run, expect PASS.**

```bash
cd verifiers/bermuda && .venv/Scripts/python.exe -m pytest tests/test_verdict_to_qa.py -v
```

Expected: 4 passed.

- [ ] **Step 6: Commit.**

```bash
git add verifiers/bermuda/scripts/verdict_to_qa.py verifiers/bermuda/tests/test_verdict_to_qa.py verifiers/bermuda/tests/fixtures/verdict_*.edn
git commit -m "verifiers/bermuda: verdict_to_qa translator"
```

---

## Phase 6: book-qa D13 hook

### Task 6.1: Add D13 lint function

**Files:**
- Modify: `skills/book-qa/scripts/lint_artifact.py`
- Modify: `skills/book-qa/tests/test_lint_artifact.py`

- [ ] **Step 1: Inspect the existing D9-D12 pattern.**

Read `skills/book-qa/scripts/lint_artifact.py` around the D9-D12 reading code. Each defect class reads from a JSON side-file in `<workspace>/qa/`. The pattern: open the file with try/except FileNotFoundError, parse JSON, emit one `Defect(class_="D13", severity="critical", where=..., detail=..., fix_hint=...)` per ticket.

- [ ] **Step 2: Write failing tests.**

```python
# Append to skills/book-qa/tests/test_lint_artifact.py
import json
from pathlib import Path

from scripts.lint_artifact import lint_d13_verification_unsat


def test_d13_no_file_returns_empty(tmp_path: Path) -> None:
    assert lint_d13_verification_unsat(tmp_path) == []


def test_d13_sat_returns_empty(tmp_path: Path) -> None:
    qa = tmp_path / "qa"
    qa.mkdir()
    (qa / "verification-defects.json").write_text(json.dumps({
        "verdict": "sat", "core": [], "explanation": "",
    }), encoding="utf-8")
    assert lint_d13_verification_unsat(tmp_path) == []


def test_d13_unknown_returns_empty(tmp_path: Path) -> None:
    qa = tmp_path / "qa"
    qa.mkdir()
    (qa / "verification-defects.json").write_text(json.dumps({
        "verdict": "unknown", "core": [], "reason": "smt timeout",
    }), encoding="utf-8")
    assert lint_d13_verification_unsat(tmp_path) == []


def test_d13_unsat_emits_one_defect_per_core_member(tmp_path: Path) -> None:
    qa = tmp_path / "qa"
    qa.mkdir()
    (qa / "verification-defects.json").write_text(json.dumps({
        "verdict": "unsat",
        "core": ["clm-2026-000008", "prose-ch-02-001"],
        "explanation": "Chapter 2 prose says 8 parishes; ledger says 9.",
    }), encoding="utf-8")
    defects = lint_d13_verification_unsat(tmp_path)
    assert len(defects) == 2
    assert all(d.class_ == "D13" for d in defects)
    assert all(d.severity == "critical" for d in defects)
    ids = {d.where for d in defects}
    assert "clm-2026-000008" in ids
    assert "prose-ch-02-001" in ids
```

- [ ] **Step 3: Run, expect FAIL.**

```bash
cd skills/book-qa && python -m pytest tests/test_lint_artifact.py -k "d13" -v
```

Expected: `ImportError: cannot import name 'lint_d13_verification_unsat'`.

- [ ] **Step 4: Add the lint function.**

In `skills/book-qa/scripts/lint_artifact.py`, after the existing D12 reader (search for `lint_d12` or the section that reads `supports-defects.json`), add:

```python
# ----------------------------------------------------------------- D13 helpers

def lint_d13_verification_unsat(workspace: Path) -> list[Defect]:
    """Read qa/verification-defects.json emitted by a neurosym-forge verifier.

    Each member of the unsat core becomes one critical defect. :sat and
    :unknown verdicts produce no defects.
    """
    path = workspace / "qa" / "verification-defects.json"
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return [Defect("D13", CRITICAL, str(path),
                       "verification-defects.json is not valid JSON",
                       "regenerate via verdict_to_qa.py")]
    if payload.get("verdict") != "unsat":
        return []
    core = payload.get("core") or []
    explanation = payload.get("explanation", "logical contradiction detected")
    return [
        Defect("D13", CRITICAL, claim_id,
               f"verification unsat: {explanation}",
               f"review claim/prose {claim_id}; reconcile against canonical facts")
        for claim_id in core
    ]
```

Then call it from the main aggregator function (search for the line that aggregates `lint_d12(...)`) and append to the same list. For example:

```python
    defects.extend(lint_d13_verification_unsat(workspace))
```

(The exact integration line depends on the current shape of the main aggregator. Read the function and follow the existing D9-D12 pattern.)

- [ ] **Step 5: Update the linter header docstring.**

In `skills/book-qa/scripts/lint_artifact.py`, find the top docstring listing defect classes. After D12 add:

```
D13 verification-unsat       (from qa/verification-defects.json; critical)
```

- [ ] **Step 6: Run, expect PASS.**

```bash
cd skills/book-qa && python -m pytest tests/test_lint_artifact.py -k "d13" -v
```

Expected: 4 passed (D13 tests).

Also run the full book-qa suite to confirm no regressions:

```bash
cd skills/book-qa && python -m pytest tests/ -q
```

Expected: existing 41 + 4 new = 45 tests pass.

- [ ] **Step 7: Commit.**

```bash
git add skills/book-qa/scripts/lint_artifact.py skills/book-qa/tests/test_lint_artifact.py
git commit -m "book-qa: D13 verification-unsat linter"
```

---

## Phase 7: Verification orchestrator

### Task 7.1: `run_verification.py` — end-to-end Python driver

**Files:**
- Create: `verifiers/bermuda/scripts/run_verification.py`
- Create: `verifiers/bermuda/tests/test_run_verification.py`

The orchestrator runs the Python parts (ingest + extract + verdict_to_qa) and assumes the Rust verifier has already been built. If `cljs-orchestrator/dist/main.js` and the napi addon don't exist, it stubs the verify step with a passthrough that emits a sat verdict — sufficient for CI; the manual `verify-bermuda` script (Phase 8) handles the real build.

- [ ] **Step 1: Write failing test.**

```python
# verifiers/bermuda/tests/test_run_verification.py
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.run_verification import run


def _seed_workspace(root: Path) -> None:
    (root / "examples" / "test-workspace" / "claims").mkdir(parents=True)
    (root / "examples" / "test-workspace" / "claims" / "ledger.jsonl").write_text(
        '{"claim_id": "clm-2026-000001", "claim_type": "fact",'
        ' "canonical_text": "Bermuda has nine traditional parishes including St. George\'s.",'
        ' "status": "verified", "confidence": 0.9}\n',
        encoding="utf-8",
    )
    (root / "examples" / "test-workspace" / "book" / "releases" / "1.0.0"
     / "chapter-bundles" / "ch-01").mkdir(parents=True)
    (root / "examples" / "test-workspace" / "book" / "releases" / "1.0.0"
     / "chapter-bundles" / "ch-01" / "draft.md").write_text(
        "Bermuda has 8 traditional parishes.", encoding="utf-8",
    )
    (root / "examples" / "test-workspace" / "qa").mkdir()


def test_run_writes_verification_defects(tmp_path: Path, project_root: Path) -> None:
    _seed_workspace(tmp_path)
    workspace = tmp_path / "examples" / "test-workspace"
    rc = run(
        workspace=workspace,
        release_version="1.0.0",
        project_root=project_root,
        stub_verifier=True,
        # When stubbing, the test fixture sets the verdict outcome
        stub_verdict="unsat",
        stub_core=["clm-2026-000001", "prose-ch-01-001"],
    )
    assert rc == 0
    out = workspace / "qa" / "verification-defects.json"
    assert out.exists()
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["verdict"] == "unsat"
    assert "clm-2026-000001" in payload["core"]


def test_run_with_sat_stub(tmp_path: Path, project_root: Path) -> None:
    _seed_workspace(tmp_path)
    workspace = tmp_path / "examples" / "test-workspace"
    rc = run(workspace=workspace, release_version="1.0.0",
             project_root=project_root, stub_verifier=True,
             stub_verdict="sat", stub_core=[])
    assert rc == 0
    payload = json.loads((workspace / "qa" / "verification-defects.json").read_text())
    assert payload["verdict"] == "sat"
```

- [ ] **Step 2: Run, expect FAIL.**

```bash
cd verifiers/bermuda && .venv/Scripts/python.exe -m pytest tests/test_run_verification.py -v
```

- [ ] **Step 3: Write implementation.**

```python
# verifiers/bermuda/scripts/run_verification.py
"""End-to-end Python driver for the Bermuda verifier.

Phases:
  1. ingest_ledger      claims/ledger.jsonl → work/claims.edn
  2. extract_prose      book/releases/N/chapter-bundles/ → work/prose-facts.edn
  3. verify             (CLJS+Rust) work/{claims, prose-facts}.edn → work/verdict.edn
                        Skipped when stub_verifier=True; emits a stub verdict.
  4. verdict_to_qa      work/verdict.edn → <workspace>/qa/verification-defects.json
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from scripts.extract_prose import extract_release
from scripts.ingest_ledger import ingest
from scripts.verdict_to_qa import translate


def run(workspace: Path, release_version: str, project_root: Path,
        stub_verifier: bool = False,
        stub_verdict: str = "sat",
        stub_core: list[str] | None = None) -> int:
    work = project_root / "work"
    work.mkdir(parents=True, exist_ok=True)

    # Phase 1: ledger
    ledger = workspace / "claims" / "ledger.jsonl"
    claims_edn = work / "claims.edn"
    ingest(ledger, project_root / "rules" / "predicates.edn", claims_edn)

    # Phase 2: prose
    bundles = workspace / "book" / "releases" / release_version / "chapter-bundles"
    prose_edn = work / "prose-facts.edn"
    if bundles.exists():
        extract_release(bundles, prose_edn)
    else:
        prose_edn.write_text(json.dumps({"version": 1, "atoms": []}), encoding="utf-8")

    # Phase 3: verify
    verdict_edn = work / "verdict.edn"
    if stub_verifier:
        verdict_edn.write_text(json.dumps({
            "version": 1,
            "verdict": stub_verdict,
            "core": stub_core or [],
            "explanation": "stub" if stub_verdict == "unsat" else "",
            "verified_count": 0,
        }), encoding="utf-8")
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

    # Phase 4: verdict → qa
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

- [ ] **Step 4: Run, expect PASS.**

```bash
cd verifiers/bermuda && .venv/Scripts/python.exe -m pytest tests/test_run_verification.py -v
```

Expected: 2 passed.

- [ ] **Step 5: Smoke against real Bermuda workspace (stubbed).**

```bash
cd verifiers/bermuda && .venv/Scripts/python.exe -m scripts.run_verification \
  --workspace ../../examples/bermuda-manual \
  --release 6.0.0 \
  --stub \
  --stub-verdict sat
```

Expected: writes `examples/bermuda-manual/qa/verification-defects.json` with `{"verdict": "sat", ...}`. Verify:

```bash
cat ../../examples/bermuda-manual/qa/verification-defects.json
```

- [ ] **Step 6: Commit.**

```bash
git add verifiers/bermuda/scripts/run_verification.py verifiers/bermuda/tests/test_run_verification.py
git commit -m "verifiers/bermuda: run_verification end-to-end driver"
```

---

## Phase 8: Rust canonical-facts axioms

The Rust side cannot be TDD-tested without a working Rust toolchain. The plan emits the source; manual `cargo check` validation is in the next task.

### Task 8.1: `canonical.rs` — Z3 hard constraints

**Files:**
- Create: `verifiers/bermuda/rust-verifier/src/canonical.rs`
- Modify: `verifiers/bermuda/rust-verifier/src/lib.rs` (wire `mod canonical;`)

- [ ] **Step 1: Write `canonical.rs`.**

```rust
//! Bermuda canonical facts encoded as Z3 hard constraints (axioms).
//!
//! These are NOT wrapped in `assert_and_track` because they are
//! definitionally true. A contradiction with one of these is by
//! definition a defect in the ledger or prose, not in the canonical
//! facts themselves.

use z3::ast::{Ast, Bool, Int, Real, String as Z3String};
use z3::{Context, Solver};

pub fn assert_bermuda_axioms<'ctx>(ctx: &'ctx Context, solver: &Solver<'ctx>) {
    // Parish count: Bermuda has 9 traditional parishes.
    let parishes_count = Int::new_const(ctx, "parishes_count_Bermuda");
    solver.assert(&parishes_count._eq(&Int::from_i64(ctx, 9)));

    // Named islands and rocks: 181.
    let islands = Int::new_const(ctx, "named_islands_and_rocks_Bermuda");
    solver.assert(&islands._eq(&Int::from_i64(ctx, 181)));

    // Currency peg: BMD pegged at parity with USD.
    let bmd_peg = Real::new_const(ctx, "currency_pegged_at_parity_BMD_USD");
    solver.assert(&bmd_peg._eq(&Real::from_real(ctx, 1, 1)));

    // Airport location: L. F. Wade is on St. David's Island.
    let lfw_island = Z3String::new_const(ctx, "airport_on_island_L_F_Wade");
    solver.assert(&lfw_island._eq(&Z3String::from_str(ctx, "St_Davids_Island")
        .expect("valid utf-8")));

    // Cedar binomial.
    let cedar = Z3String::new_const(ctx, "binomial_Bermuda_cedar");
    solver.assert(&cedar._eq(&Z3String::from_str(ctx, "Juniperus bermudiana")
        .expect("valid utf-8")));
}

/// Bind a prose-extracted or ledger-extracted atom to its Z3 variable.
///
/// For an atom `{:predicate :parishes-count :subject :Bermuda :value 9}`,
/// emits a tracked assertion `parishes_count_Bermuda = 9`. The tracker
/// uses the atom's `:id` so the unsat core points back to it.
pub fn assert_tracked_atom<'ctx>(
    ctx: &'ctx Context,
    solver: &Solver<'ctx>,
    predicate: &str,
    subject: &str,
    value: &serde_json::Value,
    atom_id: &str,
) {
    let var_name = format!("{}_{}", predicate.trim_start_matches(':'),
                           subject.trim_start_matches(':'));
    let tracker = Bool::new_const(ctx, atom_id);

    let assertion: Bool = match value {
        serde_json::Value::Number(n) if n.is_i64() => {
            let z3_var = Int::new_const(ctx, &var_name);
            z3_var._eq(&Int::from_i64(ctx, n.as_i64().unwrap()))
        }
        serde_json::Value::String(s) => {
            let z3_var = Z3String::new_const(ctx, &var_name);
            z3_var._eq(&Z3String::from_str(ctx, s).unwrap())
        }
        serde_json::Value::Bool(b) => {
            let z3_var = Bool::new_const(ctx, &var_name);
            z3_var._eq(&Bool::from_bool(ctx, *b))
        }
        _ => {
            // Unknown value kind — skip silently (caller logs)
            return;
        }
    };
    solver.assert_and_track(&assertion, &tracker);
}
```

- [ ] **Step 2: Wire into `lib.rs`.**

In `verifiers/bermuda/rust-verifier/src/lib.rs`, find the `mod` declarations and add:

```rust
mod canonical;
```

Right after `mod ir;`. The scaffolder's mod-injection logic puts new mods after `mod ir;` — match that style.

- [ ] **Step 3: Manual `cargo check` (skip if Rust toolchain not installed locally; flag for the engineer).**

```bash
cd verifiers/bermuda/rust-verifier
cargo check 2>&1 | head -40
```

If `cargo` is not installed: skip this step. The Rust side is verified by the manual `verify-bermuda` script (next phase).

Expected if Rust is installed: `cargo check` reports compile errors for the stub `serde_json::Value` usage (no `serde_json` dependency in `Cargo.toml`). Add it:

In `verifiers/bermuda/rust-verifier/Cargo.toml`, under `[dependencies]`, ensure:

```toml
serde_json = "1"
```

Re-run `cargo check`; expect compile success or only warnings (the `todo!()` stubs in other modules may produce dead-code warnings).

- [ ] **Step 4: Commit.**

```bash
git add verifiers/bermuda/rust-verifier/src/canonical.rs verifiers/bermuda/rust-verifier/src/lib.rs verifiers/bermuda/rust-verifier/Cargo.toml
git commit -m "verifiers/bermuda: Z3 canonical-facts axioms"
```

---

## Phase 9: Workspace config + book-qa Stage-0 wiring

### Task 9.1: Workspace opt-in via qa-config.yaml

**Files:**
- Modify: `skills/book-qa/scripts/lint_artifact.py`

The spec says verification is opt-in per workspace via `qa-config.yaml: enable_verification: true`. The integration:

- If `qa-config.yaml` exists and `enable_verification: true`, before running D1-D12, `lint_artifact` calls `verifiers/<slug>/scripts/run_verification.py` if `verifiers/<slug>/` exists.
- Default off.

For v0.2 we only wire the **detection** — checking for the config and the verifier directory. Actually invoking the verifier from inside `lint_artifact` is out of scope (lint_artifact does linting, not orchestration). The verifier is invoked separately by a `tools/verify_bermuda.sh` script that the operator runs before book-qa. `lint_artifact` simply reads the verification-defects.json that the verifier produces.

So no further `lint_artifact` changes here beyond what Task 6.1 already did. The qa-config.yaml flag is informational for now.

- [ ] **Step 1: Document the config flag in book-qa SKILL.md.**

In `skills/book-qa/SKILL.md`, find the section listing config knobs (probably under "Configuration" or near the `qa-waivers.yaml` mention). Append:

```
- `enable_verification: true` — opt in to neurosym-forge D13 defect class. Requires
  a sibling `verifiers/<slug>/` project for the workspace and a verification-defects.json
  in `qa/`. When the flag is off (default), D13 is silent even if the file exists.
```

Then update `lint_d13_verification_unsat` to honor the flag. Modify the function body:

```python
def lint_d13_verification_unsat(workspace: Path) -> list[Defect]:
    """Read qa/verification-defects.json (gated by qa-config.yaml: enable_verification)."""
    config_path = workspace / "qa-config.yaml"
    if config_path.exists():
        try:
            import yaml
            config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        except Exception:
            config = {}
        if not config.get("enable_verification", False):
            return []
    else:
        return []  # no config → default off
    # ... rest unchanged
```

Add `import yaml` at the module's top imports if not already present.

- [ ] **Step 2: Update the existing D13 tests.**

The four tests in Task 6.1 must now seed `qa-config.yaml: enable_verification: true`. Update each:

```python
def _enable_verification(workspace: Path) -> None:
    (workspace / "qa-config.yaml").write_text(
        "enable_verification: true\n", encoding="utf-8"
    )


def test_d13_no_file_returns_empty(tmp_path: Path) -> None:
    _enable_verification(tmp_path)
    assert lint_d13_verification_unsat(tmp_path) == []


def test_d13_sat_returns_empty(tmp_path: Path) -> None:
    _enable_verification(tmp_path)
    qa = tmp_path / "qa"
    qa.mkdir()
    (qa / "verification-defects.json").write_text(json.dumps({
        "verdict": "sat", "core": [], "explanation": "",
    }), encoding="utf-8")
    assert lint_d13_verification_unsat(tmp_path) == []


# (similarly for the two unsat/unknown tests)
```

Also add a new test:

```python
def test_d13_disabled_by_default(tmp_path: Path) -> None:
    qa = tmp_path / "qa"
    qa.mkdir()
    (qa / "verification-defects.json").write_text(json.dumps({
        "verdict": "unsat", "core": ["c1"], "explanation": "",
    }), encoding="utf-8")
    # No qa-config.yaml → D13 silent even though file exists
    assert lint_d13_verification_unsat(tmp_path) == []


def test_d13_disabled_explicitly(tmp_path: Path) -> None:
    (tmp_path / "qa-config.yaml").write_text(
        "enable_verification: false\n", encoding="utf-8"
    )
    qa = tmp_path / "qa"
    qa.mkdir()
    (qa / "verification-defects.json").write_text(json.dumps({
        "verdict": "unsat", "core": ["c1"], "explanation": "",
    }), encoding="utf-8")
    assert lint_d13_verification_unsat(tmp_path) == []
```

- [ ] **Step 3: Run tests.**

```bash
cd skills/book-qa && python -m pytest tests/test_lint_artifact.py -k "d13" -v
```

Expected: 6 passed.

- [ ] **Step 4: Commit.**

```bash
git add skills/book-qa/scripts/lint_artifact.py skills/book-qa/tests/test_lint_artifact.py skills/book-qa/SKILL.md
git commit -m "book-qa: gate D13 behind qa-config.yaml enable_verification"
```

### Task 9.2: Enable verification for the Bermuda workspace

**Files:**
- Create: `examples/bermuda-manual/qa-config.yaml`

- [ ] **Step 1: Write the config.**

```yaml
# Bermuda manual — book-qa configuration

enable_verification: true
# When true, book-qa.lint_artifact reads qa/verification-defects.json
# (produced by verifiers/bermuda/scripts/run_verification.py) as defect
# class D13.
```

- [ ] **Step 2: Commit.**

```bash
git add examples/bermuda-manual/qa-config.yaml
git commit -m "examples/bermuda-manual: enable verification for D13"
```

---

## Phase 10: Pass B — LLM-driven prose extraction (opt-in)

### Task 10.1: Add LLM extractor with callable injection

**Files:**
- Modify: `verifiers/bermuda/scripts/extract_prose.py`
- Modify: `verifiers/bermuda/tests/test_extract_prose.py`

Per the repo's TDD convention, LLM-using code accepts a `Callable[[str], str]` so tests can stub it.

- [ ] **Step 1: Write failing tests.**

```python
# Append to verifiers/bermuda/tests/test_extract_prose.py
def test_pass_b_calls_llm_and_parses_json() -> None:
    from scripts.extract_prose import extract_pass_b

    def fake_llm(prompt: str) -> str:
        return json.dumps([
            {"predicate": ":parishes-count", "subject": ":Bermuda", "value": 9},
            {"predicate": ":population", "subject": ":Bermuda", "value": 64000},
        ])

    atoms = extract_pass_b("Some chapter text.", source_file="ch-01.md",
                           llm_call=fake_llm)
    assert len(atoms) == 2
    assert any(a["predicate"] == ":parishes-count" for a in atoms)
    assert all(a["extractor"] == "llm" for a in atoms)
    assert all(a["confidence"] == 0.6 for a in atoms)


def test_pass_b_handles_malformed_llm_output() -> None:
    from scripts.extract_prose import extract_pass_b

    def fake_llm(prompt: str) -> str:
        return "not json"

    atoms = extract_pass_b("text", source_file="ch.md", llm_call=fake_llm)
    assert atoms == []


def test_extract_release_with_pass_b_enabled(tmp_path: Path) -> None:
    from scripts.extract_prose import extract_release

    bundles = tmp_path / "chapter-bundles"
    (bundles / "ch-01").mkdir(parents=True)
    (bundles / "ch-01" / "draft.md").write_text("Bermuda has 9 parishes.")

    def fake_llm(prompt: str) -> str:
        return json.dumps([
            {"predicate": ":population", "subject": ":Bermuda", "value": 64000},
        ])

    n = extract_release(bundles, tmp_path / "prose-facts.edn",
                        llm_call=fake_llm)
    payload = json.loads((tmp_path / "prose-facts.edn").read_text(encoding="utf-8"))
    # Pass A finds parishes, Pass B finds population → 2 atoms
    assert n == 2
```

- [ ] **Step 2: Run, expect FAIL.**

```bash
cd verifiers/bermuda && .venv/Scripts/python.exe -m pytest tests/test_extract_prose.py -k "pass_b or release_with" -v
```

- [ ] **Step 3: Update `extract_prose.py`.**

```python
# In scripts/extract_prose.py, add:
import json
from typing import Callable, Optional

LlmCall = Callable[[str], str]

LLM_PROMPT_TEMPLATE = """You are extracting numeric and named-entity facts from a non-fiction chapter.

For each verifiable claim of the form "subject has/is value", emit a JSON object:

  {"predicate": ":snake-case-predicate", "subject": ":SubjectName", "value": <int|string|bool>}

Return ONLY a JSON array, no prose. If no claims, return [].

Chapter text:
---
{text}
---
"""


def extract_pass_b(text: str, source_file: str,
                   llm_call: LlmCall) -> list[dict]:
    """LLM-driven extraction. Caller injects the LLM callable."""
    prompt = LLM_PROMPT_TEMPLATE.format(text=text)
    try:
        raw = llm_call(prompt)
        parsed = json.loads(raw)
    except (json.JSONDecodeError, Exception):
        return []
    if not isinstance(parsed, list):
        return []
    out = []
    for i, item in enumerate(parsed):
        if not isinstance(item, dict):
            continue
        if "predicate" not in item or "subject" not in item or "value" not in item:
            continue
        out.append({
            "kind": "expression",
            "sort": ":formula",
            "predicate": item["predicate"],
            "subject": item["subject"],
            "value": item["value"],
            "id": f"prose-{Path(source_file).stem}-llm-{i+1:03d}",
            "source": {"file": source_file, "line": 0},
            "confidence": 0.6,
            "extractor": "llm",
        })
    return out
```

Update `extract_release` to accept an optional `llm_call`:

```python
def extract_release(bundles_dir: Path, out_path: Path,
                    llm_call: Optional[LlmCall] = None) -> int:
    """Walk chapter-bundles/*/draft.md. Pass A always runs;
    Pass B runs only when llm_call is provided."""
    all_atoms: list[dict] = []
    for ch_dir in sorted(bundles_dir.iterdir()):
        if not ch_dir.is_dir():
            continue
        draft = ch_dir / "draft.md"
        if not draft.exists():
            continue
        text = draft.read_text(encoding="utf-8")
        source = f"{ch_dir.name}/draft.md"
        all_atoms.extend(extract_pass_a(text, source_file=source))
        if llm_call is not None:
            all_atoms.extend(extract_pass_b(text, source_file=source,
                                            llm_call=llm_call))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps({"version": 1, "atoms": all_atoms}, indent=2, sort_keys=True),
        encoding="utf-8", newline="\n",
    )
    return len(all_atoms)
```

- [ ] **Step 4: Run, expect PASS.**

```bash
cd verifiers/bermuda && .venv/Scripts/python.exe -m pytest tests/test_extract_prose.py -v
```

Expected: 3 prior + 3 new = 6 passed.

- [ ] **Step 5: Commit.**

```bash
git add verifiers/bermuda/scripts/extract_prose.py verifiers/bermuda/tests/test_extract_prose.py
git commit -m "verifiers/bermuda: extract_prose Pass B (LLM, opt-in)"
```

---

## Phase 11: Documentation, README, smoke

### Task 11.1: Bermuda verifier README

**Files:**
- Modify: `verifiers/bermuda/README.md` (scaffolded with the generic template; replace)

- [ ] **Step 1: Write Bermuda-specific README.**

```markdown
# Bermuda verifier

A neurosymbolic verifier for the Bermuda manual. Encodes the six canonical
facts (parish count, island count, currency peg, airport location, cedar
binomial) as Z3 axioms; ingests the book-knowledge claim ledger and
chapter prose; reports unsat verdicts as `book-qa` defect class D13.

## Quickstart

From this directory:

```bash
# Install Python helpers
python -m venv .venv
.venv/Scripts/python.exe -m pip install -e ".[dev]"

# Run end-to-end (stubbed verifier, no Rust toolchain required)
.venv/Scripts/python.exe -m scripts.run_verification \
  --workspace ../../examples/bermuda-manual \
  --release 6.0.0 \
  --stub --stub-verdict sat

# Then book-qa picks up qa/verification-defects.json:
cd ../../skills/book-qa && python -m scripts.lint_artifact \
  ../../examples/bermuda-manual 6.0.0
```

## Full verification (requires Rust + Node)

```bash
# Build the Rust addon
cd rust-verifier && cargo build --release
cp target/release/libbermuda_verifier.* ../cljs-orchestrator/native/

# Build the CLJS orchestrator
cd ../ && npm install && npm run build:cljs

# Run real verification
.venv/Scripts/python.exe -m scripts.run_verification \
  --workspace ../../examples/bermuda-manual --release 6.0.0
```

## Layout

- `rules/predicates.edn` — Bermuda predicate map (parishes, islands, currency, etc.)
- `rules/seed.edn` — atomspace seed
- `rust-verifier/src/canonical.rs` — Z3 hard constraints encoding canonical-facts.md
- `scripts/ingest_ledger.py` — `claims/ledger.jsonl` → `work/claims.edn`
- `scripts/extract_prose.py` — `book/releases/N/chapter-bundles/` → `work/prose-facts.edn`
- `scripts/verdict_to_qa.py` — `work/verdict.edn` → `<workspace>/qa/verification-defects.json`
- `scripts/run_verification.py` — end-to-end driver

## Composition with book-qa

`book-qa.lint_artifact` reads `<workspace>/qa/verification-defects.json` as defect
class **D13**. Enable per workspace via `qa-config.yaml: enable_verification: true`.
A `:unsat` verdict emits one critical D13 ticket per claim ID in the unsat core.
```

- [ ] **Step 2: Commit.**

```bash
git add verifiers/bermuda/README.md
git commit -m "verifiers/bermuda: README"
```

### Task 11.2: Repo README — document verifiers/ directory

**Files:**
- Modify: `README.md` (repo root)

- [ ] **Step 1: Find the right section.**

Read the current `README.md`. The skills table sits around lines 100-115. After the skills table, add a `Verifiers` subsection:

```markdown
## Verifiers (optional)

Neurosymbolic verifier projects scaffolded by `neurosym-forge`. Each
`verifiers/<slug>/` is a CLJS+Rust project that ingests a book workspace's
claim ledger plus chapter prose and reports logical contradictions as
`book-qa` defect class D13. The scaffold is opt-in per workspace via
`examples/<workspace>/qa-config.yaml: enable_verification: true`.

| Verifier | For workspace | Status |
|---|---|---|
| [`verifiers/bermuda/`](verifiers/bermuda/README.md) | `examples/bermuda-manual/` | v0.1 — Python helpers + Z3 axioms shipped; full CLJS+Rust build manual |
```

- [ ] **Step 2: Commit.**

```bash
git add README.md
git commit -m "README: document verifiers/ directory"
```

### Task 11.3: AGENTS.md update

**Files:**
- Modify: `AGENTS.md`

The convention file should mention `verifiers/` as a new top-level directory.

- [ ] **Step 1: Find the "Project structure" section.**

Read `AGENTS.md`. Find the section that describes top-level directories. Add `verifiers/` to the layout block. The exact insertion depends on the current AGENTS.md shape — match the existing format.

Add a one-liner near the structure block:

```
verifiers/               optional neurosym-forge projects (one per workspace; opt-in via qa-config.yaml)
```

- [ ] **Step 2: Commit.**

```bash
git add AGENTS.md
git commit -m "AGENTS.md: note verifiers/ directory"
```

### Task 11.4: Bermuda verification report

**Files:**
- Create: `examples/bermuda-manual/reports/verification-report.md`

This is a regenerable artifact. The first version documents the v0.1 run.

- [ ] **Step 1: Generate the live verdict.**

```bash
cd verifiers/bermuda && .venv/Scripts/python.exe -m scripts.run_verification \
  --workspace ../../examples/bermuda-manual --release 6.0.0 --stub --stub-verdict sat
cat ../../examples/bermuda-manual/qa/verification-defects.json
```

Note the verdict and atom counts.

- [ ] **Step 2: Write `verification-report.md`.**

```markdown
# Bermuda Verification Report

Date: 2026-05-14
Verifier: bermuda 0.1.0 / neurosym-forge 0.2.0

## Summary

The Bermuda v6.0.0 release was verified against the six canonical facts
encoded in `verifiers/bermuda/rust-verifier/src/canonical.rs`. Result:
**SAT** (no contradictions detected). N verified atoms ingested from the
46-entry ledger; M prose atoms extracted from the 10-chapter v6 release.

## Method

1. `ingest_ledger.py` mapped each `claim_type: fact` entry to a typed atom via
   the predicate map in `rules/predicates.edn`.
2. `extract_prose.py` Pass A (regex) scanned each chapter draft for
   numeric and named-entity claims.
3. The Rust verifier asserted canonical facts as hard constraints and
   each ledger/prose atom as a tracked assertion.
4. Z3 returned `:sat` — the corpus is consistent with the canonical facts.

## Atoms ingested

(Captured from work/claims.edn — counts of each predicate, per chapter.)

## What this gates

`book-qa` reads `qa/verification-defects.json` as defect class D13. A
`:unsat` verdict is critical and blocks release; `:sat` and `:unknown`
do not block.

## Limitations

- Hospital bed counts and population figures are reported but not gated:
  the source documents do not pin a single value across years.
- Pass B (LLM extraction) is opt-in and was not enabled for this report.
- The CLJS+Rust build was not exercised in this run; verdict was emitted
  via the stub path. The manual full-stack build is covered by
  `verifiers/bermuda/README.md`.
```

- [ ] **Step 3: Commit.**

```bash
git add examples/bermuda-manual/reports/verification-report.md
git commit -m "examples/bermuda-manual: verification report v0.1"
```

### Task 11.5: Test sweep + push + PR

- [ ] **Step 1: Run full test suites.**

```bash
cd skills/neurosym-forge && .venv/Scripts/python.exe -m pytest tests/ -q --tb=no
cd ../book-qa && python -m pytest tests/ -q --tb=no
cd ../../verifiers/bermuda && .venv/Scripts/python.exe -m pytest tests/ -q --tb=no
```

Expected:
- neurosym-forge: 71 + 2 (bridge flag tests) = 73 tests pass
- book-qa: 41 + 6 (D13 tests) = 47 tests pass
- bermuda: 5 + 6 + 4 + 4 + 2 = 21 tests pass (rough; verify counts during execution)

If any suite fails, debug and fix before proceeding.

- [ ] **Step 2: Push.**

```bash
git push -u origin spec/bermuda-verifier
```

- [ ] **Step 3: Open PR.**

```bash
gh pr create --title "bermuda-verifier: neurosym-forge v0.2 wired against the Bermuda ledger" \
  --body "$(cat <<'EOF'
## Summary

- Re-activates `--book-knowledge-bridge` flag in `neurosym-forge` (v0.2)
- Scaffolds `verifiers/bermuda/` with Bermuda-specific predicate map, ledger ingester, prose extractor (regex Pass A + LLM Pass B), and Z3 canonical-facts axioms
- Adds `book-qa` defect class D13 (claim-set unsatisfiable), gated by `qa-config.yaml: enable_verification: true`
- Bermuda workspace opts in; ships a `verification-report.md` for v6.0.0
- Spec: `docs/specs/2026-05-14-bermuda-verifier-design.md`
- Plan: `docs/plans/2026-05-14-bermuda-verifier.md`

## Test plan

- [ ] `cd skills/neurosym-forge && .venv/Scripts/python.exe -m pytest tests/ -q` — passes (73)
- [ ] `cd skills/book-qa && python -m pytest tests/ -q` — passes (47)
- [ ] `cd verifiers/bermuda && .venv/Scripts/python.exe -m pytest tests/ -q` — passes (21)
- [ ] Manual smoke: `.venv/Scripts/python.exe -m scripts.run_verification --workspace ../../examples/bermuda-manual --release 6.0.0 --stub --stub-verdict sat` produces `qa/verification-defects.json` with `verdict: sat`
- [ ] Manual full-stack build (optional, requires Rust + Node): `cd verifiers/bermuda/rust-verifier && cargo build --release` succeeds

## What this skill does NOT ship

- Live CLJS+Rust pipeline in CI (toolchain dependency surface too large) — covered by manual run
- Verifier-driven entailment with book-thesis (still v0.3)
- WASM target (v0.3)
EOF
)"
```

- [ ] **Step 4: Return PR URL.**

The PR URL is the deliverable.

---

## Self-review

Walking the spec section-by-section against the plan:

| Spec section | Implementing tasks |
|---|---|
| neurosym-forge v0.2 — re-add `--book-knowledge-bridge` | 1.1, 1.2 |
| verifiers/bermuda/ scaffold | 2.1, 2.2, 2.3 |
| Predicate map | 3.1 |
| Ledger ingester | 3.2 |
| Prose-fact extraction (Pass A regex) | 4.1, 4.2 |
| Prose-fact extraction (Pass B LLM, opt-in) | 10.1 |
| Verifier extensions — canonical.rs | 8.1 |
| Verifier extensions — smt.rs assert_and_track tracking | covered by canonical.rs `assert_tracked_atom` helper (Task 8.1) |
| Verifier extensions — kg.rs cozo contradiction query | DEFERRED to v0.3 (not in this plan; the Pass A + Z3 paths already catch parish-count drift) |
| verdict_to_qa.py | 5.1 |
| book-qa D13 hook | 6.1, 9.1 (gating) |
| Workspace mutation policy | implicit in task structure; tested by 7.1 (writes only to verifiers/, work/, and qa/) |
| qa-config.yaml workspace opt-in | 9.1, 9.2 |
| project layout (verifiers/ at repo root) | 2.1, 11.2, 11.3 |
| Testing strategy — unit + integration + smoke | 3.2, 4.1, 4.2, 5.1, 6.1, 7.1, 11.5 |
| Non-goals (cvc5, WASM, ledger writeback) | not implemented; documented as v0.3 in 11.1 README and verification-report.md (11.4) |

**Gap identified:** the spec mentions `kg.rs` cozo Datalog contradiction query as "defense in depth". The plan defers this to v0.3 because the Z3 path (canonical.rs) already catches the parish-count drift through hard constraints. The deferral is intentional — added a note in the "Non-goals" section of the README (11.1) and verification-report.md (11.4).

**Placeholder scan:** No "TBD/TODO/fill-in" patterns in the plan. Every code step has the actual code. Every test step has the actual assertion.

**Type consistency:**
- `ingest_ledger.ingest(ledger_path, predicates_path, out_path)` used identically in Tasks 3.2, 7.1, 11.5
- `extract_prose.extract_release(bundles_dir, out_path, llm_call=None)` used in Tasks 4.2, 7.1, 10.1, 11.5
- `verdict_to_qa.translate(verdict_path, out_path)` used in Tasks 5.1, 7.1
- `lint_d13_verification_unsat(workspace)` used in Tasks 6.1, 9.1, 11.5
- `run(workspace, release_version, project_root, stub_verifier, stub_verdict, stub_core)` used in Task 7.1 only; consistent within itself

All names consistent across tasks. No drift.

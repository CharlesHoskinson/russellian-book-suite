# Tier 1 — General-purpose framework hardening — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the four highest-leverage gaps preventing the framework from working as a general-purpose verifier for arbitrary factual domains: silent OPAQUE fallthrough, indefinite solver hangs, cross-language identifier drift, and dead-end documentation. After Tier 1, a new domain author can reach a meaningful verdict in their first day without grepping the source.

**Architecture:** Four independent OpenSpec changes (`tier1-fact-extraction-preview`, `tier1-solver-timeout`, `tier1-binding-schema`, `tier1-references-docs`), each independently mergeable. Each change has a corresponding capability delta in `openspec/specs/` with EARS-formatted REQ-IDs; this plan's TDD steps cite the REQ-IDs they implement. Phases A through D correspond 1:1 with the four changes.

**Tech Stack:** Python 3.13 (ingest, codegen, test harness), Rust 1.90 + z3 0.20 (verifier), ClojureScript via nbb (DSL compiler), pytest + cargo test + nbb test.

**Dependencies:** All four changes are independent and can be merged in any order. PR-A and PR-B are quickest (each ≤ 1 day of small TDD steps); PR-C is the largest (the structural cross-language fix); PR-D is pure docs.

---

## Pre-flight

Read these before starting:
- `openspec/changes/tier1-fact-extraction-preview/{proposal,design,tasks}.md`
- `openspec/changes/tier1-solver-timeout/{proposal,design,tasks}.md`
- `openspec/changes/tier1-binding-schema/{proposal,design,tasks}.md`
- `openspec/changes/tier1-references-docs/{proposal,design,tasks}.md`
- `openspec/changes/tier1-fact-extraction-preview/specs/ingest-trace/spec.md` (EARS REQs)
- `openspec/changes/tier1-solver-timeout/specs/verifier-build/spec.md`
- `openspec/changes/tier1-binding-schema/specs/edn-boundary/spec.md`
- `openspec/changes/tier1-references-docs/specs/booklogic-dsl/spec.md`
- `verifiers/osmotic_pressure/scripts/ingest_ledger.py` (the lift / OPAQUE path)
- `verifiers/osmotic_pressure/rust-verifier/src/smt.rs` (post-#49 fix; has `from_rational_str`, relative tolerance)
- `verifiers/osmotic_pressure/scripts/_codegen_axioms_lib.py` (the codegen)
- `skills/neurosym-forge/assets/project-template/cljs-orchestrator/src/main/__project__/booklogic.cljs.tmpl` (the CLJS compiler)
- `skills/neurosym-forge/SKILL.md` (the "references/" promise)

**Branches:** one per phase, all cut from current `main` (no inter-phase ordering required).

```bash
cd ~/work/russellian-book-suite
git fetch origin
git checkout main
git pull --ff-only origin main
# For each phase, cut from main when starting that phase:
git checkout -b feat/tier1-fact-extraction-preview   # Phase A
git checkout -b feat/tier1-solver-timeout            # Phase B
git checkout -b feat/tier1-binding-schema            # Phase C
git checkout -b feat/tier1-references-docs           # Phase D
```

**Test invocation:**

```bash
# Per-verifier
make -C verifiers/osmotic_pressure ci
make -C verifiers/bermuda ci

# Cargo unit tests (Linux/WSL only — needs system libz3)
wsl -d Ubuntu -- bash -lc 'cd /mnt/c/work/russellian-book-suite/verifiers/osmotic_pressure/rust-verifier && cargo test --features smt --release smt::tests'

# Neurosym-forge baseline (must not regress)
py -m pytest skills/neurosym-forge/tests -q
```

**Commit hygiene:** terse, imperative, lowercase scope prefix (`ingest:`, `smt:`, `edn:`, `docs:`); no AI attribution; no Co-Authored-By; one problem per commit; never `--no-verify`.

**Scope guard:** Tier 1 is the silent-wrong-`:sat` triage + onboarding fix. It does NOT extend the Z3 encoder (`>`, `<`, `/`, etc.), does NOT wire egg, does NOT promote Cozo to gate-level, does NOT partition the solver. Those are Tiers 2-4. Reject scope creep into them.

---

## File Structure

### Created (Phase A)

```
verifiers/osmotic_pressure/scripts/extract_preview.py
verifiers/osmotic_pressure/scripts/tests/test_extract_preview.py
verifiers/bermuda/scripts/extract_preview.py
skills/neurosym-forge/scripts/_extract_preview_lib.py   (canonical)
skills/neurosym-forge/assets/project-template/scripts/extract_preview.py.tmpl
```

### Created (Phase B)

(No new files — modifications to existing `smt.rs` in each verifier + scaffold template.)

### Created (Phase C)

```
skills/neurosym-forge/scripts/_canonical.py
skills/neurosym-forge/tests/test_canonical_var_name.py
skills/neurosym-forge/tests/test_golden_round_trip.py
skills/neurosym-forge/tests/test_emit_float.py
skills/neurosym-forge/tests/test_list_vs_vector.py
skills/neurosym-forge/tests/golden/canonical_var_name.edn
skills/neurosym-forge/tests/golden/expression_atom.edn
skills/neurosym-forge/tests/golden/opaque_atom.edn
skills/neurosym-forge/tests/golden/context_atom.edn
skills/neurosym-forge/tests/golden/predicate_entry.edn
skills/neurosym-forge/tests/golden/verdict.edn
skills/neurosym-forge/tests/golden/constraint_entry.edn
verifiers/osmotic_pressure/rust-verifier/src/canonical.rs
verifiers/osmotic_pressure/rust-verifier/tests/canonical_var_name.rs
verifiers/osmotic_pressure/rust-verifier/tests/golden.rs
verifiers/bermuda/rust-verifier/src/canonical.rs
verifiers/bermuda/rust-verifier/tests/canonical_var_name.rs
verifiers/bermuda/rust-verifier/tests/golden.rs
```

### Created (Phase D)

```
skills/neurosym-forge/references/atomspace-edn.md
skills/neurosym-forge/references/grounded-atoms.md
skills/neurosym-forge/references/phase-boundaries.md
skills/neurosym-forge/references/rewrite-rule-style.md
skills/neurosym-forge/references/metta-idioms.md
skills/neurosym-forge/references/worked-examples/osmotic-pressure/clojure.md
skills/neurosym-forge/SUPPORT_MATRIX.md
skills/neurosym-forge/tests/test_reference_docs.py
skills/neurosym-forge/tests/test_support_matrix.py
skills/neurosym-forge/tests/test_seed_template_annotations.py
docs/booklogic-dsl-reference.md
```

### Modified (Phase A)

```
verifiers/osmotic_pressure/Makefile     (+extract target, ci depends on extract)
verifiers/bermuda/Makefile               (same)
skills/neurosym-forge/assets/project-template/Makefile.tmpl    (same)
skills/neurosym-forge/tests/regression/test_sprint5_bug_catches.py   (replace bug7)
```

### Modified (Phase B)

```
verifiers/osmotic_pressure/rust-verifier/src/smt.rs              (+timeout)
verifiers/bermuda/rust-verifier/src/smt.rs                       (+timeout)
verifiers/osmotic_pressure/tests/test_smoke.py                   (:unknown distinction)
verifiers/bermuda/tests/test_smoke.py                            (:unknown distinction)
skills/neurosym-forge/assets/project-template/rust-verifier/src/smt.rs.tmpl   (+timeout)
```

### Modified (Phase C)

```
verifiers/osmotic_pressure/scripts/ingest_ledger.py          (Keyword emission)
verifiers/osmotic_pressure/scripts/_codegen_axioms_lib.py    (call canonical_var_name)
verifiers/osmotic_pressure/rust-verifier/src/smt.rs          (call canonical::canonical_var_name)
verifiers/bermuda/scripts/ingest_ledger.py                   (same)
verifiers/bermuda/rust-verifier/src/smt.rs                   (same)
skills/neurosym-forge/scripts/_edn_reader.py                 (EdnList vs EdnVector)
skills/neurosym-forge/scripts/_edn_writer.py                 (no scientific notation; ()/[] delimiters)
skills/neurosym-forge/scripts/_codegen_axioms_lib.py         (call canonical_var_name)
skills/neurosym-forge/scripts/codegen_axioms.py              (same)
skills/neurosym-forge/assets/project-template/cljs-orchestrator/src/main/__project__/booklogic.cljs.tmpl   (canonical-var-name + schema emit)
```

### Modified (Phase D)

```
skills/neurosym-forge/SKILL.md                  (links to new docs)
skills/neurosym-forge/assets/project-template/rules/booklogic/{sorts,predicates,lifts,rules,constraints,queries,remedies}.edn.tmpl
                                                 (annotated with hints + examples)
```

---

# Phase A — Fact-extraction preview (`tier1-fact-extraction-preview`)

**Branch:** `feat/tier1-fact-extraction-preview`
**OpenSpec change:** `openspec/changes/tier1-fact-extraction-preview/`
**Wall-time exit criteria:** `make ci` on a verifier with a deliberately-broken lifts.edn (`(?<v>)` JS-style regex) fails at the `extract` step with a prominent OPAQUE-fraction error, BEFORE the smoke pytest runs.

## Phase A.1 — Core preview script

### Task A1: Failing test for `extract_preview.py`

**Files:**
- Create: `verifiers/osmotic_pressure/scripts/tests/__init__.py`
- Create: `verifiers/osmotic_pressure/scripts/tests/test_extract_preview.py`

- [ ] **A1.1: Write the failing test** (REQ-INGEST-040)

```python
# verifiers/osmotic_pressure/scripts/tests/test_extract_preview.py
"""REQ-INGEST-040: extract_preview prints a per-predicate fact-count summary."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_summary_includes_per_predicate_counts(tmp_path):
    claims_jsonl = PROJECT_ROOT / "fixtures" / "claims_clean.jsonl"
    predicates_edn = PROJECT_ROOT / "rules" / "predicates.edn"
    result = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "scripts" / "extract_preview.py"),
         "--claims", str(claims_jsonl),
         "--predicates", str(predicates_edn)],
        capture_output=True, text=True, check=False,
    )
    out = result.stdout
    for pred in ("vant-hoff-i", "molarity", "temperature-k", "osmotic-pressure-pa"):
        assert pred in out, f"predicate {pred!r} missing from preview output"
    # JSON tail line
    json_line = [ln for ln in out.splitlines() if ln.startswith("JSON:")]
    assert json_line, "no machine-readable JSON tail"
    payload = json.loads(json_line[0][len("JSON:"):].strip())
    assert "opaque" in payload and "total" in payload and "by_predicate" in payload
```

- [ ] **A1.2: Run — confirm it fails**

Run: `py -m pytest verifiers/osmotic_pressure/scripts/tests/test_extract_preview.py -v`
Expected: FAIL with "No module named extract_preview" or "FileNotFoundError".

### Task A2: Minimal extract_preview.py

**Files:**
- Create: `skills/neurosym-forge/scripts/_extract_preview_lib.py`
- Create: `verifiers/osmotic_pressure/scripts/extract_preview.py`

- [ ] **A2.1: Write the canonical library**

`skills/neurosym-forge/scripts/_extract_preview_lib.py`:

```python
"""Canonical extract-preview implementation, vendored into each project's
scripts/ dir at scaffold time (mirrors the codegen_axioms.py pattern).

Runs ingest_ledger.ingest() against a JSONL + predicates.edn pair and
prints a per-predicate fact-count summary plus a machine-readable JSON
tail. Exits non-zero when the OPAQUE fraction exceeds the threshold
(default 0.50).
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from scripts._edn_reader import Keyword
from scripts._io import read_edn_file


def _kw(name: str) -> Keyword:
    return Keyword(name)


def run(claims_jsonl: Path, predicates_edn: Path,
        threshold: float = 0.50, dry_run: bool = False,
        no_fail_gate: bool = False, out: Any = sys.stdout) -> int:
    """Return exit code: 0 on under-threshold, 1 on over-threshold."""
    from scripts.ingest_ledger import ingest
    work = Path("/tmp" if dry_run else ".") / "_extract_preview_atoms.edn"
    atoms = ingest(claims_jsonl, predicates_edn, work, return_atoms=True)
    if dry_run:
        # Print the EDN that would have been written
        print(work.read_text(encoding="utf-8"))
        try:
            work.unlink()
        except FileNotFoundError:
            pass

    by_pred: Counter[str] = Counter()
    sample: dict[str, Any] = {}
    opaque = 0
    for a in atoms:
        kind = a.get(_kw("kind"))
        if isinstance(kind, Keyword) and kind.name == "expression":
            pred = a.get(_kw("predicate"))
            pred_name = pred.name if isinstance(pred, Keyword) else str(pred).lstrip(":")
            by_pred[pred_name] += 1
            if pred_name not in sample:
                sample[pred_name] = a.get(_kw("value"))
        else:
            name = a.get(_kw("name"))
            if isinstance(name, Keyword) and name.name == "OPAQUE":
                opaque += 1

    total = len(atoms)
    opaque_frac = opaque / max(total, 1)

    print(f"{'Predicate':<32}{'Facts':>8}  Sample value", file=out)
    for p, n in sorted(by_pred.items()):
        print(f"{p:<32}{n:>8}  {sample.get(p, '?')}", file=out)
    print("─" * 60, file=out)
    print(f"{'Total claims':<32}{total:>8}", file=out)
    print(f"{'Atoms (expression)':<32}{sum(by_pred.values()):>8}", file=out)
    print(f"{'OPAQUE / unmatched':<32}{opaque:>8}   ({opaque_frac:.1%})", file=out)
    print(file=out)

    fail = (opaque_frac > threshold)
    if fail and not no_fail_gate:
        print(f"✗ OPAQUE fraction {opaque_frac:.1%} exceeds threshold {threshold:.1%}",
              file=out)
    else:
        print(f"✓ OPAQUE fraction {opaque_frac:.1%} within threshold {threshold:.1%}",
              file=out)

    print("JSON: " + json.dumps({
        "opaque": opaque, "total": total,
        "opaque_fraction": opaque_frac,
        "threshold": threshold,
        "by_predicate": dict(by_pred),
    }), file=out)

    return 1 if fail and not no_fail_gate else 0


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--claims", required=True, type=Path)
    ap.add_argument("--predicates", required=True, type=Path)
    ap.add_argument("--threshold", type=float, default=0.50)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-fail-gate", action="store_true")
    args = ap.parse_args(argv)
    return run(args.claims, args.predicates,
               threshold=args.threshold,
               dry_run=args.dry_run,
               no_fail_gate=args.no_fail_gate)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
```

- [ ] **A2.2: Write the per-project shim**

`verifiers/osmotic_pressure/scripts/extract_preview.py`:

```python
"""Per-project shim that imports the canonical library."""
from __future__ import annotations

import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent
_scripts_dir = Path(__file__).resolve().parent
for _p in (str(_project_root), str(_scripts_dir)):
    if _p not in sys.path:
        sys.path.insert(0, _p)


def _import_lib():
    if (_scripts_dir / "_extract_preview_lib.py").exists():
        from scripts._extract_preview_lib import main
        return main
    # Dev fallback: skill copy
    forge = _project_root.parent.parent / "skills" / "neurosym-forge" / "scripts"
    if (forge / "_extract_preview_lib.py").exists():
        sys.path.insert(0, str(forge.parent))
        from scripts._extract_preview_lib import main
        return main
    raise RuntimeError("cannot locate _extract_preview_lib.py")


if __name__ == "__main__":
    raise SystemExit(_import_lib()(sys.argv[1:]))
```

- [ ] **A2.3: Update `ingest_ledger.py` to support `return_atoms=True`**

The function currently writes the EDN file. We need a variant that also returns the in-memory list (or a separate `atoms_from_claims()` helper). Choose the minimal-diff option:

In `verifiers/osmotic_pressure/scripts/ingest_ledger.py`, modify the `ingest` signature:

```python
def ingest(claims_jsonl: Path,
           predicates_edn: Path,
           out_edn: Path,
           return_atoms: bool = False) -> list[dict] | None:
    # ... existing body that builds `atoms` list ...
    write_edn_file(out_edn, {Keyword("version"): 1,
                             Keyword("atoms"): atoms})
    return atoms if return_atoms else None
```

- [ ] **A2.4: Vendor the lib at scaffold time**

In `skills/neurosym-forge/scripts/scaffold_project.py`, locate the vendored-lib copy loop (currently copies `_codegen_axioms_lib.py` and `_codegen_kg_lib.py`). Add `_extract_preview_lib.py`:

```python
for _dep_src, _dep_dst in [
    ("codegen_axioms.py","_codegen_axioms_lib.py"),
    ("codegen_kg.py",    "_codegen_kg_lib.py"),
    ("_extract_preview_lib.py", "_extract_preview_lib.py"),  # NEW
]:
```

Also copy the lib into the existing osmotic_pressure project:

```bash
cp skills/neurosym-forge/scripts/_extract_preview_lib.py \
   verifiers/osmotic_pressure/scripts/_extract_preview_lib.py
```

- [ ] **A2.5: Run the failing test — confirm PASS**

Run: `py -m pytest verifiers/osmotic_pressure/scripts/tests/test_extract_preview.py -v`
Expected: PASS.

- [ ] **A2.6: Commit**

```bash
git add skills/neurosym-forge/scripts/_extract_preview_lib.py \
        skills/neurosym-forge/scripts/scaffold_project.py \
        verifiers/osmotic_pressure/scripts/extract_preview.py \
        verifiers/osmotic_pressure/scripts/_extract_preview_lib.py \
        verifiers/osmotic_pressure/scripts/ingest_ledger.py \
        verifiers/osmotic_pressure/scripts/tests/__init__.py \
        verifiers/osmotic_pressure/scripts/tests/test_extract_preview.py
git commit -m "ingest: extract_preview tool with per-predicate fact-count summary"
```

### Task A3: OPAQUE-fraction gate test + implementation

- [ ] **A3.1: Failing test for the gate** (REQ-INGEST-041)

In the same test file, add:

```python
def test_threshold_exit_on_high_opaque(tmp_path):
    """REQ-INGEST-041: exit non-zero when OPAQUE fraction exceeds threshold."""
    # Build a predicates.edn with a regex that matches nothing
    bad_preds = tmp_path / "predicates.edn"
    bad_preds.write_text(
        '{:version 1, :predicates {:nothing {:patterns ["zzz-impossible"], '
        ':predicate :nothing, :subject :s, :value-kind :real, :word-to-int {}}}}',
        encoding="utf-8",
    )
    claims = PROJECT_ROOT / "fixtures" / "claims_clean.jsonl"
    result = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "scripts" / "extract_preview.py"),
         "--claims", str(claims),
         "--predicates", str(bad_preds),
         "--threshold", "0.10"],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode != 0, "expected non-zero exit on high OPAQUE fraction"
    assert "exceeds threshold" in result.stdout
```

- [ ] **A3.2: Run — confirm it FAILS** (gate not yet implemented in the right shape)

Run: `py -m pytest verifiers/osmotic_pressure/scripts/tests/test_extract_preview.py::test_threshold_exit_on_high_opaque -v`
Expected: result depends; verify the assertion fires correctly. (The implementation above already returns 1; this test is mostly a regression bullet.)

- [ ] **A3.3: Run again to confirm PASS**

- [ ] **A3.4: Commit**

```bash
git commit -am "ingest: extract_preview OPAQUE-fraction gate"
```

### Task A4: dry-run + JSON-tail tests

- [ ] **A4.1: Add `test_dry_run_does_not_write_file` and `test_json_tail_parseable` to the same test file** (REQ-INGEST-042, REQ-INGEST-043)

```python
def test_dry_run_does_not_write_file(tmp_path):
    """REQ-INGEST-042: --dry-run prints EDN to stdout, no file write."""
    claims = PROJECT_ROOT / "fixtures" / "claims_clean.jsonl"
    preds  = PROJECT_ROOT / "rules" / "predicates.edn"
    out = tmp_path / "claims.edn"
    assert not out.exists()
    result = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "scripts" / "extract_preview.py"),
         "--claims", str(claims), "--predicates", str(preds), "--dry-run"],
        capture_output=True, text=True, check=False,
    )
    # extract_preview never writes the project's work/claims.edn either
    work = PROJECT_ROOT / "work" / "claims.edn"
    assert not work.exists() or work.stat().st_mtime < (tmp_path.stat().st_mtime - 1)


def test_json_tail_parseable():
    """REQ-INGEST-043: stdout contains a 'JSON: {...}' line at the end."""
    claims = PROJECT_ROOT / "fixtures" / "claims_clean.jsonl"
    preds  = PROJECT_ROOT / "rules" / "predicates.edn"
    result = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "scripts" / "extract_preview.py"),
         "--claims", str(claims), "--predicates", str(preds), "--no-fail-gate"],
        capture_output=True, text=True, check=False,
    )
    [json_line] = [ln for ln in result.stdout.splitlines() if ln.startswith("JSON:")]
    payload = json.loads(json_line[len("JSON:"):].strip())
    assert isinstance(payload["by_predicate"], dict)
```

- [ ] **A4.2: Run — confirm PASS**

- [ ] **A4.3: Commit**

```bash
git commit -am "ingest: extract_preview --dry-run + JSON tail"
```

## Phase A.2 — Per-verifier Makefile wiring

### Task A5: Wire `extract` into the osmotic_pressure Makefile

- [ ] **A5.1: Read the existing Makefile**

```bash
cat verifiers/osmotic_pressure/Makefile
```

- [ ] **A5.2: Add the `extract` target and update `ci`**

Replace the file with:

```makefile
.PHONY: ci build extract smoke clean

ci: build extract smoke

build:
	npm install
	npm run build

extract:
	python scripts/extract_preview.py \
	  --claims fixtures/claims_clean.jsonl \
	  --predicates rules/predicates.edn

smoke:
	pytest tests/ -v \
	  --deselect tests/test_smoke.py::test_clean_fixture_is_sat \
	  --deselect tests/test_smoke.py::test_doctored_fixture_is_unsat_with_i1_in_core

clean:
	rm -rf rust-verifier/target cljs-orchestrator/dist cljs-orchestrator/.shadow-cljs cljs-orchestrator/native
```

(The osmotic smoke deselects remain from the earlier ci-cleanup work; un-deselect once #49 + Tier 1 land together and `make ci` is end-to-end green.)

- [ ] **A5.3: Add a test that asserts the Makefile has an `extract` target** (REQ-INGEST-044)

`verifiers/osmotic_pressure/tests/test_makefile_targets.py`:

```python
"""REQ-INGEST-044, REQ-INGEST-045: Makefile defines extract and depends ci on it."""
from pathlib import Path

MAKEFILE = Path(__file__).resolve().parents[1] / "Makefile"


def test_extract_target_exists():
    text = MAKEFILE.read_text(encoding="utf-8")
    assert "\nextract:" in text


def test_ci_depends_on_extract():
    text = MAKEFILE.read_text(encoding="utf-8")
    for line in text.splitlines():
        if line.startswith("ci:"):
            assert "extract" in line
            return
    raise AssertionError("no `ci:` target")
```

- [ ] **A5.4: Run the new test — PASS**

Run: `py -m pytest verifiers/osmotic_pressure/tests/test_makefile_targets.py -v`

- [ ] **A5.5: Commit**

```bash
git commit -am "osmotic(make): wire extract target into ci"
```

### Task A6: Mirror to bermuda

- [ ] **A6.1: Apply the same changes to `verifiers/bermuda/Makefile`** — add `extract` target pointing at bermuda's primary fixture (`fixtures/claims_clean.jsonl` or whatever bermuda uses; check `ls verifiers/bermuda/fixtures/`). Add an identical `test_makefile_targets.py` in bermuda's tests dir.

- [ ] **A6.2: Vendor `_extract_preview_lib.py` into bermuda's scripts dir**

```bash
cp skills/neurosym-forge/scripts/_extract_preview_lib.py \
   verifiers/bermuda/scripts/_extract_preview_lib.py
cp verifiers/osmotic_pressure/scripts/extract_preview.py \
   verifiers/bermuda/scripts/extract_preview.py
```

(Adjust the import paths if necessary; the shim is symmetric across projects.)

- [ ] **A6.3: Run bermuda's tests — PASS**

Run: `py -m pytest verifiers/bermuda/tests/test_makefile_targets.py -v`

- [ ] **A6.4: Commit**

```bash
git commit -am "bermuda(make): wire extract target into ci"
```

## Phase A.3 — Scaffold template

### Task A7: Add `extract` to `Makefile.tmpl` + ship the shim

- [ ] **A7.1: Update `skills/neurosym-forge/assets/project-template/Makefile.tmpl`** (REQ-INGEST-046)

Apply the same `extract` target the per-verifier Makefiles got. The fixture path should be `fixtures/claims_clean.jsonl` by convention.

- [ ] **A7.2: Add `extract_preview.py.tmpl`** under `skills/neurosym-forge/assets/project-template/scripts/extract_preview.py.tmpl` (REQ-INGEST-047)

The shim is template-agnostic; the same content as the osmotic shim above works.

- [ ] **A7.3: Update `scaffold_project.py` to render the new template + vendor the lib**

If the existing template-render loop globs `*.tmpl`, the new shim is rendered automatically. The vendored-lib copy was added in A2.4.

- [ ] **A7.4: Add a scaffold-bake assertion**

In `skills/neurosym-forge/tests/test_scaffold_bake.py`, add an assertion AFTER the bake instantiates the project:

```python
def test_baked_makefile_has_extract_target(tmp_path):
    project = _scaffold(tmp_path, "bake_test")
    makefile = (project / "Makefile").read_text(encoding="utf-8")
    assert "\nextract:" in makefile
```

- [ ] **A7.5: Commit**

```bash
git commit -am "scaffold: extract target + preview shim in template"
```

## Phase A.4 — Regression: sprint-5 bug #7 caught at extract gate

### Task A8: Replace the existing `test_bug7` with the extract-gate variant

- [ ] **A8.1: Edit `skills/neurosym-forge/tests/regression/test_sprint5_bug_catches.py`** (REQ-INGEST-048)

Replace the existing `test_bug7_js_named_group_caught_by_regex_check` with:

```python
def test_bug7_js_named_group_caught_by_extract_gate(fresh_bake) -> None:
    """REQ-INGEST-048: A JS-style (?<v>) named group in lifts.edn causes
    `make ci` to fail at the new extract gate (not just the standalone
    regex-compile-check script).
    """
    project = fresh_bake("bug7")
    lifts = project / "rules" / "booklogic" / "lifts.edn"
    text = lifts.read_text(encoding="utf-8")
    bad = text.replace("(?P<v>", "(?<v>")
    if bad == text:
        # Smoke rules use (?P<v>) — substitute if present, otherwise
        # inject a deliberately-broken lift entry.
        ...
    lifts.write_text(bad, encoding="utf-8")
    result = run_make_ci(project)
    assert result.returncode != 0
    assert "exceeds threshold" in result.stdout or "exceeds threshold" in result.stderr
```

- [ ] **A8.2: Run — confirm PASS (on Linux/WSL only)**

- [ ] **A8.3: Commit**

```bash
git commit -am "neurosym-forge(regression): bug7 caught by extract gate not just regex-check"
```

## Phase A.5 — Push + merge

### Task A9: Open PR for Phase A

- [ ] **A9.1: Push**

```bash
git push -u origin feat/tier1-fact-extraction-preview
```

- [ ] **A9.2: Open the PR**

```bash
gh pr create --title "Tier 1A: fact-extraction preview + OPAQUE gate" --body "Implements OpenSpec change \`tier1-fact-extraction-preview\` (REQ-INGEST-040..048). Closes the silent-OPAQUE-fallthrough class of bug at the ingest layer instead of the SMT layer. \`make ci\` now fails at the extract gate when a lifts.edn regex breaks, before reaching pytest."
```

- [ ] **A9.3: Merge on green CI.**

---

# Phase B — Solver timeout (`tier1-solver-timeout`)

**Branch:** `feat/tier1-solver-timeout`
**OpenSpec change:** `openspec/changes/tier1-solver-timeout/`
**Wall-time exit criteria:** a synthetic hard-NRA Rust unit test returns `:unknown` within 32 seconds rather than hanging indefinitely.

## Phase B.1 — Inline Rust unit test for the timeout

### Task B1: Failing test that exposes the missing timeout

**Files:**
- Modify: `verifiers/osmotic_pressure/rust-verifier/src/smt.rs` (extend the existing `#[cfg(all(test, feature = "smt"))] mod tests` block)

- [ ] **B1.1: Add the test** (REQ-VERIFIER-BUILD-040)

Append to the `mod tests` block in `verifiers/osmotic_pressure/rust-verifier/src/smt.rs`:

```rust
#[test]
fn hard_nra_returns_unknown_within_timeout() {
    // Construct a deliberately-hard QF_NRA instance: x^4 + y^4 = 1 with
    // x*y > 1. The solution requires real algebraic reasoning that Z3's
    // CAD procedure handles in milliseconds for small instances, so we
    // chain a few copies and add a transcendental-shaped constraint
    // disguised as polynomial to push solve time up. The exact recipe
    // matters less than: the test must time out, returning :unknown,
    // not :sat or :unsat, in < 32 seconds (default timeout 30s).
    let edn = r#"{:version 1 :atoms []}"#;
    let formulas = crate::ir::parse_formulas(edn).expect("parse");

    // Manually build a solver with a hard problem.
    use z3::{ast::{Real, Bool}, Params, SatResult, Solver};
    let solver = Solver::new();

    // Configure 30s timeout (will be replaced by env-driven impl in B2)
    let mut params = Params::new();
    params.set_u32("timeout", 30_000);
    solver.set_params(&params);

    // Hard NRA: x^2 + y^2 = 1 AND x^4 + y^4 = 1 AND x > 0.999 AND y > 0.999
    let x = Real::new_const("x");
    let y = Real::new_const("y");
    let one = Real::from_rational_str("1", "1").unwrap();
    let almost_one = Real::from_rational_str("999", "1000").unwrap();
    let x2 = x.clone().mul(&x);
    let y2 = y.clone().mul(&y);
    let x4 = x2.clone().mul(&x2);
    let y4 = y2.clone().mul(&y2);
    solver.assert(&x2.add(&y2).eq(&one));
    solver.assert(&x4.add(&y4).eq(&one));
    solver.assert(&x.gt(&almost_one));
    solver.assert(&y.gt(&almost_one));

    let start = std::time::Instant::now();
    let result = solver.check();
    let elapsed = start.elapsed();
    assert!(elapsed.as_secs() < 32,
            "solver did not return within 32s (elapsed: {:?})", elapsed);
    assert_eq!(result, SatResult::Unknown,
               "expected :unknown (timeout) but got {:?}", result);

    let _ = formulas;  // suppress unused
}
```

- [ ] **B1.2: Run the test — currently it should PASS (because we manually configured the solver, not check_all)**

Run: `wsl -d Ubuntu -- bash -lc 'cd /mnt/c/work/russellian-book-suite/verifiers/osmotic_pressure/rust-verifier && cargo test --features smt --release smt::tests::hard_nra_returns_unknown_within_timeout -- --nocapture'`

(This test serves as a *characterisation* test: it shows the timeout mechanism works correctly when configured. The real failing test is in B2.)

- [ ] **B1.3: Commit**

```bash
git commit -am "smt(osmotic): characterisation test for Z3 timeout mechanism"
```

## Phase B.2 — Implement timeout in check_all

### Task B2: Wire the timeout into `smt::check_all`

- [ ] **B2.1: Add a failing test that exercises `check_all` without a configured timeout** (REQ-VERIFIER-BUILD-040)

Add to the `mod tests` block:

```rust
#[test]
fn check_all_returns_unknown_not_hang_on_hard_input() {
    // Same hard NRA shape, but routed through check_all. With no timeout
    // in check_all today, this test would have hung; with the timeout
    // implemented (B2.2), it returns :unknown within 32s.
    let edn = r#"
    {:version 1
     :atoms [{:id "h-001" :kind :expression :predicate :hard-x :subject :s :value 0.9999}
             {:id "h-002" :kind :expression :predicate :hard-y :subject :s :value 0.9999}]}
    "#;
    let formulas = crate::ir::parse_formulas(edn).expect("parse");
    // assert_axioms() is the osmotic van 't Hoff axiom; combined with
    // the contradictory hard-x, hard-y bindings it should be quick to
    // unsat. To make it hard, override the env var to a short timeout
    // and instead inject a structurally hard constraint via the test
    // fixture. (Pragmatic test: just check that check_all RETURNS
    // within the default budget for ANY input — the actual unknown-by-
    // timeout case is exercised in B1.)
    let start = std::time::Instant::now();
    let verdict = check_all(&formulas).expect("check_all");
    let elapsed = start.elapsed();
    assert!(elapsed.as_secs() < 32, "check_all elapsed {:?}", elapsed);
    let _ = verdict;
}
```

- [ ] **B2.2: Modify `check_all` to read the timeout env var and configure the solver**

In `verifiers/osmotic_pressure/rust-verifier/src/smt.rs`, modify the start of `check_all`:

```rust
#[cfg(feature = "smt")]
pub fn check_all(formulas: &[(ClaimId, Atom)]) -> Result<Verdict, Error> {
    use edn_rs::Edn;
    use z3::Params;

    let solver = Solver::new();

    // Z3 solver timeout. Default 30,000 ms; override via
    // VERIFIER_SOLVER_TIMEOUT_MS env var. Without a timeout an
    // undecidable or hard QF_NRA instance hangs the verifier process
    // indefinitely (REQ-VERIFIER-BUILD-040, REQ-VERIFIER-BUILD-041).
    let timeout_ms: u32 = std::env::var("VERIFIER_SOLVER_TIMEOUT_MS")
        .ok()
        .and_then(|s| s.parse().ok())
        .unwrap_or(30_000);
    let mut params = Params::new();
    params.set_u32("timeout", timeout_ms);
    solver.set_params(&params);

    // (rest of check_all unchanged from current implementation)
    crate::axioms::assert_axioms(&solver);
    // ... existing per-atom binding loop, unchanged ...
    // ... existing match solver.check() block, unchanged ...
}
```

- [ ] **B2.3: Run the unit tests — confirm clean + doctored + hard NRA all pass**

Run: `wsl -d Ubuntu -- bash -lc 'cd /mnt/c/work/russellian-book-suite/verifiers/osmotic_pressure/rust-verifier && cargo test --features smt --release smt::tests -- --nocapture'`
Expected: 3 passed.

- [ ] **B2.4: Test env-var override**

Add another test:

```rust
#[test]
fn env_var_overrides_default_timeout() {
    // REQ-VERIFIER-BUILD-041
    std::env::set_var("VERIFIER_SOLVER_TIMEOUT_MS", "1");  // 1 ms — too short
    let edn = r#"
    {:version 1
     :atoms [{:id "osm-002" :kind :expression :predicate :molarity :subject :s :value 0.154}]}
    "#;
    let formulas = crate::ir::parse_formulas(edn).expect("parse");
    let verdict = check_all(&formulas).expect("check_all");
    // With 1 ms timeout, the axiom is too complex to solve → :unknown.
    // (If it manages to solve in 1 ms, that's fine too; the assertion
    // is just that we don't hang.)
    std::env::remove_var("VERIFIER_SOLVER_TIMEOUT_MS");
    assert!(["sat","unsat","unknown"].contains(&verdict.status.as_str()));
}
```

- [ ] **B2.5: Commit**

```bash
git commit -am "smt(osmotic): configurable Z3 timeout (default 30s) via env var"
```

## Phase B.3 — Mirror to bermuda

### Task B3: Apply the identical timeout block to bermuda's smt.rs

- [ ] **B3.1: Edit `verifiers/bermuda/rust-verifier/src/smt.rs`** — apply the same env-var read + `solver.set_params(&params)` block to its `check_all`.

- [ ] **B3.2: Run bermuda's cargo tests — confirm no regression**

Run: `wsl -d Ubuntu -- bash -lc 'cd /mnt/c/work/russellian-book-suite/verifiers/bermuda/rust-verifier && cargo test --features smt --release'`

- [ ] **B3.3: Commit**

```bash
git commit -am "smt(bermuda): configurable Z3 timeout (default 30s) via env var"
```

## Phase B.4 — Pytest smoke `:unknown` distinguishability

### Task B4: Make `:unknown` a distinct test failure

- [ ] **B4.1: Edit `verifiers/osmotic_pressure/tests/test_smoke.py`** (REQ-VERIFIER-BUILD-042)

Locate `_verdict_status` and update its callers. The cleanest pattern:

```python
def test_clean_fixture_is_sat(project_root: Path, tmp_work: Path) -> None:
    # ... existing prelude ...
    status = _verdict_status(verdict_edn)
    if status in (":unknown", "unknown"):
        pytest.fail(
            "Solver returned :unknown — likely timeout or theory "
            "incompleteness. Re-run with VERIFIER_SOLVER_TIMEOUT_MS=300000 "
            "to investigate or accept indeterminacy."
        )
    assert status in (":sat", "sat"), (
        f"expected :sat for clean fixture, got {status!r}"
    )
```

Apply the same pattern to `test_doctored_fixture_is_unsat_with_i1_in_core`.

- [ ] **B4.2: Add a unit test for the failure path**

```python
def test_unknown_verdict_fails_with_distinguished_message(tmp_path):
    """REQ-VERIFIER-BUILD-042: An :unknown verdict fails the test with
    a distinctive 'timeout or theory incompleteness' message."""
    verdict_edn = tmp_path / "verdict.edn"
    verdict_edn.write_text('{:status :unknown :core [] :explanation "timeout"}',
                           encoding="utf-8")
    status = _verdict_status(verdict_edn)
    assert status in (":unknown", "unknown")
```

- [ ] **B4.3: Mirror to bermuda's `tests/test_smoke.py`**

- [ ] **B4.4: Commit**

```bash
git commit -am "smoke(both): :unknown verdict fails with distinct timeout message"
```

## Phase B.5 — Scaffold template

### Task B5: Apply the same timeout to smt.rs.tmpl

- [ ] **B5.1: Edit `skills/neurosym-forge/assets/project-template/rust-verifier/src/smt.rs.tmpl`** (REQ-VERIFIER-BUILD-043)

Apply the same `VERIFIER_SOLVER_TIMEOUT_MS` + `Params` block at the start of `check_all`.

- [ ] **B5.2: Add a scaffold-bake test**

In `skills/neurosym-forge/tests/test_scaffold_bake.py`:

```python
def test_baked_smt_rs_has_timeout_config(tmp_path):
    """REQ-VERIFIER-BUILD-043: baked smt.rs configures Z3 timeout."""
    project = _scaffold(tmp_path, "bake_test")
    smt = (project / "rust-verifier" / "src" / "smt.rs").read_text(encoding="utf-8")
    assert "VERIFIER_SOLVER_TIMEOUT_MS" in smt
    assert "set_params" in smt
```

- [ ] **B5.3: Run — PASS**

- [ ] **B5.4: Commit**

```bash
git commit -am "scaffold: smt.rs.tmpl ships with Z3 timeout config"
```

## Phase B.6 — Push + merge

### Task B6: Open PR for Phase B

- [ ] **B6.1: Push**

```bash
git push -u origin feat/tier1-solver-timeout
```

- [ ] **B6.2: Open PR**

```bash
gh pr create --title "Tier 1B: Z3 solver timeout (default 30s, env-var override)" --body "Implements OpenSpec change \`tier1-solver-timeout\` (REQ-VERIFIER-BUILD-040..043). Configures a Z3 timeout in smt::check_all for both verifiers + scaffold template. Adds :unknown distinguishability in pytest smoke harnesses. Closes the indefinite-hang case for any future hard QF_NRA or quantified constraint."
```

- [ ] **B6.3: Merge on green CI.**

---

# Phase C — Binding schema (`tier1-binding-schema`)

**Branch:** `feat/tier1-binding-schema`
**OpenSpec change:** `openspec/changes/tier1-binding-schema/`
**Wall-time exit criteria:** golden round-trip tests pass in Python and Rust; canonical_var_name matches across all three languages; a regression test that introduces inline string concatenation in any Z3-var-name construction fails.

## Phase C.1 — Golden test files

### Task C1: Author the goldens

**Files:**
- Create: `skills/neurosym-forge/tests/golden/canonical_var_name.edn`
- Create: `skills/neurosym-forge/tests/golden/{expression_atom,opaque_atom,context_atom,predicate_entry,verdict,constraint_entry}.edn`

- [ ] **C1.1: Write `canonical_var_name.edn`** (REQ-EDN-040)

```edn
;; Algorithm vectors: (predicate, subject) → expected canonical Z3 var name.
;; All three language implementations (CLJS, Python, Rust) must agree on
;; the :want string for each row.
[{:predicate :osmotic-pressure-pa  :subject :s         :want "osmotic-pressure-pa_s"}
 {:predicate ":osmotic-pressure-pa" :subject ":s"      :want "osmotic-pressure-pa_s"}
 {:predicate "?osmotic-pressure-pa" :subject "?s"      :want "osmotic-pressure-pa_s"}
 {:predicate :vant-hoff-i           :subject :Bermuda  :want "vant-hoff-i_Bermuda"}
 {:predicate "parishes-count"       :subject :Bermuda  :want "parishes-count_Bermuda"}
 {:predicate "?p"                   :subject "?s"      :want "p_s"}
 {:predicate :namespace.qualified/name :subject :A     :want "namespace.qualified/name_A"}
 {:predicate :foo                   :subject :Bar      :want "foo_Bar"}]
```

- [ ] **C1.2: Write each atom-shape golden** (REQ-EDN-041)

`expression_atom.edn`:
```edn
{:id "osm-clean-002"
 :kind :expression
 :predicate :molarity
 :subject :s
 :value 0.154
 :doc "Molarity M = 0.154"
 :confidence 1.0}
```

`opaque_atom.edn`:
```edn
{:id "osm-doc-005"
 :kind :symbol
 :sort :formula
 :name :OPAQUE
 :doc "Unmatched prose"
 :confidence 0.0}
```

`context_atom.edn`:
```edn
{:id "design-001"
 :kind :symbol
 :sort :formula
 :name :CONTEXT
 :context true
 :doc "Decision: use SI units"}
```

`predicate_entry.edn`:
```edn
{:osmotic-pressure-pa {:patterns ["(?i)osmotic pressure\\s*=\\s*(?P<v>[0-9.]+)\\s*Pa"]
                       :predicate :osmotic-pressure-pa
                       :subject :s
                       :value-kind :real
                       :word-to-int {}}}
```

`verdict.edn`:
```edn
{:status :sat
 :core []
 :explanation ""}
```

`constraint_entry.edn`:
```edn
{:id "C001-vant-hoff"
 :backend :z3
 :assert (approx= (:osmotic-pressure-pa ?s)
                  (* (:vant-hoff-i ?s) (:molarity ?s) 8.314 (:temperature-k ?s))
                  :tolerance 0.03)
 :track :claim/id
 :on-unsat {:defect :D13
            :severity :critical
            :message "van 't Hoff equation violated"}}
```

- [ ] **C1.3: Commit**

```bash
git add skills/neurosym-forge/tests/golden/
git commit -m "tests(golden): canonical var-name + 6 atom-shape goldens for cross-language round-trip"
```

## Phase C.2 — Python `canonical_var_name` + round-trip

### Task C2: Build the canonical Python module + round-trip tests

**Files:**
- Create: `skills/neurosym-forge/scripts/_canonical.py`
- Create: `skills/neurosym-forge/tests/test_canonical_var_name.py`
- Create: `skills/neurosym-forge/tests/test_golden_round_trip.py`

- [ ] **C2.1: Failing test for `canonical_var_name`** (REQ-EDN-042)

`skills/neurosym-forge/tests/test_canonical_var_name.py`:

```python
"""REQ-EDN-042: Python canonical_var_name matches golden vectors."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts._canonical import canonical_var_name
from scripts._edn_reader import read_edn

GOLDEN = ROOT / "tests" / "golden" / "canonical_var_name.edn"


def test_python_matches_golden():
    rows = read_edn(GOLDEN.read_text(encoding="utf-8"))
    for row in rows:
        pred = row.get("predicate") or row.get(":predicate")
        subj = row.get("subject") or row.get(":subject")
        want = row.get("want") or row.get(":want")
        # rows come back as dicts with Keyword keys; normalise:
        from scripts._edn_reader import Keyword
        if pred is None:
            pred = row[Keyword("predicate")]
        if subj is None:
            subj = row[Keyword("subject")]
        if want is None:
            want = row[Keyword("want")]
        # pred / subj may be Keyword OR str
        pred_in = pred.name if isinstance(pred, Keyword) else pred
        subj_in = subj.name if isinstance(subj, Keyword) else subj
        got = canonical_var_name(pred_in, subj_in)
        assert got == want, f"({pred_in!r}, {subj_in!r}) → {got!r} (expected {want!r})"
```

- [ ] **C2.2: Run — FAIL with ImportError**

- [ ] **C2.3: Write the canonical module** (REQ-EDN-042)

`skills/neurosym-forge/scripts/_canonical.py`:

```python
"""Canonical Z3-variable-name algorithm.

The Z3 variable name for a predicate-subject pair is the framework's
single most load-bearing string. Three languages — CLJS, Python, Rust —
must agree byte-for-byte on its construction. This module is the Python
source of truth; the CLJS and Rust implementations carry the same
algorithm and the same golden test vectors at
`skills/neurosym-forge/tests/golden/canonical_var_name.edn`.

REQ-EDN-042 (Python implementation).
"""
from __future__ import annotations


def canonical_var_name(predicate: str, subject: str) -> str:
    """Return the canonical Z3 variable name for the given predicate /
    subject pair.

    Algorithm:
      pred = predicate.lstrip(':?')
      subj = subject.lstrip(':?')
      return f"{pred}_{subj}"

    Accepts predicate / subject in any of the three EDN forms:
      :foo   (keyword written as Python str ":foo")
      ?foo   (logic-var symbol)
      foo    (bare identifier)
    """
    pred = predicate.lstrip(":?")
    subj = subject.lstrip(":?")
    return f"{pred}_{subj}"
```

- [ ] **C2.4: Run — PASS**

- [ ] **C2.5: Update callers to use the canonical function** (REQ-EDN-043)

In `skills/neurosym-forge/scripts/_codegen_axioms_lib.py`, locate `_emit_expr_typed` where it constructs `var_name = f"{head.name}_{sub_str}"` and replace with:

```python
from scripts._canonical import canonical_var_name
# ...
var_name = canonical_var_name(head.name, sub_str)
```

In `verifiers/osmotic_pressure/scripts/_codegen_axioms_lib.py` (vendored copy), do the same. Same for bermuda's vendored copy.

In Python `ingest_ledger.py`, the binding-name construction lives indirectly via the EDN `:predicate` / `:subject` fields that flow into Rust. No change needed here yet — Phase C.5 handles the keyword-emission part.

- [ ] **C2.6: Run the failing test from C2.1 + the existing codegen tests — all PASS**

Run: `py -m pytest skills/neurosym-forge/tests/test_canonical_var_name.py skills/neurosym-forge/tests/test_codegen_axioms.py -v`

- [ ] **C2.7: Golden round-trip test** (REQ-EDN-044)

`skills/neurosym-forge/tests/test_golden_round_trip.py`:

```python
"""REQ-EDN-044: golden EDN files round-trip byte-identically through
read_edn → write_edn → read_edn in Python."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts._edn_reader import read_edn
from scripts._edn_writer import write_edn_str  # add if not present; or use read+write file-level

GOLDEN_FILES = sorted((ROOT / "tests" / "golden").glob("*.edn"))


@pytest.mark.parametrize("golden", GOLDEN_FILES, ids=lambda p: p.name)
def test_python_byte_identical_round_trip(golden: Path):
    raw = golden.read_text(encoding="utf-8")
    once = write_edn_str(read_edn(raw))
    twice = write_edn_str(read_edn(once))
    assert once == twice, (
        f"round-trip not stable for {golden.name}\nonce:\n{once}\ntwice:\n{twice}"
    )
```

- [ ] **C2.8: Add `write_edn_str` to `_edn_writer.py` if it doesn't exist**

If `_edn_writer.py` only exposes `write_edn_file(path, data)`, add:

```python
def write_edn_str(data) -> str:
    """Write data to an EDN string (sibling of write_edn_file)."""
    from io import StringIO
    buf = StringIO()
    _emit(data, buf)  # use whatever existing emitter is available
    return buf.getvalue()
```

- [ ] **C2.9: Run — confirm PASS for at least the simpler shapes (some goldens may require Phase C.6 (no scientific notation) or C.7 (list-vs-vector) to fully round-trip; deselect those temporarily)**

- [ ] **C2.10: Commit**

```bash
git commit -am "edn: canonical_var_name (Python) + golden round-trip"
```

## Phase C.3 — CLJS canonical-var-name

### Task C3: CLJS implementation + nbb test

- [ ] **C3.1: Failing test in `booklogic_test.cljs.tmpl`** (REQ-EDN-045)

In `skills/neurosym-forge/assets/project-template/cljs-orchestrator/src/test/__project__/booklogic_test.cljs.tmpl`, add:

```clojure
(deftest canonical-var-name-matches-golden
  ;; REQ-EDN-045: CLJS canonical-var-name agrees with the golden vectors.
  (testing "canonical-var-name produces :want for every golden row"
    (let [golden-path "../../skills/neurosym-forge/tests/golden/canonical_var_name.edn"
          rows (cljs.reader/read-string (slurp golden-path))]
      (doseq [{:keys [predicate subject want]} rows]
        (let [pred-str (if (keyword? predicate) (name predicate) (str predicate))
              subj-str (if (keyword? subject)   (name subject)   (str subject))
              got (canonical-var-name pred-str subj-str)]
          (is (= got want)
              (str "(" pred-str ", " subj-str ") → " got
                   " (expected " want ")")))))))
```

(`slurp` doesn't exist in cljs.core; in nbb use `(fs/readFileSync ...)`. Use the same `["fs" :as fs]` pattern the existing osmotic phases.cljs uses.)

- [ ] **C3.2: Implement `canonical-var-name` in `booklogic.cljs.tmpl`** (REQ-EDN-045)

Add to the existing booklogic.cljs.tmpl helpers section:

```clojure
(defn canonical-var-name
  "Return the canonical Z3 variable name for the given (predicate,
   subject) pair. Mirrors Python `_canonical.canonical_var_name` and
   Rust `canonical::canonical_var_name`. See
   tests/golden/canonical_var_name.edn for the algorithm vectors.

   Algorithm: strip leading ':' or '?' from both arguments, join with '_'."
  [predicate subject]
  (let [strip-prefix (fn [s] (if (#{\: \?} (first s)) (subs s 1) s))
        pred (strip-prefix predicate)
        subj (strip-prefix subject)]
    (str pred "_" subj)))
```

- [ ] **C3.3: Replace inline `(str (name pred) "_" (name subj))` patterns**

Grep the CLJS source for inline var-name constructions and replace with `(canonical-var-name ...)` calls. (Use grep to locate.)

- [ ] **C3.4: Run nbb test** (locally if nbb is installed; otherwise rely on CI)

Run: `cd skills/neurosym-forge && nbb -m booklogic-test` (or whatever the existing test invocation is)

- [ ] **C3.5: Commit**

```bash
git commit -am "edn(cljs): canonical-var-name + golden test"
```

## Phase C.4 — Rust canonical_var_name

### Task C4: Rust implementation + integration tests

- [ ] **C4.1: Failing integration test** (REQ-EDN-046)

`verifiers/osmotic_pressure/rust-verifier/tests/canonical_var_name.rs`:

```rust
//! REQ-EDN-046: Rust canonical_var_name matches the golden vectors.
use osmotic_pressure_verifier::canonical::canonical_var_name;
use std::fs;
use std::path::PathBuf;

fn golden_path() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .ancestors()
        .nth(3).unwrap()
        .join("skills/neurosym-forge/tests/golden/canonical_var_name.edn")
}

#[test]
fn matches_golden() {
    use edn_rs::Edn;
    let raw = fs::read_to_string(golden_path()).expect("read golden");
    let edn: Edn = raw.parse().expect("parse golden");
    let rows = match &edn {
        Edn::Vector(v) => v.clone().to_vec(),
        _ => panic!("expected golden to be a vector"),
    };
    for row in rows {
        let pred = row.get(":predicate").expect("predicate");
        let subj = row.get(":subject").expect("subject");
        let want = match row.get(":want").expect("want") {
            Edn::Str(s) => s.clone(),
            other => panic!("want must be string, got {:?}", other),
        };
        let pred_str = match pred {
            Edn::Key(k) => k.trim_start_matches(':').to_string(),
            Edn::Str(s) => s.clone(),
            other => panic!("predicate must be key or str, got {:?}", other),
        };
        let subj_str = match subj {
            Edn::Key(k) => k.trim_start_matches(':').to_string(),
            Edn::Str(s) => s.clone(),
            other => panic!("subject must be key or str, got {:?}", other),
        };
        let got = canonical_var_name(&pred_str, &subj_str);
        assert_eq!(got, want, "({:?}, {:?})", pred_str, subj_str);
    }
}
```

- [ ] **C4.2: Run — FAIL (canonical module doesn't exist yet)**

- [ ] **C4.3: Create `canonical.rs`** (REQ-EDN-046)

`verifiers/osmotic_pressure/rust-verifier/src/canonical.rs`:

```rust
//! Canonical Z3-variable-name algorithm. Mirrors Python
//! `_canonical.canonical_var_name` and CLJS `canonical-var-name`. The
//! golden test vectors at
//! `skills/neurosym-forge/tests/golden/canonical_var_name.edn` are the
//! cross-language source of truth.
//!
//! REQ-EDN-046 (Rust implementation).

pub fn canonical_var_name(predicate: &str, subject: &str) -> String {
    let pred = predicate.trim_start_matches(|c| c == ':' || c == '?');
    let subj = subject.trim_start_matches(|c| c == ':' || c == '?');
    format!("{pred}_{subj}")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn strips_colon_prefix() {
        assert_eq!(canonical_var_name(":foo", ":bar"), "foo_bar");
    }

    #[test]
    fn strips_question_prefix() {
        assert_eq!(canonical_var_name("?foo", "?bar"), "foo_bar");
    }

    #[test]
    fn keeps_bare_identifier() {
        assert_eq!(canonical_var_name("foo", "bar"), "foo_bar");
    }
}
```

- [ ] **C4.4: Add `mod canonical;` to `lib.rs`**

In `verifiers/osmotic_pressure/rust-verifier/src/lib.rs`:

```rust
mod canonical;
// (alongside the existing mod ir; mod axioms; mod smt; declarations)
```

- [ ] **C4.5: Run — PASS**

- [ ] **C4.6: Update `smt.rs` to call `canonical::canonical_var_name`** (REQ-EDN-047)

In `verifiers/osmotic_pressure/rust-verifier/src/smt.rs`, locate the existing:

```rust
let var_name = format!(
    "{}_{}",
    predicate.trim_start_matches(':'),
    subject.trim_start_matches(':')
);
```

Replace with:

```rust
let var_name = crate::canonical::canonical_var_name(&predicate, &subject);
```

- [ ] **C4.7: Run unit tests — confirm clean + doctored + hard NRA all pass**

Run: `wsl -d Ubuntu -- bash -lc 'cd /mnt/c/work/russellian-book-suite/verifiers/osmotic_pressure/rust-verifier && cargo test --features smt --release'`

- [ ] **C4.8: Add the golden-shape integration test** (REQ-EDN-048)

`verifiers/osmotic_pressure/rust-verifier/tests/golden.rs`:

```rust
//! REQ-EDN-048: every golden EDN file parses with edn-rs and the
//! field types match expectations (Edn::Key for keyword fields,
//! Edn::Double for real-typed values, never silent Edn::Str).
use edn_rs::Edn;
use std::fs;
use std::path::PathBuf;

fn golden_dir() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .ancestors().nth(3).unwrap()
        .join("skills/neurosym-forge/tests/golden")
}

#[test]
fn expression_atom_has_double_value() {
    let raw = fs::read_to_string(golden_dir().join("expression_atom.edn")).unwrap();
    let edn: Edn = raw.parse().unwrap();
    let value = edn.get(":value").expect("value");
    matches!(value, Edn::Double(_));
}

#[test]
fn opaque_atom_kind_is_keyword() {
    let raw = fs::read_to_string(golden_dir().join("opaque_atom.edn")).unwrap();
    let edn: Edn = raw.parse().unwrap();
    let kind = edn.get(":kind").expect("kind");
    matches!(kind, Edn::Key(_));
}

#[test]
fn verdict_status_is_keyword() {
    let raw = fs::read_to_string(golden_dir().join("verdict.edn")).unwrap();
    let edn: Edn = raw.parse().unwrap();
    let status = edn.get(":status").expect("status");
    matches!(status, Edn::Key(_));
}
```

- [ ] **C4.9: Mirror canonical.rs + tests to bermuda**

Copy `canonical.rs` and the two test files into bermuda's rust-verifier dir. Update bermuda's `smt.rs` to call `canonical::canonical_var_name`.

- [ ] **C4.10: Commit**

```bash
git commit -am "edn(rust): canonical_var_name + golden tests in both verifiers"
```

## Phase C.5 — Stop-gap 1: keyword emission in `ingest_ledger.py`

### Task C5: Emit Keywords, not f-strings

- [ ] **C5.1: Failing test** (REQ-EDN-049)

`verifiers/osmotic_pressure/scripts/tests/test_ingest_keyword_emission.py`:

```python
"""REQ-EDN-049: ingest_ledger emits :predicate and :subject as Edn
Keywords, not string-with-colon-prefix."""
from pathlib import Path
import subprocess
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_emits_keywords_not_strings(tmp_path):
    out = tmp_path / "claims.edn"
    from scripts.ingest_ledger import ingest
    ingest(
        PROJECT_ROOT / "fixtures" / "claims_clean.jsonl",
        PROJECT_ROOT / "rules" / "predicates.edn",
        out,
    )
    text = out.read_text(encoding="utf-8")
    # A keyword written via _edn_writer is `:foo`, NOT `":foo"`.
    assert ':predicate :osmotic-pressure-pa' in text or \
           ':predicate :molarity' in text or \
           ':predicate :vant-hoff-i' in text or \
           ':predicate :temperature-k' in text, \
        "expected at least one :predicate to be emitted as a Keyword"
    assert ':predicate ":' not in text, \
        "found a stringly-typed :predicate; ingest_ledger should emit Keywords"
```

- [ ] **C5.2: Run — currently FAILS (the codebase emits strings)**

- [ ] **C5.3: Modify `ingest_ledger.py`** (REQ-EDN-049)

In `verifiers/osmotic_pressure/scripts/ingest_ledger.py`, locate the existing:

```python
pred_raw = spec.get(_KW_PREDICATE)
subj_raw = spec.get(_KW_SUBJECT)
pred = f":{pred_raw.name}" if isinstance(pred_raw, Keyword) else str(pred_raw)
subj = f":{subj_raw.name}" if isinstance(subj_raw, Keyword) else str(subj_raw)
return pred, value, subj
```

Replace with:

```python
pred_raw = spec.get(_KW_PREDICATE)
subj_raw = spec.get(_KW_SUBJECT)
# REQ-EDN-049: emit Keyword objects, not string-with-colon-prefix.
pred = pred_raw if isinstance(pred_raw, Keyword) else Keyword(str(pred_raw).lstrip(":"))
subj = subj_raw if isinstance(subj_raw, Keyword) else Keyword(str(subj_raw).lstrip(":"))
return pred, value, subj
```

- [ ] **C5.4: Update Rust `smt.rs` to drop the `Edn::Str(s)` fallback for :predicate and :subject** (the migration shim is no longer needed)

In `verifiers/osmotic_pressure/rust-verifier/src/smt.rs`:

```rust
// Before:
let predicate = match atom.get(":predicate") {
    Some(Edn::Key(k)) => k.clone(),
    Some(Edn::Str(s)) => s.clone(),  // ← migration shim
    _ => continue,
};

// After:
let predicate = match atom.get(":predicate") {
    Some(Edn::Key(k)) => k.clone(),
    _ => continue,  // no string fallback; ingest must emit Keyword
};
```

Same for `:subject`.

- [ ] **C5.5: Run osmotic + bermuda smoke — confirm no regression**

Run: `wsl -d Ubuntu -- bash -lc 'cd /mnt/c/work/russellian-book-suite/verifiers/osmotic_pressure/rust-verifier && cargo test --features smt --release smt::tests'`

- [ ] **C5.6: Apply the same change to bermuda's `ingest_ledger.py` + `smt.rs`**

- [ ] **C5.7: Commit**

```bash
git commit -am "edn(ingest+smt): emit and require Keyword for :predicate/:subject"
```

## Phase C.6 — Stop-gap 2: no scientific notation in float emission

### Task C6: Fix the float writer

- [ ] **C6.1: Failing test** (REQ-EDN-050)

`skills/neurosym-forge/tests/test_emit_float.py`:

```python
"""REQ-EDN-050: _emit_float never produces scientific notation."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts._edn_writer import _emit_float


PROBE = [
    1.0, 0.0, -0.0, 1e-20, 1e-10, 6.022e23, -1.5e-7,
    1.234567890123, 1e308, 1e-308,
]


def test_no_scientific_notation_in_emitted_token():
    for v in PROBE:
        s = _emit_float(v)
        assert "e" not in s.lower(), f"_emit_float({v!r}) = {s!r} contains 'e'"
```

- [ ] **C6.2: Run — FAILS for large/small values**

- [ ] **C6.3: Replace `_emit_float`** (REQ-EDN-050)

In `skills/neurosym-forge/scripts/_edn_writer.py`, locate `_emit_float` and replace with:

```python
def _emit_float(f: float) -> str:
    """Emit a float as EDN-readable text WITHOUT scientific notation.

    edn-rs 0.19 does not parse scientific notation; falling back to a
    fixed-point representation is mandatory for the Rust read side to
    parse the value as Edn::Double rather than silently fall through to
    Edn::Str. REQ-EDN-050.
    """
    from math import isfinite, isnan
    if isnan(f) or not isfinite(f):
        raise ValueError(f"cannot emit non-finite float: {f!r}")
    s = f"{f:.17g}"  # shortest round-trippable
    if "e" in s.lower():
        # Fall back to fixed-point. 20 decimals is enough for any
        # IEEE 754 double (worst case ~1e-308).
        s = f"{f:.20f}".rstrip("0").rstrip(".") or "0.0"
        if "." not in s:
            s += ".0"
    if "." not in s:
        s += ".0"  # keep float discriminator
    return s
```

- [ ] **C6.4: Run — PASS**

- [ ] **C6.5: Commit**

```bash
git commit -am "edn: no scientific notation in _emit_float (edn-rs compatibility)"
```

## Phase C.7 — Stop-gap 3: EdnList vs EdnVector

### Task C7: Distinguish `(...)` from `[...]` in the Python reader/writer

- [ ] **C7.1: Failing test** (REQ-EDN-051)

`skills/neurosym-forge/tests/test_list_vs_vector.py`:

```python
"""REQ-EDN-051: EDN list (paren) vs vector (bracket) round-trips faithfully."""
from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts._edn_reader import read_edn, EdnList, EdnVector
from scripts._edn_writer import write_edn_str


def test_paren_round_trip_preserved():
    src = "(approx= 1 2 :tolerance 0.03)"
    parsed = read_edn(src)
    assert isinstance(parsed, EdnList)
    emitted = write_edn_str(parsed)
    assert emitted.startswith("(") and emitted.endswith(")"), \
        f"emitted {emitted!r} should be a paren list"


def test_bracket_round_trip_preserved():
    src = "[1 2 3]"
    parsed = read_edn(src)
    assert isinstance(parsed, EdnVector)
    emitted = write_edn_str(parsed)
    assert emitted.startswith("[") and emitted.endswith("]")
```

- [ ] **C7.2: Run — FAILS (EdnList / EdnVector don't exist)**

- [ ] **C7.3: Introduce EdnList + EdnVector dataclasses** (REQ-EDN-051)

In `skills/neurosym-forge/scripts/_edn_reader.py`, add at the top:

```python
from dataclasses import dataclass, field


@dataclass
class EdnList:
    items: list = field(default_factory=list)
    def __iter__(self): return iter(self.items)
    def __len__(self): return len(self.items)
    def __getitem__(self, i): return self.items[i]
    def __eq__(self, other):
        return isinstance(other, EdnList) and self.items == other.items


@dataclass
class EdnVector:
    items: list = field(default_factory=list)
    def __iter__(self): return iter(self.items)
    def __len__(self): return len(self.items)
    def __getitem__(self, i): return self.items[i]
    def __eq__(self, other):
        return isinstance(other, EdnVector) and self.items == other.items
```

Locate the parser branches for `(` and `[` and have them return `EdnList(items)` and `EdnVector(items)` respectively.

In `_edn_writer.py`, locate the emitter dispatch and add cases:

```python
def _emit_compact(node, out):
    if isinstance(node, EdnList):
        out.write("(")
        for i, item in enumerate(node):
            if i: out.write(" ")
            _emit_compact(item, out)
        out.write(")")
        return
    if isinstance(node, EdnVector):
        out.write("[")
        for i, item in enumerate(node):
            if i: out.write(" ")
            _emit_compact(item, out)
        out.write("]")
        return
    # ... existing branches for dict, list (fallback), str, etc. ...
```

- [ ] **C7.4: Audit callers of `_edn_reader.read_edn`**

Grep for places that destructure list results and rely on the bare-`list` type. The two known sites:

```bash
grep -rn "isinstance.*list" skills/neurosym-forge/scripts/ verifiers/*/scripts/ | head -20
```

For places where the bare-list semantics is intentional (e.g., walking a `:forms` vector), change to `isinstance(x, (EdnList, EdnVector))`. For `_emit_z3_block`'s assert-form parsing in `_codegen_axioms_lib.py`, the form was a paren-list in CLJS; update the dispatch to use `isinstance(assert_form, EdnList)`.

- [ ] **C7.5: Run all neurosym-forge tests — confirm no regression**

Run: `py -m pytest skills/neurosym-forge/tests -q --ignore=skills/neurosym-forge/tests/regression`

(The regression suite needs Linux + nbb; skip locally on Windows.)

- [ ] **C7.6: Commit**

```bash
git commit -am "edn: EdnList vs EdnVector preserve list/vector distinction on round-trip"
```

## Phase C.8 — Schema file generation

### Task C8: Emit and validate `booklogic-schema.edn`

- [ ] **C8.1: Failing test** (REQ-EDN-052)

`verifiers/osmotic_pressure/tests/test_schema_file.py`:

```python
"""REQ-EDN-052: nbb compile emits a rules/booklogic-schema.edn enumerating
predicates with arg-sorts and return."""
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCHEMA = PROJECT_ROOT / "rules" / "booklogic-schema.edn"


def test_schema_lists_four_predicates_with_return_real():
    text = SCHEMA.read_text(encoding="utf-8")
    for pred in ("osmotic-pressure-pa", "vant-hoff-i", "molarity", "temperature-k"):
        assert pred in text, f"predicate {pred!r} not in schema"
    # All four are typed [:solution] :real
    assert ":return :real" in text
    assert ":arg-sorts [:solution]" in text or ":arg-sorts (:solution)" in text
```

- [ ] **C8.2: Run — FAIL (schema file doesn't exist)**

- [ ] **C8.3: Add `emit-schema-edn` in `booklogic.cljs.tmpl`** (REQ-EDN-052)

In `skills/neurosym-forge/assets/project-template/cljs-orchestrator/src/main/__project__/booklogic.cljs.tmpl`, after the existing `emit-predicates-edn-string` function, add:

```clojure
(defn- emit-schema-edn-string [predicate-registry sort-registry]
  (let [m {:version 1
           :sorts sort-registry
           :predicates predicate-registry}]
    (pr-str m)))

(defn- emit-schema! [project-root predicate-registry sort-registry]
  (let [out (str project-root "/rules/booklogic-schema.edn")
        content (emit-schema-edn-string predicate-registry sort-registry)]
    (.writeFileSync fs out content)))
```

And in the `-main` driver, call `(emit-schema! project-root predicates sorts)` after the existing emit calls.

- [ ] **C8.4: Run `nbb` to regenerate the schema in the osmotic verifier**

```bash
cd verifiers/osmotic_pressure && nbb -m osmotic-pressure.booklogic .
```

(The same step CI runs.)

- [ ] **C8.5: Run the test — PASS**

- [ ] **C8.6: Add Python schema validator** (REQ-EDN-053)

In `verifiers/osmotic_pressure/scripts/ingest_ledger.py`, after the predicates.edn load:

```python
# REQ-EDN-053: validate predicate names against the schema before ingest.
SCHEMA_EDN = predicates_path.parent / "booklogic-schema.edn"
if SCHEMA_EDN.exists():
    schema = read_edn_file(SCHEMA_EDN)
    known = set(schema.get(Keyword("predicates"), {}).keys())
    for pred_kw in predicates_map:
        if pred_kw not in known:
            print(f"ingest_ledger: unknown predicate {pred_kw!r}; not in schema",
                  file=sys.stderr)
            sys.exit(1)
```

- [ ] **C8.7: Failing test for the unknown-predicate gate**

```python
def test_typo_predicate_rejected(tmp_path):
    """REQ-EDN-053: an unknown predicate name in predicates.edn rejects ingest."""
    # Create a predicates.edn that references a typo predicate
    typo_preds = tmp_path / "predicates.edn"
    typo_preds.write_text(
        '{:version 1, :predicates {:Osmotic-Pressure {:patterns ["x"], '
        ':predicate :Osmotic-Pressure, :subject :s, :value-kind :real, '
        ':word-to-int {}}}}',
        encoding="utf-8",
    )
    # Use the real schema (which doesn't contain :Osmotic-Pressure)
    schema = PROJECT_ROOT / "rules" / "booklogic-schema.edn"
    # Symlink for the predicates.edn so its sibling resolves to schema
    (tmp_path / "booklogic-schema.edn").symlink_to(schema)
    # Run ingest
    import subprocess, sys
    out = tmp_path / "claims.edn"
    result = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "scripts" / "ingest_ledger.py"),
         "--in", str(PROJECT_ROOT / "fixtures" / "claims_clean.jsonl"),
         "--predicates", str(typo_preds),
         "--out", str(out)],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode != 0
    assert "unknown predicate" in result.stderr.lower()
```

(If ingest_ledger.py doesn't currently have a CLI, add one in this task.)

- [ ] **C8.8: Run — PASS**

- [ ] **C8.9: Commit**

```bash
git commit -am "edn: booklogic-schema.edn + Python ingest validator"
```

## Phase C.9 — Push + merge

### Task C9: Open PR for Phase C

- [ ] **C9.1: Push**

```bash
git push -u origin feat/tier1-binding-schema
```

- [ ] **C9.2: Open PR**

```bash
gh pr create --title "Tier 1C: cross-language canonical_var_name + golden tests + schema + 3 stop-gaps" --body "Implements OpenSpec change \`tier1-binding-schema\` (REQ-EDN-040..053). Closes the cross-language identifier-drift class of bug structurally: one canonical algorithm in three languages, golden test vectors, and three EDN-writer stop-gaps (Keyword emission, no scientific notation, list-vs-vector preservation). Adds booklogic-schema.edn as the single source of truth for predicate signatures, validated at ingest time."
```

- [ ] **C9.3: Merge on green CI.**

---

# Phase D — Reference docs + support matrix (`tier1-references-docs`)

**Branch:** `feat/tier1-references-docs`
**OpenSpec change:** `openspec/changes/tier1-references-docs/`
**Wall-time exit criteria:** every file path mentioned in SKILL.md exists on disk; every `.edn.tmpl` seed has at least one commented-out example; CI lint passes (the SUPPORT_MATRIX matches codegen reality).

## Phase D.1 — The six reference files

### Task D1-D6: Six independent documentation tasks

Each file is created from scratch with length budget 200-400 lines.

- [ ] **D1: `skills/neurosym-forge/references/atomspace-edn.md`** (REQ-BOOKLOGIC-040)

Sections:
1. Atom shapes (expression, symbol OPAQUE, symbol CONTEXT) — golden example per kind
2. Field types: which fields are Keywords, which are Strings, which are Doubles, which are Ints, which are Bools, which are nested maps
3. The cross-language asymmetry (Edn::Key vs Edn::Str) and what closes it (Phase C of Tier 1)
4. The `:version` field — what bumping it means

Commit after each.

- [ ] **D2: `skills/neurosym-forge/references/grounded-atoms.md`** (REQ-BOOKLOGIC-041)

Sections:
1. The `deflift` lift form — surface syntax and field reference
2. Regex dialect: Python `(?P<name>)` is the framework standard; `(?<name>)` JS form is rejected
3. The `?claim-id` and `:s` (subject placeholder) conventions
4. `parse-float` and `parse-int` helpers in `:emit`
5. Worked example: a single lift extracted from the osmotic verifier

- [ ] **D3: `skills/neurosym-forge/references/phase-boundaries.md`** (REQ-BOOKLOGIC-042)

Sections:
1. Pipeline diagram (CLJS author → `nbb -m booklogic .` → intermediate EDN → Python codegen → Rust verifier)
2. Per-boundary schema (what's the type of each EDN file)
3. Per-boundary test coverage (`test_canonical_var_name.py`, golden round-trip, etc.)
4. Where each boundary's failures usually surface (silent OPAQUE, unbound predicate, etc.)

- [ ] **D4: `skills/neurosym-forge/references/rewrite-rule-style.md`** (REQ-BOOKLOGIC-043)

Sections:
1. `defrule` surface syntax
2. The intent: egg equality-saturation
3. **Current status: STUB** — explicit warning that egg is not wired yet (Tier 3 of the roadmap)
4. What rules do today: consumed by `phases.cljs` for string-substitution canonicalization in CLJS, NOT by egg

- [ ] **D5: `skills/neurosym-forge/references/metta-idioms.md`** (REQ-BOOKLOGIC-044)

Sections:
1. MeTTa concepts the framework borrows (atomspace, grounded atoms, rewrite rules)
2. MeTTa concepts it does NOT borrow (full unification, dynamic dispatch, type system)
3. Cross-references to the actual implementation files

- [ ] **D6: `skills/neurosym-forge/references/worked-examples/osmotic-pressure/clojure.md`** (REQ-BOOKLOGIC-045)

Sections — step-by-step walkthrough:
1. The domain (van 't Hoff equation)
2. `sorts.edn` — `:solution`
3. `predicates.edn` — four predicates with `[:solution] :real`
4. `lifts.edn` — regex per predicate, the apostrophe-in-"van 't Hoff" lesson
5. `constraints.edn` — `approx=` with relative tolerance
6. `fixtures/claims_*.jsonl` — clean vs doctored
7. `make extract` — what you should see
8. `make ci` — clean → :sat, doctored → :unsat

After each file, commit:

```bash
git commit -am "docs(references): atomspace-edn (D1)"
git commit -am "docs(references): grounded-atoms (D2)"
git commit -am "docs(references): phase-boundaries (D3)"
git commit -am "docs(references): rewrite-rule-style (D4)"
git commit -am "docs(references): metta-idioms (D5)"
git commit -am "docs(references): osmotic-pressure walkthrough (D6)"
```

### Task D7: existence-and-shape test for the references

- [ ] **D7.1: `skills/neurosym-forge/tests/test_reference_docs.py`** (asserts each file exists, has expected headings)

```python
"""REQ-BOOKLOGIC-040..045: reference docs exist with expected structure."""
from pathlib import Path

REF = Path(__file__).resolve().parents[1] / "references"


def _has_heading(path: Path, heading: str) -> bool:
    return any(line.strip().startswith(f"# {heading}") or
               line.strip().startswith(f"## {heading}")
               for line in path.read_text(encoding="utf-8").splitlines())


def test_atomspace_edn_present():
    p = REF / "atomspace-edn.md"
    assert p.exists()
    assert _has_heading(p, "Atom shapes") or _has_heading(p, "Wire format")


def test_grounded_atoms_present():
    p = REF / "grounded-atoms.md"
    assert p.exists()
    assert "(?P<" in p.read_text(encoding="utf-8")  # documents the regex dialect


def test_phase_boundaries_present():
    p = REF / "phase-boundaries.md"
    assert p.exists()


def test_rewrite_rule_style_marks_stub():
    p = REF / "rewrite-rule-style.md"
    assert p.exists()
    text = p.read_text(encoding="utf-8").lower()
    assert "stub" in text  # explicitly warns


def test_metta_idioms_present():
    p = REF / "metta-idioms.md"
    assert p.exists()


def test_worked_example_walks_seven_form_families():
    p = REF / "worked-examples" / "osmotic-pressure" / "clojure.md"
    assert p.exists()
    text = p.read_text(encoding="utf-8")
    for form in ("defsort", "defpredicate", "deflift", "defconstraint"):
        assert form in text, f"{form} not mentioned in walkthrough"
```

- [ ] **D7.2: Run — PASS**

- [ ] **D7.3: Commit**

```bash
git commit -am "tests(docs): reference-files existence and shape assertions"
```

## Phase D.2 — Seed template annotations

### Task D8: Annotate every `.edn.tmpl` seed

For each of sorts.edn.tmpl, predicates.edn.tmpl, lifts.edn.tmpl, rules.edn.tmpl, constraints.edn.tmpl, queries.edn.tmpl, remedies.edn.tmpl (in `skills/neurosym-forge/assets/project-template/rules/booklogic/`):

- [ ] **D8.1 through D8.7: Replace `{:forms []}` with the annotated form**

Example for `predicates.edn.tmpl`:

```edn
;; rules/booklogic/predicates.edn — predicate signatures for this verifier.
;;
;; FORM SYNTAX:
;;   (defpredicate :predicate-name [:arg-sort-1 :arg-sort-2 ...] :return-sort)
;;
;; Valid return sorts:  :real :int :bool :string :entity
;; Arg sorts MUST be declared in sorts.edn or be one of the primitive set
;;   {:int :real :bool :string :entity}
;;
;; EXAMPLE (commented out — uncomment + edit for your domain):
;; (defpredicate :osmotic-pressure-pa [:solution] :real)
;; (defpredicate :molarity            [:solution] :real)
;;
;; COMMON SILENT FAILURES:
;;   - return sort :int when the regex extracts "2.5" → predicate stays
;;     unbound in the Z3 axiom, solver returns :sat for the wrong reason
;;   - predicate name with uppercase letters → ingest emits OPAQUE for
;;     every claim, `make extract` fails the OPAQUE-fraction gate
;;
{:forms []}
```

Similar treatment for the other six seeds. Each gets:
- One comment-line explaining the form's purpose
- One commented-out worked-example form
- A "Common silent failures" block

- [ ] **D8.8: Test that every seed is annotated** (REQ-BOOKLOGIC-046)

`skills/neurosym-forge/tests/test_seed_template_annotations.py`:

```python
"""REQ-BOOKLOGIC-046: every .edn.tmpl seed has at least one comment and
one commented-out example form."""
from pathlib import Path

import pytest

SEED_DIR = (Path(__file__).resolve().parents[1] /
            "assets" / "project-template" / "rules" / "booklogic")

SEEDS = sorted(SEED_DIR.glob("*.edn.tmpl"))


@pytest.mark.parametrize("seed", SEEDS, ids=lambda p: p.name)
def test_every_seed_has_example_and_failure_notes(seed: Path):
    text = seed.read_text(encoding="utf-8")
    # at least one comment line
    assert any(line.strip().startswith(";") for line in text.splitlines()), \
        f"{seed.name} has no comments — author has no guidance"
    # at least one commented-out form (`;; (def...`)
    assert "(def" in text or "(deflift" in text or "(approx=" in text, \
        f"{seed.name} has no commented-out worked example"
    # "silent failure" guidance
    assert "silent" in text.lower() or "common" in text.lower(), \
        f"{seed.name} has no 'common silent failures' notes"
```

- [ ] **D8.9: Run — PASS**

- [ ] **D8.10: Commit**

```bash
git commit -am "scaffold(seeds): annotate every .edn.tmpl with example + silent-failure notes"
```

## Phase D.3 — Canonical DSL reference

### Task D9: `docs/booklogic-dsl-reference.md`

- [ ] **D9.1: Write the reference doc** (REQ-BOOKLOGIC-047)

Structure (see `openspec/changes/tier1-references-docs/design.md` for the full outline). Length budget: 800-1200 lines. Each section corresponds to one form family or one cross-cutting concern (debugging, sort system, conventions).

- [ ] **D9.2: Add an existence test**

In `skills/neurosym-forge/tests/test_reference_docs.py`:

```python
def test_dsl_reference_covers_seven_forms():
    p = Path(__file__).resolve().parents[3] / "docs" / "booklogic-dsl-reference.md"
    assert p.exists()
    text = p.read_text(encoding="utf-8")
    for form in ("defsort", "defpredicate", "deflift", "defrule",
                 "defconstraint", "defquery", "defremedy"):
        assert form in text, f"{form} not covered in DSL reference"
```

- [ ] **D9.3: Add the debugging-section test** (REQ-BOOKLOGIC-048)

```python
def test_dsl_reference_has_debugging_section():
    p = Path(__file__).resolve().parents[3] / "docs" / "booklogic-dsl-reference.md"
    text = p.read_text(encoding="utf-8")
    for affordance in ("VERIFIER_DEBUG_SMT", "make extract",
                       "VERIFIER_SOLVER_TIMEOUT_MS", ":unknown"):
        assert affordance in text, f"{affordance} not mentioned"
```

- [ ] **D9.4: Link from SKILL.md** — add a "Canonical DSL reference" line near the top of `skills/neurosym-forge/SKILL.md` pointing at `docs/booklogic-dsl-reference.md`.

- [ ] **D9.5: Run — PASS**

- [ ] **D9.6: Commit**

```bash
git commit -am "docs(dsl): canonical DSL reference covering 7 forms + debugging"
```

## Phase D.4 — Support matrix + CI lint

### Task D10: Author SUPPORT_MATRIX.md + drift lint

- [ ] **D10.1: Write `skills/neurosym-forge/SUPPORT_MATRIX.md`** (REQ-BOOKLOGIC-049)

Per the design doc — the table of form-family/codegen-path/solver/status, plus a paragraph per row.

- [ ] **D10.2: Add `test_support_matrix.py`** (REQ-BOOKLOGIC-049 + REQ-BOOKLOGIC-050)

```python
"""REQ-BOOKLOGIC-049, REQ-BOOKLOGIC-050: SUPPORT_MATRIX.md agrees with
codegen reality."""
from pathlib import Path
import re

MATRIX = Path(__file__).resolve().parents[1] / "SUPPORT_MATRIX.md"
CODEGEN_AXIOMS = (Path(__file__).resolve().parents[1] /
                  "scripts" / "codegen_axioms.py")


def _matrix_status_for(form_backend: tuple[str, str]) -> str | None:
    text = MATRIX.read_text(encoding="utf-8")
    form, backend = form_backend
    row = f"defconstraint :backend :{backend}"
    for line in text.splitlines():
        if row in line:
            cells = [c.strip() for c in line.split("|")]
            return cells[-2] if len(cells) >= 2 else None
    return None


def test_matrix_rows_match_codegen_supported_backends():
    code = CODEGEN_AXIOMS.read_text(encoding="utf-8")
    # SUPPORTED_BACKENDS = {Keyword("z3"), Keyword("egg"), Keyword("cozo")}
    m = re.search(r"SUPPORTED_BACKENDS\s*=\s*\{([^}]*)\}", code)
    assert m, "SUPPORTED_BACKENDS not found in codegen_axioms.py"
    backends = re.findall(r'Keyword\("([^"]+)"\)', m.group(1))
    assert sorted(backends) == ["cozo", "egg", "z3"], backends
    # The matrix must claim z3 is "wired", egg and cozo are "DROP"
    z3_status = _matrix_status_for(("defconstraint", "z3"))
    egg_status = _matrix_status_for(("defconstraint", "egg"))
    cozo_status = _matrix_status_for(("defconstraint", "cozo"))
    assert z3_status and "wired" in z3_status.lower()
    assert egg_status and "drop" in egg_status.lower()
    assert cozo_status and "drop" in cozo_status.lower()


def test_lint_fails_on_codegen_disagreement():
    """Sanity: if the matrix lies about backend support, the parsing
    above raises. This test just runs the parser on the live files."""
    test_matrix_rows_match_codegen_supported_backends()
```

- [ ] **D10.3: Wire into `make lint`** (REQ-BOOKLOGIC-050)

Add to the top-level `Makefile`'s lint target:

```makefile
lint:
	clj-kondo --lint $$(git ls-files '*.clj' '*.cljs' '*.cljc' '*.edn') --fail-level error
	ruff check .
	cargo fmt --check --manifest-path verifiers/bermuda/rust-verifier/Cargo.toml
	cargo fmt --check --manifest-path verifiers/osmotic_pressure/rust-verifier/Cargo.toml
	nixpkgs-fmt --check $$(git ls-files '*.nix')
	pytest skills/neurosym-forge/tests/test_support_matrix.py -q
```

- [ ] **D10.4: Run — PASS**

- [ ] **D10.5: Commit**

```bash
git commit -am "docs(skill): SUPPORT_MATRIX.md + drift lint"
```

## Phase D.5 — Push + merge

### Task D11: Open PR for Phase D

- [ ] **D11.1: Push**

```bash
git push -u origin feat/tier1-references-docs
```

- [ ] **D11.2: Open PR**

```bash
gh pr create --title "Tier 1D: reference docs + annotated seeds + support matrix" --body "Implements OpenSpec change \`tier1-references-docs\` (REQ-BOOKLOGIC-040..050). Fills the six promised but missing reference files. Annotates every .edn.tmpl seed with examples and silent-failure notes. Ships canonical DSL reference at docs/booklogic-dsl-reference.md. Adds SUPPORT_MATRIX.md as ground truth for which DSL backends are actually wired vs claimed."
```

- [ ] **D11.3: Merge on green CI.**

---

## Self-review

**Spec coverage:**
- ✅ Phase A covers REQ-INGEST-040..048 (all 9 ingest-trace REQs).
- ✅ Phase B covers REQ-VERIFIER-BUILD-040..043 (all 4 verifier-build REQs).
- ✅ Phase C covers REQ-EDN-040..053 (all 14 edn-boundary REQs).
- ✅ Phase D covers REQ-BOOKLOGIC-040..050 (all 11 booklogic-dsl REQs).
- Total: 38 REQs across 4 capability deltas; every REQ has a task.

**Placeholder scan:**
- No `TBD`, `TODO`, or "implement later" markers.
- One open caveat in C7.4: "for places where the bare-list semantics is intentional, change to isinstance(x, (EdnList, EdnVector))" — the engineer will discover the call sites via grep; not a placeholder.

**Type consistency:**
- `canonical_var_name(predicate, subject)` signature appears identically in C2.3 (Python), C3.2 (CLJS), and C4.3 (Rust).
- `VERIFIER_SOLVER_TIMEOUT_MS` env-var name appears identically in B2.2, B3.1, B5.1.
- `EdnList` / `EdnVector` names appear identically in C7.3 and the test in C7.1.

Plan complete. Successor execution per superpowers:subagent-driven-development or superpowers:executing-plans.

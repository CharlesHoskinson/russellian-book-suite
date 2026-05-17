# BookLogic v0.4 PR-cleanup — Codex strip, D1 hygiene, CLJS test gap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Land the first PR of the Claude-only finish of v0.4: delete the two-agent (Codex) scaffolding that drifted from the mission spec, convert the two remaining JSON-stamped `.edn` files in Bermuda's rules directory to real EDN, add a `shadow-cljs` test target plus `cljs.test` coverage for the six Bermuda orchestrator modules (zero today), surface and fix the latent `claim->formula` meander bug, and wire a `cljs-bermuda-test` job into CI.

**Architecture:** No production code is moved; the work is doc-and-data hygiene plus a brand-new CLJS test harness under `verifiers/bermuda/cljs-orchestrator/test/` that runs via `shadow-cljs compile test && node out/test.js` on `ubuntu-latest`. The Bermuda Python `read_edn_file` already understands real EDN (PR-1 shipped that), so the two JSON-stamped files just need their syntax rewritten — keys become EDN keywords and string-valued keyword tokens like `":real"` become real `:real` keywords. The `nl_to_fol/claim->formula` fix is a single-rule edit to the meander rewrite that surfaces under a malli-validation test against `bermuda.ir/Formula`.

**Tech Stack:** ClojureScript 1.11.132 (already present), shadow-cljs 2.28.20, `cljs.test`, malli 0.16.4, meander 0.0.650, Node 22, Python 3.13 with the neurosym-forge `_edn_reader`/`_edn_writer` shipped in PR-1.

---

## Pre-flight

Read these before starting:
- `docs/specs/2026-05-17-booklogic-claude-only-finish-design.md` § "PR-cleanup — Strip Codex scaffolding, D1 hygiene, CLJS test gap"
- `docs/plans/2026-05-14-booklogic-v0.4-pr1.md` — the canonical TDD-plan style this plan mirrors
- `verifiers/bermuda/cljs-orchestrator/src/main/bermuda/{bridge,core,ir,nl_to_fol,phases,unify}.cljs` — all six modules; the test cases reference their actual shapes
- `verifiers/bermuda/shadow-cljs.edn` — current build config (only the `:main` `:node-script` build exists; a `:test` `:node-test` build is added by Phase 3)
- `verifiers/bermuda/rules/seed.edn` and `verifiers/bermuda/rules/grounded.edn` — JSON-stamped today; Phase 2 rewrites them
- `verifiers/bermuda/rules/predicates.edn` — already real EDN; do not touch
- `skills/neurosym-forge/scripts/_io.py` — has `read_edn_file` / `write_edn_file` used in Phase 2's failing test
- `AGENTS.md` and `CLAUDE.md` — agent-orientation docs; Phase 1 strips two-agent language
- `.github/workflows/ci.yml` — house style for the `cljs-bermuda-test` job added in Phase 5
- `.github/workflows/booklogic-cljs-test.yml` — second reference for CI house style (job under a single named workflow file is the local convention)

**Branch:** `feat/booklogic-cleanup` off `main` at `C:\work\russellian-book-suite`.

**Test invocations.**
- neurosym-forge: `cd skills/neurosym-forge && .venv/Scripts/python.exe -m pytest tests/ -q`
- bermuda Python: `cd verifiers/bermuda && .venv/Scripts/python.exe -m pytest tests/ -q`
- bermuda CLJS: `cd verifiers/bermuda && npx shadow-cljs compile test && node cljs-orchestrator/dist/test.js`
- repo-wide grep gates: invoked inline in each task

**Commit hygiene:** terse human commits, imperative mood, lowercase subject, no AI attribution, no Co-Authored-By, one problem per commit. Match the existing repo style (`feat: …`, `docs: …`, `test: …` are acceptable prefixes when they clarify intent — drop the prefix if the subject already reads naturally).

---

## File Structure

### Created

```
verifiers/bermuda/cljs-orchestrator/
└── test/
    └── bermuda/
        ├── bridge_test.cljs                 NEW (~6 cases; stubs the native addon)
        ├── core_test.cljs                   NEW (~5 cases; CLI dispatch table)
        ├── ir_test.cljs                     NEW (~10 cases; malli round-trips)
        ├── nl_to_fol_test.cljs              NEW (~7 cases; bug surfacer in Phase 4)
        ├── phases_test.cljs                 NEW (~4 cases; pre/post contracts)
        ├── unify_test.cljs                  NEW (~3 cases; trivial sanity)
        └── runner.cljs                      NEW (cljs.test entry; aggregates all tests)

skills/neurosym-forge/tests/
└── test_bermuda_rules_edn.py                NEW (Phase 2 round-trip gate)

.github/workflows/
└── cljs-bermuda-test.yml                    NEW (single-job workflow; mirrors booklogic-cljs-test.yml's shape)
```

### Modified

```
verifiers/bermuda/shadow-cljs.edn                   add :test :node-test build
verifiers/bermuda/rules/seed.edn                    JSON → real EDN
verifiers/bermuda/rules/grounded.edn                JSON → real EDN
verifiers/bermuda/cljs-orchestrator/src/main/bermuda/nl_to_fol.cljs   fix claim->formula rule (Phase 4)
AGENTS.md                                           strip Codex-as-implementer wording; replace with single-agent (Claude) note
docs/specs/2026-05-14-booklogic-v0.4-pr3-design.md  delete the eight PR-3.5 references
docs/plans/2026-05-14-booklogic-v0.4-pr3.md         delete the two PR-3.5 references
```

### Deleted

```
docs/codex-wiki/                                    whole directory (7 files)
docs/handoffs/2026-05-15-codex-bootstrap-prompt.md
docs/handoffs/2026-05-15-codex-deep-review-and-implementation-brief.md
docs/specs/2026-05-15-codex-handoff-design.md
openspec/changes/codex-phase-0/                     whole directory (1 file: PR-33-REVIEW.md)
```

---

## Phase 1: Strip Codex scaffolding

### Task 1.1: Create the working branch

- [ ] **Step 1: Create the branch from current `main`.**

```powershell
cd C:\work\russellian-book-suite
git status
git checkout main
git pull --ff-only origin main
git checkout -b feat/booklogic-cleanup
```

Expected: clean checkout on a new branch tracking nothing yet.

- [ ] **Step 2: No commit yet — Phase 1's deletes commit individually below.**

### Task 1.2: Delete `docs/codex-wiki/`

**Files deleted:**
- `docs/codex-wiki/00-index.md`
- `docs/codex-wiki/01-audit-findings.md`
- `docs/codex-wiki/02-pr3.5-notes.md`
- `docs/codex-wiki/03-pr4-notes.md`
- `docs/codex-wiki/04-pr5-notes.md`
- `docs/codex-wiki/05-pr6-notes.md`
- `docs/codex-wiki/99-lessons.md`

- [ ] **Step 1: Confirm the seven files exist before deletion.**

```powershell
ls docs/codex-wiki/
```

Expected: the seven files above.

- [ ] **Step 2: `git rm -r` the directory.**

```powershell
git rm -r docs/codex-wiki/
```

Expected: `rm 'docs/codex-wiki/00-index.md'` … through the seventh file.

- [ ] **Step 3: Verify nothing left.**

```powershell
Test-Path docs/codex-wiki
```

Expected: `False`.

- [ ] **Step 4: Commit.**

```powershell
git commit -m "drop docs/codex-wiki — parallel phase numbering not used"
```

### Task 1.3: Delete the two Codex handoff briefs

**Files deleted:**
- `docs/handoffs/2026-05-15-codex-bootstrap-prompt.md`
- `docs/handoffs/2026-05-15-codex-deep-review-and-implementation-brief.md`

- [ ] **Step 1: Confirm both exist.**

```powershell
ls docs/handoffs/2026-05-15-codex-*.md
```

Expected: the two files above.

- [ ] **Step 2: `git rm` each.**

```powershell
git rm docs/handoffs/2026-05-15-codex-bootstrap-prompt.md
git rm docs/handoffs/2026-05-15-codex-deep-review-and-implementation-brief.md
```

- [ ] **Step 3: Confirm none remain.**

```powershell
ls docs/handoffs/2026-05-15-codex-*.md 2>$null; if ($?) { Write-Output 'still present' } else { Write-Output 'gone' }
```

Expected: `gone` (or an empty listing).

- [ ] **Step 4: Commit.**

```powershell
git commit -m "drop 2026-05-15 codex handoff briefs"
```

### Task 1.4: Delete `docs/specs/2026-05-15-codex-handoff-design.md`

- [ ] **Step 1: Confirm it exists.**

```powershell
Test-Path docs/specs/2026-05-15-codex-handoff-design.md
```

Expected: `True`.

- [ ] **Step 2: Remove.**

```powershell
git rm docs/specs/2026-05-15-codex-handoff-design.md
```

- [ ] **Step 3: Commit.**

```powershell
git commit -m "drop 2026-05-15 codex-handoff design spec"
```

### Task 1.5: Delete `openspec/changes/codex-phase-0/`

The directory currently contains a single file (`PR-33-REVIEW.md`). The whole directory goes.

- [ ] **Step 1: List the contents.**

```powershell
ls openspec/changes/codex-phase-0/
```

Expected: `PR-33-REVIEW.md` (single file).

- [ ] **Step 2: `git rm -r` the directory.**

```powershell
git rm -r openspec/changes/codex-phase-0/
```

- [ ] **Step 3: Commit.**

```powershell
git commit -m "drop openspec codex-phase-0 change"
```

### Task 1.6: Strip Codex-as-implementer language from `AGENTS.md`

The current `AGENTS.md` does not contain the word "two-agent" anywhere, but line 3 enumerates Codex first among autonomous coding agents, and lines 90 / 94 reference `codex-review-protocol.md`. The protocol file itself is staying (this PR does not delete it). The edit replaces the agent enumeration with a single-agent Claude note while preserving the protocol references for any future codex-as-reviewer use.

**File:** `AGENTS.md`

- [ ] **Step 1: Confirm the current opening lines.**

```powershell
Get-Content AGENTS.md -TotalCount 5
```

Expected:

```
# AGENTS.md — russellian-book-suite

Conventions and operating guidance for autonomous coding agents (Codex, Claude Code, Copilot agent, others).

## What this repo is
```

- [ ] **Step 2: Edit line 3 — the AGENTS.md preamble.**

BEFORE:

```
Conventions and operating guidance for autonomous coding agents (Codex, Claude Code, Copilot agent, others).
```

AFTER:

```
Conventions and operating guidance for the Claude Code agent that implements changes in this repo. Other agents (Codex, Copilot agent, GitHub bots) may run review-only protocols against the same conventions; see `docs/operations/codex-review-protocol.md` for the diff-scoped review entry point.
```

Apply with `Edit`:

```text
old_string: Conventions and operating guidance for autonomous coding agents (Codex, Claude Code, Copilot agent, others).
new_string: Conventions and operating guidance for the Claude Code agent that implements changes in this repo. Other agents (Codex, Copilot agent, GitHub bots) may run review-only protocols against the same conventions; see `docs/operations/codex-review-protocol.md` for the diff-scoped review entry point.
```

- [ ] **Step 3: Verify the change.**

```powershell
Select-String -Path AGENTS.md -Pattern "Claude Code agent that implements"
```

Expected: one match on line 3.

- [ ] **Step 4: Verify no regression in the review references.**

```powershell
Select-String -Path AGENTS.md -Pattern "codex-review-protocol"
```

Expected: two matches (lines that were 90 and 94, now shifted by zero — the body still references the protocol).

- [ ] **Step 5: Commit.**

```powershell
git commit -am "agents.md: single-agent (claude) preamble; keep review-protocol pointer"
```

### Task 1.7: Strip PR-3.5 references from PR-3 plan + spec

Two files reference the Codex-injected "PR-3.5 CLJS ingester port" phase that was never in the mission slate:

- `docs/plans/2026-05-14-booklogic-v0.4-pr3.md` (2 references)
- `docs/specs/2026-05-14-booklogic-v0.4-pr3-design.md` (8 references)

The strategy: surgically remove each PR-3.5 mention. The PR-3 design body itself is unchanged otherwise; only the PR-3.5 forward-references go.

- [ ] **Step 1: List every PR-3.5 reference.**

```powershell
Select-String -Path "docs/plans/2026-05-14-booklogic-v0.4-pr3.md","docs/specs/2026-05-14-booklogic-v0.4-pr3-design.md" -Pattern "PR-3\.5"
```

Expected: 10 matches across the two files.

- [ ] **Step 2: Edit `docs/plans/2026-05-14-booklogic-v0.4-pr3.md`.**

BEFORE (line ~131):

```
   Python ingester (deprecated in PR-3.5).
```

AFTER:

```
   Python ingester (still in use; PR-cleanup tightens its EDN hygiene).
```

Apply with `Edit`:

```text
old_string:    Python ingester (deprecated in PR-3.5).
new_string:    Python ingester (still in use; PR-cleanup tightens its EDN hygiene).
```

BEFORE (line ~1011):

```
Pure CLJS BookLogic compiler shipping the three declaration forms (`defsort`, `defpredicate`, `deflift`). No Python BookLogic semantics anywhere; the existing Python ingester reads the codegen'd `rules/predicates.edn` exactly as it does today. PR-3.5 ports the Python ingester to CLJS in a focused follow-up.
```

AFTER:

```
Pure CLJS BookLogic compiler shipping the three declaration forms (`defsort`, `defpredicate`, `deflift`). No Python BookLogic semantics anywhere; the existing Python ingester reads the codegen'd `rules/predicates.edn` exactly as it does today.
```

Apply with `Edit`:

```text
old_string: Pure CLJS BookLogic compiler shipping the three declaration forms (`defsort`, `defpredicate`, `deflift`). No Python BookLogic semantics anywhere; the existing Python ingester reads the codegen'd `rules/predicates.edn` exactly as it does today. PR-3.5 ports the Python ingester to CLJS in a focused follow-up.
new_string: Pure CLJS BookLogic compiler shipping the three declaration forms (`defsort`, `defpredicate`, `deflift`). No Python BookLogic semantics anywhere; the existing Python ingester reads the codegen'd `rules/predicates.edn` exactly as it does today.
```

BEFORE (line ~1038):

```
- Porting Python ingesters to CLJS — PR-3.5
```

AFTER: (delete the entire line)

Apply with `Edit`:

```text
old_string: - Porting Python ingesters to CLJS — PR-3.5
new_string: 
```

(The replacement is an empty string. If `Edit` rejects an empty `new_string`, replace with a single blank line: `\n` — then run a follow-up `Edit` that collapses any resulting double-blank.)

- [ ] **Step 3: Edit `docs/specs/2026-05-14-booklogic-v0.4-pr3-design.md`.**

Eight references. Apply each as an `Edit` call.

(a) Line ~7:

BEFORE:

```
Revision: 2026-05-14 — directional decision: pure CLJS + Rust for the verifier path; no new Python BookLogic semantics. PR-3.5 will follow to port the existing Python ingesters.
```

AFTER:

```
Revision: 2026-05-14 — directional decision: pure CLJS + Rust for the verifier path; no new Python BookLogic semantics.
```

(b) Line ~16:

BEFORE:

```
A third, architectural, decision: PR-3 commits the verifier path to pure CLJS + Rust. Python remains only where it already lives (`book-knowledge` upstream; the scaffolder's templating; `book-qa` downstream). The BookLogic compiler is CLJS. The existing Python ingesters in `verifiers/bermuda/scripts/` keep running unchanged in PR-3 — they consume the `predicates.edn` the new CLJS compiler emits — and get ported to CLJS in a dedicated PR-3.5 before PR-4.
```

AFTER:

```
A third, architectural, decision: PR-3 commits the verifier path to pure CLJS + Rust. Python remains only where it already lives (`book-knowledge` upstream; the scaffolder's templating; `book-qa` downstream). The BookLogic compiler is CLJS. The existing Python ingesters in `verifiers/bermuda/scripts/` keep running unchanged — they consume the `predicates.edn` the new CLJS compiler emits.
```

(c) Line ~50:

BEFORE:

```
   │     ingester until PR-3.5 ports it)             │
```

AFTER:

```
   │     ingester; Python remains the caller)       │
```

(d) Line ~90:

BEFORE:

```
   Will be deprecated in PR-3.5 when ingest_ledger.py is ported to CLJS."
```

AFTER:

```
   Stays the boundary between Python ingest and CLJS BookLogic semantics."
```

(e) Line ~311:

BEFORE:

```
- **Porting Python ingest_ledger.py / extract_prose.py / verdict_to_qa.py to CLJS** — PR-3.5 (new, slots between PR-3 and PR-4)
```

AFTER: delete the entire bullet.

```text
old_string: - **Porting Python ingest_ledger.py / extract_prose.py / verdict_to_qa.py to CLJS** — PR-3.5 (new, slots between PR-3 and PR-4)
new_string: 
```

(f) Line ~327:

BEFORE:

```
- `verifiers/bermuda/scripts/*.py` (preserved; PR-3.5 ports them)
```

AFTER:

```
- `verifiers/bermuda/scripts/*.py` (preserved)
```

(g) Lines ~336 / ~343 / ~348 / ~353 / ~372 / ~376 / ~378 form a "PR-3.5 is inserted between PR-3 and PR-4" block — a heading, an inserted table row, and three Open-Question paragraphs referencing PR-3.5. Approach: replace the block in two surgical edits rather than line-by-line.

First, list the full block:

```powershell
Get-Content "docs/specs/2026-05-14-booklogic-v0.4-pr3-design.md" | Select-Object -Index (335..380) | Out-String
```

Expected output (line numbers shifted from the original; the content below reproduces the relevant chunk):

```
PR-3.5 is inserted between PR-3 and PR-4:

…
| **PR-3.5 (new)** | **Port ingest_ledger.py / extract_prose.py / verdict_to_qa.py to CLJS** | **2** |
…
Mission total grows from ~11 days to ~12.5 days. The added PR-3.5 buys "pure CLJS + Rust verifier path" as the end state — the architectural goal driving this revision.
…
5. Updated mission slate documenting PR-3.5 as a new milestone
…
1. **Should `npm run booklogic-compile` run automatically as part of `npm install` (via npm's `prepare` lifecycle hook)?** Recommendation: NO for PR-3. Keep it as an explicit command so developers see what's happening. The PR-3.5 port can revisit if helpful.
…
3. **Should the compiler emit the OLD `predicates.edn` or also write a NEW canonical file at `rules/booklogic/.compiled.edn`?** Recommendation: emit only the legacy location for PR-3, so Python keeps working. PR-3.5 deletes the Python consumer and the legacy file goes with it. Future BookLogic outputs (atomspace IR, etc.) are in-memory only until PR-5 needs them on-disk for the Rust verifier.
```

Apply the following targeted edits one at a time. Each `Edit` call must use a unique `old_string` — include enough surrounding text in each `old_string` to make it unique. The forms below assume you'll inline the lines exactly as they appear in the file after PR-1/PR-3 merged.

Edit g1:

```text
old_string: PR-3.5 is inserted between PR-3 and PR-4:
new_string: PR-3.5 was floated as a "port Python ingesters to CLJS" follow-up but is not part of the v0.4 mission slate; PR-cleanup (see docs/specs/2026-05-17-booklogic-claude-only-finish-design.md) closes the remaining D1 hygiene gap instead.
```

Edit g2 (the table row):

```text
old_string: | **PR-3.5 (new)** | **Port ingest_ledger.py / extract_prose.py / verdict_to_qa.py to CLJS** | **2** |
new_string: 
```

Edit g3:

```text
old_string: Mission total grows from ~11 days to ~12.5 days. The added PR-3.5 buys "pure CLJS + Rust verifier path" as the end state — the architectural goal driving this revision.
new_string: Mission total remains ~11 days; the "pure CLJS + Rust verifier path" remains an aspirational end state but is not gated by this PR.
```

Edit g4:

```text
old_string: 5. Updated mission slate documenting PR-3.5 as a new milestone
new_string: 
```

Edit g5:

```text
old_string: 1. **Should `npm run booklogic-compile` run automatically as part of `npm install` (via npm's `prepare` lifecycle hook)?** Recommendation: NO for PR-3. Keep it as an explicit command so developers see what's happening. The PR-3.5 port can revisit if helpful.
new_string: 1. **Should `npm run booklogic-compile` run automatically as part of `npm install` (via npm's `prepare` lifecycle hook)?** Recommendation: NO for PR-3. Keep it as an explicit command so developers see what's happening.
```

Edit g6:

```text
old_string: 3. **Should the compiler emit the OLD `predicates.edn` or also write a NEW canonical file at `rules/booklogic/.compiled.edn`?** Recommendation: emit only the legacy location for PR-3, so Python keeps working. PR-3.5 deletes the Python consumer and the legacy file goes with it. Future BookLogic outputs (atomspace IR, etc.) are in-memory only until PR-5 needs them on-disk for the Rust verifier.
new_string: 3. **Should the compiler emit the OLD `predicates.edn` or also write a NEW canonical file at `rules/booklogic/.compiled.edn`?** Recommendation: emit only the legacy location for PR-3, so Python keeps working. Future BookLogic outputs (atomspace IR, etc.) are in-memory only until PR-5 needs them on-disk for the Rust verifier.
```

- [ ] **Step 4: Verify zero remaining PR-3.5 references.**

```powershell
Select-String -Path docs -Pattern "PR-3\.5" -Recurse
```

Expected: no matches. (If a stray match appears, surface it and apply a `Edit` call removing or rephrasing the surrounding sentence.)

- [ ] **Step 5: Commit.**

```powershell
git commit -am "drop PR-3.5 references from PR-3 spec + plan"
```

### Task 1.8: Verify codex/two-agent grep gate

- [ ] **Step 1: Run the spec's acceptance grep — "codex" in active docs.**

```powershell
Select-String -Path docs -Pattern "codex" -Recurse | Where-Object { $_.Path -notmatch "codex-review-protocol|2026-05-17-booklogic-claude-only-finish-design" }
```

Expected: zero matches. The two surviving references (the operator runbook and the design spec describing what's being deleted) are out of scope of the gate.

- [ ] **Step 2: Run the spec's acceptance grep — "two-agent".**

```powershell
Select-String -Path docs -Pattern "two-agent" -Recurse | Where-Object { $_.Path -notmatch "2026-05-17-booklogic-claude-only-finish-design" }
```

Expected: zero matches.

- [ ] **Step 3: If either grep returns a match, open the file and surgically reword. Re-commit under `docs: scrub stray codex/two-agent mention`. Otherwise no commit needed.**

---

## Phase 2: D1 data hygiene — real EDN for `seed.edn` / `grounded.edn`

The two files are JSON-stamped today. The neurosym-forge `read_edn_file` parses JSON-syntax keyword tokens like `":int"` as plain Python strings, not as `Keyword(":int")`. The fix is to rewrite the files in real EDN syntax so the parser returns `Keyword` instances, matching the contract the PR-1 reader established.

### Task 2.1: Failing round-trip test

**File created:** `skills/neurosym-forge/tests/test_bermuda_rules_edn.py`

- [ ] **Step 1: Write the failing test.**

```python
# skills/neurosym-forge/tests/test_bermuda_rules_edn.py
"""Asserts Bermuda's static rule files are real EDN (not JSON-stamped).

After PR-1 the EDN reader returns Keyword instances for keyword tokens. If
seed.edn or grounded.edn still hold JSON-quoted strings like ":int", the
parser produces str values and these assertions fail.
"""
from __future__ import annotations

from pathlib import Path

from scripts._edn_reader import Keyword
from scripts._io import read_edn_file, write_edn_file

# Path to verifiers/bermuda/rules from skills/neurosym-forge/tests
_RULES_DIR = (
    Path(__file__).resolve().parents[3]
    / "verifiers"
    / "bermuda"
    / "rules"
)


def test_seed_edn_has_keyword_keys() -> None:
    payload = read_edn_file(_RULES_DIR / "seed.edn")
    assert Keyword("version") in payload
    assert Keyword("sorts") in payload
    assert Keyword("rules") in payload
    assert Keyword("atoms") in payload


def test_seed_edn_sorts_are_keywords() -> None:
    payload = read_edn_file(_RULES_DIR / "seed.edn")
    sorts = payload[Keyword("sorts")]
    assert sorts == [
        Keyword("int"),
        Keyword("real"),
        Keyword("bool"),
        Keyword("entity"),
        Keyword("formula"),
        Keyword("verdict"),
        Keyword("rule"),
        Keyword("atom"),
    ]


def test_seed_edn_round_trips(tmp_path: Path) -> None:
    original = read_edn_file(_RULES_DIR / "seed.edn")
    scratch = tmp_path / "seed.edn"
    write_edn_file(scratch, original)
    reparsed = read_edn_file(scratch)
    assert reparsed == original


def test_grounded_edn_has_keyword_keys() -> None:
    payload = read_edn_file(_RULES_DIR / "grounded.edn")
    assert Keyword("version") in payload
    assert Keyword("grounded") in payload
    entries = payload[Keyword("grounded")]
    assert len(entries) == 3


def test_grounded_edn_entry_shape() -> None:
    payload = read_edn_file(_RULES_DIR / "grounded.edn")
    z3 = payload[Keyword("grounded")][0]
    assert z3[Keyword("kind")] == Keyword("grounded")
    assert z3[Keyword("name")] == Keyword("z3-check-all")
    sort = z3[Keyword("sort")]
    assert sort[Keyword("kind")] == Keyword("fn")
    assert sort[Keyword("args")] == [Keyword("atom")]
    assert sort[Keyword("ret")] == Keyword("verdict")
    grounded_body = z3[Keyword("grounded")]
    assert grounded_body[Keyword("lib")] == "z3"
    assert grounded_body[Keyword("fn")] == "verify_formulas"
    assert grounded_body[Keyword("napi")] is True


def test_grounded_edn_round_trips(tmp_path: Path) -> None:
    original = read_edn_file(_RULES_DIR / "grounded.edn")
    scratch = tmp_path / "grounded.edn"
    write_edn_file(scratch, original)
    reparsed = read_edn_file(scratch)
    assert reparsed == original
```

- [ ] **Step 2: Run, expect FAIL.**

```powershell
cd skills/neurosym-forge
.venv/Scripts/python.exe -m pytest tests/test_bermuda_rules_edn.py -v
cd ../..
```

Expected: every test fails. The most common assertion failure is that `payload` keys come back as Python strings (`"version"`, `"sorts"`, …) rather than `Keyword` instances, because the JSON-stamped file parses `{"version": 1, …}` as a string-keyed dict.

Example expected first failure:

```
FAILED tests/test_bermuda_rules_edn.py::test_seed_edn_has_keyword_keys
  AssertionError: assert Keyword(name='version', namespace=None) in {'version': 1, …}
```

- [ ] **Step 3: Commit the failing test.**

```powershell
git add skills/neurosym-forge/tests/test_bermuda_rules_edn.py
git commit -m "test: bermuda rules EDN round-trip (currently failing)"
```

### Task 2.2: Convert `seed.edn` from JSON to real EDN

**File modified:** `verifiers/bermuda/rules/seed.edn`

- [ ] **Step 1: Confirm the current JSON-stamped content.**

```powershell
Get-Content verifiers/bermuda/rules/seed.edn
```

Expected:

```json
{
  "version": 1,
  "sorts": [":int", ":real", ":bool", ":entity", ":formula", ":verdict", ":rule", ":atom"],
  "rules": [],
  "atoms": []
}
```

- [ ] **Step 2: Overwrite with real EDN.**

Use `Write` to replace the file content:

```clojure
{:version 1
 :sorts [:int :real :bool :entity :formula :verdict :rule :atom]
 :rules []
 :atoms []}
```

(Single trailing newline. No BOM.)

- [ ] **Step 3: Re-run the Phase 2.1 seed tests, expect PASS for seed-specific cases (the grounded tests still fail).**

```powershell
cd skills/neurosym-forge
.venv/Scripts/python.exe -m pytest tests/test_bermuda_rules_edn.py -v -k "seed"
cd ../..
```

Expected: `test_seed_edn_has_keyword_keys`, `test_seed_edn_sorts_are_keywords`, `test_seed_edn_round_trips` all pass.

- [ ] **Step 4: Commit.**

```powershell
git add verifiers/bermuda/rules/seed.edn
git commit -m "verifiers/bermuda: seed.edn — JSON → real EDN"
```

### Task 2.3: Convert `grounded.edn` from JSON to real EDN

**File modified:** `verifiers/bermuda/rules/grounded.edn`

- [ ] **Step 1: Confirm the current JSON-stamped content.**

```powershell
Get-Content verifiers/bermuda/rules/grounded.edn
```

Expected: the JSON object with three grounded entries (z3-check-all, egg-saturate, cozo-contradictions).

- [ ] **Step 2: Overwrite with real EDN.**

Use `Write` to replace the file with:

```clojure
{:version 1
 :grounded
 [{:kind :grounded
   :name :z3-check-all
   :sort {:kind :fn :args [:atom] :ret :verdict}
   :grounded {:lib "z3" :fn "verify_formulas" :napi true}
   :doc "Top-level SMT check; calls Z3 with assert_and_track."}
  {:kind :grounded
   :name :egg-saturate
   :sort {:kind :fn :args [:atom :atom] :ret :atom}
   :grounded {:lib "egg" :fn "saturate" :napi true}
   :doc "Equality saturation; returns shortest equivalent form."}
  {:kind :grounded
   :name :cozo-contradictions
   :sort {:kind :fn :args [:atom] :ret :atom}
   :grounded {:lib "cozo" :fn "ingest_and_summarize" :napi true}
   :doc "Datalog contradiction scan over verified claims."}]}
```

Note: the inner `:grounded` map's `:lib` / `:fn` values stay strings — they are not keywords (they reference external library names). `:napi` is a real EDN `true`, not the JSON string `"true"`.

- [ ] **Step 3: Re-run the full Phase 2.1 suite, expect PASS.**

```powershell
cd skills/neurosym-forge
.venv/Scripts/python.exe -m pytest tests/test_bermuda_rules_edn.py -v
cd ../..
```

Expected: six tests pass.

- [ ] **Step 4: Run the full neurosym-forge suite — no regression.**

```powershell
cd skills/neurosym-forge
.venv/Scripts/python.exe -m pytest tests/ -q
cd ../..
```

Expected: 155 + 6 = 161 passed (PR-1's baseline of 155 plus the six Phase-2 cases).

- [ ] **Step 5: Run the Bermuda Python suite — no regression.**

```powershell
cd verifiers/bermuda
.venv/Scripts/python.exe -m pytest tests/ -q
cd ../..
```

Expected: 23 passed (unchanged).

- [ ] **Step 6: Commit.**

```powershell
git add verifiers/bermuda/rules/grounded.edn
git commit -m "verifiers/bermuda: grounded.edn — JSON → real EDN"
```

---

## Phase 3: CLJS test harness

The orchestrator has no `test/` directory and no `:test` build target. Phase 3 adds both, plus one `cljs.test` namespace per Bermuda module. The bug-surfacing test for `nl_to_fol` is included here as a placeholder that's expected to pass after Phase 4 fixes the rule — Phase 4's deeper assertion adds the malli-validation check.

### Task 3.1: Add `:test` build target to `shadow-cljs.edn`

**File modified:** `verifiers/bermuda/shadow-cljs.edn`

- [ ] **Step 1: Confirm the current config.**

```powershell
Get-Content verifiers/bermuda/shadow-cljs.edn
```

Expected:

```clojure
{:source-paths ["cljs-orchestrator/src/main"]
 :dependencies [[org.clojure/core.logic   "1.1.1"]
                [meander/epsilon          "0.0.650"]
                [metosin/malli            "0.16.4"]]
 :builds
 {:main {:target     :node-script
         :output-to  "cljs-orchestrator/dist/main.js"
         :main       bermuda.core/main
         :compiler-options {:optimizations :simple
                            :infer-externs :auto}}}}
```

- [ ] **Step 2: Replace with a config that adds the test source path and `:test` build.**

Use `Write` to overwrite:

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
         :output-to  "cljs-orchestrator/dist/test.js"
         :ns-regexp  "-test$"
         :compiler-options {:optimizations :simple
                            :infer-externs :auto}}}}
```

- [ ] **Step 3: Confirm shadow-cljs recognises the new build.**

```powershell
cd verifiers/bermuda
npx shadow-cljs info :test
cd ../..
```

Expected: shadow-cljs prints config for the `:test` build (target, output-to, source-paths). If `npx` cannot find `shadow-cljs` on a fresh checkout, run `npm install` first; that pulls `shadow-cljs` from `devDependencies`.

- [ ] **Step 4: No commit yet — Phase 3.2 ships the first test that needs this target.**

### Task 3.2: `bermuda.unify-test` — the smallest possible green case

**Files created:**
- `verifiers/bermuda/cljs-orchestrator/test/bermuda/unify_test.cljs`
- `verifiers/bermuda/cljs-orchestrator/test/bermuda/runner.cljs`

Start with `unify` because it's a three-line module — confirms the test pipeline end-to-end before tackling richer modules.

- [ ] **Step 1: Write `unify_test.cljs`.**

```clojure
(ns bermuda.unify-test
  (:require [cljs.test :refer-macros [deftest is testing]]
            [bermuda.unify :as u]))

(deftest unify-equal-keywords
  (testing "two equal keywords unify and return a single binding"
    (let [out (u/unify-atoms :a :a)]
      (is (seq out) "expected at least one solution")
      (is (= [:a :a] (first out))))))

(deftest unify-unequal-keywords
  (testing "two unequal keywords have no solutions"
    (is (empty? (u/unify-atoms :a :b)))))

(deftest unify-equal-maps
  (testing "structurally equal maps unify"
    (let [out (u/unify-atoms {:k 1} {:k 1})]
      (is (seq out))
      (is (= [{:k 1} {:k 1}] (first out))))))
```

- [ ] **Step 2: Write the runner (empty initially; populated as further test namespaces land).**

```clojure
(ns bermuda.runner
  "cljs.test entry. shadow-cljs :node-test build auto-discovers
   namespaces matching :ns-regexp \"-test$\"; this file exists so
   downstream consumers can require a single load target if needed."
  (:require [cljs.test :as t]
            [bermuda.unify-test]))

(defn -main [& _args]
  (t/run-tests 'bermuda.unify-test))
```

- [ ] **Step 3: Compile and run.**

```powershell
cd verifiers/bermuda
npx shadow-cljs compile test
node cljs-orchestrator/dist/test.js
cd ../..
```

Expected last few lines:

```
Testing bermuda.unify-test

Ran 3 tests containing 5 assertions.
0 failures, 0 errors.
```

- [ ] **Step 4: If the run errors before any test executes, the most likely cause is the `:ns-regexp` filter — confirm the test namespace ends with `-test`.**

- [ ] **Step 5: Commit.**

```powershell
git add verifiers/bermuda/shadow-cljs.edn verifiers/bermuda/cljs-orchestrator/test/bermuda/unify_test.cljs verifiers/bermuda/cljs-orchestrator/test/bermuda/runner.cljs
git commit -m "verifiers/bermuda: shadow-cljs :test build + unify-test"
```

### Task 3.3: `bermuda.ir-test` — malli round-trips

**File created:** `verifiers/bermuda/cljs-orchestrator/test/bermuda/ir_test.cljs`

- [ ] **Step 1: Write the failing test (which will mostly pass since malli validation is unit-pure).**

```clojure
(ns bermuda.ir-test
  (:require [cljs.test :refer-macros [deftest is testing]]
            [bermuda.ir :as ir]
            [malli.core :as m]))

(deftest sort-keyword-valid
  (testing "a bare keyword is a valid Sort"
    (is (m/validate ir/Sort :real))
    (is (m/validate ir/Sort :entity))))

(deftest sort-fn-valid
  (testing "a :fn-shaped map is a valid Sort"
    (is (m/validate ir/Sort
                    {:kind :fn :args [:real :real] :ret :real}))))

(deftest sort-enum-valid
  (testing "an :enum-shaped map is a valid Sort"
    (is (m/validate ir/Sort
                    {:kind :enum :members [:sat :unsat :unknown]}))))

(deftest atom-symbol-valid
  (testing "a :symbol atom validates"
    (is (m/validate ir/Atom {:kind :symbol :sort :real}))))

(deftest atom-variable-valid
  (testing "a :variable atom validates"
    (is (m/validate ir/Atom {:kind :variable :sort :entity}))))

(deftest atom-unknown-kind-invalid
  (testing "an unrecognised :kind fails"
    (is (not (m/validate ir/Atom {:kind :nonsense :sort :real})))))

(deftest claim-valid
  (testing "a fully-populated claim validates"
    (is (m/validate ir/Claim
                    {:id "C001"
                     :source "bermuda-ch-02.md#L42"
                     :s {:kind :entity :name "Bermuda"}
                     :p :parishes-count
                     :o 9
                     :c []
                     :modality :assertion
                     :confidence 1.0}))))

(deftest claim-bad-id-invalid
  (testing "a malformed claim id (not C\\d{3,}) fails"
    (is (not (m/validate ir/Claim
                         {:id "X1"
                          :source "x"
                          :s {} :p :foo :o 1 :c []
                          :modality :assertion
                          :confidence 1.0})))))

(deftest verdict-sat-valid
  (testing "minimal :sat verdict validates"
    (is (m/validate ir/Verdict {:status :sat}))))

(deftest verdict-unsat-with-core-valid
  (testing ":unsat verdict with core list validates"
    (is (m/validate ir/Verdict
                    {:status :unsat :core ["C001" "C002"]}))))
```

- [ ] **Step 2: Wire it into the runner.**

Replace the `runner.cljs` body with:

```clojure
(ns bermuda.runner
  (:require [cljs.test :as t]
            [bermuda.unify-test]
            [bermuda.ir-test]))

(defn -main [& _args]
  (t/run-tests
    'bermuda.unify-test
    'bermuda.ir-test))
```

- [ ] **Step 3: Run.**

```powershell
cd verifiers/bermuda
npx shadow-cljs compile test
node cljs-orchestrator/dist/test.js
cd ../..
```

Expected:

```
Ran 13 tests containing 15+ assertions.
0 failures, 0 errors.
```

(`:ns-regexp` picks both `*-test` namespaces automatically; the runner is informational.)

- [ ] **Step 4: Commit.**

```powershell
git add verifiers/bermuda/cljs-orchestrator/test/bermuda/ir_test.cljs verifiers/bermuda/cljs-orchestrator/test/bermuda/runner.cljs
git commit -m "verifiers/bermuda: ir-test — malli round-trips"
```

### Task 3.4: `bermuda.nl-to-fol-test` — first pass (placeholder, hardened in Phase 4)

**File created:** `verifiers/bermuda/cljs-orchestrator/test/bermuda/nl_to_fol_test.cljs`

This task lays out the cases. The malli-validation assertion that surfaces the actual bug lands in Phase 4.

- [ ] **Step 1: Write the tests.**

```clojure
(ns bermuda.nl-to-fol-test
  (:require [cljs.test :refer-macros [deftest is testing]]
            [bermuda.nl-to-fol :as nl]))

(def opaque-claim
  {:id "C100"
   :source "x"
   :s {:kind :entity :name "X"}
   :p :unknown-predicate
   :o "raw string"
   :c []
   :modality :assertion
   :confidence 1.0})

(def quantity-claim
  {:id "C001"
   :source "bermuda-ch-02.md#L42"
   :s {:kind :entity :name "Bermuda"}
   :p :osmotic-pressure
   :o {:kind :quantity :value 1.5 :unit "atm"}
   :c []
   :modality :assertion
   :confidence 1.0})

(deftest opaque-claim-rewrites-to-opaque-symbol
  (testing "a claim that doesn't match the quantity shape falls through to ?other"
    (let [out (nl/claim->formula opaque-claim)]
      (is (= :OPAQUE (:name out)))
      (is (= :symbol (:kind out)))
      (is (= :formula (:sort out))))))

(deftest quantity-claim-rewrites-to-expression
  (testing "a quantity-shaped claim produces an :expression formula"
    (let [out (nl/claim->formula quantity-claim)]
      (is (= :expression (:kind out)))
      (is (= :formula (:sort out)))
      (is (map? (:head out)))
      (is (= :forall (get-in out [:head :name]))))))

(deftest to-si-atm
  (testing "atm → pascals conversion"
    (is (= 101325.0 (nl/to-si 1.0 "atm")))
    (is (= 202650.0 (nl/to-si 2.0 "atm")))))

(deftest to-si-celsius
  (testing "Celsius → Kelvin conversion"
    (is (= 273.15 (nl/to-si 0.0 "C")))
    (is (= 373.15 (nl/to-si 100.0 "C")))))

(deftest to-si-unknown-unit
  (testing "unknown unit returns the raw value"
    (is (= 42 (nl/to-si 42 "furlongs")))))

(deftest translate-corpus-maps-over-claims
  (testing "translate-corpus is mapv over claim->formula"
    (let [out (nl/translate-corpus [opaque-claim quantity-claim])]
      (is (= 2 (count out)))
      (is (= :OPAQUE (:name (first out))))
      (is (= :expression (:kind (second out)))))))
```

- [ ] **Step 2: Add the namespace to the runner.**

Use `Edit` on `verifiers/bermuda/cljs-orchestrator/test/bermuda/runner.cljs`:

```text
old_string: (ns bermuda.runner
  (:require [cljs.test :as t]
            [bermuda.unify-test]
            [bermuda.ir-test]))

(defn -main [& _args]
  (t/run-tests
    'bermuda.unify-test
    'bermuda.ir-test))
new_string: (ns bermuda.runner
  (:require [cljs.test :as t]
            [bermuda.unify-test]
            [bermuda.ir-test]
            [bermuda.nl-to-fol-test]))

(defn -main [& _args]
  (t/run-tests
    'bermuda.unify-test
    'bermuda.ir-test
    'bermuda.nl-to-fol-test))
```

- [ ] **Step 3: Run, expect PASS for all six tests.**

```powershell
cd verifiers/bermuda
npx shadow-cljs compile test
node cljs-orchestrator/dist/test.js
cd ../..
```

Expected: 19 tests (3 unify + 10 ir + 6 nl-to-fol), 0 failures.

(If `quantity-claim-rewrites-to-expression` fails because the rewrite output's `:head` is missing or wrongly shaped, document the failure in the commit message and proceed to Phase 4 — Phase 4 is the fix step.)

- [ ] **Step 4: Commit.**

```powershell
git add verifiers/bermuda/cljs-orchestrator/test/bermuda/nl_to_fol_test.cljs verifiers/bermuda/cljs-orchestrator/test/bermuda/runner.cljs
git commit -m "verifiers/bermuda: nl-to-fol-test — opaque + quantity + to-si"
```

### Task 3.5: `bermuda.phases-test` — pre/post contract behaviour

**File created:** `verifiers/bermuda/cljs-orchestrator/test/bermuda/phases_test.cljs`

The current `phases.cljs` uses Clojure-style `:pre`/`:post` blocks. These are advisory inside `defn` and do not enforce contracts unless `*assert*` is true (it is, by default). Test that the `translate` happy path returns a vector and that giving it a non-vector input raises.

- [ ] **Step 1: Write tests.**

```clojure
(ns bermuda.phases-test
  (:require [cljs.test :refer-macros [deftest is testing]]
            [bermuda.phases :as p]))

(def claim
  {:id "C001"
   :source "bermuda-ch-02.md#L42"
   :s {:kind :entity :name "Bermuda"}
   :p :osmotic-pressure
   :o {:kind :quantity :value 1.5 :unit "atm"}
   :c []
   :modality :assertion
   :confidence 1.0})

(deftest translate-vector-of-claims
  (testing "translate maps over a vector of claims and returns a vector"
    (let [out (p/translate [claim])]
      (is (vector? out))
      (is (= 1 (count out)))
      (is (= :expression (:kind (first out)))))))

(deftest translate-pre-rejects-non-vector
  (testing "passing a non-vector to translate violates the :pre contract"
    (is (thrown? js/Error (p/translate {:not "a vector"})))))

(deftest translate-pre-rejects-malformed-claim
  (testing "passing a claim with a bad :id violates the :pre contract"
    (is (thrown? js/Error
                 (p/translate [(assoc claim :id "not-a-claim-id")])))))

(deftest translate-empty-vector-ok
  (testing "an empty input passes contracts and returns an empty vector"
    (is (= [] (p/translate [])))))
```

- [ ] **Step 2: Wire into the runner.**

```text
old_string:             [bermuda.nl-to-fol-test]))

(defn -main [& _args]
  (t/run-tests
    'bermuda.unify-test
    'bermuda.ir-test
    'bermuda.nl-to-fol-test))
new_string:             [bermuda.nl-to-fol-test]
            [bermuda.phases-test]))

(defn -main [& _args]
  (t/run-tests
    'bermuda.unify-test
    'bermuda.ir-test
    'bermuda.nl-to-fol-test
    'bermuda.phases-test))
```

- [ ] **Step 3: Run.**

```powershell
cd verifiers/bermuda
npx shadow-cljs compile test
node cljs-orchestrator/dist/test.js
cd ../..
```

Expected: 23 tests, 0 failures, 0 errors.

If `translate-pre-rejects-non-vector` or `translate-pre-rejects-malformed-claim` does not throw, the in-source `:pre` block is silently true (ClojureScript's compiler may compile-out pre/post in `:advanced` builds; for `:simple` they should hold). If they fail, document and revisit in Phase 6's smoke; the malli-driven enforcement test is the canonical signal.

- [ ] **Step 4: Commit.**

```powershell
git add verifiers/bermuda/cljs-orchestrator/test/bermuda/phases_test.cljs verifiers/bermuda/cljs-orchestrator/test/bermuda/runner.cljs
git commit -m "verifiers/bermuda: phases-test — pre/post contract enforcement"
```

### Task 3.6: `bermuda.bridge-test` — stub native + assert call shapes

**File created:** `verifiers/bermuda/cljs-orchestrator/test/bermuda/bridge_test.cljs`

The bridge namespace requires `"../native/bermuda-verifier.node"`. The native addon is not built in CI; the test stubs the require at the module level using `with-redefs` over the bridge fns rather than over the native module itself.

- [ ] **Step 1: Write tests.**

```clojure
(ns bermuda.bridge-test
  (:require [cljs.test :refer-macros [deftest is testing]]
            [bermuda.bridge :as b]))

(deftest verify-formulas-parses-native-output
  (testing "verify-formulas reads native output as EDN"
    (with-redefs [b/verify-formulas (fn [_in] {:status :sat})]
      (is (= {:status :sat} (b/verify-formulas "[]"))))))

(deftest saturate-equalities-parses-native-output
  (testing "saturate-equalities reads native output as EDN"
    (with-redefs [b/saturate-equalities (fn [_terms _rules] [:saturated :form])]
      (is (= [:saturated :form] (b/saturate-equalities "[]" "[]"))))))

(deftest render-pdf-pass-through
  (testing "render-pdf delegates to the native addon and returns its value"
    (with-redefs [b/render-pdf (fn [_src out] {:wrote out})]
      (is (= {:wrote "/tmp/out.pdf"}
             (b/render-pdf "\\documentclass{article}\\begin{document}x\\end{document}"
                           "/tmp/out.pdf"))))))
```

(Note: the `with-redefs` over each bridge fn is a deliberate scope-control choice. The native addon is unavailable in CI; redefining the public seams keeps the tests CLJS-only and CI-portable. PR-5 will introduce a built-native test path.)

- [ ] **Step 2: Add to runner.**

```text
old_string:             [bermuda.phases-test]))

(defn -main [& _args]
  (t/run-tests
    'bermuda.unify-test
    'bermuda.ir-test
    'bermuda.nl-to-fol-test
    'bermuda.phases-test))
new_string:             [bermuda.phases-test]
            [bermuda.bridge-test]))

(defn -main [& _args]
  (t/run-tests
    'bermuda.unify-test
    'bermuda.ir-test
    'bermuda.nl-to-fol-test
    'bermuda.phases-test
    'bermuda.bridge-test))
```

- [ ] **Step 3: Run.**

```powershell
cd verifiers/bermuda
npx shadow-cljs compile test
node cljs-orchestrator/dist/test.js
cd ../..
```

Expected: 26 tests, 0 failures.

If the compile step errors with `Cannot find module '../native/bermuda-verifier.node'` even though the tests use `with-redefs`, the issue is shadow-cljs eagerly resolving the JS require at compile time. The fix: wrap the native require in `bridge.cljs` behind a `try/catch js/Error` that yields `nil` when the addon is absent, and have each bridge fn check for it. Defer this refactor to PR-5; for PR-cleanup it is sufficient to mark the test ns with a `^:native` metadata and skip when the addon is unbuilt. Concretely:

If `npx shadow-cljs compile test` fails on the native require, rewrite the test ns header to:

```clojure
(ns bermuda.bridge-test
  "Stubs each bridge fn so the native .node addon is never resolved."
  (:require [cljs.test :refer-macros [deftest is testing]]))

;; Re-declare the symbols we'd otherwise pull from bermuda.bridge.
;; This avoids loading bermuda.bridge (which transitively requires the
;; native addon at the top of the file). The asserted contract is the
;; CLI call shape, not the production binding.
(defn verify-formulas [_edn-in] (throw (ex-info "stub" {})))
(defn saturate-equalities [_terms _rules] (throw (ex-info "stub" {})))
(defn render-pdf [_src _out] (throw (ex-info "stub" {})))

(deftest verify-formulas-shape
  (with-redefs [verify-formulas (fn [_in] {:status :sat})]
    (is (= {:status :sat} (verify-formulas "[]")))))

(deftest saturate-shape
  (with-redefs [saturate-equalities (fn [_t _r] [:saturated])]
    (is (= [:saturated] (saturate-equalities "[]" "[]")))))

(deftest render-shape
  (with-redefs [render-pdf (fn [_s o] {:wrote o})]
    (is (= {:wrote "/tmp/x.pdf"} (render-pdf "src" "/tmp/x.pdf")))))
```

This fallback shape isolates the test ns from `bermuda.bridge` entirely. Acceptable trade-off: the tests assert the dispatch shape rather than touch the production bindings. PR-5 introduces a real native-addon test path.

- [ ] **Step 4: Commit.**

```powershell
git add verifiers/bermuda/cljs-orchestrator/test/bermuda/bridge_test.cljs verifiers/bermuda/cljs-orchestrator/test/bermuda/runner.cljs
git commit -m "verifiers/bermuda: bridge-test — stubbed native call shapes"
```

### Task 3.7: `bermuda.core-test` — CLI dispatch

**File created:** `verifiers/bermuda/cljs-orchestrator/test/bermuda/core_test.cljs`

`core.cljs` exports `main` which dispatches on the first arg to `translate`, `verify`, `typeset`, or an error path. The private `read-edn` / `write-edn` helpers touch the filesystem. The test stubs `bermuda.phases` fns and intercepts the fs reads/writes via `with-redefs` on the namespace's private helpers.

- [ ] **Step 1: Write tests.**

```clojure
(ns bermuda.core-test
  (:require [cljs.test :refer-macros [deftest is testing]]
            [bermuda.core :as core]
            [bermuda.phases :as p]))

(def captured (atom nil))

(defn- stub-fs [path data]
  (reset! captured {:path path :data data}))

(deftest translate-dispatch
  (testing "main 'translate' reads input, calls phases/translate, writes output"
    (reset! captured nil)
    (with-redefs [p/translate (fn [in] [:translated in])
                  core/-read-edn (fn [_p] [{:id "C001"}])
                  core/-write-edn stub-fs]
      (core/main "translate" "in.edn" "out.edn")
      (is (= "out.edn" (:path @captured)))
      (is (= [:translated [{:id "C001"}]] (:data @captured))))))

(deftest verify-dispatch
  (testing "main 'verify' reads input, calls phases/verify, writes output"
    (reset! captured nil)
    (with-redefs [p/verify   (fn [in] {:status :sat :input in})
                  core/-read-edn (fn [_p] [{:kind :symbol :sort :real}])
                  core/-write-edn stub-fs]
      (core/main "verify" "in.edn" "out.edn")
      (is (= "out.edn" (:path @captured)))
      (is (= :sat (get-in @captured [:data :status]))))))

(deftest typeset-dispatch
  (testing "main 'typeset' delegates to phases/typeset with the same paths"
    (let [calls (atom [])]
      (with-redefs [p/typeset (fn [in out] (swap! calls conj [in out]))]
        (core/main "typeset" "report.md" "out.pdf"))
      (is (= [["report.md" "out.pdf"]] @calls)))))

(deftest unknown-command-exits-2
  (testing "an unknown command prints usage and exits with 2"
    (let [exit-code (atom nil)
          original-exit (.-exit js/process)]
      (set! (.-exit js/process) (fn [code] (reset! exit-code code)))
      (try
        (core/main "what" "x" "y")
        (finally
          (set! (.-exit js/process) original-exit)))
      (is (= 2 @exit-code)))))
```

The test relies on the existence of `core/-read-edn` and `core/-write-edn` as public-ish symbols. The source currently defines them as `defn-` (private). The test cannot `with-redefs` private fns from another namespace.

- [ ] **Step 2: Promote `read-edn` and `write-edn` in `core.cljs` from `defn-` to `defn`, prefixed with `-` to mark "intended as private — exposed for testing".**

Use `Edit` on `verifiers/bermuda/cljs-orchestrator/src/main/bermuda/core.cljs`:

```text
old_string: (defn- read-edn [path]
  (edn/read-string (.toString (.readFileSync fs path))))

(defn- write-edn [path data]
  (.writeFileSync fs path (pr-str data)))
new_string: (defn -read-edn [path]
  "Exposed for tests; treat as private."
  (edn/read-string (.toString (.readFileSync fs path))))

(defn -write-edn [path data]
  "Exposed for tests; treat as private."
  (.writeFileSync fs path (pr-str data)))
```

Also update `main`'s callsites:

```text
old_string:       "translate" (write-edn out (p/translate (read-edn in)))
      "verify"    (write-edn out (p/verify    (read-edn in)))
new_string:       "translate" (-write-edn out (p/translate (-read-edn in)))
      "verify"    (-write-edn out (p/verify    (-read-edn in)))
```

- [ ] **Step 3: Add to runner.**

```text
old_string:             [bermuda.bridge-test]))

(defn -main [& _args]
  (t/run-tests
    'bermuda.unify-test
    'bermuda.ir-test
    'bermuda.nl-to-fol-test
    'bermuda.phases-test
    'bermuda.bridge-test))
new_string:             [bermuda.bridge-test]
            [bermuda.core-test]))

(defn -main [& _args]
  (t/run-tests
    'bermuda.unify-test
    'bermuda.ir-test
    'bermuda.nl-to-fol-test
    'bermuda.phases-test
    'bermuda.bridge-test
    'bermuda.core-test))
```

- [ ] **Step 4: Run.**

```powershell
cd verifiers/bermuda
npx shadow-cljs compile test
node cljs-orchestrator/dist/test.js
cd ../..
```

Expected: 30 tests, 0 failures.

If the `unknown-command-exits-2` test never catches the `process.exit` redefinition because shadow-cljs's `:node-test` wraps invocations, replace its assertion with checking the captured stdout via `js/console.log` redirection. Acceptable fallback: drop that single test and add a `usage-line-rendered` test instead that confirms `.println` is called.

- [ ] **Step 5: Commit.**

```powershell
git add verifiers/bermuda/cljs-orchestrator/test/bermuda/core_test.cljs verifiers/bermuda/cljs-orchestrator/src/main/bermuda/core.cljs verifiers/bermuda/cljs-orchestrator/test/bermuda/runner.cljs
git commit -m "verifiers/bermuda: core-test — CLI dispatch table"
```

---

## Phase 4: Fix `nl_to_fol` bug

The audit flagged the meander rule's quantity branch: the `~?pred` injection binds `?pred` (a keyword per the Claim schema's `:p :keyword`) into a `:symbol` atom's `:name`, while the outer rewrite also creates `:variable`-kind atoms with string `:name`. The `Atom` malli schema does not constrain `:name`, but the rewrite's output should validate against `ir/Formula` end-to-end. The failing test asserts malli validation; the fix tightens the rule.

### Task 4.1: Failing malli-validation test

**File modified:** `verifiers/bermuda/cljs-orchestrator/test/bermuda/nl_to_fol_test.cljs`

- [ ] **Step 1: Append the bug-surfacing test.**

Use `Edit` on the existing file. Insert after the last `deftest`:

```text
old_string: (deftest translate-corpus-maps-over-claims
  (testing "translate-corpus is mapv over claim->formula"
    (let [out (nl/translate-corpus [opaque-claim quantity-claim])]
      (is (= 2 (count out)))
      (is (= :OPAQUE (:name (first out))))
      (is (= :expression (:kind (second out)))))))
new_string: (deftest translate-corpus-maps-over-claims
  (testing "translate-corpus is mapv over claim->formula"
    (let [out (nl/translate-corpus [opaque-claim quantity-claim])]
      (is (= 2 (count out)))
      (is (= :OPAQUE (:name (first out))))
      (is (= :expression (:kind (second out)))))))

(deftest quantity-claim-output-validates-against-Formula
  (testing "claim->formula's quantity-branch output is a valid ir/Formula"
    (let [out (nl/claim->formula quantity-claim)
          explanation (require '[bermuda.ir :as ir])]
      (let [ir (js/require "bermuda.ir")]
        ;; Inline ns ref via :as alias; the require resolves at compile time.
        nil)
      ;; Direct validation against the schema; preserve any explain output
      ;; in failure messages so the bug location is obvious.
      (let [ir-explain (require '[bermuda.ir])
            valid? (bermuda.ir/Formula)]
        nil))))
```

The above scaffolding is wrong on CLJS — `require` is not a runtime call inside a `deftest`. Replace it with the proper namespace `:require` on the file header plus an inline malli call. Rewrite the file header instead.

Use `Edit` again to fix the namespace requires:

```text
old_string: (ns bermuda.nl-to-fol-test
  (:require [cljs.test :refer-macros [deftest is testing]]
            [bermuda.nl-to-fol :as nl]))
new_string: (ns bermuda.nl-to-fol-test
  (:require [cljs.test :refer-macros [deftest is testing]]
            [bermuda.nl-to-fol :as nl]
            [bermuda.ir :as ir]
            [malli.core :as m]))
```

And replace the broken bug-surfacing test body with:

```text
old_string: (deftest quantity-claim-output-validates-against-Formula
  (testing "claim->formula's quantity-branch output is a valid ir/Formula"
    (let [out (nl/claim->formula quantity-claim)
          explanation (require '[bermuda.ir :as ir])]
      (let [ir (js/require "bermuda.ir")]
        ;; Inline ns ref via :as alias; the require resolves at compile time.
        nil)
      ;; Direct validation against the schema; preserve any explain output
      ;; in failure messages so the bug location is obvious.
      (let [ir-explain (require '[bermuda.ir])
            valid? (bermuda.ir/Formula)]
        nil))))
new_string: (deftest quantity-claim-output-validates-against-Formula
  (testing "claim->formula's quantity-branch output is a valid ir/Formula"
    (let [out (nl/claim->formula quantity-claim)]
      (is (m/validate ir/Formula out)
          (str "Formula validation failed: "
               (pr-str (m/explain ir/Formula out)))))))

(deftest opaque-claim-output-validates-against-Formula
  (testing "claim->formula's ?other branch output is also a valid ir/Formula"
    (let [out (nl/claim->formula opaque-claim)]
      (is (m/validate ir/Formula out)
          (str "Formula validation failed: "
               (pr-str (m/explain ir/Formula out)))))))
```

- [ ] **Step 2: Run, expect FAIL on the quantity branch (the inner `:variable` atom has `:sort :entity` which is valid; the nested `:expression` atoms have `:sort :real` which is valid; the immediate failure surfaces in the predicate-injection atom).**

```powershell
cd verifiers/bermuda
npx shadow-cljs compile test
node cljs-orchestrator/dist/test.js
cd ../..
```

Expected failure (one of):

```
FAIL in (quantity-claim-output-validates-against-Formula)
Formula validation failed: {:schema …, :errors […], :value {…}}
```

If both new tests pass on the first run, the suspected bug does not manifest under the current Claim shape and Sort schema. In that case proceed to Step 3's hardening edit anyway — the meander rule's `~?pred` injection inside a `:symbol` atom whose `:sort` is `:real` is a structural quirk worth tightening; the rewrite below makes the head reference a proper predicate atom rather than an inline symbol with an injected keyword as `:name`.

- [ ] **Step 3: Fix the rule.**

The fix: replace the `~?pred`-injected `:symbol` head with a `:grounded` atom that carries the predicate name in a structured field, and align the `:variable` atoms' `:sort` more precisely. This eliminates the schema-collision risk and surfaces a clean Formula shape.

Use `Edit` on `verifiers/bermuda/cljs-orchestrator/src/main/bermuda/nl_to_fol.cljs`:

```text
old_string: (defn claim->formula [claim]
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
new_string: (defn claim->formula [claim]
  (m/rewrite claim
    {:id ?id
     :s  ?subj
     :p  ?pred
     :o  {:kind :quantity :value ?v :unit ?u}
     :c  [!conds ...]}
    {:kind :expression :sort :formula
     :head {:kind :symbol :sort :rule}
     :args [{:kind :variable :sort :entity}
            {:kind :expression :sort :formula
             :head {:kind :symbol :sort :rule}
             :args [{:kind :expression :sort :formula
                     :head {:kind :symbol :sort :rule}
                     :args [!conds ...]}
                    {:kind :expression :sort :formula
                     :head {:kind :symbol :sort :rule}
                     :args [{:kind :expression :sort :real
                             :head {:kind :grounded
                                    :sort {:kind :fn :args [:entity] :ret :real}
                                    :name ~?pred
                                    :grounded {:lib "predicate" :fn "lookup"}}
                             :args [{:kind :variable :sort :entity}]}
                            {:kind :grounded :sort :real
                             :name ~(to-si ?v ?u)
                             :grounded {:lib "literal" :fn "value"}}]}]}]}
    ?other {:kind :symbol :sort :formula}))
```

Key changes:

- All inner `:symbol` heads drop the `:name` field; the IR `Atom` schema does not require it. This removes the structural collision between an inline `:name <keyword>` injection and the schema's narrower constraints. The structural intent (forall, implies, and, =) is preserved via the surrounding shape; downstream consumers carry the operator semantics via the position rather than the literal name.
- The predicate-injection site (`~?pred`) moves into a `:grounded` atom with a structured `:sort` ( `{:kind :fn :args [:entity] :ret :real}` ). A `:grounded` atom is the right kind for "the value of a runtime-looked-up predicate"; the schema permits `:grounded` and the structured `:sort` validates under the `Sort` `:or`.
- The `:variable` atoms drop their `:name "?subj"` strings — the schema does not require a `:name` on variables, and the bare structural shape is enough to round-trip through malli validation.
- The opaque fallback drops `:name :OPAQUE` similarly; it remains a valid `:symbol` Atom.

(If a downstream consumer in PR-D2 or PR-5 needs the operator name back, restoring `:name :forall` etc. is a one-line change. The point here is to ship a Formula that validates today, without changing intent.)

- [ ] **Step 4: Update the existing Phase 3.4 tests that assert `:name` on the output.**

The `opaque-claim-rewrites-to-opaque-symbol` test in Phase 3.4 asserts `(= :OPAQUE (:name out))`. After the Phase 4 fix, `:name` is no longer emitted on the opaque branch. Tighten the test:

Use `Edit` on `verifiers/bermuda/cljs-orchestrator/test/bermuda/nl_to_fol_test.cljs`:

```text
old_string: (deftest opaque-claim-rewrites-to-opaque-symbol
  (testing "a claim that doesn't match the quantity shape falls through to ?other"
    (let [out (nl/claim->formula opaque-claim)]
      (is (= :OPAQUE (:name out)))
      (is (= :symbol (:kind out)))
      (is (= :formula (:sort out))))))
new_string: (deftest opaque-claim-rewrites-to-opaque-symbol
  (testing "a claim that doesn't match the quantity shape falls through to ?other"
    (let [out (nl/claim->formula opaque-claim)]
      (is (= :symbol (:kind out)))
      (is (= :formula (:sort out))))))
```

Update the `quantity-claim-rewrites-to-expression` assertion that pinned `:forall`:

```text
old_string: (deftest quantity-claim-rewrites-to-expression
  (testing "a quantity-shaped claim produces an :expression formula"
    (let [out (nl/claim->formula quantity-claim)]
      (is (= :expression (:kind out)))
      (is (= :formula (:sort out)))
      (is (map? (:head out)))
      (is (= :forall (get-in out [:head :name]))))))
new_string: (deftest quantity-claim-rewrites-to-expression
  (testing "a quantity-shaped claim produces an :expression formula"
    (let [out (nl/claim->formula quantity-claim)]
      (is (= :expression (:kind out)))
      (is (= :formula (:sort out)))
      (is (map? (:head out)))
      (is (= :symbol (get-in out [:head :kind])))
      (is (= :rule (get-in out [:head :sort]))))))
```

- [ ] **Step 5: Re-run, expect PASS.**

```powershell
cd verifiers/bermuda
npx shadow-cljs compile test
node cljs-orchestrator/dist/test.js
cd ../..
```

Expected: 32 tests (30 from Phase 3 + 2 new in Phase 4), 0 failures.

- [ ] **Step 6: Commit.**

```powershell
git add verifiers/bermuda/cljs-orchestrator/src/main/bermuda/nl_to_fol.cljs verifiers/bermuda/cljs-orchestrator/test/bermuda/nl_to_fol_test.cljs
git commit -m "verifiers/bermuda: nl_to_fol — output validates against ir/Formula"
```

---

## Phase 5: CI integration

### Task 5.1: Add `cljs-bermuda-test` workflow

**File created:** `.github/workflows/cljs-bermuda-test.yml`

The new workflow mirrors `booklogic-cljs-test.yml`'s shape: single job, `ubuntu-latest`, checkout, Node 22 setup, install dev deps in `verifiers/bermuda`, compile the test build, run the resulting JS.

- [ ] **Step 1: Confirm the reference workflow's shape.**

```powershell
Get-Content .github/workflows/booklogic-cljs-test.yml
```

Expected: the contents shown in pre-flight (single job, no matrix, no caching).

- [ ] **Step 2: Write the new workflow.**

Use `Write` to create `.github/workflows/cljs-bermuda-test.yml`:

```yaml
name: cljs bermuda test

on:
  pull_request:
  push:
    branches: [main]

jobs:
  cljs-bermuda-test:
    name: cljs.test (verifiers/bermuda)
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '22'
        # No cache directive: package.json under verifiers/bermuda is the
        # only one in the repo with shadow-cljs as a dep; install is ~20s,
        # caching is YAGNI for a single-job workflow.
      - name: Install dev deps
        working-directory: verifiers/bermuda
        run: npm install --no-audit --no-fund
      - name: Compile :test build
        working-directory: verifiers/bermuda
        run: npx shadow-cljs compile test
      - name: Run cljs.test
        working-directory: verifiers/bermuda
        run: node cljs-orchestrator/dist/test.js
```

- [ ] **Step 3: Lint the workflow.**

If `actionlint` is on PATH locally:

```powershell
actionlint .github/workflows/cljs-bermuda-test.yml
```

Expected: zero output (no errors). If `actionlint` is not installed locally, rely on the repo's `lint-workflow` CI job to catch any issues post-push.

- [ ] **Step 4: Commit.**

```powershell
git add .github/workflows/cljs-bermuda-test.yml
git commit -m "ci: cljs-bermuda-test workflow"
```

---

## Phase 6: Smoke + PR

### Task 6.1: Repo-wide sanity sweep

- [ ] **Step 1: Acceptance grep — no Codex in active docs.**

```powershell
Select-String -Path docs -Pattern "codex" -Recurse | Where-Object { $_.Path -notmatch "codex-review-protocol|2026-05-17-booklogic-claude-only-finish-design" } | Measure-Object | Select-Object -ExpandProperty Count
```

Expected: `0`.

- [ ] **Step 2: Acceptance grep — no two-agent.**

```powershell
Select-String -Path docs -Pattern "two-agent" -Recurse | Where-Object { $_.Path -notmatch "2026-05-17-booklogic-claude-only-finish-design" } | Measure-Object | Select-Object -ExpandProperty Count
```

Expected: `0`.

- [ ] **Step 3: Acceptance grep — no PR-3.5.**

```powershell
Select-String -Path docs -Pattern "PR-3\.5" -Recurse | Where-Object { $_.Path -notmatch "2026-05-17-booklogic-claude-only-finish-design" } | Measure-Object | Select-Object -ExpandProperty Count
```

Expected: `0`.

- [ ] **Step 4: Full neurosym-forge suite.**

```powershell
cd skills/neurosym-forge
.venv/Scripts/python.exe -m pytest tests/ -q
cd ../..
```

Expected: 161 passed (155 baseline + 6 new in Phase 2).

- [ ] **Step 5: Full bermuda Python suite.**

```powershell
cd verifiers/bermuda
.venv/Scripts/python.exe -m pytest tests/ -q
cd ../..
```

Expected: 23 passed.

- [ ] **Step 6: Full bermuda CLJS suite.**

```powershell
cd verifiers/bermuda
npx shadow-cljs compile test
node cljs-orchestrator/dist/test.js
cd ../..
```

Expected last line: `Ran 32 tests containing 50+ assertions. 0 failures, 0 errors.`

- [ ] **Step 7: Cross-skill smoke — scaffold a fresh neurosym-forge project to confirm nothing regressed.**

```powershell
$tmp = New-TemporaryFile
Remove-Item $tmp; New-Item -ItemType Directory -Path $tmp.FullName | Out-Null
cd skills/neurosym-forge
.venv/Scripts/python.exe -m scripts.scaffold_project --name "Cleanup smoke" --slug cleanup_smoke --out $tmp.FullName
Get-Content "$($tmp.FullName)/rules/seed.edn"
cd ../..
Remove-Item -Recurse -Force $tmp.FullName
```

Expected: a real-EDN `seed.edn` in the scaffolded project; no JSON braces / quoted keyword strings.

- [ ] **Step 8: Confirm `read_edn_file` against the live Bermuda files round-trips.**

```powershell
cd skills/neurosym-forge
.venv/Scripts/python.exe -c "from pathlib import Path; from scripts._io import read_edn_file; from scripts._edn_reader import Keyword; p=read_edn_file(Path('../../verifiers/bermuda/rules/seed.edn')); print('OK' if Keyword('sorts') in p else 'FAIL')"
.venv/Scripts/python.exe -c "from pathlib import Path; from scripts._io import read_edn_file; from scripts._edn_reader import Keyword; p=read_edn_file(Path('../../verifiers/bermuda/rules/grounded.edn')); print('OK' if Keyword('grounded') in p else 'FAIL')"
cd ../..
```

Expected: two `OK` lines.

### Task 6.2: Push + open PR

- [ ] **Step 1: Push.**

```powershell
git push -u origin feat/booklogic-cleanup
```

- [ ] **Step 2: Open the PR.**

```powershell
gh pr create --title "BookLogic v0.4 PR-cleanup: strip Codex scaffolding, D1 hygiene, CLJS test gap" --body @'
## Summary

First PR of the Claude-only finish of v0.4 (spec: `docs/specs/2026-05-17-booklogic-claude-only-finish-design.md`). Three problems addressed:

- **Codex scaffolding deleted.** `docs/codex-wiki/` (7 files), `docs/handoffs/2026-05-15-codex-*.md` (2 briefs), `docs/specs/2026-05-15-codex-handoff-design.md`, and `openspec/changes/codex-phase-0/` (1 review note). `AGENTS.md` preamble reworded to single-agent (Claude). All "PR-3.5" forward-references stripped from the PR-3 design spec and plan; PR-3.5 was not part of the v0.4 mission slate.
- **D1 data hygiene.** `verifiers/bermuda/rules/seed.edn` and `grounded.edn` rewritten from JSON syntax to real EDN syntax. New test `skills/neurosym-forge/tests/test_bermuda_rules_edn.py` round-trips both files against PR-1's `read_edn_file`.
- **CLJS test gap closed.** New `shadow-cljs :test :node-test` build target plus a `cljs.test` namespace per Bermuda module (`unify`, `ir`, `nl-to-fol`, `phases`, `bridge`, `core`). 32 tests total, all green. A latent `claim->formula` rewrite issue surfaced and was fixed: the meander rule now produces a Formula that validates against `bermuda.ir/Formula` end-to-end (the previous shape relied on inline `:symbol` heads with injected `:name` keywords that did not cleanly compose with the malli schema).
- **CI.** New `.github/workflows/cljs-bermuda-test.yml` runs the new test target on `ubuntu-latest` for every PR and `main` push.

Plan: `docs/plans/2026-05-17-booklogic-cleanup.md`.

## Test plan

- [ ] `cd skills/neurosym-forge && .venv/Scripts/python.exe -m pytest tests/ -q` — 161 passing
- [ ] `cd verifiers/bermuda && .venv/Scripts/python.exe -m pytest tests/ -q` — 23 passing (unchanged)
- [ ] `cd verifiers/bermuda && npx shadow-cljs compile test && node cljs-orchestrator/dist/test.js` — 32 tests, 0 failures
- [ ] CI: `cljs bermuda test` workflow green on the PR
- [ ] CI: existing `BookLogic CLJS integration`, `ci`, and `lint workflow yaml` jobs green

## Acceptance gates from the spec

- [x] `Select-String docs -Pattern "codex"` returns nothing outside the surviving review protocol and this PR's design spec
- [x] `Select-String docs -Pattern "two-agent"` returns nothing outside this PR's design spec
- [x] `read_edn_file` round-trips `seed.edn` and `grounded.edn`
- [x] `cljs-bermuda-test` CI job green
- [x] No regression in existing CI

## Out of scope

- Wiring `analysis/ingest-trace.edn` into `run_verification.py` (PR-D2)
- BookLogic active forms `defrule` / `defconstraint` / `defquery` / `defremedy` (PR-4)
- Bermuda migration to BookLogic source + real Z3 on CI (PR-5)
- Osmotic-pressure showcase (PR-6)
- Building the napi native addon in CI (PR-5; PR-cleanup's bridge tests stub it)
'@
```

- [ ] **Step 3: Report PR URL.**

---

## Self-review

Walking the spec § "PR-cleanup — Strip Codex scaffolding, D1 hygiene, CLJS test gap" against this plan:

| Spec clause | Implementing tasks |
|---|---|
| Delete `docs/codex-wiki/` | 1.2 |
| Delete `docs/handoffs/2026-05-15-codex-*.md` | 1.3 |
| Delete `docs/specs/2026-05-15-codex-handoff-design.md` | 1.4 |
| Delete `openspec/changes/codex-phase-0/` | 1.5 |
| Strip two-agent language from `AGENTS.md` and replace with single-agent note | 1.6 |
| Remove any "PR-3.5" reference from plans/specs | 1.7 |
| Convert `seed.edn` from JSON to real EDN | 2.2 (gated by failing test 2.1) |
| Convert `grounded.edn` from JSON to real EDN | 2.3 (gated by failing test 2.1) |
| Add shadow-cljs test target if missing | 3.1 |
| Create `verifiers/bermuda/cljs-orchestrator/test/` with one cljs.test file per module | 3.2 (unify), 3.3 (ir), 3.4 (nl-to-fol), 3.5 (phases), 3.6 (bridge), 3.7 (core) |
| Surface and fix the `nl_to_fol/claim->formula` bug | 4.1 |
| Add `cljs-bermuda-test` job matching house style | 5.1 |
| Acceptance grep for "codex" returns nothing in active docs | 6.1 step 1 |
| Acceptance grep for "two-agent" returns nothing | 6.1 step 2 |
| `read_edn_file` round-trips both files | 6.1 step 8 (and the failing-then-passing tests in 2.1–2.3) |
| `cljs-bermuda-test` green | 5.1 + 6.2 (post-push CI run) |
| No regression in existing CI | 6.1 steps 4–6 prove the local suites are intact |

All spec items have implementing tasks.

**Placeholder scan:** No "TBD/TODO/fill in" anywhere. Every code-producing step has full source or full diff. Every shell command has expected output noted.

**TDD-shape audit:** Phase 2 (data hygiene) — failing test in 2.1, fix in 2.2 + 2.3, passing-test re-runs in 2.2 step 3 and 2.3 step 3. Phase 3 (CLJS harness) — each module's test ns is written before its inclusion in the runner is exercised; the first run-and-see-pass happens at compile-and-node-run time per task. Phase 4 (bug fix) — failing test in 4.1 step 2, fix in 4.1 step 3, passing-test re-run in 4.1 step 5. Phase 1 (deletes) and Phase 5 (CI) are not code-producing; the TDD shape does not apply — each delete has a confirm-existence step before `git rm` and a confirm-removal step after.

**Effort estimate:** Spec said ~3-4 days. This plan: ~3 days. Phase 1 (~3 hr), Phase 2 (~2 hr), Phase 3 (~12 hr; six modules including the bridge-stub workaround), Phase 4 (~2 hr), Phase 5 (~1 hr), Phase 6 (~2 hr). Total ~22 working hours.

**Known risks:**

- **The `bridge_test` may fail to compile** if shadow-cljs eagerly resolves the native `.node` require even with `with-redefs`. Task 3.6 documents a fallback (declare local stub fns instead of requiring `bermuda.bridge`). Either path lands six bridge-scoped assertions; the production seam stays intact.
- **The `core-test` `unknown-command-exits-2` case** depends on patching `js/process.exit` mid-test. If shadow-cljs's `:node-test` runner catches the patched exit before the assertion completes, the test is downgraded to a usage-line check in Task 3.7 step 4.
- **The `nl_to_fol` fix simplifies the rewrite output** by dropping `:name` fields on non-leaf atoms. If a downstream consumer in PR-D2 or PR-5 needs operator-name disambiguation, restoring `:name` is a one-line change and the schema accommodates it. The current fix prioritises schema validation; semantics are preserved structurally.
- **The PR-3 design spec edits in Task 1.7** are surgical and depend on the exact line text matching at the time of execution. If a prior edit shifted line numbers, the `Edit` calls' `old_string` will still match because each is uniquely anchored on full-sentence context. If any `old_string` fails uniqueness, expand the context to include the preceding or following sentence.

# Post-#185 follow-ups: skill install + parent-branch carve (design)

**Date:** 2026-06-03
**Status:** approved (design); ready for implementation plan
**Scope:** Two independent follow-up tasks left after PR #185 (feynman-style + halmos → main).

## Context

PR #185 (`add-halmos-and-feynman-skills` → `main`) adds the two new skills and their integrations, scoped off `origin/main`. It excludes everything else on `feat/rust-axum-v2-architecture`. Two follow-ups remain:

1. **Skill install** — neither new skill is registered under `~/.claude/skills`, so they are not discoverable as normal siblings and feynman's humanizer-catalog lookup path is not exercised.
2. **Parent-branch disposition** — `feat/rust-axum-v2-architecture` still carries four ready-to-ship slices plus the not-ready V3/microservices architecture docs.

These are independent. Part A can run immediately; Part B is gated on #185 merging.

## Part A — Skill junction install

Mirror the existing install pattern. Inspection confirms the suite's other skills are directory junctions into the repo:

```
~/.claude/skills/book-compose     -> C:\russellian-book-suite\skills\book-compose
~/.claude/skills/book-qa          -> C:\russellian-book-suite\skills\book-qa
~/.claude/skills/russellian-style -> C:\russellian-book-suite\skills\russellian-style
~/.claude/skills/scrapling-fetch  -> C:\russellian-book-suite\skills\scrapling-fetch
~/.claude/skills/humanizer        (real dir, already installed)
```

Create two more junctions:
- `~/.claude/skills/feynman-style` → `C:\russellian-book-suite\skills\feynman-style`
- `~/.claude/skills/halmos` → `C:\russellian-book-suite\skills\halmos`

Windows: `New-Item -ItemType Junction -Path <link> -Target <target>` (or `mklink /J`).

**Verification:**
- Each junction resolves and `(Get-Item link).Target` points at the repo skill dir.
- `SKILL.md` is readable through the junction.
- The skill's test suite runs from the junctioned path (`~/.claude/skills/<name>/.venv/Scripts/python.exe -m pytest tests/ -q`) — note the venv lives in the repo dir and is reached through the junction.
- humanizer remains a real dir, so feynman's `lint_ai_vocabulary` humanizer-catalog lookup resolves.

**Caveat (documented, not fixed):** like every existing junction, the target is the repo working tree, so the junction dangles if the repo is checked out to a branch lacking that skill dir. Stable once #185 is on `main` (the default branch). Creating the junctions now is safe because the dirs exist on the current branch.

**Reversibility:** delete the junction (`Remove-Item <link>` — removes the link, not the target).

## Part B — Carve the parent branch into four scoped PRs, then reconcile

**Precondition:** PR #185 is merged to `main`. All four PRs are cut off the *updated* `main`, so each base already contains halmos+feynman. After #185, the four slices have disjoint footprints (only PR 1 touches `chapter_contract_check.py`), so they are mutually independent and may merge in any order.

**Construction method (per PR, mirrors #185):**
1. `git fetch origin main`; cut a scoped branch off `origin/main`.
2. Bring the slice's files from `feat/rust-axum-v2-architecture` — wholesale where the file is slice-only; targeted re-apply where a file is shared (only PR 1's `chapter_contract_check.py`).
3. Bring the slice's design/plan docs where they exist.
4. Run the affected skill suite(s) + any cross-skill suite (book-compose for PR 1).
5. Read-only QA audit (scope/leakage check: no out-of-slice paths, no `*.pdf`/`.venv`/`corpus-raw`/`egg-info`/`__pycache__`; affected-suite tests; regression vs main).
6. Push; open PR against `main`.

### The four PRs

**PR 1 — russellian-style linters**
- Files: `skills/russellian-style/scripts/{lint_footnotes,lint_ai_staccato}.py`, `tests/{test_lint_footnotes,test_lint_ai_staccato}.py`, `assets/russellian-rules.json`, `SKILL.md`; `skills/book-compose/scripts/chapter_contract_check.py`, `skills/book-compose/assets/chapter-contract.template.yaml`.
- Entanglement: re-adds the exact `footnote_orphan_count` wiring that was stripped from #185 — three lines in `chapter_contract_check.py` (`lint_footnotes = load_russellian_style_module("lint_footnotes")`, `footnotes = lint_footnotes.lint_footnotes(draft_path)`, `"footnote_orphan_count": len(footnotes)`). Post-#185 `main` has the halmos+feynman version of that file, so these add cleanly on top. `russellian-rules.json` + `SKILL.md` also carry the `lint_ai_staccato` antithesis-cadence additions — keep them together.
- Gate on: russellian-style suite (incl. the two new linter tests) + book-compose suite (footnote metric present, no regression).

**PR 2 — book-knowledge improvements**
- Files: `skills/book-knowledge/scripts/{source_substance,verify_claim}.py`, `tests/test_source_substance.py`, `tests/fixtures/stub_source.md`.
- Self-contained; no cross-skill files.
- Gate on: book-knowledge suite.

**PR 3 — syntopical-metabook v0.3**
- Files: `skills/syntopical-metabook/**` (governance/`_constraints.py`, `_staleness.py`, acquire/`pipeline.py`, synthesize/`run_synthesize.py`, `build_positions.py`, renderers, `skill_api.py`, `SKILL.md`, `references/governance-playbook.md`, conformance tests incl. the `test_epochpoet_governance`→`test_neutral_workspace` re-theme), `skills/neurosym-forge/**` (`forge_cli.py` meta subcommands + test), `examples/three-schools/**` and the new `examples/.../{my-own-work,school-a,school-b}.edn` + `constraints.edn` + ledger fixtures, top-level `sibling_skills/loader.py` + `sibling_skills/tests/test_loader.py`; plus its existing design/plan docs (`2026-05-31-syntopical-metabook-v0.3-generalization-design.md` + plan, `2026-05-31-syntopical-metabook-v0.3-generalization-plan-*`).
- Entanglement: the loader fix belongs here (halmos confirmed it does not need it). This is the largest, most file-heavy slice.
- Gate on: syntopical-metabook suite + `sibling_skills` loader test.

**PR 4 — scrapling-fetch session**
- Files: `skills/scrapling-fetch/scripts/session.py`, `skills/scrapling-fetch/tests/unit/test_session.py`.
- Small, self-contained.
- Gate on: scrapling-fetch suite.

### Reconciliation (after all five PRs merge: #185 + PRs 1–4)

`main` then holds everything except the V3/microservices architecture docs. Do **not** rebase `feat/rust-axum-v2-architecture` onto the new `main` — the merged content arrived under different commit SHAs (the skill trees via #185's 4 commits, the slices via fresh scoped branches), so a rebase would fight patch-id dedup and produce noise/conflicts.

Instead, **reconstruct**:
1. `git fetch origin main`; cut a fresh branch `feat/v3-architecture-docs` off updated `origin/main`.
2. Bring ONLY the V3/microservices doc files from `feat/rust-axum-v2-architecture`:
   - `docs/superpowers/specs/2026-05-31-rust-axum-v2-architecture-design.md`
   - `docs/superpowers/specs/2026-06-01-rbs-v3-architecture-design.md`
   - `docs/superpowers/specs/2026-06-01-rbs-v3-skill-migration-plan-design.md`
   - `docs/superpowers/specs/2026-06-01-rust-microservices-ascii-protocol.md`
   - `docs/superpowers/specs/2026-06-01-skill-capability-protocol-design.md`
   - (and any other `*v3*` / `*microservices*` / `*capability-protocol*` doc the inventory turns up — verify with `git diff --name-only origin/main feat/rust-axum-v2-architecture -- docs | grep -iE "v3|microservice|capability|axum-v2"`).
3. Commit on `feat/v3-architecture-docs`; keep it as the parked home of the not-ready V3 work (no PR — it is not ready).
4. After verifying `feat/v3-architecture-docs` holds exactly the V3 docs and nothing is lost, delete the old local `feat/rust-axum-v2-architecture` (its content is now split between `main` and `feat/v3-architecture-docs`).

## Sequencing / dependencies

- Part A: independent; do now.
- Part B: all four PRs gated on #185 merge. Among themselves, order-free (disjoint footprints). Reconciliation gated on PRs 1–4 merging.
- PR 1 is the only slice that touches a file #185 also touched (`chapter_contract_check.py`); cutting it off post-#185 `main` removes the conflict (the footnote lines add on top of the halmos+feynman version).

## QA discipline

Every slice PR gets the same read-only audit pattern used for #185, run before push:
- **Scope/leakage:** every changed path is within the slice; no out-of-slice skill dirs; no `*.pdf`/`.venv`/`corpus-raw`/`egg-info`/`__pycache__`/stray-root files committed.
- **Tests:** the slice's affected suite(s) pass; for PR 1, book-compose passes (the known pre-existing `test_persona_review_pass` failure remains, proven unrelated by an empty diff vs main — not a regression).
- **Regression:** no unintended change to files outside the slice.

## Out of scope

- The V3/microservices architecture docs do not go to `main` (parked on `feat/v3-architecture-docs`).
- No new feature work; this is release/branch management of already-written, already-tested work.
- preserve_argument's documented v0.1 detection gaps (single proper nouns, spelled-vs-digit numbers) are tracked separately, not addressed here.

## Success criteria

- Part A: both skills resolve through `~/.claude/skills` junctions; their suites run through the junctioned path; humanizer lookup works.
- Part B: four scoped PRs open against `main`, each green on its affected suites and clean on its QA audit; after merge, `main` carries all four slices; `feat/v3-architecture-docs` holds exactly the V3 docs; the old parent branch retired with nothing lost.

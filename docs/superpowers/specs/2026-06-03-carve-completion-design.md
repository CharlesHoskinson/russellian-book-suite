# Carve completion + dependabot drain — design

**Date:** 2026-06-03
**Predecessor:** `docs/superpowers/plans/2026-06-03-post-185-skill-install-and-branch-carve.md` (Tasks A1, B0–B4 complete; B5 pending). A prior session executed through B4 (PRs #191–#194 pushed and open) before dying; this design covers everything left.

## Problem

Two CI failures block all four open carve PRs, B5 reconciliation never ran, and nine dependabot PRs are queued behind the red `ci-required` gate.

1. `python-skill (paragraph-weaver / windows-2022)` fails **on main**. The Windows leg runs `pytest -m windows_canary`; paragraph-weaver has no marked tests and no registered marker, so pytest exits 5 (no tests collected). Every other skill marks test files with `pytestmark = pytest.mark.windows_canary` and registers the marker in `pyproject.toml`; paragraph-weaver merged after the 2026-05-21 marker sweep was reverted and never got either. This one job reddens `ci-required` on every PR.
2. PR #193 (`add-syntopical-v0.3`) fails its import-smoke leg: `ModuleNotFoundError: No module named 'sibling_skills'`. Six v0.3 scripts (`acquire/expand_seeds.py`, `acquire/download_and_ingest.py`, `gap/coverage_report.py`, `synthesize/topic_map.py`, `synthesize/disputed_questions.py`, `synthesize/concept_reconcile.py`) import the repo-root `sibling_skills` package at module top level, and `skill_api.py` eagerly imports all of them. The smoke leg installs only the base skill package — the gate exists precisely to catch top-level import regressions, and it did.

## Decisions

- **Windows fix:** register the marker and add `pytestmark = pytest.mark.windows_canary` to every paragraph-weaver test file, by hand. Matches the feynman-style precedent. No sweep tool — the automated `_insert_pytestmark` sweep is what broke on 05-21.
- **#193 fix:** move the `from sibling_skills import load_skill_api` imports inside the consuming functions in the six scripts. `import skill_api` becomes sibling-free again, matching the smoke gate's contract and the suite's graceful-degradation pattern. No CI changes.
- **Merge method:** merge commits (`gh pr merge --merge`), matching repo history. Delete remote branches on merge.
- **Dependabot rule:** update branch, let CI judge. Green → merge. Red → diagnose briefly, fix only if trivial, otherwise leave open with a findings comment. Majors (shadow-cljs 2→3, actions/checkout 4→6, pytest 9) are judged by CI, not by hand.

## Phases

**Phase 0 — unbreak main.** Branch `fix/paragraph-weaver-windows-canary` off `origin/main`. Marker registration + per-file pytestmark in paragraph-weaver. Fold in the two carve docs from `plan/post-185-followups` (spec + plan) and this design doc, so the plan branch can be retired in Phase 3. Verify locally: `pytest -m windows_canary` collects >0; full suite green. Push, PR, merge when green.

**Phase 1 — merge the clean three.** `gh pr update-branch` on #191, #192, #194; wait for green; merge.

**Phase 2 — fix and merge #193.** Lazy imports on `add-syntopical-v0.3`. Verify: full syntopical suite green; `import skill_api` succeeds without `sibling_skills` importable (simulation: run the smoke import with the package hidden). Update branch, wait green, merge.

**Phase 3 — B5 reconciliation.** Cut `feat/v3-architecture-docs` off updated main; bring the five V3/axum specs from `feat/rust-axum-v2-architecture`:

```
docs/superpowers/specs/2026-05-31-rust-axum-v2-architecture-design.md
docs/superpowers/specs/2026-06-01-rbs-v3-architecture-design.md
docs/superpowers/specs/2026-06-01-rbs-v3-skill-migration-plan-design.md
docs/superpowers/specs/2026-06-01-rust-microservices-ascii-protocol.md
docs/superpowers/specs/2026-06-01-skill-capability-protocol-design.md
```

Commit (no PR — parked). Prove the parent has nothing else unique: `git diff origin/main feat/rust-axum-v2-architecture -- ':(exclude)docs'` must be empty, and the docs-side remainder must be exactly the five files above. Then delete local branches `feat/rust-axum-v2-architecture`, `feat/syntopical-metabook-v0.3-generalization`, `feat/feynman-style-skill`, `plan/post-185-followups`. If the uniqueness check is non-empty, halt and report — delete nothing.

**Phase 4 — dependabot drain.** Apply the dependabot rule to #179–#182, #186–#190.

## QA discipline

Each phase ends with a read-only QA subagent that verifies, against the live repo and GitHub state:

- diff scope matches the phase footprint exactly (`git diff --name-only origin/main HEAD`);
- no binaries, `.venv`, `__pycache__`, or egg-info committed;
- claimed test results reproduce (re-run, don't trust);
- for merges: `origin/main` actually contains the expected files afterward;
- for Phase 3: the uniqueness proofs are empty before any branch deletion.

Nothing pushes, merges, or deletes until its auditor passes.

## Out of scope

- The parked V3/microservices architecture work itself (lives on `feat/v3-architecture-docs`, no PR).
- The reverted windows-canary sweep tool (`_insert_pytestmark` ordering bug) — paragraph-weaver is fixed by hand; the tool stays retired until someone needs it again.
- Untracked conlang files in the repo root — not repo work, left untouched.

# Production-readiness audit — findings

**Date:** 2026-05-16
**Branch:** `audit/2026-05-16-production-readiness`
**Method:** six parallel audit agents (package metadata, pytest, cross-skill interfaces, Quickstart reproduction, doc truth, security & supply chain) against the repo at `HEAD`.

## Baseline numbers

- Eight skills under `skills/`.
- 545 tests passing, 82 failing pre-fix; **82 failures are all the same root cause** (spaCy `en_core_web_sm` model not installed).
- No committed secrets, no runtime network egress, no AI-attribution leakage, no dangerous code patterns.
- Two of five Quickstart commands silently exit 0 doing nothing (`workspace init`, `verify_claim`).

## Must-fix — addressed in this PR

| # | Finding | Fix |
|---|---|---|
| 1 | `skills/book-qa/` has no `pyproject.toml`; Quickstart `pip install -e .[dev]` fails. | Added `pyproject.toml` declaring `pyyaml` runtime, `pytest`+`jsonschema` dev. |
| 2 | `skills/book-qa/SKILL.md` has no YAML frontmatter; Claude Code skill loader cannot discover it. | Prepended `name`/`description`/`license`/`metadata` frontmatter. |
| 3 | `skills/book-compose/SKILL.md` `invokes:` declares only `russellian-style` but production code invokes `book-review` and `review-conductor` too. | Updated `invokes:` to list all three. |
| 4 | `skills/book-review/SKILL.md` advertises five personas but seven ship and `review-conductor/panels/chapter-default.yaml` wires all seven. | Updated description, body, and the Personas list to seven. |
| 5 | `python -m scripts.workspace init <path>` silently exits 0 with no `__main__`. | Added `argparse`-based CLI to `workspace.py`. |
| 6 | `python -m scripts.verify_claim <ws>` silently exits 0 with no `__main__`. | Added CLI to `verify_claim.py`; new `verify_all_proposed()` helper. |
| 7 | 71/110 russellian-style tests and 11/102 book-compose tests fail because `en_core_web_sm` is not installed and no skip-gate exists. | Added `collect_ignore_glob` in both `conftest.py` files; documented `python -m spacy download en_core_web_sm` in the README Quickstart. |
| 8 | `skills/book-thesis/scripts/datalog_consistency.py` resolves `.knowledge/claims.jsonl` / `.knowledge/ledger.jsonl` paths that no other skill writes — dead legacy. | Simplified `_resolve_claims_path` to the canonical `claims/ledger.jsonl`. |
| 9 | README "78-page book … manuscript.pdf 78 pages, 1.4 MB" — actual v6.0.0 PDF is 41 KB / 1 page (the body render is broken; cover/TOC only). | Reframed as "ten-chapter, ~28,000-word manuscript", noted the PDF render limitation, and corrected the release-bundle listing. |
| 10 | README pipeline diagram and release-tree listed `claims-bibliography.md`; actual file is `.jsonl`. | Renamed both references and added the missing `claims-bibliography.jsonl` line to the tree. |
| 11 | README quickstart promises `shacl_conforms: True`; actual report text is `Conforms: True`. | Updated the documented expectation. |
| 12 | README "seven core skills" heading + Quickstart `for skill in …; do` loop omits `neurosym-forge`; repo-layout block lists only seven skill subdirs. | Added neurosym-forge to the install snippet (gated on "if you need the verifier side-channel"), the PowerShell equivalent, and the repo-layout block. |
| 13 | `AGENTS.md` and `CLAUDE.md` enumerate only seven skills and claim `book-qa` has no `pyproject.toml`. | Updated both to mention the eighth optional skill and the now-present book-qa metadata. |
| 14 | README spec and plan lists were missing 10+ entries each. | Added neurosym-forge and bermuda-verifier entries; framed both lists as "major designs/plans, directory holds more." |
| 15 | README operations runbook list missing `neurosym-forge-runbook.md`. | Added. |
| 16 | Quickstart used a bash `for` loop with Windows venv paths; no PowerShell variant. | Added PowerShell `foreach` equivalent under the bash loop. |

## Tier-2 follow-ups — captured here, not addressed in this PR

These are real but each needs its own scoped change. Listing rather than fixing keeps this PR coherent.

| # | Finding | Why deferred |
|---|---|---|
| T1 | **Bundle C closed-loop is fixture-only.** `book-qa/scripts/propose_writeback.py` reads `qa/lint-findings.json` and `qa/swarm-findings.json`, but `lint_artifact.py` writes `qa/defects.json` with a `Defect` dataclass that has no `claim_id` or `claim_current_status` — fields `transition_rules.map_ticket_to_proposed_transition` requires. The defect→ticket adapter is missing in production code; only test fixtures synthesise the rich-ticket payload. | Real architectural gap. Needs (a) a defect-enrichment pass that joins `Defect` rows against the claim ledger to add `claim_id` + `claim_current_status`, or (b) a rewrite of `lint_artifact` to emit a richer ticket schema. Either is a multi-day change. |
| T2 | `requires-python` drift: six skills `>=3.11`, `book-thesis` `>=3.12`, `neurosym-forge` `>=3.13`. | Both higher-floor skills install and pass on their declared floor; relaxing to 3.11 needs feature audit (PEP 695 type syntax etc.). |
| T3 | `tools/` ships 16 Python scripts (playwright, reportlab, pdf munging) with no `pyproject.toml`/`requirements.txt`. | Folder is one-shot operator scripts; deps should be enumerated. |
| T4 | `pyDatalog>=0.17` is unmaintained (last release 2017). Acceptable today; future supply-chain risk. | Replacement requires either a Datalog-engine swap or rolling consistency rules by hand. |
| T5 | Dep version floors with no upper bounds — `spacy 4.x` / `pyshacl 1.x` could break the suite silently. | Caps are conservative but a real product decision; not blocking. |
| T6 | No `Cargo.lock` (verifiers) or `package-lock.json` (verifiers) committed. | Reproducibility hardening, not a bug. |
| T7 | `book-knowledge` script CLIs are inconsistent — some have argparse, several are library-only. The fixed two (`workspace`, `verify_claim`) are the ones the README references; others (`apply_writeback`, `belief_graph`, etc.) remain library-only. | Out of scope for "what the Quickstart promises." A follow-up could unify under a single `python -m scripts <subcommand>` dispatcher. |
| T8 | `humanizer` is referenced as a sibling skill in four SKILL.md files but no `skills/humanizer/` exists in this repo. | The references probably resolve to an external user-skill; should be documented or removed. |
| T9 | 801 rdflib DeprecationWarnings in book-knowledge tests; 3235 warnings total in book-compose (rdflib + pyshacl). | Cosmetic; tracks rdflib 7.6+ API rename to `default_graph`. |

## Notes (no action recommended)

- Sibling-loader pattern (`sibling_skills.py`) is consistent and correct across all callers; alias-namespacing dodges `scripts.` package collisions cleanly.
- D9-D12 hand-off between book-thesis and book-qa uses consistent filenames (`qa/supports-defects.json`, `qa/datalog-defects.json`, `qa/entailment-results.json`).
- The "no network egress at runtime" claim holds — verified by greps for `requests`, `httpx`, `urllib.request`, `socket`, `aiohttp`, subprocess curl/wget calls. The only `urlopen` hits are in archived planning docs, not executed code.
- SHACL `Conforms: True` and all eight competency queries return zero rows on the v6.0.0 Bermuda release.

## Test gate after fixes

After applying this PR's changes, every skill's pytest suite should pass on a clean install with the spaCy model present. Without the spaCy model, suite passes via skip — 0 failures. The previous 82 failing tests were not testing broken code; they were testing linters that need a runtime model.

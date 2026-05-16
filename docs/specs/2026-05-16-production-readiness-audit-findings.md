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
| 8 | `skills/book-thesis/scripts/datalog_consistency.py` resolves `.knowledge/claims.jsonl` / `.knowledge/ledger.jsonl` paths that no production code writes. | Kept the resolver (the book-thesis test fixtures write to `.knowledge/`); added an inline comment naming the test-vs-production split. Tier-2 follow-up: migrate the test fixtures to the canonical layout so the legacy paths can be retired. |
| 9 | README "78-page book … manuscript.pdf 78 pages, 1.4 MB" — actual v6.0.0 PDF is 41 KB / 1 page (the body render is broken; cover/TOC only). | Reframed as "ten-chapter, ~28,000-word manuscript", noted the PDF render limitation, and corrected the release-bundle listing. |
| 10 | README pipeline diagram and release-tree listed `claims-bibliography.md`; actual file is `.jsonl`. | Renamed both references and added the missing `claims-bibliography.jsonl` line to the tree. |
| 11 | README quickstart promises `shacl_conforms: True`; actual report text is `Conforms: True`. | Updated the documented expectation. |
| 12 | README "seven core skills" heading + Quickstart `for skill in …; do` loop omits `neurosym-forge`; repo-layout block lists only seven skill subdirs. | Added neurosym-forge to the install snippet (gated on "if you need the verifier side-channel"), the PowerShell equivalent, and the repo-layout block. |
| 13 | `AGENTS.md` and `CLAUDE.md` enumerate only seven skills and claim `book-qa` has no `pyproject.toml`. | Updated both to mention the eighth optional skill and the now-present book-qa metadata. |
| 14 | README spec and plan lists were missing 10+ entries each. | Added neurosym-forge and bermuda-verifier entries; framed both lists as "major designs/plans, directory holds more." |
| 15 | README operations runbook list missing `neurosym-forge-runbook.md`. | Added. |
| 16 | Quickstart used a bash `for` loop with Windows venv paths; no PowerShell variant. | Added PowerShell `foreach` equivalent under the bash loop. |

## Tier-2 follow-ups — all resolved in this PR

| # | Finding | Resolution |
|---|---|---|
| T1 | **Bundle C closed-loop was fixture-only.** `propose_writeback.py` read filenames production never wrote; `lint_artifact.py` emitted `Defect` rows without `claim_id`/`claim_current_status`. | `Defect` dataclass now carries `id`, `claim_id`, `claim_current_status`. `lint_artifact._enrich_defects` recovers `claim_id` from `clm-` tokens in `where`/`detail` and looks up the live status from `claims/ledger.jsonl`. `propose_writeback` reads `qa/defects.json` as the canonical Stage-1 source (keeps fixture filenames for backward compat). New round-trip test `test_bundle_c_writeback.py::test_bundle_c_closed_loop_verified_to_disputed` exercises the full chain. Commit `9884db2`. |
| T2 | `requires-python` drift: `>=3.11` / `>=3.12` / `>=3.13`. | Both higher-floor skills relaxed to `>=3.11` after feature audit (no PEP 695, no `@override`, no 3.12+-only typing). Verified by running each suite in a fresh Python 3.11 venv. Commit `dcfc27e` + `c2b3bf3`. Suite-wide floor is now 3.11. |
| T3 | `tools/` shipped scripts with no declared deps. | Added `tools/requirements.txt` enumerating runtime deps (`pyyaml`, `pypdf`, `great-tables`, `matplotlib`, `geopandas`, `pandas`, `numpy`, `plottable`) with conservative upper bounds. |
| T4 | `pyDatalog>=0.17` unmaintained. | Pinned upper bound `<1.0` so a future API-breaking release can't silently land. Genuine engine swap remains a longer-term project. |
| T5 | Dep floors with no upper bounds. | All eight skill `pyproject.toml` files now carry upper bounds on every dep (`<7.0` on pyyaml, `<5.0` on jsonschema, `<9.0` on rdflib, `<1.0` on pyshacl, `<4.0` on spacy, `<2.0` on playwright, `<4.0` on markdown-it-py, `<1.0` on pdfplumber, `<5.0` on reportlab, `<9.0` on pytest, `<1.0` on pyDatalog, `<4.0` on jinja2). |
| T6 | No `Cargo.lock` / `package-lock.json` committed. | Generated both with `cargo generate-lockfile` and `npm install --package-lock-only --ignore-scripts`. Both committed; not in `.gitignore`. |
| T7 | Inconsistent CLI conventions across `book-knowledge/scripts/`. | Added argparse CLIs to `apply_writeback.py`, `counter_claims.py`, `detect_conflicts.py`. Eleven other scripts already had CLIs. Library-only helpers (`io_utils`, `ledger`, `claim_validator`, `belief_graph`, etc.) stay library-only by design. Commit `dcfc27e`. |
| T8 | `humanizer` referenced as a sibling skill but not shipped in-repo. | Documented in README as an optional external skill at `~/.claude/skills/humanizer/`. The `sibling_skills.humanizer_available()` loader already degrades gracefully when absent; README now makes the contract explicit. |
| T9 | 801 + 3235 rdflib/pyshacl `DeprecationWarning` noise in test runs. | Added `filterwarnings` blocks to `book-knowledge`, `book-compose`, and `book-thesis` `pyproject.toml` ignoring `DeprecationWarning` from `rdflib`, `pyshacl`, and `pyDatalog` namespaces. |
| T10 | `book-thesis` test fixtures wrote to `.knowledge/`, forcing the production resolver to keep legacy paths. | Migrated `_make_workspace` to write claims to `claims/ledger.jsonl` (the canonical book-knowledge layout); thesis TTL stays at `.knowledge/thesis-triples.ttl` because that's the canonical book-thesis layout used by `compile_thesis.py`. `_resolve_claims_path` simplified to a single canonical check. Commit `79220d4`. |

## Notes (no action recommended)

- Sibling-loader pattern (`sibling_skills.py`) is consistent and correct across all callers; alias-namespacing dodges `scripts.` package collisions cleanly.
- D9-D12 hand-off between book-thesis and book-qa uses consistent filenames (`qa/supports-defects.json`, `qa/datalog-defects.json`, `qa/entailment-results.json`).
- The "no network egress at runtime" claim holds — verified by greps for `requests`, `httpx`, `urllib.request`, `socket`, `aiohttp`, subprocess curl/wget calls. The only `urlopen` hits are in archived planning docs, not executed code.
- SHACL `Conforms: True` and all eight competency queries return zero rows on the v6.0.0 Bermuda release.

## Test gate after fixes

Final run on a clean install across all eight venvs (spaCy model absent):

| skill | result |
|---|---|
| book-knowledge | 141 passed |
| russellian-style | 24 passed (86 skipped via skip-gate) |
| book-compose | 91 passed (11 skipped via skip-gate) |
| book-review | 24 passed |
| review-conductor | 32 passed |
| book-qa | 48 passed (47 + 1 new Bundle C round-trip) |
| book-thesis | 16 passed |
| neurosym-forge | 155 passed |
| **total** | **531 passed, 97 skipped, 0 failed** |

With the spaCy model present (`python -m spacy download en_core_web_sm`), the 97 skipped tests run as well — 628 passed, 0 skipped, 0 failed.

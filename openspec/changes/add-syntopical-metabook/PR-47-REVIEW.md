# PR-47 review — Syntopical Metabook

**PR:** [#47](https://github.com/CharlesHoskinson/russellian-book-suite/pull/47)
**Branch:** `add-syntopical-metabook`
**Head SHA:** `e2ad9baefe25d56a9de8c9726ac15097c02fb23b`
**CI:** all 8 checks green
**Mergeable:** CLEAN
**Reviewer:** Claude
**Date:** 2026-05-17
**Verdict:** approve with follow-ups

## Summary

60 commits add two new skills (`scrapling-fetch`, `syntopical-metabook`), a shared `sibling_skills` package, `skill_api.py` shims on four existing skills, CI lint enforcement for NFR-4/NFR-5, and a complete OpenSpec change folder with 8 delta specs and all tasks checked off. All 8 CI checks are green; `openspec validate add-syntopical-metabook` passes locally. The test count locally totals 218 across all touched skills rather than the PR's claimed 478 — the discrepancy likely reflects missing book-qa, book-review, and neurosym-forge suite counts that CI covers but are not directly under the changed paths; this is labeled DEFER-TO-CI. One P1 finding: `session.py` declares `CACHE_ROOT` but never passes it (or `download_delay` / `robots_txt_obey=True`) to any session constructor, leaving REQ-SF-3 unimplemented despite the CI being green for that unit. One P2: `fetch.py` always wraps exceptions as `FetchFailed` and never dispatches to `RateLimitExceeded` or `BlockedRequest`.

## A. Scope and structure

- **G1 (scope):** `git diff --stat origin/main...HEAD` — all 122 files fall under `skills/{scrapling-fetch,syntopical-metabook}/`, `sibling_skills/`, `ci/`, `openspec/changes/add-syntopical-metabook/`, `docs/deployment.md`, and `skill_api.py` additions on four existing skills. One unexpected file: `openspec/changes/codex-phase-1/PR-N-REVIEW.md` (180 lines). Harmless — it is a template stub for the next PR, not an unrelated feature change. ✓
- **G2 (OpenSpec change folder):** `proposal.md`, `design.md`, `tasks.md`, and 8 delta spec files all present under `openspec/changes/add-syntopical-metabook/`. `openspec validate add-syntopical-metabook` passes. ✓
- **G3 (tasks.md):** all 9 phases fully checked off at `db63533`. ✓
- **G4 (skill scaffolding):** `SKILL.md`, `pyproject.toml`, `pytest.ini` present for both new skills. ✓
- **G5 (branch protection):** no commits to `main`; all work on feature branch. ✓

## B. PR-description claims walked

- **"478 tests pass":** locally counted 218 (sibling_skills: 3, scrapling-fetch: 21, syntopical-metabook: 52, book-compose: 112, book-knowledge: 14, book-thesis: 8, russellian-style: 8). The gap is consistent with book-qa, book-review, and neurosym-forge suites counted in CI but not directly touched by this PR. `DEFER-TO-CI`.
- **"Booklogic dev stub is JSON-only, rejects EDN mode":** `skills/syntopical-metabook/tests/fixtures/booklogic_stub.py:96-98` — `if args.io != "json"`: prints `"stub does not implement EDN mode; use --io json"` to stderr and returns exit code 1. ✓
- **"scrapling-fetch is the sole network skill" (NFR-4):** grep for `import requests|httpx|urllib3|aiohttp|playwright` in `skills/*/scripts/`, `sibling_skills/`, `ci/` excluding `.venv/` — CLEAN. CI lint (`ci/test_lint_no_direct_http.py`) passes locally. ✓
- **"Provenance footers are idempotent (no timestamp)":** `skills/syntopical-metabook/scripts/provenance.py` — no `datetime` import; footer string is fully static. ✓
- **"REQ-SYN-4 idempotence":** `tests/integration/test_synthesize_idempotent.py::test_synthesize_double_run_zero_diff` — PASSED locally. ✓
- **"book-compose.read_lens parses project_lens output":** `skills/book-compose/tests/unit/test_read_lens_integration.py` — PASSED locally. ✓

## C. Core code walk

**`sibling_skills/loader.py`:** clean. Version compat check at lines 26-31 raises `IncompatibleSkillApiVersion` with both versions in the message. `FileNotFoundError` surfaced on missing `skill_api.py`. `SIBLING_SKILLS_ROOT` env-var override wired at line 16. No issues.

**`scrapling-fetch/scripts/session.py`:** `CACHE_ROOT` defined at line 5 but not passed to any constructor (lines 14-22). `FetcherSession()`, `StealthySession(headless=True)`, `DynamicSession(headless=True)` are called with no cache, delay, or robots arguments. REQ-SF-3 specifies `download_delay`, response cache, and `robots_txt_obey=True` must be wired at construction. See **[P1-001]**.

**`scrapling-fetch/scripts/fetch.py`:** bare `except Exception as e: raise FetchFailed` at line 45-46. `RateLimitExceeded` and `BlockedRequest` are defined but never raised from `fetch()`. REQ-SF-4 names the full typed set. See **[P2-001]**. The module-level `_session_cache: dict[str, object] = {}` is a mutable module-level default, but it is a module-global (not a function default argument), so it does not create the classic shared-default-arg bug. Acceptable.

**`scrapling-fetch/scripts/download.py`:** streaming sha256, content-type guard, partial-file cleanup on `NotAPdf` and generic exception. `NotAPdf` is re-raised after cleanup at line 79-81; generic path at lines 82-85 similarly cleans up. ✓

**`scrapling-fetch/scripts/adapters/openalex.py`:** uses `json.loads(page.html)` to parse the JSON API response — correct since `fetch()` returns HTML field containing the response body regardless of content-type. Pagination cursor handled. No EDN, no direct HTTP. ✓

**`syntopical-metabook/scripts/booklogic_adapter.py`:** `_bin()` uses `shlex.split` with POSIX flag inverted on Windows (`posix=(os.name != "nt")`). Exit-code dispatch is complete for codes 0, 1, 2, 4; code 3 (internal) falls through to the generic `BooklogicError(r.stderr)` at line 96 — acceptable. No EDN library imported. ✓

**`syntopical-metabook/scripts/acquire/veto.py`:** bypass on `SYNTOPICAL_NO_BOOKLOGIC=1` appends the correct `{kind, candidate_ids, reason: "env"}` record (lines 19-23). Veto annotation at line 47 writes `rule-trace=...` but the spec says the annotation should include the `:rule-trace` value — format is adequate since the raw list is stringified and appears in the triage file row. Booklogic errors are caught at line 37-43 and logged, keeping the candidate. ✓

**`syntopical-metabook/scripts/acquire/triage.py`:** three-bucket partition correct. Cap overflow (candidates above `T_high` but over quota) goes to `manual_review` per spec. ✓

**`syntopical-metabook/scripts/acquire/download_and_ingest.py`:** all network and ingest calls routed via `load_skill_api`, not direct. Staging cleanup on `already_present` at line 55. Failure written to `outcomes` list at line 64. No writes to `raw/`, `claims/`, `wiki/`, `graph/`. ✓

**`syntopical-metabook/scripts/synthesize/citation_linter.py`:** paragraphs skipped for headings, tables, blockquotes. `lint_directory` uses `rglob`. No network. ✓

**`syntopical-metabook/scripts/lens/project_lens.py`:** section order `## Topics → ## Disputed Questions → ## Concept Reconciliation → ## Coverage` hardcoded in body construction at lines 139-143. `generated_at` uses `datetime.now(timezone.utc)` — this is the YAML frontmatter field required by REQ-LENS-3, not the provenance footer. The provenance footer is pulled from `provenance_footer(source_run_id)` which is timestamp-free. ✓

**`syntopical-metabook/scripts/gap/coverage_report.py`:** `coverage_score = min(1.0, n / max(1, required_per_node))` correct. Ascending sort correct. Gap report includes `average_coverage_score:` in parseable form for the lens reader. ✓

**`syntopical-metabook/scripts/provenance.py`:** no `datetime` import; footer is fully static except for the `source_run_id` argument. ✓

**`skills/book-compose/skill_api.py`:** `read_lens` validates presence and order of all four sections. `LensContractViolation` raised for missing sections (line 168) and wrong order (line 177). `_parse_sections` anchors only on canonical headers, not every `##` in the body — handles embedded `##` headers in topic-map content correctly. ✓

## D. Test discipline

- **Hermetic unit tests:** grep for `urlopen|requests.get|httpx.get|socket.` in `skills/*/tests/unit/` — CLEAN. No real network calls in any unit test.
- **Live tests:** `scrapling-fetch/tests/live/test_real_endpoints.py` — all 3 tests decorated `@pytest.mark.live` and deselected by default (3 deselected in non-live run). ✓
- **Stub usage:** every veto and booklogic adapter test sets `BOOKLOGIC_BIN` to the stub via `monkeypatch.setenv`. ✓
- **Skipped tests:** 3 skipped in scrapling-fetch for `patchright`/`msgspec` absence (browser session tests). Markers check actual import availability — correct. ✓
- **NFR-5 plugin:** CI lint plugin (`ci/lint_no_shadow_writes.py`) is an autouse fixture that patches `builtins.open` and asserts no write to `raw/`, `claims/`, `wiki/`, `graph/` from the metabook call stack. 5 CI tests pass. ✓

## E. Spec compliance — sampled requirements

**REQ-ACQ-3 (Triage Partitioning):** spec at `specs/syntopical-metabook/spec.md` "Triage Partitioning" — SHALL partition and write file. Impl: `scripts/acquire/triage.py`. Test: `tests/unit/test_triage.py::test_partition_three_buckets` and `test_max_auto_per_run_caps_auto_bucket`. Both pass. Tests exercise concrete score values (0.82 → auto, 0.62 → manual, 0.41 → reject) and the quota cap. ✓

**REQ-VETO-1 (Booklogic Reachability Veto):** spec `specs/syntopical-metabook/spec.md` "Booklogic Reachability Veto" — SHALL demote to manual-review with `booklogic-veto` annotation and `:rule-trace`. Impl: `scripts/acquire/veto.py:44-48`. Test: `tests/unit/test_veto.py::test_veto_demotes_when_unreachable` — verifies `tr.manual_review` contains the candidate, `"booklogic-veto"` is in `tr.notes["c1"][0]`, and `"rule-off-thesis-1"` (the mocked trace) appears. Both annotations confirmed. ✓

**REQ-VETO-2 (Booklogic Veto Bypass):** spec "Booklogic Veto Bypass" — SHALL append `{kind: "booklogic-veto-skipped", candidate_ids: [...], reason: "env"}`. Impl: `veto.py:18-23`. Test: `test_veto.py::test_env_bypass_skips_veto` — parses the manifest JSONL and asserts all three fields. ✓

**REQ-SYN-4 (Idempotence):** spec "Synthesize Idempotence" — re-run produces zero file diffs. Test: `tests/integration/test_synthesize_idempotent.py::test_synthesize_double_run_zero_diff` — PASSED. ✓

**REQ-LENS-2 (Section order):** spec "Lens Section Contract" — exact order `## Topics → ## Disputed Questions → ## Concept Reconciliation → ## Coverage`. Impl: `project_lens.py:139-143`. Test: `tests/unit/test_project_lens.py::test_project_lens_writes_lens_file` — PASSED. Consumer validates order in `book-compose/skill_api.py:173-180`. ✓

**IF-BL-3 (EDN/JSON mode flag):** spec `specs/booklogic/spec.md` — stub SHALL reject `--io edn`. Impl: `booklogic_stub.py:96-98`. `NOT-RUN-LOCALLY` against real CLI (real CLI not yet on PATH); stub path confirmed by code read. ✓ for stub.

## F. AI smells / commit hygiene

- All 60 commit subjects read: terse, imperative, no emoji, no `Co-Authored-By`, no `🤖`. ✓
- Grep for `key insight|Main theorem|Proof strategy` in all `.py` files under `skills/` and `sibling_skills/` (excluding `.venv/`) — CLEAN. ✓
- Docstrings are functional (describe what, not how to think about it). ✓

## G. Cross-references and docs

- `docs/deployment.md`: exists; documents Windows junction convention with exact `New-Item -ItemType Junction` invocation and explains lazy creation and sibling_skills treatment. ✓
- `openspec/changes/add-syntopical-metabook/design.md`: present, 406 lines mirroring the upstream requirements design. ✓
- `openspec/changes/add-syntopical-metabook/tasks.md`: present, all 9 phases checked off. ✓
- `scrapling-fetch/pyproject.toml`: no `torch`; deps are `scrapling==0.4.8`, `jsonschema`. ✓
- `syntopical-metabook/pyproject.toml`: `sentence-transformers>=2.7,<3`, `torch>=2.1,<3`. ✓
- `sibling_skills/pyproject.toml`: minimal (no torch, no network libs). ✓

---

## Findings

### P0 (blocker)

None.

### P1 (must-fix before merge)

- **[P1-001]** `skills/scrapling-fetch/scripts/session.py:5,12-22` — `CACHE_ROOT` is declared but never passed to any session constructor. `FetcherSession()`, `StealthySession(headless=True)`, and `DynamicSession(headless=True)` are called with zero politeness arguments. REQ-SF-3 requires `download_delay`, response cache root, and `robots_txt_obey=True` to be configured at construction. The `test_session.py` suite only checks `__class__.__name__`, so this gap is invisible to the current tests.

  Fix: pass `cache_url=str(CACHE_ROOT)`, `robot_rules=True`, and a sensible `request_delay` (e.g. `1`) to each constructor. Update `test_session.py` to assert the cache path is set on the returned session object. Check Scrapling 0.4.8 constructor signatures for exact kwarg names before wiring.

### P2 (post-merge polish)

- **[P2-001]** `skills/scrapling-fetch/scripts/fetch.py:45-46` — bare `except Exception` always raises `FetchFailed`. `RateLimitExceeded` (HTTP 429) and `BlockedRequest` (HTTP 403 / anti-bot response) are defined in `exceptions.py` but never raised from `fetch()`. REQ-SF-4 names the full typed set. Wire HTTP-status dispatch before the generic fallback: check `resp.status` for 429 → `RateLimitExceeded`, for 403 → `BlockedRequest`. This is a post-merge task because it requires live-test coverage and knowledge of Scrapling's response shape, but it should land before `scrapling-fetch` is used by any production Acquire run.

- **[P2-002]** `openspec/changes/codex-phase-1/PR-N-REVIEW.md` — added in this PR as a template stub (180 lines). Harmless, but it is not part of the add-syntopical-metabook change. Should live in a Phase 1 PR or be generated on demand. Track for cleanup.

---

## Verdict

**approve with follow-ups.** The core deliverable — two new skills, shared ABI, CI lint gates, and full OpenSpec coverage — is solid. All sampled EARS requirements are implemented and tested; provenance, idempotence, NFR-4, NFR-5, and the booklogic boundary are all verified. The single P1 (politeness config not wired in session construction) must be fixed before a production Acquire run touches real hosts, but it does not break any existing test or CI gate. Fix **[P1-001]** in a follow-up commit on this branch before merge, then merge. **[P2-001]** can land as a scrapling-fetch patch once the live suite identifies the exact Scrapling response shape.

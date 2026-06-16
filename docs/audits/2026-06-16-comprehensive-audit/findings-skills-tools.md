# Findings — Python skills + tools

All severities. Items on the protocol's "What NOT to flag" list and already-tracked-unchanged prior findings are excluded (see `reconciliation.md`). Suites were run; counts in `README.md` baseline.

## book-knowledge (174✓ — healthy; all prior highs fixed)

- **[MEDIUM] `scripts/generate_counter_claims.py:51`** — `rivals = json.loads(raw)` on LLM output with no try/except and no shape validation before iterating `rival["text"]`/`rival["disagreement_vector"]`. The only unprotected LLM boundary in the subsystem. Fix: guard `JSONDecodeError`, assert list-of-dicts with required keys.
- **[MEDIUM] `scripts/detect_conflicts.py:47-77` ↔ `project_graph.py:88`** — auto-detected antonym conflicts write `claims/conflicts.jsonl` and flip claims to `disputed`, but never set the claim's `conflicts_with` field, the only thing projected as `tbf:conflictsWith`. So `contradiction_scan.rq` never fires on detector output — the release gate can't see machine-detected contradictions. Fix: append updated records adding the conflicting id to `conflicts_with`, or project `conflicts.jsonl`.
- **[LOW] `scripts/export_symbolic_trace.py:127,137,149`** — bare `json.loads` on manifests + ledger + events lines; the rest of the codebase reads the ledger through `io_utils.read_jsonl` (skip-and-warn on a corrupt line). A single bad line aborts the export. Fix: reuse `io_utils.read_jsonl`.
- **[LOW] `assets/queries/coverage/orphan_wiki_pages.rq:6`** — references `tbf:referencesPage`, never projected by `project_graph.py`; in a `FILTER NOT EXISTS` it over-reports (a page referenced only by a chapter is still flagged orphan). Fix: project the edge or drop the filter.
- **[LOW] `skill_api.py:180`** — `spans[0]["doc_id"]` subscript (next line uses `.get`); a span lacking `doc_id` crashes `query_claims`. Fix: `.get("doc_id","")`.
- **[LOW] `scripts/run_competency_queries.py:73`** — docstring says defeasible fires are non-blocking by default, but line 21 sets `BLOCKING_DEFEASIBLE = True`. Doc contradicts code. Fix: update docstring.

## composition (book-compose 133✓, book-thesis 33✓, paragraph-weaver 49✓)

- **[HIGH carry-forward] `book-thesis/scripts/datalog_consistency.py:147-156`** — D10/D11/invariant detectors read `claim_value`/`implies` (forbidden by `additionalProperties:false`); inert on a real ledger (0 occurrences in bermuda's 50). Only `declared_conflict` works. See README H-05. Fix: add optional schema fields + populate them, or read from a typed thesis projection.
- **[MEDIUM] `book-thesis/tests/test_datalog_consistency.py:54-185`** — the positive-fire tests inject `subject`/`value`/`implies` records that `validate_claim` rejects, so they pass while proving nothing about production data. Fix: drive at least one test from a schema-valid record.
- **[MEDIUM carry-forward] `book-compose/scripts/build_book.py:90-107`** — `_assemble_manuscript` emits no `::: paragraph`/`<!-- supports: -->` carriers, so `book-thesis/lint_supports.py` flags every paragraph as a D9 orphan (committed example shows 333/333). Fix: emit carriers, or gate `lint_supports` to manuscripts that declare them.
- **[LOW] `book-thesis/scripts/datalog_consistency.py:91` + `synthesize_exemplars.py:87`** — two unguarded `json.loads(line)` sites diverging from `io_utils.read_jsonl`.
- **[LOW/INFO] `book-thesis/SKILL.md:6-7` + `skill_api.py:61-67`** — SKILL.md bills the transitive-contradiction pass as a headline capability that doesn't fire on real data; `read_thesis_tree` defines a second, unwired thesis schema. Fix: scope the doc; deprecate the stub.
- **[INFO] `book-compose/scripts/book_summary.py:109`** — per-chapter ledger re-read (O(chapters × ledger)); read once and thread.

## style/voice (russellian 185✓, feynman 45✓, halmos 29✓; triadic-voice doc-accurate)

- **[IMPORTANT] `halmos/scripts/aggregate_halmos.py:17,30` + `dispatch_halmos_review.py:82`** — `rollup` reads `f["check"]`/`f["severity"]` as required keys on dispatcher (LLM) output with no shape check; a malformed/non-dict reply crashes chapter aggregation with KeyError/AttributeError. Fix: validate shape before iterating; add a malformed-dispatcher test.
- **[HIGH] `feynman-style/scripts/score_feynman_delta.py:43-53`** — asymmetric delta normalization (README H-07). Reproduced 10× inflation. Fix: match denominators (normalize sample over in-vocab tokens, or rebuild profile over full corpus count); add a known-answer test.
- **[MEDIUM] `feynman-style/tests/test_score_feynman_delta.py:7-13`** — scorer is smoke-tested only (`isinstance`/`>=0`); no known-answer case, which is why H-07 went undetected. Fix: add a calibrated fixture test.
- **[LOW] `russellian-style/scripts/lint_ai_staccato.py:200`** — ReDoS (quadratic) in `\bnot\s+[^.!?,;]{1,60}?\s+but\s+` on whitespace runs (reproduced: 4000 spaces → 1.76s). Trusted prose, so slow-lint not hang. Fix: anchor the gap to `[^\s.!?,;]`.
- **[LOW] `russellian-style/scripts/score_russell_delta.py:37-50`** — empty/single-token/all-OOV text returns a confident "outside Russell's range" verdict instead of abstaining. Fix: relabel as "insufficient text" below `min_words`.
- **[LOW] `feynman-style/scripts/delta_math.py`** — entire module dead except `manhattan_delta`; scorer reimplements its own logic. Diverges from the same-named Russell module. Fix: delete unused fns or use them.
- triadic-voice SKILL.md is **accurate**, all referenced corpus/tool paths exist, modes/wiring claims true. No code findings (no Python in-skill).

## review/QA (book-qa 68✓, book-review 34✓, review-conductor 55✓, iacr-review 6✓)

The prior **CRITICAL is fixed**: `sentinel.py:30-33` now hard-fails D9/D10/D11/D13 at critical, regression-tested (`test_critical_d9_d13_are_hard_fail`).

- **[IMPORTANT] `book-qa/scripts/sentinel.py:107` + `healer.py:92,106`** — unguarded `json.loads` on internal QA artifacts; a corrupt `qa/chapter-tickets/ch-NN.json` aborts the whole sentinel rollup (the sibling `lint_artifact._load_json_if_exists` catches it). Fail-closed for release but brittle. Fix: guard + surface corruption as a synthetic hard-fail ticket.
- **[IMPORTANT] tests** — `sentinel.main()` / `lint_artifact.main()` exit codes (the literal CI gate signal: `1 if hard_fail else 0`) are never asserted by any test. A regression inverting the return would pass the suite. Fix: add exit-code tests for critical-present vs clean.
- **[MINOR] `review-conductor/scripts/reading_scores.py:91`** — `s[d]` over LLM-supplied score dicts, no shape guard → KeyError on a missing dimension. Fix: validate keys + add a malformed test.
- **[MINOR] `iacr-review/scripts/consolidate.py:188`** — `int(statistics.median(recs))` truncates even-count medians toward strong-reject (display-only). Fix: round-half-even.
- **[MINOR] `book-qa/lint_artifact.py:158`** — D3 ToC check `zip(toc, headings)` silently truncates to the shorter list. Fix: compare lengths.
- **[MINOR] `review-conductor/scripts/aggregate_panel.py:119`** — writes `verdict.json` without validating against the present `verdict.schema.json`. Fix: validate before write.

## neurosym-forge (517✓ — see README H-01/H-02 for the two Importants)

- **[IMPORTANT] H-01** — holdout + tautology gates wired only into the test-only Python orchestrator, not the production CLJS `induce_theory.cljs -main`.
- **[IMPORTANT] H-02** — codegen_axioms Rust injection via unescaped identifiers/strings (reproduced).
- **[IMPORTANT] `tests/test_scaffold_bake.py:65`** — bake tests assert only `make ci` returncode 0; never confirm the smoke constraint reached `axioms.rs` (the placeholder compiles, so a codegen regression to an empty file passes green). Fix: read `axioms.rs` and assert the fixture constraint landed; better, use a known-unsat fixture and assert the emitted defect.
- **[MINOR] `scaffold_project.py:34`** — `--out` guard permits writing to a *sibling* of cwd (`is_relative_to(cwd.parent)`), contradicting SKILL.md's "under the current working directory." Fix: use `cwd` as the boundary or correct the doc.
- **[MINOR] `_io.py write_edn_file`** — non-atomic write (no temp+rename); a crash truncates `seed.edn`. Fix: atomic write.
- **[MINOR] `_llm_lift.py:163,201`** — `json.loads(<llm output>)` with no shape validation.
- **[MINOR]** cross-platform fallback tests are existence/substring only; generated Rust/CLJS is never structurally validated off the Linux-nix path. Fix: add a toolchain-free structural gate (tree-sitter parse / per-constraint `assert_and_track` count).

## tools (build-voice-corpus 58✓; see README H-06)

- **[HIGH] H-06** — `run_bermuda_counter_claim_gen.py:138` non-idempotent (doubles the canonical counter-claim ledger).
- **[MEDIUM] `build-voice-corpus/scripts/manifest.py:33`** — uncaught `JSONDecodeError` in the resumable ledger reader; one bad line abandons the whole pipeline (the ledger that exists to survive crashes). Fix: skip+warn.
- **[MEDIUM] `split_bermuda_for_v6.py:68`** — uncaught `json.loads` mid-write of the canonical v6 release tree; can leave a half-materialized tree `build_book` then consumes. Fix: validate before writing.
- **[MEDIUM] `build-voice-corpus/scripts/append_to_index.py:29`** — per-video id counter not seeded from existing entries; re-indexing a video crashes on id collision once manifest/index fall out of sync. Fix: seed from existing.
- **[LOW] `build-russell-corpus/scripts/cross_check.py:66,72`** — `json.loads(llm_call(...))` + unchecked `response["top3_tags"]`. Dev tool; guard + shape-check.
- **[LOW] `strip_internal_ids.py`** — `BARE_CLM_RE` over-matches `[^)]*` to a later `)`, can delete a paragraph. Fix: split parenthesised vs bare.
- **[LOW] `process_footnotes.py:73`** — silently inlines "(definition missing)" with no warning + a dead `seen[name]` statement.
- **[LOW] `finalize_book.py:40`** — hard-coded `C:/tmp` import path + unguarded read (dead-by-path today; fragile).
- **[Coverage]** Nothing under `tools/` runs in CI (`compute_matrix` selects only `skills/<skill>/`); even `test_tag_load_bearing.py` is outside the matrix. The 4 LIVE canonical-artifact writers (`synthesize_bermuda_ledger`, `split_bermuda_for_v6`, `run_bermuda_counter_claim_gen`, `process_footnotes`) mutate canonical state with zero tests.

## Cross-skill consistency

- **[MEDIUM] value/implies lead** — confirmed isolated to book-thesis (H-05); book-qa/book-compose/tools read only canonical fields.
- **[MINOR] `russellian-style/scripts/lint_epistemic_precision.py:36`** — loose `\[clm-\d+-\d+\]` (variable-length) vs the canonical `^clm-[0-9]{4}-[0-9]{6}$`. Presence-detection only.
- **[MINOR] D11 taxonomy collision** — book-qa D11 = "failed-entailment"; book-thesis emits `class:"D11"` for datalog invariant/conflict/missing-evidence. Gate impact nil (both critical). Worth disambiguating.

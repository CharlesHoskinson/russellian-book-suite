# Tasks — review-revise-validate cycle

**Capability slug:** `REVISE`
**Authoritative source:** `proposal.md` + `design.md` in this directory
**Convention:** each task line cites the REQ IDs it satisfies; each commit should reference one or more tasks.

## Phase A: Scaffold the new skill

- [ ] **A.1** Create skill directory `skills/review-revise-validate/` with subdirs `scripts/`, `tests/`, `personas/`, `assets/`. Satisfies: structural.
- [ ] **A.2** Create `skills/review-revise-validate/SKILL.md` with frontmatter (name, description, license, metadata: author=charles-hoskinson, version=0.1.0, category=writing, workspace-aware=true) and a brief "what this owns" section pointing to the OpenSpec change. Satisfies: structural.
- [ ] **A.3** Create `skills/review-revise-validate/.venv/` via `python -m venv .venv` and install `pip install -e c:/governance/llm-infra` + `pip install pytest pytest-mock`. Satisfies: structural.
- [ ] **A.4** Add the `review-revise-validate` directory to the russellian-book-suite root layout documentation if such a doc exists. Satisfies: structural.

## Phase B: Reviser persona

- [ ] **B.1** Write `skills/review-revise-validate/personas/reviser.md`:
  - Frontmatter: `persona_id: reviser`, `display_name: Reviser`, `role: targeted-paragraph-rewriter`, `recommended_num_predict: 8192` (REQ-REVISE-008)
  - Identity section: precision editor applying revision instructions; does not invent content; does not change unflagged passages
  - Lens section: paragraph-level rewrites only; preserves voice (rhythm, vocabulary, sentence-length variance)
  - Output format section: JSON array of `{original: <verbatim text>, revised: <rewrite>, rationale: <which cluster/findings>}`; if cluster can't be resolved, append entry to `unresolved` array with reason
  - Tone: terse instructions to the model
- [ ] **B.2** Write `skills/review-revise-validate/assets/reviser-prompt-template.md` with slots `{{persona_body}}`, `{{chapter_id}}`, `{{chapter_md}}`, `{{revision_instructions}}`, `{{output_path}}`. Mirror the structure of `skills/book-review/assets/persona-prompt-template.md` so `run_persona_via_ollama` can render it directly.

## Phase C: Stage 3 — synthesize_findings (pure-Python)

- [ ] **C.1** Write `skills/review-revise-validate/scripts/synthesize_findings.py` skeleton with argparse: `--panel-summary PATH` (input), `--output PATH` (revision-instructions.md output). Satisfies: scaffolding for REQ-REVISE-003.
- [ ] **C.2** Implement parsing of `panel-summary.md`: extract per-persona Critical/Important/Minor sections; capture line-range refs via regex `(?:lines?\s+)(\d+)(?:[-–](\d+))?`. Satisfies: scaffolding for REQ-REVISE-003.
- [ ] **C.3** Implement clustering: group findings whose line ranges overlap or are within 5 lines of each other. Output: `list[Cluster]` with `line_start`, `line_end`, `findings: list[Finding]`, `distinct_personas: set[str]`, `severity_tier: str`. Satisfies: scaffolding for REQ-REVISE-003.
- [ ] **C.4** Implement theme tagging via regex match against finding text. Themes: `listicle`, `mechanical-parallel`, `hedging`, `formulaic-template`, `em-dash-overuse`, `jargon-density`, `lead-buried`, `voice-slip`. Satisfies: scaffolding for REQ-REVISE-003.
- [ ] **C.5** Implement Markdown emission per the format in `design.md` §2.2. Sort clusters: severity DESC, distinct_personas DESC, line_start ASC. Forward only Critical and Important clusters. Satisfies: scaffolding for REQ-REVISE-003.
- [ ] **C.6** Unit tests in `skills/review-revise-validate/tests/test_synthesize_findings.py`: empty input → empty instructions; single cluster from one persona; multi-cluster across personas; overlapping line ranges merge; Minor-only clusters excluded. Satisfies: REQ-REVISE-003.

## Phase D: Stage 4 — revise.py (LLM + apply)

- [ ] **D.1** Write `skills/review-revise-validate/scripts/revise.py` skeleton: argparse `--chapter PATH`, `--instructions PATH`, `--output-dir PATH`, `--model MODEL` (default gemma4:31b), `--num-predict N` (default uses persona frontmatter via persona_dispatch). Two phases: revise (LLM call) and apply (string replacement). Satisfies: scaffolding for REQ-REVISE-001, REQ-REVISE-002.
- [ ] **D.2** Implement Phase A (revise):
  - Read chapter + revision instructions
  - Build slots dict for the reviser template
  - Call `run_persona_via_ollama(persona_id="reviser", template_path=<asset>, persona_path=<reviser.md>, slots=slots, ...)`
  - Capture full response to `revisions-raw-response.md`
  - Parse JSON out of response: tolerate code-fence wrapping (use `re.search(r'```json\s*(.*?)\s*```', re.DOTALL)` then fall back to `re.search(r'(\[\s*\{.*\}\s*\])', re.DOTALL)`)
  - Write parsed JSON to `revisions.json`
  - Satisfies: REQ-REVISE-001.
- [ ] **D.3** Implement Phase B (apply):
  - For each `{original, revised, rationale}` entry: verify `original` appears verbatim in chapter (substring check on `chapter.read_text()`)
  - On failure: collect to `failures` list; after all entries checked, if `failures` non-empty, write `revisions-apply-failures.json` and exit 2
  - On success: apply replacements via `chapter_text.replace(original, revised)`; assert each replacement actually changed the text (paranoia check); write `revised-chapter.md`
  - Satisfies: REQ-REVISE-002.
- [ ] **D.4** Unit tests in `tests/test_revise_apply.py`: happy path (3 rewrites all apply); single missing-original failure exits 2 with failures file; multiple-match: assert replacement applied uniformly; whitespace-sensitive: leading/trailing whitespace must match exactly. Mock `run_persona_via_ollama` for stage A. Satisfies: REQ-REVISE-002.
- [ ] **D.5** Unit test for JSON extraction: response with `\`\`\`json ... \`\`\`` fence; response with bare JSON array; response with no JSON (error). Satisfies: REQ-REVISE-001.

## Phase E: Stage 6 — cycle_report.py (pure-Python diff)

- [ ] **E.1** Write `skills/review-revise-validate/scripts/cycle_report.py` skeleton: argparse `--before PATH`, `--after PATH`, `--output PATH`. Satisfies: scaffolding for REQ-REVISE-003, REQ-REVISE-005.
- [ ] **E.2** Implement summary parsing: extract per-persona verdict + Critical/Important/Minor counts from each summary markdown. Reuse the same regex/parse logic as the aggregator (extract to shared helper in `synthesize_findings.py` and import). Satisfies: REQ-REVISE-003.
- [ ] **E.3** Implement diff computation: per-persona verdict change; aggregate Critical/Important/Minor delta; resolved-findings list (text in before, not in after); new-findings list (text in after, not in before). Satisfies: REQ-REVISE-003.
- [ ] **E.4** Implement regression detection: if `after.critical_total > before.critical_total`, set `regression=True` and capture the new Critical findings. Satisfies: REQ-REVISE-005.
- [ ] **E.5** Implement markdown emission per `design.md` §2.5. Place the `## ⚠ REGRESSION` block at the very top above verdicts when `regression=True`. Satisfies: REQ-REVISE-003, REQ-REVISE-005.
- [ ] **E.6** Unit tests in `tests/test_cycle_report.py`: improvement case (Critical drops); regression case (Critical rises) writes the warning block; unchanged case; revision-skipped case (REQ-REVISE-007 — synthesize that scenario). Satisfies: REQ-REVISE-005.

## Phase F: Orchestrator — run_cycle.py

- [ ] **F.1** Write `skills/review-revise-validate/scripts/run_cycle.py`: argparse `--chapter-id`, `--draft-path`, `--workspace-dir` (default `workspace/review-cycle/<chapter-id>/<ISO>/`), `--model gemma4:31b`, `--skip-revise`, `--skip-revalidate`. Satisfies: REQ-REVISE-001.
- [ ] **F.2** Stage 1 wrapper: subprocess `book-review` panel into `<workspace>/panel-before/` via `python -m scripts.review_pass --chapter-id ... --draft-path ... --output-dir ... --llm-backend ollama --model ...`. Capture exit; on non-zero, halt with stage error. Satisfies: REQ-REVISE-001.
- [ ] **F.3** Stage 2 wrapper: subprocess `book-review aggregate_reviews.py` → `<workspace>/panel-summary-before.md`. Satisfies: REQ-REVISE-001, REQ-REVISE-006.
- [ ] **F.4** Early-exit check: parse `panel-summary-before.md` Critical count; if zero, write `cycle-report.md` with "no Critical findings; revision skipped" and exit 0. Satisfies: REQ-REVISE-007.
- [ ] **F.5** Stages 3 + 4: invoke `synthesize_findings.py` then `revise.py` in-process or via subprocess (this skill's own scripts; in-process is fine if same venv). Satisfies: REQ-REVISE-001, REQ-REVISE-002.
- [ ] **F.6** Stages 5: subprocess `book-review` panel again against `<workspace>/revised-chapter.md` → `<workspace>/panel-after/`; then `aggregate_reviews.py` → `<workspace>/panel-summary-after.md`. Satisfies: REQ-REVISE-006.
- [ ] **F.7** Stage 6: invoke `cycle_report.py` → `<workspace>/cycle-report.md`. Satisfies: REQ-REVISE-003, REQ-REVISE-005.
- [ ] **F.8** Optional REQ-REVISE-004 hook: if `<workspace>/../../claims/ledger.jsonl` exists (workspace-relative discovery), subprocess `book-knowledge claim_validator.py` against `revised-chapter.md`; append output as a section to `cycle-report.md`. Satisfies: REQ-REVISE-004.
- [ ] **F.9** Unit test in `tests/test_run_cycle_orchestration.py`: mock the four subprocess invocations + the three in-process modules; assert correct invocation order, correct argument passing, workspace layout matches `design.md` §4. Satisfies: REQ-REVISE-001.
- [ ] **F.10** End-to-end smoke test with gemma3:4b (faster, for CI): single persona variant of `book-review`, tiny synthetic chapter with a deliberate listicle, expect cycle to complete and produce a `revisions.json` plus a regression-free `cycle-report.md`. Skipped by default; run with `pytest -m e2e`. Satisfies: REQ-REVISE-001, REQ-REVISE-003.

## Phase G: Documentation + integration

- [ ] **G.1** Update `skills/review-revise-validate/SKILL.md` with operator-facing usage examples: full cycle on a chapter; skip-revise; skip-revalidate; how to interpret `cycle-report.md`.
- [ ] **G.2** Add the new skill to `AGENTS.md` skill inventory (if such an inventory exists).
- [ ] **G.3** Cross-reference: add a "See also" pointer from `book-review/SKILL.md` to this cycle skill ("To revise a chapter based on a panel, see review-revise-validate").

## Phase H: Validation against Ch1

- [ ] **H.1** Run the cycle against `c:/governance/wiki/report/articles-of-cardano-governance.md` `--chapter-id ch-01` end-to-end.
- [ ] **H.2** Inspect `revisions.json`: are the rationales coherent? do the rewrites address Cluster 1/2/3 from the panel? do any rewrites dilute voice?
- [ ] **H.3** Inspect `cycle-report.md`: did Critical count drop? are any regressions flagged?
- [ ] **H.4** Decision point: accept the cycle's revisions (copy `revised-chapter.md` over the source), or reject (note rejection reason; keep workspace as historical record).
- [ ] **H.5** If accepted: commit the revised chapter with reference to the cycle workspace path.

## Phase I: OpenSpec archive

- [ ] **I.1** When all REQ-REVISE-NNN gates pass and the validation on Ch1 has produced an accepted revision (or a documented rejection with reasoning), move `openspec/changes/2026-05-24-review-revise-validate/` to `openspec/changes/archive/2026-05-24-review-revise-validate/`.
- [ ] **I.2** Merge the `specs/review-cycle/spec.md` delta into a new `openspec/specs/review-cycle/spec.md` (steady-state truth for the capability).
- [ ] **I.3** Update the `## REQ ID convention` table in `openspec/README.md` to add the `REVISE` row.

## REQ ID coverage check

| REQ | Tasks |
|---|---|
| REQ-REVISE-001 | C.1-C.5, D.1-D.2, F.1-F.7, F.9 |
| REQ-REVISE-002 | D.1, D.3, D.4 |
| REQ-REVISE-003 | C.1-C.6, E.1-E.6, F.7, F.10 |
| REQ-REVISE-004 | F.8 |
| REQ-REVISE-005 | E.4-E.6 |
| REQ-REVISE-006 | F.3, F.6 |
| REQ-REVISE-007 | F.4 |
| REQ-REVISE-008 | B.1 |

All 8 EARS requirements traced to at least one task.

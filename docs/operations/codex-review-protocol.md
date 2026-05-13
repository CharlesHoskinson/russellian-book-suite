# Codex Review Protocol — russellian-book-suite

This document is the single source of truth for whole-repo autonomous review. When `AGENTS.md` says "follow the protocol at docs/operations/codex-review-protocol.md," follow this file exactly.

The protocol is calibrated for OpenAI Codex (autonomous mode) but generalises to any agentic reviewer. A copy-pasteable **trigger prompt** lives at the bottom of this file.

## Goals

Produce a single, high-signal markdown review report covering the whole repo:

1. Critical / Important / Minor findings, each with `file:line` precision and a concrete fix.
2. Empirical baseline: did tests pass, did linters pass, what version of main was reviewed.
3. Cross-cutting concerns that span multiple files (drift between docs and code, schema/query mismatches, unprojected RDF predicates).
4. A short next-steps list, prioritized by leverage.

The report is read by a human who will decide what to act on. The agent's job is to surface signal, not to fix.

## Operating model

**Read-only.** Do not modify any tracked file. Do not open a PR. Do not push commits. Treat the working tree as immutable.

**One report per run.** Aggregate everything into a single markdown document at the end. Do not stream partial reports.

**Bias to action on signal, restraint on noise.** When in doubt about a finding's severity, downgrade rather than upgrade. The cost of a developer chasing a phantom is higher than the cost of a missed minor.

**Cite or omit.** Every finding must carry `file:line` (or `file` if the issue spans the whole file). No floating assertions.

## Pre-flight (do these in order before any review reasoning)

1. **Read the conventions.** `README.md`, `CLAUDE.md`, `AGENTS.md`, `skills/<skill>/SKILL.md` for each skill, `skills/book-compose/MEMORY.md`. These tell you what is intentional. A "violation" of a documented convention is not a finding.
2. **Establish the baseline.** Run `git rev-parse HEAD` and record the commit. Run the three primary test suites and record pass counts:
   ```bash
   for s in book-knowledge book-qa book-compose; do
     (cd skills/$s && .venv/Scripts/python.exe -m pytest tests/ -q --tb=no || echo "FAIL: $s")
   done
   ```
   If a suite fails, that is finding #0. Stop, surface the failure, and continue review with the failing baseline noted.
3. **Run ruff if configured.** `ruff check .` from repo root. Capture violations verbatim.
4. **Enumerate the file list.** `git ls-files skills/ tests/ docs/specs/ docs/plans/ docs/operations/ tools/ AGENTS.md CLAUDE.md README.md`. This is the authoritative scope.
5. **Read the most recent spec, plan, and runbook in `docs/`.** They are the design intent for whatever shipped last. Code that contradicts a recent spec is a finding.

## Review dimensions

Cover the seven dimensions below. Codex's strongest add is **correctness, security, and tests** — spend more depth there. Architecture and design are areas where human-led review already provides coverage — sanity-check only.

### 1. Correctness (deep)

- Logic errors, edge cases, off-by-one
- Append-only invariants on `claims/*.jsonl` files (writers must use `"a"` mode)
- `latest_per` semantics applied wherever the same `id` can recur in an append-only file
- `json.loads(line)` wrapped in try/except — uncaught `JSONDecodeError` is a critical correctness defect
- State machine: `proposed → verified → disputed → {refuted, superseded}` — any transition outside this DAG is a defect
- LLM output handling: every `json.loads(llm_response)` should validate shape before iterating

### 2. Security (deep)

- Network calls — the suite is local-only. Any `requests`, `urllib`, `httpx`, `http.client` in production code is a finding (test fixtures or developer tools are OK).
- Subprocess calls — `shell=True`, user-controlled string interpolation
- Path traversal — workspace-relative paths that don't enforce `is_relative_to(workspace_root)`
- Dependency CVEs — note major dependency versions (`rdflib`, `pyshacl`, `jsonschema`, `pdfplumber`) and flag any known CVE
- Pickled or eval'd input from untrusted sources (there should be none)

### 3. Tests (deep)

- Untested code paths that could fail silently — particularly in `healer.py`, `generate_for_all_load_bearing`, state-machine recovery transitions
- Positive-fire tests for SPARQL queries — every defeasible query in `assets/queries/defeasible/` should have a test that proves it fires when it should and skips when its exception escape is met
- Live-LLM calls in tests — there should be none; all LLM calls must inject a `Callable[[str], str]` stub
- Test quality: assertions that test behavior, not implementation. `assert "pPosterior" in text or "0.42" in text` is too loose — flag.

### 4. Schema and data (medium)

- JSON Schema `additionalProperties: false` on all `.schema.json` files
- ID pattern consistency — `^clm-[0-9]{4}-[0-9]{6}$` for claims, `^cc-[0-9]{4}-[0-9a-f]{6}$` for counter-claims
- SHACL `sh:in` lists must match schema enums exactly
- Every predicate referenced in `assets/queries/*.rq` must be projected by `project_graph.py`. The four predicates we project today are: `tbf:pPosterior`, `tbf:loadBearing`, `tbf:axiom`, `tbf:pinLowConfidence`, `tbf:conflictsWith`, `tbf:rebuts`, `tbf:ccStatus`. If a `.rq` file references a predicate not in this list, it is a critical finding (the query will always fire or never fire).
- `tbf:rebuttalWindowOk` is a known gap — it is referenced by `contested-rebuttal-window.rq` but not asserted by any script. Note it as a known issue, not a new finding.

### 5. Documentation (medium)

- `SKILL.md` accuracy: do the listed components match `scripts/`? Do usage examples actually work?
- `docs/operations/*.md` runbooks: do the commands match the actual CLIs?
- `docs/specs/*.md` recent specs vs. shipped code: anything the spec promised that isn't implemented?
- `README.md` accuracy: skill count, layout tree, artifact paths

### 6. Architecture and layering (light — sanity check)

- Skill ownership: book-knowledge writes `claims/`/`wiki/`/`raw/`/`graph/`; book-compose writes `chapters/` and `book/`; book-qa writes `qa/`. Cross-skill writes are findings.
- Sibling-skill imports via `sibling_skills.load_*_module` rather than direct relative imports
- Layered model: book-thesis sits on book-knowledge, not the other way around

Spend less depth here. The human review already covered this dimension.

### 7. Performance and robustness (light — sanity check)

- Obvious O(N²) ledger scans
- Unbounded loops or recursion
- Network calls or PDF reads without size/encryption guards
- Race conditions on append-only files

## What NOT to flag

Negative prompting matters. The following are intentional design choices and are NOT findings:

- **`claim_type` `confidence` field set at extraction time vs `p_prior`/`p_posterior` set at propagation time.** Intentional. The schema carries both; they have distinct semantics. Documented in the Bundle C spec.
- **`proposed-transitions.jsonl` overwritten per build.** Intentional. Documented in `propose_writeback.py` docstring and in `CLAUDE.md`. Operators are warned.
- **`exception_queries` raises `NotImplementedError` when non-empty.** Intentional guard. The mechanism is documented but not implemented; the guard prevents silent incorrect behavior.
- **Two `sibling_skills.py` files with slightly different factoring.** Known. Tracked as a Minor item in the prior review.
- **`book-qa` has no `pyproject.toml`.** Known. CI installs deps directly.
- **The bermuda example's manuscript uses Russell-style prose with declarative phrasing.** This is the project's *house style*. Do not flag it as "too assertive" or "lacking nuance."
- **`Rivals and Limits` subsections in chapters 1, 2, 8 of the bermuda manuscript.** These are intentional — they engage Bundle C counter-claims. Do not flag as "out of place."
- **Style choices in `russellian-style` test fixtures.** Some test text is deliberately bad prose to exercise linter rules. Do not flag the fixtures themselves.
- **`tools/run_bermuda_counter_claim_gen.py` having hard-coded rivals.** Intentional bermuda-specific fixture; not a generic adapter.
- **`tools/synthesize_bermuda_ledger.py` writing a non-canonical source manifest shape.** Known issue, tracked as Important in the prior review. Note it; do not re-litigate.

If you encounter something that *looks* like a defect but matches one of these patterns, check `CLAUDE.md`, the recent spec, and `skills/book-compose/MEMORY.md` before flagging. When in doubt, omit.

## Output format

Produce exactly one markdown document at the end of the run. Structure:

````markdown
# Codex Whole-Repo Review — russellian-book-suite

**Reviewed commit:** <git rev-parse HEAD>
**Date:** <UTC iso date>
**Baseline:** book-knowledge <N> passed / book-qa <N> passed / book-compose <N> passed
**Ruff:** <clean | N violations>

## Executive summary

One short paragraph. Overall health, critical count, go/no-go on shipping. End with a single sentence saying whether the suite is currently in a releasable state.

## Findings

### Critical

- **[C-001]** `path/to/file.py:42` — One-line description. Impact (what breaks). Recommended fix (one or two sentences, code snippet if obvious).
- **[C-002]** ...

(If none: write "None.")

### Important

- **[I-001]** ...

(If none: write "None.")

### Minor

- **[M-001]** ...

(If none, or if you ran out of budget: write either "None." or "TRUNCATED — budget reached." Do not silently drop Minor findings.)

## Cross-cutting concerns

Issues that span multiple files. Each with the list of affected `file:line` anchors and one sentence on the pattern.

## Test failures

Paste verbatim if any. If clean: "All three suites pass: 123 / 41 / 94."

## Tooling violations

Paste ruff or other linter output verbatim if any. If clean: "No ruff violations."

## Next steps

Ordered bullet list, 3–5 items max, prioritized by leverage. Each one sentence.
````

## Scope-control signals

- If budget is tight, complete Critical and Important sections fully; mark Minor as `TRUNCATED — budget reached`.
- Do not pad. Empty sections should say "None.", not be filled with marginal findings.
- Never fabricate. If you can't find anything in a dimension, that's a valid finding.
- If a finding is uncertain, prefix it with `[Tentative]` and explain what would confirm or deny it.

## Anti-patterns

- **Don't suggest unrelated refactors.** Stick to defects and concrete improvements tied to the review dimensions.
- **Don't flag intentional deletions.** If something was removed between the prior commit and now, check if it was intentional before flagging.
- **Don't review docs as if they were code.** Documentation issues belong in dimension 5, with their own bar.
- **Don't recommend changes that violate the user's commit conventions** (no AI attribution, no Co-Authored-By, terse style).
- **Don't repeat findings already raised in prior reviews** unless the issue has regressed. The prior internal review's top items are summarised in PR #5; assume they are tracked.

## Trigger prompt

Paste this into Codex (web UI, CLI, or `@codex` GitHub mention). Adjust the repo / branch reference as needed for your invocation surface.

```
Goal: Perform a whole-repo end-to-end autonomous review of russellian-book-suite at main.
Context: AGENTS.md (auto-loaded) and docs/operations/codex-review-protocol.md contain
the full review protocol — apply them exactly. Read CLAUDE.md and the most recent
spec in docs/specs/ before reviewing.
Constraints: Read-only. Do not modify any file, open a PR, or push commits. Skip the
paths listed under "Out of scope" in AGENTS.md. Use `git ls-files` as the authoritative
file list. Bias toward correctness, security, and tests; sanity-check architecture and
design only. Do not flag items in the "What NOT to flag" list in the protocol.
Done when: A single markdown report matching the output format in
docs/operations/codex-review-protocol.md is complete; tests have been run via the
commands in AGENTS.md and pass counts reported; ruff has been run if configured.
```

### For PR-scoped review

Inline-comment the same protocol but scoped to a diff:

```
@codex review for correctness regressions, security issues, and test coverage gaps
in the changed files. Follow docs/operations/codex-review-protocol.md output format
where applicable. Skip nitpicks; flag only Critical and Important.
```

### For targeted-dimension review

For a focused review (e.g., just the schema dimension), use the same prompt structure but narrow the scope:

```
Goal: Review the SPARQL queries and graph projection for correctness and consistency.
Context: Apply docs/operations/codex-review-protocol.md "Schema and data" dimension only.
Constraints: Read-only. Scope is `skills/book-knowledge/assets/queries/`,
`skills/book-knowledge/scripts/project_graph.py`, and
`skills/book-knowledge/assets/shapes.ttl`.
Done when: A markdown findings block for the Schema dimension is complete, with
file:line citations.
```

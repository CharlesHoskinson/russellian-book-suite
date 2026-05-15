# Codex GPT-5.5 — deep review and remaining-PR implementation brief

**For Codex.** This is your working document for the BookLogic v0.4 mission. Read it once at the start of every session. Update the wiki (`docs/codex-wiki/`) every time you finish a phase or learn something non-obvious.

**Spec:** [`docs/specs/2026-05-15-codex-handoff-design.md`](../specs/2026-05-15-codex-handoff-design.md)
**Mission spec:** [`docs/specs/2026-05-14-booklogic-v0.4-mission-design.md`](../specs/2026-05-14-booklogic-v0.4-mission-design.md)
**Review protocol:** [`docs/operations/codex-review-protocol.md`](../operations/codex-review-protocol.md)
**Repo guidance:** [`AGENTS.md`](../../AGENTS.md), [`CLAUDE.md`](../../CLAUDE.md)

You implement and push branches. A Claude session opens the PR, reviews, files `PR-N-REVIEW.md`, and merges. You do not need `gh` auth and you never invoke `gh`.

---

## Ground rules

These apply across every phase. Internalise them before reading the phase work.

1. **One problem per branch.** No grab-bags. If you find something out of scope mid-branch, write it to `docs/codex-wiki/99-lessons.md` and keep moving.
2. **Real QA before pushing any branch.** Run pytest, run nbb integration tests, run cargo if Rust changed. Put counts in your final commit message body under `### Local QA evidence` (Claude reads the commit and uses it as the PR body). Branches without QA evidence get a request-changes PR opened by Claude.
3. **Never push to main.** Branch, push, stop. Claude opens the PR, reviews, and merges. If review feedback requires a fix, push to a follow-up branch (`codex/<phase>-fixes`) — never `--amend` on a pushed commit.
4. **Never skip hooks.** No `--no-verify`. No `-c commit.gpgsign=false`. If a pre-commit hook fails, fix the underlying issue.
5. **No AI attribution.** No `Co-Authored-By`. No "AI-generated" markers. No `Co-Authored-By: Claude` in commits or files. Terse, human-style commit messages. Imperative mood. ≤72 char subject line. Body only when the why isn't obvious (or when carrying the For-reviewer section on the final commit).
6. **No AI smells.** Don't write `## Main theorem:` or `**Proof strategy:**` or "key insight" or numbered proof steps or six-level emoji-bulleted lists. Read CLAUDE.md if uncertain.
7. **Skill ownership is sacred.** `book-knowledge` owns `claims/`, `wiki/`, `raw/`, `graph/`. `book-compose` owns `chapters/`, `book/`. `book-qa` owns `qa/`. Mission branches touch `skills/neurosym-forge/`, `skills/book-knowledge/` (only the symbolic-trace pieces), `verifiers/bermuda/`, and the worked-example READMEs.
8. **Append-only ledgers.** `claims/ledger.jsonl`, `claims/counter-claims.jsonl`, `claims/events.jsonl` are append-only. Use `book-knowledge/scripts/io_utils.py` (`read_jsonl`, `latest_per`).
9. **No outbound network.** `npm install` and `git push origin <branch>` are allowed. No `gh`, curl, wget, API calls. The verifier is local-only by design.
10. **Patch, don't rewrite.** Use `apply_patch` with minimal diffs. Don't regenerate a 400-line file to change three lines.

If you violate any of these, expect Claude's PR-N-REVIEW.md to flag it as a P1 and the merge to be blocked.

---

## Worktree setup (Phase 0 prerequisite)

The user will have created your worktree before launching you. Verify with:

```bash
git rev-parse --show-toplevel
git status -sb
git log --oneline -3
```

You should be in `C:/Users/charl/code/russellian-book-suite-codex` on a branch like `codex/phase-0-bootstrap` off the latest origin/main. If not, stop and tell the user.

Verify the toolchain:

```bash
python --version          # 3.13.x
node --version            # v22 or v24
npm --version
git --version
git config --get remote.origin.url   # confirm git push will work
```

You do not need `gh`. Claude opens, reviews, and merges PRs.

Skill venvs are junction-linked from `~/.claude/skills/<name>/.venv`. If `skills/neurosym-forge/.venv/Scripts/python.exe` is missing, run:

```bash
cd skills/neurosym-forge
python -m venv .venv
.venv/Scripts/pip install -e ".[dev]"
```

(Repeat for `book-knowledge`, `book-qa`, `book-compose`, etc., as needed.)

Baseline test run, full repo:

```bash
for s in book-knowledge book-qa book-compose neurosym-forge book-thesis russellian-style book-review review-conductor; do
  (cd skills/$s && .venv/Scripts/python.exe -m pytest tests/ -q --tb=no || echo "FAIL: $s")
done
(cd verifiers/bermuda && python -m pytest tests/ -q --tb=no || echo "FAIL: bermuda")
```

Record the baseline counts in `docs/codex-wiki/00-index.md` under a new section `## Baseline at handoff`.

---

## Phase 0 — bootstrap

**Deliverable:** wiki seeded, baseline recorded, you can articulate the mission.

Steps:

1. Read **in this order**: AGENTS.md, CLAUDE.md, `docs/operations/codex-review-protocol.md`, `docs/specs/2026-05-14-booklogic-v0.4-mission-design.md`, `docs/specs/2026-05-15-codex-handoff-design.md`, this brief.
2. Read the most recent three specs in `docs/specs/` and the most recent three plans in `docs/plans/` to understand the existing rhythm.
3. Read `skills/neurosym-forge/SKILL.md` end to end.
4. Read `skills/neurosym-forge/scripts/_edn_reader.py`, `_edn_writer.py`, `_io.py`, `scaffold_project.py`.
5. Read `skills/neurosym-forge/assets/project-template/cljs-orchestrator/src/main/__project__/booklogic.cljs.tmpl` (the PR-3 compiler).
6. Read `skills/neurosym-forge/assets/project-template/cljs-orchestrator/src/test/__project__/booklogic_test.cljs.tmpl`.
7. Read `verifiers/bermuda/scripts/ingest_ledger.py`, `extract_prose.py`, `verdict_to_qa.py`, `run_verification.py` (the Python ingesters slated for CLJS port in PR-3.5).
8. Read `verifiers/bermuda/rust-verifier/src/{canonical.rs,ir.rs,smt.rs}`.
9. Stub the per-phase wiki files (`01-audit-findings.md`, `02-pr3.5-notes.md`, etc.) with the section template from the spec.
10. Update `docs/codex-wiki/00-index.md` to reflect "Phase 0 complete, Phase 1 starting."

Push branch `codex/phase-0-bootstrap` containing only the seeded wiki files. Final commit message body should include the For-reviewer section so Claude can use it as the PR body verbatim. Suggested PR title: `docs: seed Codex working-wiki for v0.4 mission remainder`. The For-reviewer section's Local QA evidence carries the baseline test counts.

This branch exists so Claude can sanity-check the wiki structure before any real code lands.

---

## Phase 1 — deep audit

**Deliverable:** `docs/codex-wiki/01-audit-findings.md` — read-only review of neurosym-forge and the CLJS surface.

**Scope:** only the files relevant to the mission. Specifically:

- `skills/neurosym-forge/scripts/` (every `.py`)
- `skills/neurosym-forge/assets/project-template/` (every file)
- `skills/neurosym-forge/tests/` (every test)
- `skills/book-knowledge/scripts/export_symbolic_trace.py`, `load_symbolic_trace.py`
- `skills/book-knowledge/tests/test_export_symbolic_trace.py`, `test_load_symbolic_trace.py`
- `skills/book-knowledge/assets/ingest-trace.schema.json`
- `verifiers/bermuda/scripts/` (every `.py`)
- `verifiers/bermuda/rust-verifier/src/` (every `.rs`)
- `verifiers/bermuda/rules/predicates.edn`
- `verifiers/bermuda/tests/`

**Out of scope** (read-only protocol exclusions apply): venvs, generated artifacts, `examples/*/book/releases/`, `examples/*/graph/reports/`. See AGENTS.md "Out of scope for any review or analysis."

**Protocol:** apply `docs/operations/codex-review-protocol.md` exactly. Seven dimensions, severity-bucketed findings with `file:line` citations, single markdown report at the end. Bias toward correctness, security, tests. Do not modify any file in Phase 1. This is read-only.

**Additions for this audit** (mission-specific):

- Examine the **EDN reader/writer** for round-trip correctness, edge cases (empty maps, nested vectors, regex patterns), Unicode, and the metadata-discard logic for `^{...}` reader-metadata forms.
- Examine the **scaffolder** for Windows path bugs, junction-link assumptions, template-substitution leaks (any `__project__` or `{{ project_slug }}` that escapes templating).
- Examine the **PR-3 CLJS compiler** for:
  - completeness against PR-3 spec (`docs/specs/2026-05-14-booklogic-v0.4-pr3-design.md`)
  - hidden coupling between forms (e.g., does `expand-defpredicate` accidentally depend on sort-registry order?)
  - missing validation (what happens if `defsort` is missing for a sort referenced by a predicate?)
  - the `infer-value-kind` body-index fix — is the docstring index map correct in every case?
  - error messages: are they actionable? Do they include the offending form?
- Examine the **Rust verifier scaffold** for `unsafe` blocks, panic-on-input paths, missing `Result` wrapping.
- Examine the **bermuda ingesters** with PR-3.5 in mind: what does the Python actually do that needs faithful CLJS reproduction? Note edge cases the port must preserve.

**Output:** `docs/codex-wiki/01-audit-findings.md`. Follow the protocol's Output Format section. Add one extra section after `Next steps`:

```markdown
## PR-3.5 portability assessment

For each Python ingester slated for CLJS port (PR-3.5), one paragraph covering:
- What it does, mechanically
- The hardest part to port faithfully
- Suggested CLJS approach
- Test fixtures that must survive the port
```

Push branch `codex/phase-1-audit` with `01-audit-findings.md` and the wiki housekeeping. Final commit's For-reviewer body lists Critical/Important counts. Suggested PR title: `docs/codex-wiki: deep audit of neurosym-forge and CLJS surface`. Stop after pushing. Wait for `openspec/changes/codex-phase-1/PR-<N>-REVIEW.md` to land on main, then read it and the user's go/no-go signal before starting Phase 2.

---

## Phase 2 — remediation

**Deliverable:** one PR fixing every Critical and Important finding from Phase 1.

**Constraints:**

- **Fix only Critical and Important.** Minor findings are deferred. Do NOT bundle minors "since I'm in the file anyway."
- **One commit per finding.** Each commit's subject names the finding ID (e.g., `fix(C-001): tighten subject-keyword validation in deflift`). Body explains the fix.
- **Add a regression test for each Critical finding.** Important findings get a test only if the bug is observable from outside the function (no testing-for-its-own-sake).
- **No refactoring beyond what each fix demands.** If a finding says "split this function," that's the work. Don't also rename three variables.
- **Update the audit document.** As you fix each finding, change its status in `01-audit-findings.md` from `Open` to `Fixed: <commit-sha>`. Ship the audit-doc change in the same PR.

Push branch `codex/phase-2-remediation`. Final commit's For-reviewer body lists each finding ID and one-line fix description. Suggested PR title: `fix: address audit Critical and Important findings`. Phase 8 QA section in the commit body is mandatory.

Wait for the merged PR-N-REVIEW.md before starting Phase 3.

---

## Phase 3 — PR-3.5: port Python ingesters to CLJS

**Deliverable:** Bermuda's `scripts/ingest_ledger.py`, `extract_prose.py`, `verdict_to_qa.py` become CLJS modules under `verifiers/bermuda/cljs-orchestrator/src/main/bermuda/`. The Python files are deleted (or shrunk to thin shells that shell out to nbb — but deletion is preferred).

**Why:** PR-1 through PR-3 established that EDN flows through CLJS as the canonical orchestration layer. Bermuda's Python ingesters are the last layer of legacy Python in the pipeline. Removing them locks in the "pure CLJS + Rust" architecture the user chose.

**Detailed work order:**

1. **Read Bermuda's current shape.**
   - `verifiers/bermuda/scripts/ingest_ledger.py` — reads `examples/bermuda-manual/claims/ledger.jsonl`, applies lift rules from `verifiers/bermuda/rules/predicates.edn`, emits structured facts.
   - `verifiers/bermuda/scripts/extract_prose.py` — handles regex-based prose extraction.
   - `verifiers/bermuda/scripts/verdict_to_qa.py` — reads Z3 verdict JSON, writes a `qa/symbolic-findings.json` consumable by `book-qa`.
   - `verifiers/bermuda/scripts/run_verification.py` — orchestrator; keep this thin or delete.

2. **Spec the port.** Write `docs/specs/2026-05-15-booklogic-v0.4-pr3.5-design.md`. Architecture: each Python script becomes a CLJS namespace under `verifiers/bermuda/cljs-orchestrator/src/main/bermuda/`. EDN-on-the-boundary stays — input is JSONL ledger files, output is EDN facts plus JSON verdicts.

3. **Plan the port.** Write `docs/plans/2026-05-15-booklogic-v0.4-pr3.5.md` as a TDD plan in the writing-plans style: one task per ingester, each task has failing test → minimal impl → passing test → commit.

4. **Implement under TDD.** Start with `ingest-ledger` (smallest surface). For each Python script:
   - Write CLJS deftest fixtures that pin its current behavior (read the Python source carefully).
   - Implement the CLJS port using `cljs.reader`, `clojure.string`, and the existing `booklogic` namespace.
   - Verify byte-for-byte parity on `examples/bermuda-manual/` outputs.
   - Delete the Python script.

5. **Update bermuda's `run_verification`.** This becomes either an nbb invocation (`nbb -m bermuda.run-verification`) or is deleted entirely if its job is now done by nbb scripts in `package.json`.

6. **Keep the Rust verifier untouched.** PR-3.5 is the CLJS port. The Rust side already speaks EDN.

7. **Update `verifiers/bermuda/SKILL.md`** (or its equivalent README) to describe the new CLJS-first flow.

8. **Phase 8 QA:**
   - All 23 bermuda tests pass (some will be CLJS now, run via `npm run test:bermuda`).
   - The live nbb integration test (`skills/neurosym-forge/tests/test_cljs_integration.py`) still passes.
   - End-to-end: `examples/bermuda-manual/qa/symbolic-findings.json` is byte-identical to its main-branch counterpart, OR the diff is fully explained in `02-pr3.5-notes.md`.

9. **Wiki update.** Fill in `02-pr3.5-notes.md`: design decisions, hardest port, test-fixture choices, lessons.

10. **Push branch** `codex/phase-3-pr-3.5`. Final commit's For-reviewer body includes spec link, plan link, wiki link, Phase 8 evidence. Suggested PR title: `verifiers/bermuda: port Python ingesters to CLJS (PR-3.5)`.

---

## Phase 4 — PR-4: BookLogic active forms

**Deliverable:** the CLJS compiler at `skills/neurosym-forge/assets/project-template/cljs-orchestrator/src/main/__project__/booklogic.cljs.tmpl` gains four new forms: `defrule`, `defconstraint`, `defquery`, `defremedy`.

**Why:** PR-3 covered the *declaration* forms (defsort, defpredicate, deflift). PR-4 is the *active* layer: rules that fire over facts, constraints the SMT layer must satisfy, queries against the atomspace, remedies that propose state transitions back to the ledger.

**Detailed work order:**

1. **Read the mission spec section on each form.** `docs/specs/2026-05-14-booklogic-v0.4-mission-design.md` covers the seven-form taxonomy. Each form's syntax is specified.

2. **Spec the implementation.** Write `docs/specs/2026-05-15-booklogic-v0.4-pr4-design.md`. Cover: form syntax, expansion targets (what each form compiles to), validation rules, error messages, what `predicates.edn` codegen looks like after these forms exist.

3. **Plan.** `docs/plans/2026-05-15-booklogic-v0.4-pr4.md`. One task per form, plus tasks for the cross-form validation (e.g., `defrule` body referencing predicates not declared via `defpredicate`).

4. **Implement under TDD.** For each form:
   - Write `expand-defrule` (or equivalent) in `booklogic.cljs.tmpl`.
   - Add validation: every predicate referenced must exist; every sort referenced must exist; every variable in the body must appear in the head or be a literal.
   - Add a `booklogic_test.cljs.tmpl` deftest that exercises the form against fixtures.
   - Add a Python-side integration test that scaffolds a project containing the form and asserts the expected compiled output.

5. **Codegen target for `defrule`:** rules emit into a new file `rules/rules.edn` alongside the existing `rules/predicates.edn`. The Rust verifier loads both. Plumb the read path in `verifiers/bermuda/rust-verifier/src/canonical.rs` (or its successor).

6. **Codegen target for `defconstraint`:** constraints emit into `rules/constraints.edn`. These become Z3 assertions in the SMT layer.

7. **Codegen target for `defquery`:** queries emit into `rules/queries.edn`. Used by `book-qa` to ask the verifier specific questions during the QA gate.

8. **Codegen target for `defremedy`:** remedies emit into `rules/remedies.edn`. These describe ledger transitions the verifier can recommend (mapping to `propose_writeback` patterns).

9. **Phase 8 QA:**
   - All 155+ neurosym-forge tests pass.
   - Live nbb integration test passes with new fixtures exercising each of the four new forms.
   - A new scaffolded project that uses all seven forms compiles to non-empty `predicates.edn`, `rules.edn`, `constraints.edn`, `queries.edn`, `remedies.edn` files.

10. **Wiki update.** Fill in `03-pr4-notes.md`. Pay special attention to surprises in the cross-form validation logic.

11. **Push branch** `codex/phase-4-pr-4`. Suggested PR title: `skills/neurosym-forge: BookLogic active forms (defrule/defconstraint/defquery/defremedy) (PR-4)`.

---

## Phase 5 — PR-5: Bermuda migration + real Z3 + quantitative predicates

**Deliverable:** Bermuda's `rules/predicates.edn` is rewritten in terms of the v0.4 form vocabulary. The Rust verifier actually invokes Z3 (not a stub). Four quantitative predicates land: `parishes-count`, `mean-depth`, `coastline-length`, `population`.

**Detailed work order:**

1. **Spec.** `docs/specs/2026-05-15-booklogic-v0.4-pr5-design.md`. Covers: which existing predicates migrate to which v0.4 form; the four new quantitative predicates; Z3 wiring details; verdict-EDN shape changes.

2. **Plan.** `docs/plans/2026-05-15-booklogic-v0.4-pr5.md`. TDD throughout. One task per quantitative predicate. Separate tasks for Z3 wiring.

3. **Migrate predicates.** Replace hand-maintained `predicates.edn` with `rules/booklogic/{sorts,predicates,lifts,rules,constraints}.edn` written in v0.4 forms. `predicates.edn` is regenerated by the CLJS compiler.

4. **Wire real Z3.** The current `verifiers/bermuda/rust-verifier/src/smt.rs` likely stubs SMT. Replace with a real `z3-sys` (or `z3.rs`) integration that produces a sat / unsat / unknown verdict per `defconstraint`.

5. **Four quantitative predicates:**
   - `parishes-count : Bermuda → Int` — extracted via `(parse-int ?n)` lift.
   - `mean-depth : OceanArea → Real` — extracted via `(parse-float ?x)`.
   - `coastline-length : Bermuda → Real` — Real, kilometres.
   - `population : Year → Int` — keyed on year for time-series claims.

   Each gets a `defpredicate`, at least one `deflift`, and at least one `defconstraint` that exercises Z3 (e.g., `(>= (population year) 0)`).

6. **Verdict-EDN shape.** Extend `verdict.edn` to carry per-constraint sat/unsat plus the model when unsat. Document the new shape in `verifiers/bermuda/rust-verifier/src/canonical.rs`.

7. **Phase 8 QA:**
   - All bermuda tests pass.
   - End-to-end: `examples/bermuda-manual/qa/symbolic-findings.json` contains the four new predicate findings.
   - Z3 actually runs (assert in the test that the verdict isn't a placeholder).
   - The bermuda book still composes — run `book-compose` against the workspace and verify chapters survive.

8. **Wiki update.** Fill in `04-pr5-notes.md`. Z3 has subtle behaviors (integer vs real, divide-by-zero, unknown verdicts); record what you learned.

9. **Push branch** `codex/phase-5-pr-5`. Suggested PR title: `verifiers/bermuda: migrate to BookLogic v0.4 + real Z3 + quantitative predicates (PR-5)`.

---

## Phase 6 — PR-6: osmotic-pressure showcase

**Deliverable:** the worked example at `skills/neurosym-forge/worked-examples/osmotic-pressure/` is rewritten end to end using BookLogic v0.4 forms. The README walks a new user from raw text to symbolic verdict.

**Detailed work order:**

1. **Spec.** `docs/specs/2026-05-15-booklogic-v0.4-pr6-design.md`. Brief — this is a showcase, not new functionality.

2. **Plan.** `docs/plans/2026-05-15-booklogic-v0.4-pr6.md`. One task per section of the showcase narrative.

3. **Scaffold a fresh project** in the worked-example directory using `scaffold_project.py`. Build its `rules/booklogic/*.edn` files using every relevant v0.4 form.

4. **Pick a worked claim:** osmotic pressure formula `π = MRT` (van 't Hoff equation). Show:
   - A `defsort` for `Solution`.
   - A `defpredicate` for `osmotic-pressure : Solution → Real`.
   - A `deflift` that extracts the formula from prose text.
   - A `defrule` that derives `osmotic-pressure` from constituent measurements.
   - A `defconstraint` that asserts physical sanity (e.g., temperature > 0K).
   - A `defquery` that asks "what is the osmotic pressure at 298K, 0.1M NaCl?"
   - A `defremedy` that proposes a ledger transition when the constraint fails.

5. **Compile and run.** Show the full pipeline: scaffold → write rules → `npm run booklogic-compile` → `cargo run --bin verify` → verdict.

6. **Update the README** to be a tutorial. The user should be able to follow it as their first BookLogic project.

7. **Phase 8 QA:**
   - The showcase project compiles and verifies end to end.
   - Every command in the README, copy-pasted, works.
   - The neurosym-forge test suite gains an end-to-end test that exercises the showcase project.

8. **Wiki update.** Fill in `05-pr6-notes.md`. Capture which parts of the v0.4 vocabulary felt awkward in practice — this informs v0.5.

9. **Push branch** `codex/phase-6-pr-6`. Suggested PR title: `worked-examples/osmotic-pressure: end-to-end BookLogic v0.4 showcase (PR-6)`.

---

## How to update the wiki

The wiki is your persistent memory across sessions. Discipline matters.

- **At session start:** read `00-index.md`, then the in-progress per-phase file. Skim the last five entries in `99-lessons.md`.
- **At every decision point:** write a one-paragraph entry in the current phase file under `## Decisions made (with rationale)`. Format: `[YYYY-MM-DD HH:MM] decided X because Y. Alternative was Z, ruled out because W.`
- **When an approach fails:** write a `## Surprises / unexpected complexity` entry. This saves the next session from re-exploring.
- **At every PR merge:** add a `## Lessons` paragraph to `99-lessons.md`. Format: `[YYYY-MM-DD PR-N] one-sentence rule. Why: brief context. How to apply: when this kicks in next.`
- **At every phase end:** update `00-index.md`'s status column and add a `last-updated` line.

If you can't think of anything to write, you probably need to do more work before writing.

---

## Working with Claude (the PR opener / reviewer / merger)

After you push a branch:

1. **Make the final commit on the branch carry the For-reviewer body.** Claude reads the last commit on the branch and uses its message body verbatim as the PR body. Use this template:

```
<terse subject — used as PR title if Claude doesn't override>

## For reviewer (Claude)

**Phase:** N — <title>
**Spec:** docs/specs/<filename>
**Plan:** docs/plans/<filename>
**Wiki:** docs/codex-wiki/<filename>

### What to verify
- [bullet] ...
- [bullet] ...
- [bullet] ...

### What I am uncertain about
- ...

### Local QA evidence

\`\`\`
<paste pytest output: counts and key suite names>
<paste npm run test:* output if applicable>
<paste python -m ruff check output if applicable>
\`\`\`
```

2. **Stop after pushing.** Do not invoke `gh`. Do not poll. Do not open the PR yourself. Tell the user "Phase N branch pushed at <SHA>" via your last session output.

3. **Read review feedback on your next session via `git pull origin main`.** Claude lands the review as a separate `review:` PR that adds `openspec/changes/codex-phase-<N>/PR-<N>-REVIEW.md`. Read that file at session start.

4. **Address P0/P1 follow-ups by pushing a new branch.** Name it `codex/phase-<N>-fixes` (or similar). The same handoff cycle applies: push, stop, wait for the merged review file.

5. **Never argue past two rounds of feedback.** If you and Claude disagree after two PR-N-REVIEW.md cycles on the same point, write a `## Disagreement` section to `docs/codex-wiki/<phase-file>.md` summarising both positions and stop. The user breaks ties.

6. **Never open or merge PRs. Never push to main. Never `--amend` published commits.**

---

## Anti-patterns (these will get a PR rejected)

- **PR without `### Local QA evidence`.**
- **PR that bundles a "while-I-was-in-there" fix with the main change.**
- **Commit that says `chore: improvements` or `wip` or anything generic.**
- **AI smells in any user-visible artifact:** `🎯 Goals`, `📋 Plan`, `## Key Insight`, numbered proof steps, `**Proof strategy:**`, ten-level emoji-bulleted lists.
- **`--amend` on a pushed commit.**
- **Refactoring a file as part of a bug fix to that file. Refactor and fix are two PRs.**
- **Wiki entry that paraphrases the PR title without adding signal.** ("Implemented PR-3.5" is not a lesson.)
- **Test that asserts implementation details rather than behavior.** `assert function.__name__ == "foo"` is a smell.
- **Bypassing skill ownership.** If a write needs to land in `claims/`, route it through `book-knowledge`. If you find yourself adding a writer to that directory in any other skill, stop.
- **Using `find` or `ls -R` to enumerate sources.** Use `git ls-files`.

---

## When to stop and surface to the user

- Toolchain is broken (no Python, no node, no gh).
- A pre-commit hook fails three times for non-trivial reasons.
- The spec contradicts the code in a way you can't resolve.
- Claude and you have disagreed twice on the same point.
- A test you didn't change starts failing and you can't explain why.
- You're about to do something the brief forbids but it seems necessary.

Surface format: append a one-paragraph status to `docs/codex-wiki/00-index.md` under a new `## BLOCKED` section, commit, push, and stop. Claude will see the BLOCKED section when opening or reviewing the PR and will route the question back to the user.

---

## Quick-reference commands

```bash
# Run the live nbb integration test
cd skills/neurosym-forge
.venv/Scripts/python.exe -m pytest tests/test_cljs_integration.py -v

# Run all skill tests
for s in book-knowledge book-qa book-compose neurosym-forge book-thesis russellian-style book-review review-conductor; do
  (cd skills/$s && .venv/Scripts/python.exe -m pytest tests/ -q --tb=no || echo "FAIL: $s")
done

# Run the bermuda end-to-end
cd verifiers/bermuda
python -m pytest tests/ -q

# Compile BookLogic in a scaffolded project
cd <scaffolded-project>
npm install
npm run booklogic-compile
npm run test:booklogic

# Push a branch (you do NOT open the PR; Claude does)
git push -u origin codex/phase-N-<slug>

# Address review comments after a merged PR-N-REVIEW.md flagged P1 follow-ups
git checkout -b codex/phase-N-fixes origin/main
git add . && git commit -m "fix(C-001): tighten subject validation in deflift"
git push -u origin codex/phase-N-fixes
```

---

You're equipped. Read AGENTS.md and CLAUDE.md if you haven't yet. Then begin Phase 0.

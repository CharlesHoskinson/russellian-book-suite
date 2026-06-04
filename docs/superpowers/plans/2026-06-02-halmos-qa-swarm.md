# Halmos QA Swarm Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Review the `halmos` skill with a parallel QA swarm, adversarially verify every gating finding, apply TDD fixes for the survivors, and confirm by re-running the test suites plus halmos end-to-end on the agentic-civ book.

**Architecture:** A persisted Workflow script runs phases 1-3 (four read-only dimension reviewers in parallel → a refute-by-default skeptic per critical/important finding → deterministic dedup/bucket producing report data). The controller writes the report, then executes phase 4 (fixes) via subagent-driven-development in a single git worktree with TDD, and phase 5 (re-verify gate) as a command runbook. The report's top-line verdict stays RED until pytest and the book re-run are both green.

**Tech Stack:** Workflow tool (JS sandbox, `agent`/`pipeline`/`parallel`/`phase`), Python 3 + pytest in two venvs (`skills/halmos/.venv`, `skills/book-compose/.venv`), git worktrees.

**Mechanism note:** The Workflow JS sandbox has no filesystem, git, or pytest access — only its spawned subagents do, and parallel worktree commits do not auto-consolidate. Therefore phases 4-5 are controller-driven (SDD + runbook), not in-sandbox. Phases 1-3 are pure fan-out over read-only reads with schema-validated returns, which is exactly what the Workflow tool is for.

**Repo / branch:** `C:\russellian-book-suite`, branch `feat/rust-axum-v2-architecture`. Commits: sole author `Charles Hoskinson <charles.hoskinson@gmail.com>`, terse messages, no AI attribution. Use `git -c user.name="Charles Hoskinson" -c user.email="charles.hoskinson@gmail.com" commit --author="Charles Hoskinson <charles.hoskinson@gmail.com>" -m "..."`.

---

## File Structure

- Create: `docs/qa/qa-halmos-review.mjs` — the Workflow script (phases 1-3). One responsibility: orchestrate review + verify + synth and return report data.
- Create: `docs/qa/2026-06-02-halmos-qa-review.md` — the synthesized review report (controller-written from the script's return).
- Modify (only if a verified finding requires it): `skills/halmos/scripts/*.py`, `skills/halmos/references/*`, `skills/halmos/{SKILL.md,README.md}`, `skills/halmos/tests/*`, `skills/book-compose/scripts/chapter_contract_check.py`, `skills/book-compose/tests/test_halmos_gate.py`.

The reviewers read these in-scope sets (kept disjoint so each agent's context stays small):
- **code**: `skills/halmos/scripts/concept_ledger.py`, `build_linkage.py`, `dispatch_halmos_review.py`, `aggregate_halmos.py`, `conductor.py`, `skill_api.py`
- **doctrine**: `skills/halmos/references/halmos-doctrine.md`, `skills/halmos/references/seed-concepts.txt`
- **tests**: `skills/halmos/tests/test_concept_ledger.py`, `test_build_linkage.py`, `test_aggregate_halmos.py`, `test_conductor_integration.py`, `skills/book-compose/tests/test_halmos_gate.py`
- **fidelity**: `skills/halmos/SKILL.md`, `skills/halmos/README.md`, `docs/superpowers/specs/2026-06-01-halmos-skill-design.md`, `docs/superpowers/plans/2026-06-01-halmos-skill.md`, `skills/book-compose/scripts/chapter_contract_check.py`

---

## Task 1: Author the QA workflow script (phases 1-3)

**Files:**
- Create: `docs/qa/qa-halmos-review.mjs`

This is a single cohesive harness file built up in steps. It is run by the Workflow tool, not by pytest (the sandbox has no test runner); its correctness is enforced by schema-validated agent returns and the phase-5 gate. Each step appends to the file; Step 6 shows the complete assembled file for an out-of-order reader.

- [ ] **Step 1: Create the directory and write the meta + JSON schemas**

```bash
mkdir -p /c/russellian-book-suite/docs/qa
```

Write the head of `docs/qa/qa-halmos-review.mjs`:

```javascript
export const meta = {
  name: 'qa-halmos-review',
  description: 'Review the halmos skill across 4 dimensions, adversarially verify findings, return report data',
  phases: [
    { title: 'Review', detail: '4 read-only dimension reviewers in parallel' },
    { title: 'Verify', detail: 'refute-by-default skeptic per critical/important finding' },
    { title: 'Synth',  detail: 'dedup + severity bucket -> report data' },
  ],
}

const FINDINGS_SCHEMA = {
  type: 'object',
  required: ['dimension', 'summary', 'findings'],
  properties: {
    dimension: { type: 'string' },
    summary: { type: 'string' },
    findings: {
      type: 'array',
      items: {
        type: 'object',
        required: ['id', 'title', 'severity', 'location', 'claim', 'evidence', 'suggested_fix'],
        properties: {
          id: { type: 'string' },
          title: { type: 'string' },
          severity: { type: 'string', enum: ['critical', 'important', 'minor'] },
          location: { type: 'string' },
          claim: { type: 'string' },
          evidence: { type: 'string' },
          suggested_fix: { type: 'string' },
        },
      },
    },
  },
}

const VERDICT_SCHEMA = {
  type: 'object',
  required: ['finding_id', 'verdict', 'reasoning', 'corrected_severity'],
  properties: {
    finding_id: { type: 'string' },
    verdict: { type: 'string', enum: ['real', 'partial', 'refuted'] },
    reasoning: { type: 'string' },
    corrected_severity: { type: 'string', enum: ['critical', 'important', 'minor'] },
  },
}
```

- [ ] **Step 2: Append the reviewer manifests and briefs**

```javascript
const ROOT = 'C:\\\\russellian-book-suite'

const REVIEWERS = [
  {
    key: 'code',
    files: [
      `${ROOT}\\\\skills\\\\halmos\\\\scripts\\\\concept_ledger.py`,
      `${ROOT}\\\\skills\\\\halmos\\\\scripts\\\\build_linkage.py`,
      `${ROOT}\\\\skills\\\\halmos\\\\scripts\\\\dispatch_halmos_review.py`,
      `${ROOT}\\\\skills\\\\halmos\\\\scripts\\\\aggregate_halmos.py`,
      `${ROOT}\\\\skills\\\\halmos\\\\scripts\\\\conductor.py`,
      `${ROOT}\\\\skills\\\\halmos\\\\skill_api.py`,
    ],
    brief: [
      'Review these Python modules for correctness and robustness. Concrete things to check:',
      '- _chapter_n parsing: off-by-one, ids that are not "ch-NN", non-numeric suffixes.',
      '- _norm / _slug: distinct concepts colliding to the same slug; empty or punctuation-only inputs.',
      '- rollup._key in aggregate_halmos.py: does the (check, concept|prior_chapter|detail) fallback ever wrongly merge or wrongly split findings?',
      '- harvest_title_case in concept_ledger.py: the regex and _ARTICLES stripping; what does it do with ALL-CAPS, hyphenated, or footnote-title text?',
      '- _read_halmos_critical in (book-compose, out of your file set but referenced): the 999 mtime sentinel logic and its failure modes.',
      '- file IO: missing files, malformed JSON, encoding; are exceptions handled or do they crash the conductor?',
      'Report only defects you can point at in the code. Each finding needs a file:line location and the exact code as evidence.',
    ].join('\\n'),
  },
  {
    key: 'doctrine',
    files: [
      `${ROOT}\\\\skills\\\\halmos\\\\references\\\\halmos-doctrine.md`,
      `${ROOT}\\\\skills\\\\halmos\\\\references\\\\seed-concepts.txt`,
    ],
    brief: [
      'Review the reviewer doctrine and seed concepts for fidelity and efficacy.',
      '- Is the doctrine faithful to Paul Halmos\\'s spiral-exposition method (concepts reintroduced and deepened, not just cross-referenced)?',
      '- Are the seven checks (orphan-reference, broken-handoff, continuity-gap, missed-recall, spiral-stall, terminology-drift, premature-definition) complete and non-overlapping? Is severity calibrated?',
      '- Two known limitations to assess head-on: (a) footnote-title noise in concept harvesting, e.g. "Safety Gridworlds" / "Existential Risk" captured as concepts; (b) introduced_in = earliest mention marks ch-01 for devices ch-1 only previews, not defines.',
      '- Seam-overlap stopword tuning: could the function-word stoplist produce a false "clean" seam (overlap that is all filler) or a false "broken" seam?',
      'Each finding needs a location (file plus heading or line) and a quote as evidence.',
    ].join('\\n'),
  },
  {
    key: 'tests',
    files: [
      `${ROOT}\\\\skills\\\\halmos\\\\tests\\\\test_concept_ledger.py`,
      `${ROOT}\\\\skills\\\\halmos\\\\tests\\\\test_build_linkage.py`,
      `${ROOT}\\\\skills\\\\halmos\\\\tests\\\\test_aggregate_halmos.py`,
      `${ROOT}\\\\skills\\\\halmos\\\\tests\\\\test_conductor_integration.py`,
      `${ROOT}\\\\skills\\\\book-compose\\\\tests\\\\test_halmos_gate.py`,
    ],
    brief: [
      'Review the tests for rigor and coverage.',
      '- Do tests exercise real behavior or only happy paths? Which branches in the scripts are untested?',
      '- Brittle assertions (exact-string matches that will break on benign change), over-mocking, or tests that would pass even if the code were wrong.',
      '- Missing regressions for the known edge cases: title-case article stripping, target-less duplicate findings in rollup, the gate mtime sentinel (verdict older than draft -> 999).',
      '- Is test_halmos_gate.py actually asserting the gate blocks when the count is non-zero, not just when it is zero?',
      'Each finding names the test (file::test_name) and what is missing or wrong.',
    ].join('\\n'),
  },
  {
    key: 'fidelity',
    files: [
      `${ROOT}\\\\skills\\\\halmos\\\\SKILL.md`,
      `${ROOT}\\\\skills\\\\halmos\\\\README.md`,
      `${ROOT}\\\\docs\\\\superpowers\\\\specs\\\\2026-06-01-halmos-skill-design.md`,
      `${ROOT}\\\\docs\\\\superpowers\\\\plans\\\\2026-06-01-halmos-skill.md`,
      `${ROOT}\\\\skills\\\\book-compose\\\\scripts\\\\chapter_contract_check.py`,
    ],
    brief: [
      'Review the built skill against its spec and plan, plus docs and integration.',
      '- Were the two plan defects fully resolved: (1) Title-Case regex capturing a leading article ("The Authority Airgap"), (2) the deterministic forward-reference check that is logically impossible and was reassigned to the agent layer?',
      '- Does SKILL.md / README accurately describe what the scripts do? Any drift between documented and actual public surface (skill_api.py)?',
      '- AI-slop in the docs (antithesis cadence, rule-of-three, "this skill", empty significance claims).',
      '- Integration: in chapter_contract_check.py, is halmos_critical_count wired so an absent or stale verdict cannot silently satisfy the == 0 gate?',
      'Each finding cites file plus line or heading.',
    ].join('\\n'),
  },
]

const REVIEW_PREAMBLE = [
  'You are a QA reviewer for the "halmos" skill (a chapter-linkage reviewer for a book pipeline).',
  'Read ONLY the files listed below, in full, then report defects in your assigned dimension.',
  'Be concrete and skeptical. Do not invent issues to seem thorough; a short, true report beats a long, padded one.',
  'Do not propose unrelated refactors. Severity: critical = wrong output or a broken gate; important = real bug or real gap that bites in normal use; minor = style, clarity, nit.',
  'Return the FINDINGS object. Give each finding a stable id like "<dimension>-1".',
].join('\\n')

function reviewerPrompt(r) {
  return `${REVIEW_PREAMBLE}\\n\\nDimension: ${r.key}\\n\\nFiles to read:\\n${r.files.map(f => '- ' + f).join('\\n')}\\n\\n${r.brief}`
}
```

- [ ] **Step 3: Append the verify stage (skeptic, refute-by-default)**

```javascript
function skepticPrompt(f, dimension) {
  return [
    'You are an adversarial verifier. A QA reviewer raised the finding below about the halmos skill.',
    'Your job is to REFUTE it. Read the cited location yourself and decide whether the claim actually holds.',
    'Default to "refuted" if you are not sure, or if the claim is subjective taste rather than a defect.',
    'Use "partial" only when a real but narrower or lower-severity issue survives.',
    '',
    `Dimension: ${dimension}`,
    `Finding id: ${f.id}`,
    `Title: ${f.title}`,
    `Severity claimed: ${f.severity}`,
    `Location: ${f.location}`,
    `Claim: ${f.claim}`,
    `Evidence given: ${f.evidence}`,
    `Suggested fix: ${f.suggested_fix}`,
    '',
    'Read the file at that location and return the VERDICT object. corrected_severity is your call, not the reviewer\\'s.',
  ].join('\\n')
}

// Verify one dimension's findings: critical/important get a skeptic; minor pass through unverified.
async function verifyDimension(findings, reviewer) {
  const dim = reviewer.key
  const gating = findings.findings.filter(f => f.severity === 'critical' || f.severity === 'important')
  const minor = findings.findings.filter(f => f.severity === 'minor')
  const verdicts = await parallel(gating.map(f => () =>
    agent(skepticPrompt(f, dim), { label: `verify:${f.id}`, phase: 'Verify', schema: VERDICT_SCHEMA })
      .then(v => ({ ...f, dimension: dim, verdict: v.verdict, corrected_severity: v.corrected_severity, verify_reasoning: v.reasoning }))
  ))
  const minorPass = minor.map(f => ({ ...f, dimension: dim, verdict: 'unverified', corrected_severity: f.severity, verify_reasoning: '' }))
  return { dimension: dim, summary: findings.summary, findings: [...verdicts.filter(Boolean), ...minorPass] }
}
```

- [ ] **Step 4: Append the synth stage (dedup + bucket) and report builder**

```javascript
function dedupeKey(f) {
  const loc = (f.location || '').split(':')[0].trim().toLowerCase()
  return `${loc}|${(f.title || '').trim().toLowerCase()}`
}

function synthesize(perDimension) {
  const all = perDimension.flatMap(d => d.findings)
  const kept = all.filter(f => f.verdict !== 'refuted')
  const refuted = all.filter(f => f.verdict === 'refuted')
  const seen = new Map()
  for (const f of kept) {
    const k = dedupeKey(f)
    if (!seen.has(k)) seen.set(k, f)
  }
  const survivors = [...seen.values()]
  const order = { critical: 0, important: 1, minor: 2 }
  survivors.sort((a, b) => (order[a.corrected_severity] ?? 3) - (order[b.corrected_severity] ?? 3))
  return { survivors, refuted }
}

function reportMarkdown({ survivors, refuted }) {
  const lines = ['# Halmos QA review', '']
  const buckets = ['critical', 'important', 'minor']
  for (const sev of buckets) {
    const items = survivors.filter(f => f.corrected_severity === sev)
    if (!items.length) continue
    lines.push(`## ${sev}`, '')
    for (const f of items) {
      lines.push(`### ${f.title}  \\`[${f.dimension}]\\``)
      lines.push(`- Location: ${f.location}`)
      lines.push(`- Problem: ${f.claim}`)
      lines.push(`- Evidence: ${f.evidence}`)
      lines.push(`- Fix: ${f.suggested_fix}`)
      lines.push('')
    }
  }
  if (refuted.length) {
    lines.push('## Refuted (raised, dismissed on verification)', '')
    for (const f of refuted) {
      lines.push(`- **${f.title}** \\`[${f.dimension}]\\` — ${f.verify_reasoning || 'refuted'}`)
    }
    lines.push('')
  }
  return lines.join('\\n')
}
```

- [ ] **Step 5: Append the body that wires the three phases and returns report data**

```javascript
phase('Review')
const perDimension = await pipeline(
  REVIEWERS,
  r => agent(reviewerPrompt(r), { label: `review:${r.key}`, phase: 'Review', schema: FINDINGS_SCHEMA }),
  (findings, r) => verifyDimension(findings, r),
)

phase('Synth')
const valid = perDimension.filter(Boolean)
const { survivors, refuted } = synthesize(valid)
log(`survivors: ${survivors.length} (crit ${survivors.filter(f => f.corrected_severity === 'critical').length}, imp ${survivors.filter(f => f.corrected_severity === 'important').length}, minor ${survivors.filter(f => f.corrected_severity === 'minor').length}); refuted: ${refuted.length}`)

return { survivors, refuted, report_md: reportMarkdown({ survivors, refuted }) }
```

- [ ] **Step 6: Verify the complete file reads as below, then commit**

The assembled `docs/qa/qa-halmos-review.mjs` is the concatenation of Steps 1-5 in order: `meta` + schemas, then `REVIEWERS` + preamble + `reviewerPrompt`, then `skepticPrompt` + `verifyDimension`, then `dedupeKey` + `synthesize` + `reportMarkdown`, then the phase body. Confirm by reading the file that (a) every function referenced in the body (`reviewerPrompt`, `verifyDimension`, `synthesize`, `reportMarkdown`) is defined above it, and (b) the file ends with the `return { survivors, refuted, report_md }` statement.

```bash
cd /c/russellian-book-suite
git add docs/qa/qa-halmos-review.mjs
git -c user.name="Charles Hoskinson" -c user.email="charles.hoskinson@gmail.com" \
  commit --author="Charles Hoskinson <charles.hoskinson@gmail.com>" \
  -m "halmos QA swarm: review/verify/synth workflow script"
```

Expected: one file committed.

---

## Task 2: Run the swarm and write the report

**Files:**
- Create: `docs/qa/2026-06-02-halmos-qa-review.md`

- [ ] **Step 1: Invoke the workflow**

The controller (you) calls the Workflow tool with `{ scriptPath: "C:\\russellian-book-suite\\docs\\qa\\qa-halmos-review.mjs" }`. This is a controller action, not a shell command. Watch `/workflows` for progress; the run returns `{ survivors, refuted, report_md }`.

Expected: four `review:*` agents complete, then `verify:*` agents for each gating finding, then a `log` line with survivor/refuted counts.

- [ ] **Step 2: Write the report file from the return**

Write the returned `report_md` verbatim to `docs/qa/2026-06-02-halmos-qa-review.md`. Do not add reviewer-process meta (no "4 reviewers found N issues"), no counting flourishes — the report builder already emits only findings and dispositions.

- [ ] **Step 3: Commit the report**

```bash
cd /c/russellian-book-suite
git add docs/qa/2026-06-02-halmos-qa-review.md
git -c user.name="Charles Hoskinson" -c user.email="charles.hoskinson@gmail.com" \
  commit --author="Charles Hoskinson <charles.hoskinson@gmail.com>" \
  -m "halmos QA review report"
```

- [ ] **Step 4: Decide the fix set**

If `survivors` contains zero `critical` and zero `important` findings, skip Task 3 (nothing gating to fix); record in the report that only minor findings remain and proceed to Task 4 to confirm the suite is still green. Otherwise partition the critical/important survivors into file-disjoint clusters (group by the `location` file prefix) and carry that list into Task 3.

---

## Task 3: Fix verified findings (subagent-driven-development, TDD)

Execute this task under superpowers:subagent-driven-development. Each cluster is one implementer subagent followed by a spec-compliance review and a code-quality review. Do the fixes in a worktree so the user's tree is untouched.

**Files:**
- Modify: whichever `skills/halmos/...` or `skills/book-compose/...` files the verified findings cite.

- [ ] **Step 1: Create an isolated worktree**

```bash
cd /c/russellian-book-suite
git worktree add ../rbs-halmos-qa-fix feat/rust-axum-v2-architecture
```

Run all fix work in `C:\rbs-halmos-qa-fix`. (If the implementer subagents use `isolation: "worktree"`, this manual worktree is the parent they branch from; commits land here for consolidation in Task 5.)

- [ ] **Step 2: For each cluster, dispatch one implementer subagent with this brief**

The implementer receives the full finding text (id, location, claim, evidence, suggested_fix) and these instructions verbatim. Do NOT make the subagent read the report file — paste the finding.

```
You are fixing one cluster of verified QA findings in the halmos skill. Work in C:\rbs-halmos-qa-fix.
Use the venv at skills\halmos\.venv (or skills\book-compose\.venv for book-compose files).

Follow TDD strictly:
1. Write or extend a test in the matching tests/ file that FAILS because of this defect. Show the failure.
2. Make the minimal change to the cited file to turn the test green. Do not fix anything not named in the finding.
3. Run the module's full test file and confirm green.
4. Commit with: git -c user.name="Charles Hoskinson" -c user.email="charles.hoskinson@gmail.com" commit --author="Charles Hoskinson <charles.hoskinson@gmail.com>" -m "<terse fix message>"

If the finding turns out not to reproduce (you cannot write a failing test that captures it), STOP and report status "unresolved" with the reason. Do not paper over it. Do not silently widen scope.

Findings in this cluster:
<paste the finding objects here>

Return: status (fixed|unresolved) per finding, the failing-then-passing test name, and the commit SHA.
```

- [ ] **Step 3: Spec-compliance review (per cluster)**

Dispatch the spec reviewer (subagent-driven-development `spec-reviewer-prompt.md`): confirm the change addresses exactly the finding — nothing missing, nothing extra. If issues, the same implementer fixes and re-reviews.

- [ ] **Step 4: Code-quality review (per cluster)**

Dispatch the code-quality reviewer (`code-quality-reviewer-prompt.md`) on the cluster's commits. Loop until approved.

- [ ] **Step 5: Mark unresolved findings**

For any finding the implementer returned `unresolved`, leave it open in the report with the implementer's reason and its failing test output (if any). Never delete it from the report.

---

## Task 4/5 boundary note

Task 4 below is the re-verify gate. It runs whether or not Task 3 produced fixes — a clean review still must prove the suite is green and halmos still runs on the book.

---

## Task 4: Re-verify gate

**Files:** none modified; this task only runs commands and updates the report verdict.

- [ ] **Step 1: Run the halmos unit tests**

```bash
cd /c/rbs-halmos-qa-fix/skills/halmos
.venv/Scripts/python.exe -m pytest tests -q
```

Expected: all halmos tests pass (the suite that was green before plus any new regression tests from Task 3).

- [ ] **Step 2: Run the book-compose gate test**

```bash
cd /c/rbs-halmos-qa-fix/skills/book-compose
.venv/Scripts/python.exe -m pytest tests/test_halmos_gate.py -q
```

Expected: 2 passed (`test_halmos_metric_reads_verdict`, `test_halmos_metric_absent_is_failing_sentinel`).

- [ ] **Step 3: Re-run halmos deterministically over the book (all 15 chapters)**

```bash
cd /c/rbs-halmos-qa-fix/skills/halmos
.venv/Scripts/python.exe -c "
import sys; sys.path.insert(0,'.')
from scripts.concept_ledger import build_concept_ledger
from scripts.build_linkage import build_linkage
from pathlib import Path
WS=Path('C:/agenticcivthoughts/book-workspace')
build_concept_ledger(WS)
broke=[c for c in range(1,16) if build_linkage(WS, f'ch-{c:02d}')['seam']['status']=='broken']
print('broken seams:', broke)
"
```

Expected: `broken seams: []`. If a Task-3 fix changed harvesting or stopwords, confirm no seam regressed to broken.

- [ ] **Step 4: Re-run the ch-13 agent path end-to-end**

Rebuild the ch-13 payload, dispatch one Halmos-reviewer subagent (read `skills/halmos/references/halmos-doctrine.md` + the payload at `C:\agenticcivthoughts\book-workspace\halmos\_payload-ch13.json`, return the strict findings JSON), then aggregate:

```bash
cd /c/rbs-halmos-qa-fix/skills/halmos
.venv/Scripts/python.exe -c "
import sys, json; sys.path.insert(0,'.')
from scripts.dispatch_halmos_review import build_payload
from pathlib import Path
WS=Path('C:/agenticcivthoughts/book-workspace')
p=build_payload(WS,'ch-13')
Path('C:/agenticcivthoughts/book-workspace/halmos/_payload-ch13.json').write_text(json.dumps(p,indent=1),encoding='utf-8')
print('payload chars:', len(p['draft']))
"
```

Then (controller dispatches the Halmos-reviewer subagent, writes its JSON to `halmos/_findings-ch13.json`):

```bash
cd /c/rbs-halmos-qa-fix/skills/halmos
.venv/Scripts/python.exe -c "
import sys, json; sys.path.insert(0,'.')
from scripts.build_linkage import build_linkage
from scripts.aggregate_halmos import aggregate_halmos
from pathlib import Path
WS=Path('C:/agenticcivthoughts/book-workspace')
linkage=build_linkage(WS,'ch-13')
findings=json.loads((WS/'halmos'/'_findings-ch13.json').read_text(encoding='utf-8'))
v=json.loads(aggregate_halmos(WS,'ch-13',findings,linkage).read_text(encoding='utf-8'))
print('halmos_critical_count:', v['halmos_critical_count'], '| spiral:', v['spiral_coherence'])
"
```

Expected: `halmos_critical_count: 0`. spiral_coherence is informational.

- [ ] **Step 5: Set the report verdict and commit**

Edit the top of `docs/qa/2026-06-02-halmos-qa-review.md` to add one line directly under the title: `Verdict: GREEN` if Steps 1-4 all passed, else `Verdict: RED` followed by a bullet list of what is still failing (test names / broken seams). Do not claim GREEN if any step failed.

```bash
cd /c/rbs-halmos-qa-fix
git add docs/qa/2026-06-02-halmos-qa-review.md
git -c user.name="Charles Hoskinson" -c user.email="charles.hoskinson@gmail.com" \
  commit --author="Charles Hoskinson <charles.hoskinson@gmail.com>" \
  -m "halmos QA: re-verify verdict"
```

---

## Task 5: Consolidate and finish

**Files:** none new.

- [ ] **Step 1: Final whole-implementation review**

Dispatch one final code reviewer over the full diff of the worktree branch vs. `feat/rust-axum-v2-architecture` (the workflow script, the report, and every fix commit). Confirm: only in-scope files changed, every fix has a regression test, no AI attribution in any commit, report has no process-meta/counting slop.

- [ ] **Step 2: Merge the worktree branch back**

```bash
cd /c/russellian-book-suite
git merge --no-ff --no-edit -  # merge the worktree's commits; resolve nothing if fast-forwardable
git worktree remove ../rbs-halmos-qa-fix
```

If the worktree committed on the same branch (no separate branch was created), the commits are already present; in that case skip the merge and only run `git worktree remove ../rbs-halmos-qa-fix`.

- [ ] **Step 3: Report to the user**

Summarize: the report path, the verdict (GREEN/RED), the surviving findings by severity and their fix dispositions, and any unresolved items. No counting flourishes, no reviewer-process meta.

---

## Self-Review

**Spec coverage:**
- 4 reviewers across the 4 dimensions → Task 1 Step 2 (REVIEWERS) + Task 2 Step 1. ✓
- Refute-by-default skeptic per critical/important; minor pass-through → Task 1 Step 3 (`verifyDimension`, `skepticPrompt`). ✓
- Deterministic dedup + severity bucket → Task 1 Step 4 (`synthesize`, `dedupeKey`). ✓
- Report with refuted appendix, no meta/counting → Task 1 Step 4 (`reportMarkdown`) + Task 2 Step 2. ✓
- Fix executor, TDD, worktree, unresolved-not-dropped → Task 3. ✓
- Re-verify gate (pytest both suites + book deterministic + ch-13 agent path), RED blocks clean → Task 4. ✓
- Honesty rules (refuted logged, fixer failure stays open, gate failure leads report, sole attribution) → Tasks 3 Step 5, 4 Step 5, commit lines throughout. ✓

**Placeholder scan:** No TBD/TODO. The only deliberately dynamic content is the fix set (unknowable until the review runs); Task 2 Step 4 defines exactly how it is derived and Task 3 consumes it. The Halmos-reviewer JSON in Task 4 Step 4 is produced by a dispatched subagent, matching the established ch-13 procedure.

**Type/name consistency:** `FINDINGS_SCHEMA`/`VERDICT_SCHEMA`, finding fields (`id,title,severity,location,claim,evidence,suggested_fix`), verdict fields (`finding_id,verdict,corrected_severity,reasoning`), and the helper names (`reviewerPrompt`, `skepticPrompt`, `verifyDimension`, `dedupeKey`, `synthesize`, `reportMarkdown`) are used consistently across Task 1's steps and the phase body.

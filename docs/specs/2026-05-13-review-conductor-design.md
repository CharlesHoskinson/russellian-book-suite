# review-conductor — Multi-Panel Editorial Review Orchestration

Design doc. 2026-05-13. Target: russellian-book-suite v6.x.

## Problem

The existing `book-review` skill runs a fixed five-persona panel against chapter drafts. Two reviewer lenses already proved their value in the v6.1 README review pass — an AI-slop detector and a first-time-visitor 30-second test — but they have no home in the skill suite. They live as ad-hoc Agent dispatches in a session transcript.

Three deficiencies follow:

1. **The panel is hard-wired.** Adding a sixth or seventh persona means editing `book-review`'s loader and aggregator. No declarative configuration.
2. **Severity gating is uniform.** Any critical finding from any persona blocks. There is no way to declare "Lay Reader critical is advisory but Domain Expert critical is gating."
3. **No exemplar memory.** Each review pass starts blind. The seven persona reviews of the v6.1 README produced exactly the kind of pattern-illustration that Anthropic's "Outcomes" pattern is designed to harvest, and the suite has no place to store them.

`review-conductor` makes panels declarative, severity per-persona configurable, and exemplars first-class.

## Scope

In:
- New skill `review-conductor` at `skills/review-conductor/`.
- New personas `ai-slop-detector` and `first-time-visitor` added to `book-review/personas/`.
- New Outcomes exemplar library at `book-review/references/outcomes/`, seeded with the v6.1 README review pass.
- One panel config shipped: `panels/chapter-default.yaml` (seven personas).
- One-line switch in `book-compose/scripts/persona_review_pass.py` to invoke `review-conductor` instead of `book-review` directly.

Out:
- Additional artifact scopes (README, intro, marketing). v1 ships chapter-only. The conductor's API accepts an `artifact_scope` field so adding scopes later is a config change, not a code change.
- Anthropic's Dreaming feature (memory consolidation across sessions). Six weeks old; revisit in a later spec.
- Auto-curation of outcomes exemplars. v1 requires manual deposit + curation gate.
- Any changes to `book-knowledge`, `book-qa`, `russellian-style`, `book-thesis`.

## Architecture

```
       chapter draft + chapter contract
                    │
                    ▼
       ┌────────────────────────────┐
       │  review-conductor          │
       │  load_panel.py             │  panels/<panel-id>.yaml
       │  outcomes_loader.py        │  references/outcomes/<exemplar>
       └──────────────┬─────────────┘
                      │ panel + exemplars + draft path
                      ▼
       ┌────────────────────────────┐
       │  book-review (existing)     │
       │  prepare_dispatch_packets   │  augmented persona registry
       └──────────────┬─────────────┘
                      │ N dispatch packets, parallel Task() calls
                      ▼
       ┌────────────────────────────────────────────────────┐
       │  Persona subagents (isolated contexts)             │
       │  ├─ gottlieb           severity: gating            │
       │  ├─ lay-reader         severity: advisory          │
       │  ├─ domain-expert      severity: gating            │
       │  ├─ copyeditor         severity: gating            │
       │  ├─ enjoyment-reader   severity: advisory          │
       │  ├─ ai-slop-detector   severity: gating            │
       │  │     delegates_to: humanizer                     │
       │  └─ first-time-visitor severity: advisory          │
       └──────────────┬─────────────────────────────────────┘
                      │ N markdown reports, severity-tagged
                      ▼
       ┌────────────────────────────┐
       │  review-conductor          │
       │  aggregate_panel.py        │  per-persona severity gate
       │                            │  emits panel-review.md + verdict.json
       └──────────────┬─────────────┘
                      ▼
        verdict ∈ {pass, soft-gate-fail, hard-gate-fail}
        chapters/drafts/<chapter-id>/panel-review.md
        chapters/drafts/<chapter-id>/verdict.json
```

## Components

### New personas in `book-review/personas/`

**`ai-slop-detector.md`.** Delegates to the `humanizer` skill's 24-pattern catalog drawn from Wikipedia's "Signs of AI writing" guide. The persona prompt embeds humanizer's checklist by reference and adds a severity rubric mapping each pattern class to a severity level.

Severity rubric:
- Critical: inflated symbolism / promotional language; listicle abstracts ("rests on N premises"); superficial -ing analyses (verb-string flattening); mechanical thesis enumeration.
- Important: AI vocabulary tells ("leverage", "navigate", "delve", "tapestry", "harness"); em-dash overuse; negative parallelism ("not just X but Y"); filler phrases ("it is worth noting that"); hedging chains.
- Minor: predictable paragraph transitions ("Furthermore", "Moreover"); empty intensifiers ("very", "extremely").

Output format: severity-tagged findings plus a one-word AI-fingerprint score (`low | moderate | high | severe`) with one-sentence justification.

**`first-time-visitor.md`.** A 30-second drive-by simulation. The persona reads the artifact as if arriving from a tweet with thirty seconds to decide whether to keep reading.

Severity rubric:
- Critical (rare): the first paragraph fails to say what or why; by line 50 the persona cannot summarise the project; the Quickstart looks infeasible in under ten minutes.
- Important: lead is buried; jargon density too high in the first two screens; no concrete output picture.
- Minor: sections that did not need to be there for a first read.

Output format: a structured timeline (`0-15s`, `15-30s`, `30-90s`) plus severity-tagged findings plus a one-sentence project summary.

Both personas conform to the existing `book-review/assets/persona-prompt-template.md` schema.

### New skill `review-conductor`

```
skills/review-conductor/
├── SKILL.md
├── pyproject.toml
├── README.md
├── assets/
│   ├── panel-config.schema.json
│   └── verdict.schema.json
├── panels/
│   └── chapter-default.yaml          # the 7-persona chapter panel
├── scripts/
│   ├── __init__.py
│   ├── load_panel.py                 # YAML loader + JSON-Schema validation
│   ├── dispatch_panel.py             # delegates to book-review.prepare_dispatch_packets
│   ├── aggregate_panel.py            # gate logic; emits panel-review.md + verdict.json
│   ├── outcomes_loader.py            # loads outcomes exemplars; renders few-shot context
│   ├── sibling_skills.py             # alias-namespace loader for book-review modules
│   └── conductor.py                  # public entrypoint: run_panel(workspace, chapter_id, panel_id)
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── fixtures/
    │   ├── panel-default.yaml
    │   ├── panel-no-advisory.yaml
    │   ├── synthetic_outcomes/
    │   └── synthetic_reviews/
    ├── test_load_panel.py
    ├── test_dispatch_panel.py
    ├── test_aggregate_panel.py
    ├── test_outcomes_loader.py
    ├── test_conductor_integration.py
    └── test_anthropic_compliance.py
```

### Panel config schema

```yaml
# panels/chapter-default.yaml
panel_id: chapter-default
artifact_scope: chapter
description: Default seven-persona panel for chapter drafts.
personas:
  - id: gottlieb
    severity_gate: gating          # gating | advisory
  - id: lay-reader
    severity_gate: advisory
  - id: domain-expert
    severity_gate: gating
  - id: copyeditor
    severity_gate: gating
  - id: enjoyment-reader
    severity_gate: advisory
  - id: ai-slop-detector
    severity_gate: gating
    delegates_to: humanizer        # optional; informs the prompt
  - id: first-time-visitor
    severity_gate: advisory
verdict:
  hard_gate: false                 # chapter review is judgment-based
  soft_gate_rule: any_critical_from_gating
outcomes:
  exemplar_paths:
    - ../book-review/references/outcomes/readme-pass-2026-05-13/
  per_persona_exemplars: 1         # how many findings to inject as few-shot
output:
  panel_report_path: chapters/drafts/{chapter_id}/panel-review.md
  verdict_path: chapters/drafts/{chapter_id}/verdict.json
```

JSON Schema for the config lives at `assets/panel-config.schema.json` and is validated on load. Unknown fields raise. The schema and the loader stay in lockstep with explicit tests.

### Outcomes exemplar library

Path: `book-review/references/outcomes/<exemplar-id>/`. Each exemplar is a directory:

```
references/outcomes/readme-pass-2026-05-13/
├── README.md                    # what this exemplar is, when captured, what artifact
├── gottlieb.md                  # the gottlieb finding from this run
├── lay-reader.md
├── domain-expert.md
├── copyeditor.md
├── enjoyment-reader.md
├── ai-slop-detector.md
├── first-time-visitor.md
└── curation-notes.md            # any redactions, why this is a useful exemplar
```

The first exemplar is seeded from the v6.1 README review pass currently in this session. Each persona file is the raw return — short, severity-tagged, illustrative.

`outcomes_loader.py` reads the exemplar directory, picks `per_persona_exemplars` representative findings per persona (random with seed by default; configurable to pick specific severity), and renders them into the persona prompt as few-shot under a "Recent findings from this rubric" header.

### Severity gate logic

Pseudocode:

```python
def compute_verdict(panel, persona_reports, deterministic_failures):
    gating_criticals = 0
    advisory_criticals = 0
    for persona in panel.personas:
        report = persona_reports[persona.id]
        criticals = count(report.findings, severity="critical")
        if persona.severity_gate == "gating":
            gating_criticals += criticals
        else:
            advisory_criticals += criticals
    if panel.verdict.hard_gate and deterministic_failures > 0:
        return Verdict("hard-gate-fail", ...)
    if panel.verdict.soft_gate_rule == "any_critical_from_gating" and gating_criticals > 0:
        return Verdict("soft-gate-fail", gating_criticals=gating_criticals)
    return Verdict("pass", advisory_criticals=advisory_criticals)
```

`verdict.json` schema:

```json
{
  "panel_id": "chapter-default",
  "artifact": {"type": "chapter", "id": "ch-01"},
  "verdict": "pass | soft-gate-fail | hard-gate-fail",
  "gating_criticals": 0,
  "advisory_criticals": 2,
  "per_persona": {
    "gottlieb": {"critical": 0, "important": 1, "minor": 3},
    "lay-reader": {"critical": 0, "important": 2, "minor": 1},
    "...": "..."
  },
  "report_path": "chapters/drafts/ch-01/panel-review.md",
  "timestamp": "2026-05-13T03:00:00Z"
}
```

### Public API

```python
from review_conductor.conductor import run_panel

verdict = run_panel(
    workspace=Path("/path/to/workspace"),
    chapter_id="ch-01",
    panel_id="chapter-default",
    dispatcher=None,                # default: real Task-tool dispatch via caller
)
# verdict is a Verdict dataclass; verdict.json + panel-review.md written to workspace
```

`run_panel` is the only public symbol. Internal scripts may be imported by sibling skills for testing but the conductor's stable surface is this one function.

### Composition

- **`book-review`** (read-only) — conductor imports `persona_loader`, `dispatch_review.render_prompt`, and `aggregate_reviews` from book-review's `scripts/`. No mutation of book-review's surface; the two new persona files extend its `personas/` directory only.
- **`humanizer`** (delegated-to) — `ai-slop-detector` persona prompt references humanizer's pattern catalog and instructs the subagent to consult it. The conductor does not invoke humanizer programmatically in v1; the persona subagent calls it inline via the Skill tool.
- **`book-compose`** (caller) — `persona_review_pass.py` swaps `book_review.run_review_pass(...)` for `review_conductor.run_panel(panel_id="chapter-default", ...)`. The return shape stays the same: an aggregator object that exposes `persona_critical_count`.
- **`book-qa`** (orthogonal) — runs after the conductor on the built artefact. No coupling.

### Testing

TDD-shaped per repo convention.

- `test_load_panel.py` — schema validation; missing-persona errors; severity-gate enum; unknown-field rejection.
- `test_dispatch_panel.py` — packet construction; outcomes-exemplar injection in prompt body; persona ordering deterministic.
- `test_aggregate_panel.py` — gate logic across all combinations of gating × critical-count; verdict-json schema validation.
- `test_outcomes_loader.py` — exemplar shape validation; few-shot rendering; seed-stable selection.
- `test_conductor_integration.py` — full seven-persona panel against a fixture chapter draft, stubbed LLM dispatcher; verdict matches expectation.
- `test_anthropic_compliance.py` — trigger calibration; description matches negative-trigger list.

No live LLM calls in tests. All dispatchers and humanizer-call sites take a callable parameter (`dispatcher=fake_dispatcher`, `llm_call=fake_llm`).

Test target: thirty-plus tests covering the conductor; ten-plus tests covering each new persona's loading and prompt rendering (extensions to `book-review`'s existing test suite).

## Migration

Two pull requests:

1. **PR-A** — extends `book-review` only.
   - Add `personas/ai-slop-detector.md` and `personas/first-time-visitor.md`.
   - Add `references/outcomes/readme-pass-2026-05-13/` exemplar (seven persona reviews from this session).
   - Add tests covering the two new personas through the existing loader.
   - Ships independently. Existing book-review consumers can opt in by passing `personas=[..., "ai-slop-detector", "first-time-visitor"]` to `run_review_pass`.

2. **PR-B** — adds `review-conductor`.
   - Depends on PR-A.
   - All of the conductor skill at `skills/review-conductor/`.
   - One-line switch in `book-compose/scripts/persona_review_pass.py`.
   - Updates `book-compose/SKILL.md` Stage-7 description.

PR-A is shippable alone and provides value (the new personas are usable through the existing `book-review.run_review_pass` API). PR-B is the orchestration layer.

## Invariants

Five contracts the conductor must hold:

1. The conductor never writes outside `chapters/drafts/<chapter-id>/`. The panel report and verdict.json live with the draft.
2. The conductor never writes into `book-review`'s subtree. Personas and outcomes ship as files in `book-review/`; conductor reads them.
3. The conductor never invokes a sibling skill's mutating endpoints. Only `book-review.prepare_dispatch_packets`, `dispatch_review.render_prompt`, and `aggregate_reviews` are imported, all read-only.
4. The default panel config is checked into git. A workspace overlay at `<workspace>/qa/panels/<panel-id>.yaml` overrides per-workspace; the conductor logs which source it used.
5. Verdict is reproducible given the same draft + panel + outcomes seed. Stochastic LLM output produces non-reproducible findings, but the aggregation logic over those findings is deterministic.

## Open questions

None as of 2026-05-13. The user has selected Approach B (chapter scope v1), AI-Slop full-delegation to humanizer, and Outcomes seeded from this session's review pass. The design has no remaining ambiguity that blocks the implementation plan.

## Future work (deferred)

- Additional panel configs: README, intro chapter, marketing copy. Each is a new YAML file under `panels/`; no code change required.
- Anthropic Dreaming integration: between-release consolidation of repeated persona findings into rubric updates. Revisit once Dreaming has six months of production data.
- Auto-curation of outcomes exemplars: a workflow that promotes a recent review pass into the exemplar library after quality screening.
- Cross-panel meta-review: a "panel of panels" that reviews the conductor's own verdicts against past releases.

## References

- Anthropic, ["Building Effective Agents"](https://www.anthropic.com/research/building-effective-agents) — Parallelization and Evaluator/Optimizer patterns this design composes.
- Anthropic, Code with Claude 2026 launch (May 6, 2026) — Managed Agents lead-and-specialists pattern; Outcomes mechanism.
- Wikipedia, ["Signs of AI writing"](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing) — the catalog the `humanizer` skill encodes and the `ai-slop-detector` persona delegates to.
- `docs/specs/2026-05-11-book-qa-v5-design.md` — Sentinel-Healer pattern this design's per-persona severity-gate echoes structurally.
- `docs/specs/2026-05-11-bundle-c-closed-loop-ledger-design.md` — closed-loop pattern this design extends (review-side loop, vs. ledger-side loop).

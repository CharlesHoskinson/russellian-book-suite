# paragraph-weaver — Design Spec

Date: 2026-05-30
Status: design approved, pending spec review → implementation plan
Home: new sibling skill in `russellian-book-suite` (`skills/paragraph-weaver/`)

## 1. Purpose

Take a collection of existing paragraphs and thread them toward a goal by
**reordering** them, **writing bridges** between them, and applying **light seam
edits**. The goal is a pluggable, typed object: `argument | emotion | narrative`.
Paragraph bodies are immutable; only each paragraph's first/last sentence may be
edited, and new bridge text may be inserted between paragraphs.

The engine is goal-agnostic. Each goal-type is a small `Target` adapter behind a
uniform interface. v1 ships the shared engine plus one deep target (`argument`)
and two interface-compliant shallow stubs (`emotion`, `narrative`).

Non-goals: from-scratch drafting, rewriting paragraph bodies, claim ingestion
(that is `book-knowledge`), thesis/consistency checking (that is `book-thesis`),
sentence-grain prose discipline (that is `russellian-style`).

## 2. Settled decisions

- New sibling skill, not an extension of `book-thesis`.
- Shared engine + pluggable `Target` modules. Pluggability proven three ways.
- Mutation level: reorder + bridge + seam-edits. Bodies immutable.
- Architecture: deterministic Python substrate + agent-in-the-loop (the
  `russellian-style` pattern). No decode-time logit steering. No heavy local ML.
- Scope: `argument` deep (reuses the suite); `emotion`/`narrative` are
  interface-compliant stubs explicitly labeled `SHALLOW`. Their deep pipelines
  (valence-curve for emotion; causal-DAG + tension for narrative) are v1.5/v2.

## 3. The Target interface

The engine never knows what a goal-type means; it calls one protocol:

```
Target:
  goal_spec_schema                     # how the goal is captured on disk
  plan_template(goal) -> [Slot]        # ordered typed slots; slots may be empty (= gaps)
  role_tagger(paragraph) -> Role       # paragraph's function in this target's vocabulary
  order_objective(seq, goal) -> float  # scalar; lower = better (soft penalties only)
  gate_hook(frozen_artifacts) -> GateResult   # target-specific scoring over FROZEN artifacts
  prose_policy                         # terminal prose stage for this target (see §8)
```

Everything else — binding, ordering search, weaving, revise loop, reporting,
provenance — lives once in the engine. A new goal-type is one adapter, no engine
change.

### v1 target depth

| Target | Depth | role_tagger | order_objective | gate_hook |
|---|---|---|---|---|
| `argument` | DEEP | Toulmin roles (claim/premise/warrant/rebuttal/conclusion) | claim-coverage-in-planned-order + convincingness edge-loading (soft) | agent-judged coherence + goal-attainment, reported with rationale |
| `emotion` | SHALLOW stub | valence bucket (coarse) | identity / trivial | emits `not-yet-deep` warning |
| `narrative` | SHALLOW stub | beat role (coarse) | identity / trivial | emits `not-yet-deep` warning |

The stubs implement the full protocol so the interface is exercised three ways;
they carry no bespoke pipeline in v1.

## 4. Determinism model (load-bearing)

Non-determinism is confined to artifact **production**. Acceptance is
deterministic.

- `weave.graph.json` splits features by provenance:
  - `features_computed` — entities (NER), embeddings. Deterministic given pinned
    model versions.
  - `features_judged` — role, slot-binding, precedence edges. Agent-produced,
    each carrying a `rationale` span and a `source: {py|agent|human}` tag.
- Agent stages write artifacts to disk with content hashes.
- **The gate is a pure `[py]` function of frozen, content-hashed artifacts.** It
  re-scores the same artifacts identically; `weave-report.md` records the hashes.
  A PASS is reproducible by re-scoring, not by re-running the agent.
- **No best-of-N against the gate.** Each produced artifact set is scored once;
  re-rolls are new artifacts that each stand or fall on their own.
- Verification pass pins model + seed.
- Checkpoint after every stage; resume from last good stage. `human`-sourced
  fields are never overwritten without `--force` (dirty-tracking by input-hash).

## 5. Intermediate representation (text-first, shrunk for v1)

```
weave.goal.md     # goal type + statement + ordered slots. Human-editable.
                  # Echoed for approval BEFORE any weaving (the iteration handle).
weave.graph.json  # nodes: {id, text, entities[], role, provenance, features_computed,
                  #         features_judged{...,rationale}, bound_slot, order_index}
                  # edges: precedence only (single type, directional) in v1.
```

Outputs:
- **provenance-marked Markdown** (default) — source / seam-edit / bridge visually
  marked, generated deterministically from `weave-report.md` so marks cannot drift.
- **clean Markdown** — opt-in after the user approves the marked render.
- **`weave-report.md`** — gate result, artifact hashes, bind map, ordering
  rationale + soft-constraint violations, every seam edit and bridge, GAPS,
  off-goal appendix, bridge-load ratio.

Richer edges (attack/elaboration/causal), a strength scalar, and valence land
only when a target consumes them. Not in v1.

## 6. Pipeline

`[py]` = deterministic; `[agent]` = generative.

1. **PLAN** — `[agent]` extract goal-spec → `weave.goal.md`, echoed for approval.
   `[py]` project ordered slots via `plan_template`.
2. **BIND** — `[py]` entities + embeddings. `[agent]` role-tag, assign each
   paragraph to its best slot, propose precedence edges **with rationale**.
   `[py]` **cycle-detection (Tarjan SCC)** on precedence; a cycle is *reported for
   adjudication*, never crashes (demote the weakest edge in the SCC to a soft
   penalty and surface it).
3. **FEASIBILITY GATE** — `[py]` if required slots unfilled, unbound fraction too
   high, or the entity graph is disconnected → **stop and emit a diagnosis, not a
   document.** The engine can refuse.
4. **ORDER** — `[py]` search minimizing `order_objective`. **One hard constraint:
   validated-acyclic precedence.** Slot-grouping and edge-loading are *soft*
   penalties. Exact topological search at demo scale; block-move neighborhood +
   restarts above that. Report objective value and soft-constraint violations.
5. **WEAVE** — `[agent]` bridge only where the relation is not already inferable
   (enthymeme discipline), drawn from a **closed connective vocabulary**: a bridge
   may name only entities present in the two flanking paragraphs and assert one
   relation from an enumerated set. `[py]` reject any bridge introducing a new
   subject-predicate; a bridge must *carry* its planned relation. When no relation
   is inferable, emit a **typed structural GAP**, not invented prose.
   Seam edits freeze each paragraph's **load-bearing tokens**; after an edit `[py]`
   asserts those tokens survive and the edit does not contradict the body, else
   revert to the original sentence.
6. **REVISE** — `[py]` score the frozen artifacts. `[agent]` if below target,
   run `book-review` personas (advisory) → localized fixes → re-score. Bounded:
   iteration cap + oscillation/plateau detector + **keep-best-seen** (never emit
   the last by default). On give-up, emit the best draft marked `PROVISIONAL` with
   an explicit "gate not met" banner. **Unfilled required slots are first-class
   soft-fail output — never bridge-filled.**

Degenerate inputs short-circuit: N=1 returns input unchanged with a message; N=2
runs but flags "single seam — relation asserted, not triangulated."
`--plan-only` stops after ORDER and emits the bind map + gaps for approval.

## 7. Acceptance gate (v1)

Mechanical, deterministic (over frozen artifacts):
- **no-silent-drops** — set-equality of input vs. output paragraphs; any dropped
  paragraph appears in a visible `## Off-goal (unthreaded)` appendix in the output
  itself, not only the report.
- **feasibility thresholds** — required-slot coverage, unbound fraction, entity-
  graph connectivity.
- **bridge entity-subset** — every bridge's entities ⊆ flanking paragraphs.
- **seam token survival** — load-bearing tokens preserved; no body contradiction.
- **bridge-load ratio** — fraction of the document that is generated connective
  tissue; capped to prevent death-by-bridges.

Agent-judged, with rationale in `weave-report.md`:
- coherence and goal-attainment.

No numeric `τ`/`δ` ships without a calibration corpus; until then the honest gate
state is "agent-judged + reported," not a fabricated threshold. Entity-grid / NLI
scorers are deferred to v1.5; if reintroduced, entity-grid runs at the **seam
(sentence level)** where the model is valid, never over paragraph columns. NLI, if
used, is a version-pinned **soft warning**, never the sole bridge-fidelity gate.

## 8. Integration boundaries

- **`book-thesis`** owns the intent substrate (thesis tree, entailment,
  contradiction). Its public API (`read_thesis_tree`, `API_VERSION=(0,1)`) exposes
  a parent-pointer **tree**, not support/attack edges. Therefore the `argument`
  target, in-workspace, **computes sequencing only** over `book-thesis`'s structure
  and does not recompute contradictions (book-thesis stays the single source of
  truth). If paragraph-level edges are later needed, they arrive via a new
  versioned `read_argument_graph()` on `book-thesis` — never by reaching into
  `.dl`/`.ttl` internals. `book-thesis` should reach `1.0` (or the loader must
  enforce a minor-version floor) before weaver hard-depends on it.
- **Standalone is the default** for loose collections (e.g. a free essay with no
  workspace). `book-thesis` composition applies **only** in-workspace. The
  standalone thesis-extractor shares the same extraction module to prevent drift;
  a differential test asserts the two paths agree in-workspace.
- **`russellian-style`** is the terminal prose stage **for the `argument` target
  only** — it refuses persuasive/fiction genres, which are exactly `emotion`/
  `narrative`. Those targets route to a different (or no) prose policy via
  `Target.prose_policy`. When `russellian-style` runs, it runs **last** and owns
  final prose; weaver seam spans are marked so it normalizes prose while
  preserving the transition's semantic role.
- **`book-review`** personas are consumed as **advisory (soft)**, like the rest of
  the suite. Weaver does not re-harden borrowed persona criticals; its own gate is
  on its sequencing metrics. Weaver declares its position in the pipeline DAG so it
  never double-runs `book-review` when its caller already will (`--no-review`).

## 9. Provenance & trust

The output mixes immutable bodies, edited seams, and generated bridges. The
**provenance-marked render is the default**; the user sees what is theirs vs.
generated before opting into a clean render. Marks are generated from
`weave-report.md` so they cannot drift from reality.

## 10. File layout

```
skills/paragraph-weaver/
  SKILL.md
  skill_api.py                       # public surface, API_VERSION
  engine/  bind.py order.py weave.py revise.py report.py   # PLAN folded into bind in v1
  targets/ base.py argument.py emotion.py narrative.py     # base = Target protocol
  scripts/ features.py provenance.py                       # cheap deterministic substrate only
  assets/  target-registry.json connectives.json
  references/ engine-doctrine.md target-authoring.md
  tests/   (pytest, per the suite convention)
```

Deferred from v1 (`scripts/`): NLI checker, entity-grid scorer, valence lexicons.

## 11. Acceptance test (the demo)

Thread the ten Russell-voice "On Snails" paragraphs toward an **argument** goal,
end-to-end: PLAN → BIND → FEASIBILITY → ORDER → WEAVE → REVISE → provenance render
+ `weave-report.md`. A human reads it and agrees the argument now coheres, every
source paragraph is accounted for, and generated text is clearly marked. If that
runs, the engine is real.

## 12. Deferral list

- **v1.5** — entity-grid coherence scorer (seam-level); NLI bridge soft-check;
  automated goal-attainment gate + `τ`/`δ` calibration corpus; constrained search
  beyond topological; promote `emotion` to a deep target with a valence pipeline.
- **v2** — `narrative` deep target (causal-DAG inference + tension model);
  emotion valence-curve fitting to Reagan's six shapes; multi-target blended goals.

## 13. Open questions for spec review

1. In-workspace `argument`: confirm "weaver computes sequencing only, book-thesis
   owns contradictions" over adding `read_argument_graph()` now.
2. `emotion`/`narrative` stub prose policy: no prose stage, or a minimal
   non-Russellian pass?
3. Connective vocabulary: enumerate the v1 relation set (contrast, elaboration,
   sequence, concession, evidence-of, …) in `connectives.json`.

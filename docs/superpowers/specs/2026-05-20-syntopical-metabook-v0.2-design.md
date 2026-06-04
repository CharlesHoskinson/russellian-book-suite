# syntopical-metabook v0.2 — Theory-induction governance layer

**Status:** Design draft, awaiting user review and a follow-up implementation plan.

## 1. Goal and scope

Turn `syntopical-metabook` from a scaffold (four sub-workflow skeletons in v0.1, never exercised on a real workspace) into the **theory-induction governance layer** of the Russellian Book-Forge suite. The skill takes the rules that `forge induce` (Tier 6) produces and the constraints that `defconstraint` (Tier 1) asserts, partitions their support by editorially-curated **schools of thought**, and emits artifacts that turn raw symbolic verdicts into literature-positioned scholarship.

**In scope for v0.2.** A new sub-workflow under `scripts/governance/` shipping four outputs (per-rule school report, school consensus map, adversarial review, feedback-to-induction gate) sharing one positions ledger.

**Out of scope for v0.2.** The existing `acquire/`, `synthesize/{topic_map,concept_reconcile,disputed_questions}`, `lens/`, and `gap/` sub-workflows from v0.1. Their scaffolds remain in place but stay dormant; a future v0.3 may revisit them.

**Non-goal.** The skill does NOT pick winners. It does not decide which school of thought is correct. It curates the schools, attributes support, and renders the partition — humans (or higher-level review skills) draw conclusions.

## 2. Data model

Two new files per book workspace, both EDN, both byte-deterministic, both diffable.

### 2.1 `syntopical/schools/<school-slug>.edn`

One file per school. Edited by hand. The schools are book-scoped editorial decisions — what counts as "the Praos school" in an EpochPoET workspace is not the right unit for a sevenlayer-ZK workspace. Example:

```clojure
{:version 1
 :school :praos
 :name "Praos school"
 :charter "Adaptively-secure Ouroboros family. Static stake during proof
           window; τ ≤ 1 leader-per-slot; common-prefix, chain-quality,
           chain-growth as the three guarantee triple."
 :members ["praos2017" "ouroboros2017" "genesis2018" "crypsinous2018"
           "hydra2019" "leios2024"]
 :canonical-rejects [:tau-multi-leader :static-vendor-weight]
 :canonical-asserts [:tau-leq-one :delayed-adaptive-corruption-model]}
```

`members` are `doc_id`s the book-knowledge ledger already recognises. `canonical-rejects` / `canonical-asserts` reference predicate or rule keywords; matching them declares the school's position editorially, overriding atom-inferred stance.

### 2.2 `syntopical/positions.edn`

Generated, not edited. The metabook writes it; humans read it. Schema:

```clojure
{:version 1
 :generated-at "2026-05-20T18:00:00Z"
 :positions
 [{:rule-id      :induced/r-001
   :rule-form    (forall [(?e :execution)] (=> ...))
   :source       :induced            ; or :defconstraint
   :school       :praos
   :stance       :supports           ; :supports | :contradicts | :silent | :extends
   :evidence     {:supporting-atoms  ["clm-2026-000042" "clm-2026-000113"]
                  :supporting-docs   ["praos2017" "genesis2018"]
                  :contradicting-atoms []}
   :provenance   {:declared-by-charter? false
                  :computed-from-atoms? true
                  :induction-prov "induced-theory.prov.edn#:induced/r-001"}}]}
```

One row per `(rule, school)` pair. A rule with five schools produces five rows.

### 2.3 Stance derivation

For each `(rule, school)`:

1. **Charter override first.** If `rule-id ∈ school.canonical-asserts`, stance is `:supports`; if `∈ school.canonical-rejects`, stance is `:contradicts`. Editorial declarations win.
2. **Otherwise inferred from atoms.** Look up the rule's `:prov/derived-from-atoms` in `induced-theory.prov.edn`. Map each atom → its `doc_id` → membership in the school. Counts of `(supporting-docs ∩ members)` versus `(contradicting-docs ∩ members)` determine the stance.
3. **For `:defconstraint` rules** (hand-written, no induction provenance): walk the `derive-via` claim links in the claim ledger and treat the cited claims as the support set.

Thresholds default to:
- `:supports` if `len(supporting-docs ∩ members) >= 2 and len(contradicting-docs ∩ members) == 0`
- `:contradicts` if `len(supporting-docs ∩ members) == 0 and len(contradicting-docs ∩ members) >= 1`
- `:extends` if some support exists but the rule's predicates go beyond what the school asserts
- `:silent` otherwise

Thresholds are configurable via `syntopical/governance-config.edn`, created with defaults on first run. The config also names the user's own work for adversarial review purposes (`:self-school :my-own-work` by default).

**Multi-school membership.** A `doc_id` may appear in `members` of more than one school — e.g., a paper that bridges two traditions, or the user's own prior work that fits the Praos pattern. The positions ledger emits one row per `(rule, school)` regardless; a doc supporting a rule contributes to every school it belongs to. This is intentional: schools of thought naturally overlap, and the metabook reflects that rather than forcing a single canonical assignment.

## 3. Sub-workflows

All four read `positions.edn` (plus the source ledgers); none recompute positions.

### 3.1 `governance/build_positions.py` — the ledger writer

The one writer. Reads schools, the induced-theory prov sidecar, the constraint registry, and the claim ledger. Applies the stance-derivation rules from §2.3 and writes `syntopical/positions.edn`. Idempotent. Byte-deterministic. Invoked by `forge govern build`.

### 3.2 `governance/render_per_rule.py` — per-rule school report (PR 1)

For each rule in `positions.edn`, writes `syntopical/rules/<rule-id>.md`. Reviewer artifact — the user reads it to decide whether to accept the rule via `forge revise --rule <id> --accept`.

```
# Induced rule :induced/r-001
> (forall [(?e :execution)] ...)

## Schools

| School      | Stance       | Evidence                                  |
|---          |---           |---                                        |
| praos       | supports     | 3 atoms across praos2017 + genesis2018    |
| algorand    | contradicts  | algorand2017 asserts the negation         |
| casper      | silent       | —                                         |
| my-own-work | extends      | adds bond-floor predicate; not in any cited school |

## Evidence
[atom-by-atom listing, grouped by school, with provenance back to ledger]
```

### 3.3 `governance/render_consensus_map.py` — consensus map (PR 2)

One TikZ figure (`syntopical/figures/consensus-map.tex`) as a bipartite graph: schools on the left, rules on the right, edges coloured by stance (green supports, red contradicts, dashed extends, grey silent). PDF-able via the host paper's `latexmk`; drop-in for the Related Work section. For workspaces without a LaTeX build, also emits `syntopical/figures/consensus-map.svg` via graphviz.

### 3.4 `governance/render_adversarial.py` — adversarial review (PR 3)

For each `defconstraint` and induced rule under the **self-school** (named in `governance-config.edn`, defaulting to `:my-own-work`), check whether any other school contradicts it. Writes `syntopical/adversarial-review.md` flagging the "I should have said something about this" moments — positions the paper takes contrary to a major cited school without acknowledging the divergence.

### 3.5 `governance/induction_gate.py` — feedback to induction (PR 4)

A pure function `governance_filter(induced_rules, positions) -> filtered` returning only rules whose `positions.edn` row meets the user-defined policy (default: `≥2 schools support AND 0 schools contradict`). Wired into `forge induce` as an optional `--governance-gate` flag. Rules failing the gate are written to the prov sidecar with `:prov/status :quarantined-by-governance` and listed in `syntopical/induction-quarantine.md`.

### 3.6 Public surface

`scripts/skill_api.py` exports `build_positions`, `render_per_rule`, `render_consensus_map`, `render_adversarial`, `governance_filter`. The `forge` CLI grows one new top-level subcommand group:

```
forge govern build       # rebuild positions.edn
forge govern report      # render per-rule reports
forge govern map         # render consensus map
forge govern review      # render adversarial review
forge govern quarantine  # show rules failing the governance gate
```

## 4. Boundaries

Unchanged from v0.1 in shape; the new sub-workflow respects them.

- **Reads only.** `syntopical/schools/*.edn`, `rules/booklogic/induced-theory.prov.edn`, `rules/constraints.edn`, `rules/booklogic-schema.edn`, `knowledge/claims/ledger.jsonl`, `raw/manifests/*.json`.
- **Writes only.** `syntopical/positions.edn`, `syntopical/rules/*.md`, `syntopical/figures/*.{tex,svg}`, `syntopical/adversarial-review.md`, `syntopical/induction-quarantine.md`, `syntopical/governance-config.edn`.
- **Never touches** the claim ledger, the RDF graph, the constraint EDN files, any source under `paper/` or `chapters/`. The metabook is a layer above book-knowledge and neurosym-forge; it does not mutate them.
- **No network.** Schools are curated locally; positions are computed from local artifacts. `scrapling-fetch` stays unused for this sub-workflow.

## 5. Dependencies

- `book-knowledge`'s `skill_api` for claim lookup by `doc_id` (already imported via `sibling_skills.load_skill_api` in v0.1).
- `neurosym-forge`'s `_provenance.py` for reading the induced-theory prov sidecar (sibling import; not a new dep).
- Existing `booklogic_adapter.py` for parsing constraint forms.
- No new third-party deps. `pyyaml`, `jsonschema`, the stdlib are sufficient.

## 6. Error handling

- **Missing school file referenced in positions.** Treat that school as silently absent; warn, do not crash.
- **Rule with no atoms** (defconstraint without provenance). Walk the constraint's surface predicates against each school's `canonical-asserts` / `canonical-rejects`; stance falls back to `:silent` if no charter match.
- **Cyclic charter** (school A asserts X, school B rejects X, both list same docs). Allowed by design — the position ledger reflects the inconsistency rather than papering over it.
- **`positions.edn` stale relative to source ledgers.** `build_positions` is idempotent and safe to re-run. Renderers refuse to execute if `positions.edn.generated-at` is older than any source-ledger mtime; the user sees a clear "run `forge govern build` first" message.

## 7. Testing

Three layers, mirroring the existing `tests/unit`, `tests/integration`, `tests/conformance` split.

- **Unit.** Stance-derivation cases (charter-override vs atom-inferred), the threshold logic, schema parsing for `schools/*.edn`. Pure functions; cover edge cases (empty members list, missing prov, all-silent).
- **Integration.** A fixture workspace with 3 schools and 5 rules; the full pipeline produces an expected `positions.edn` (golden file) and the four artifacts.
- **Conformance.** Run against the actual EpochPoET workspace (388 verified claims, 12 mechanised properties post-v0.3-β); assert that the per-rule report for C007 (τ=1) names Praos as supporting. The real-world canary. If it fails, the data model has drifted from reality.

The conformance test is the bridge from v0.1's "never exercised" state to v0.2's "exercised on the project that motivated it."

## 8. PR sequence

Staged across four PRs. Each ships a usable artifact; the ledger lands first because the others depend on it.

| PR | Adds | Touches |
|---|---|---|
| PR 1 | `governance/build_positions.py`, `governance/render_per_rule.py`, school charter format, unit + integration tests for stance derivation + per-rule rendering, conformance test against EpochPoET | New files under `skills/syntopical-metabook/scripts/governance/`; new fixtures under `tests/fixtures/governance-three-schools/`. |
| PR 2 | `governance/render_consensus_map.py`, TikZ template, SVG renderer | New file + fixture. |
| PR 3 | `governance/render_adversarial.py` | New file + fixture. |
| PR 4 | `governance/induction_gate.py`, `forge induce --governance-gate` integration | Cross-skill: adds the flag to `neurosym-forge/scripts/forge_cli.py` `induce` subcommand. |

Each PR independently merges to `main`; each ships with its own conformance test against the EpochPoET workspace where applicable.

## 9. Documentation

`SKILL.md` updates to reflect `governance/` as the v0.2 focus. New `references/governance-playbook.md` walking through:

1. Curate schools for a new book.
2. `forge govern build`.
3. Read `syntopical/rules/*.md` and `adversarial-review.md`.
4. Decide which induced rules to keep; run `forge govern quarantine` to see what failed the gate.
5. Re-run `forge induce --governance-gate` for the next round.

## 10. Open questions / explicit non-decisions

- **Multi-book aggregation.** This design is per-workspace. A future v0.3 may aggregate across workspaces (EpochPoET + sevenlayer + others) into one cross-book topic view; that is deliberately out of scope for v0.2.
- **The four dormant v0.1 sub-workflows.** `acquire/`, `synthesize/{topic_map,concept_reconcile,disputed_questions}`, `lens/`, `gap/` keep their scaffolds. A separate v0.3 design will decide whether to wake them, re-scope them, or remove them.
- **Schools-as-policy lifecycle.** When a school's charter changes (member list edited), all `positions.edn` rows touching it should be invalidated. v0.2 handles this via the staleness check in §6; a more sophisticated invalidator (per-school timestamp) is deferred.

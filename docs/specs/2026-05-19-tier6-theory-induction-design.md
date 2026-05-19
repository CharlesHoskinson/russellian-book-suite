# Tier 6 — Theory Induction Layer — Design

> Design spec. Authored 2026-05-19 after two deep-research reports (GPT + Gemini) converged on the same hybrid architecture. Companion: `docs/plans/2026-05-19-tier6-theory-induction.md` (umbrella TDD plan to be authored after spec approval).

## Problem statement

The framework after Tier 1-5 verifies hand-written BookLogic constraints against extracted atoms. It does not *derive* constraints from a corpus. A human author has to know the relationship `(approx= :herd-immunity-threshold (- 1 (/ 1 :basic-reproduction-number)) :tolerance 0.05)` and write it. The framework verifies; it does not learn.

Tier 6 closes that gap by introducing a **theory-induction layer**: read N source documents, induce typed BookLogic constraints from the extracted atomspace, validate them symbolically, emit them as a versionable artifact with atom-level provenance. The output is deterministic (Z3/egg/Cozo verify induced rules without LLM in the loop); the induction itself is neurosymbolic (LLM proposes candidates inside the BookLogic grammar; symbolic engines validate).

## Architectural alignment

Two deep-research reports converged on the same recommended hybrid:

- LLM proposes BookLogic-shaped candidates only (never invents the language)
- Popper-style typed search with failure-driven pruning
- AMIE/AnyBURL-style relational rule mining for candidate generation
- NUMSYNTH/SMT-style numeric parameter fitting (the `:tolerance` value is fitted, not guessed)
- Cozo Datalog for support counting + contradiction detection
- PROV-O sidecar for atom-level + document-level citations
- AGM-compliant theory revision via entrenchment scoring and contraction
- Bounded propose-validate-repair loops (≤3 iterations per candidate)
- Document-held-out 5-fold validation (not just atom-held-out)

Both reports explicitly recommended SKIPPING: full theorem provers (Lean / Verus), pure symbolic regression as top-level inducer, MLN/Tuffy, Hyperon/PLN runtime, DeepProbLog gradient-through-proofs.

## Architecture

Four stages, all bounded:

```
[corpus of N source documents]
        ↓
[Phase Q SemanticIndex → atom clusters by predicate]
        ↓
   STAGE 1: Candidate generation
        ├─ AMIE/AnyBURL-style Horn-body mining over the Cozo atomspace
        ├─ Popper-style typed search using booklogic-schema.edn mode declarations
        └─ LLM proposer (CLJS via nbb) emits BookLogic-grammar EDN only
        ↓ (grammar-check + type-check; reject 30-50% pre-solver)
   STAGE 2: Symbolic validation
        ├─ Cozo: support count, contradiction count, document diversity
        ├─ NUMSYNTH/SMT: fit tolerances + thresholds via Z3 parameter search
        └─ Repair loop: ≤3 iterations, edit-distance must strictly decrease
        ↓ (document-held-out 5-fold validation)
   STAGE 3: Artifact emission
        ├─ rules/booklogic/induced-theory.edn      (BookLogic forms)
        └─ rules/booklogic/induced-theory.prov.edn (PROV-O sidecar)
        ↓
   STAGE 4: Theory revision (AGM-compliant)
        └─ On new corpus / retracted paper: re-rank entrenchment,
          contract or quarantine; never silent-overwrite
```

## Design decisions (per brainstorming)

| Decision | Choice | Rationale |
|---|---|---|
| Predicate scope | **Closed** | Inducer only finds relationships among already-declared predicates. Maps to AMIE+/Popper sweet spot. Predicate invention deferred to Tier 7 — both reports flag it as open research |
| Cost cap | **Per-rule** | ≤3 LLM repair calls per candidate (AutoVerus pattern). No hard dollar cap; per-attempt discipline emerges from rule count × 3 |
| Inducer home | **ClojureScript via nbb** | Natively reads/writes EDN; lives next to `booklogic.cljs` compiler; LLM calls via `fetch` |
| Semantic retrieval role | **Cluster discovery + Candidate ranking + Provenance enrichment** | Phase Q `SemanticIndex` is the framework's existing vector layer; Tier 6 uses it three ways |
| Artifact location | **Separate `induced-theory.edn`** | Distinct from hand-authored `constraints.edn`. CLJS compiler reads both. Diffable, retractable |
| Validation folds | **5-fold document-held-out** | Standard ML default. Balanced cost vs statistical signal |
| Failure-mode tests | **Top 4 subset** | False-Correction Loop, Outcome-Driven Constraint Violation, Proof-Level Confabulation, Memorization-vs-Induction |

## File structure

```
skills/neurosym-forge/scripts/
  induce_theory.cljs              NEW — main orchestrator (nbb-driven)
  _induction_grammar.cljs         NEW — BookLogic grammar enforcer for LLM output
  _provenance.py                  NEW — PROV-O sidecar reader/writer (Python side)
  _agm_revision.py                NEW — AGM-compliant entrenchment + contraction
  forge_cli.py                    MODIFY — add `induce`, `revise`, `theory` subcommands

skills/neurosym-forge/tests/
  test_induce_theory.py           NEW — integration tests
  test_induction_grammar.py       NEW — grammar enforcement
  test_failure_modes.py           NEW — 4 failure-mode regression tests
  test_provenance_round_trip.py   NEW
  test_agm_revision.py            NEW

verifiers/<project>/rules/booklogic/
  induced-theory.edn              (emitted by `forge induce`)
  induced-theory.prov.edn         (emitted by `forge induce`)

skills/neurosym-forge/eval/prompts/
  induced-theory-domain.md        NEW — Phase N onboarding prompt for Tier 6

docs/specs/
  2026-05-19-tier6-theory-induction-design.md   THIS FILE

docs/plans/
  2026-05-19-tier6-theory-induction.md          NEW — umbrella TDD plan
```

CLI surface (extends Phase U's `forge`):

```bash
forge induce verifiers/adsc-clinical              # induce theory from existing corpus
forge induce verifiers/adsc-clinical --folds 10   # tighter validation
forge revise verifiers/adsc-clinical --retracted-paper pmid:12345
forge theory verifiers/adsc-clinical              # inspect induced-theory.edn + sidecar
```

## Schema: induced-theory.edn

```edn
;; rules/booklogic/induced-theory.edn — emitted by Tier 6 inducer
{:version 1
 :inducer-version "0.1"
 :induced-at "2026-05-19T18:00:00Z"
 :source-corpus "verifiers/adsc-clinical/fixtures/claims_clean.jsonl"
 :forms
 [(defconstraint :induced/herd-immunity-threshold
    :scope :subject
    :backend :z3
    :assert (approx= (:herd-immunity-threshold ?d)
                     (- 1.0 (/ 1.0 (:basic-reproduction-number ?d)))
                     :tolerance 0.05)
    :on-unsat {:defect :D-induced-001 :severity :advisory
               :message "herd-immunity-threshold inconsistent with R0 formula"})]}
```

## Schema: induced-theory.prov.edn (PROV-O sidecar)

```edn
;; rules/booklogic/induced-theory.prov.edn — companion sidecar
{:version 1
 :rules
 {:induced/herd-immunity-threshold
  {:prov/derived-from-atoms ["adsc-001-A12" "adsc-014-B03" ...]  ;; 112 atoms
   :prov/source-documents ["pmid:12345" "pmid:67890" ...]        ;; 37 papers
   :prov/contradiction-atoms ["adsc-099-X07" "adsc-103-Y22"]     ;; 4 atoms
   :prov/proposed-by {:lineage :llm :model "claude-haiku-4-5"
                      :provider :anthropic}
   :prov/validated-by [{:backend :z3 :held-out-folds 5
                        :sat-rate 0.89 :tolerance-fit 0.043}
                       {:backend :cozo :support-rate 0.94}]
   :prov/entrenchment 0.83
   :prov/status :active           ;; :active | :tentative | :quarantined
   :prov/llm-repair-calls 2       ;; ≤3 by per-rule cap
   :prov/cost-usd 0.018
   :prov/semantic-neighbours ["c-203" "c-411" "c-512"]}}}
```

The sidecar is the AGM revision target. On a paper retraction, the inducer locates rules with that paper in `:prov/source-documents`, re-runs validation with the paper removed, and either preserves (entrenchment holds), contracts (`:status :tentative`), or quarantines (`:status :quarantined`).

## Test plan (3 layers, ~30 tests)

**Layer A — unit tests** (~15)
- Grammar enforcer rejects malformed EDN candidates
- Cozo support counting returns expected counts on fixture atomspace
- SMT numeric fitter finds correct tolerance on a known-good fixture
- PROV-O sidecar round-trips (read → write → read)
- AGM contraction demotes a rule when its sole supporting paper retracts
- Cost cap halts repair loop after exactly 3 iterations
- 5-fold cross-validation produces 5 distinct fold splits with no document overlap

**Layer B — integration tests** (~7)
- Full pipeline: 10-paper toy corpus → induced rule → verdict on held-out
- LLM proposer's stub backend produces deterministic candidate for CI
- Phase Q semantic clustering correctly groups related atoms before proposal
- Induced rule's defect surfaces in `verification-defects.json` when violated
- `forge induce` CLI runs end-to-end on the epidemiology verifier
- Theory revision: induce → retract paper → revise → entrenchment updates
- Concurrent induction over 2 verifiers doesn't corrupt either's induced-theory.edn

**Layer C — failure-mode regression** (4)
- **False-Correction Loop:** syntactically-valid rule + spurious "error" → proposer does NOT hallucinate a different rule
- **Outcome-Driven Constraint Violation:** inducer rejects a candidate that trivially satisfies coverage (e.g., `(or true X)`)
- **Proof-Level Confabulation:** cycle detection refuses circular definitions
- **Memorization-vs-Induction:** rule that holds on training corpus but fails on document-held-out fold is rejected

Baseline that must not regress: 385 passed, 15 skipped in `skills/neurosym-forge/tests` post-Tier-5.

## Ability checklist — what Tier 6 delivers

| Ability | Before Tier 6 | After Tier 6 |
|---|---|---|
| Verify hand-written constraints against extracted atoms | ✅ | ✅ |
| LLM extracts atoms from prose (Phase P) | ✅ | ✅ |
| Cross-chapter consistency constraints (`:scope :corpus`) | ✅ | ✅ |
| **Read a corpus and DERIVE constraints from it** | ❌ | ✅ |
| **Provenance from rule → atoms → source documents** | ❌ | ✅ |
| **Validate induced rules on held-out documents (5-fold)** | ❌ | ✅ |
| **Cost-controlled LLM induction loop** | ❌ | ✅ (≤3 repair / rule) |
| **AGM-compliant theory revision on paper retraction** | ❌ | ✅ |
| **Distinguish induced rules from hand-authored** | ❌ | ✅ (separate `induced-theory.edn`) |
| **Semantic clustering before LLM proposal** | ❌ | ✅ (Phase Q integration, 3 roles) |
| **Failure-mode regression tests** | ❌ | ✅ (top 4) |
| `forge induce / revise / theory` CLI surface | ❌ | ✅ |
| Predicate invention (new predicates from prose) | ❌ | ❌ (Tier 7) |
| Full theorem proving (Lean / Verus) | ❌ | ❌ (out of scope) |
| Distributed induction across machines | ❌ | ❌ (single-machine only) |
| PLN-style probabilistic logic runtime | ❌ | ❌ |
| Symbolic regression as top-level inducer | ❌ | ❌ (numeric fitting only) |

## Explicitly out of scope (per both reports' "skip" lists)

- Full theorem provers (Lean, Verus) as the validation engine — too expensive
- Pure symbolic regression as top-level inducer — loses relational structure
- MLN/Tuffy probabilistic logic — grounding bottleneck
- Hyperon/PLN runtime — pre-alpha, doesn't solve the framework's actual problem
- DeepProbLog gradient-through-proofs — grounding bottleneck
- Predicate invention from prose — Tier 7 (open research problem)
- Distributed Atomspace / MORK / DAS — single-machine only
- On-chain / Rholang / ASI-Chain compilation — out of scope

## Open gaps after Tier 6 (Tier 7+ candidates)

Both reports identify these as requiring original engineering:
- AST-aware semantic distance metric for AGM minimal-mutation
- Predicate invention from prose under a fixed downstream DSL
- Provenance combinatorial explosion in multi-join Datalog rules
- Calibrating continuous tolerances without full tensor-based SR
- No standard benchmark for corpus-to-theory induction (the framework's eval can become one)

## Phase decomposition

7 phases, each one OpenSpec change folder:

| Phase | Change | REQs target | Scope |
|---|---|---|---|
| V | `tier6-induction-grammar` | INDUCE-040..045 | Grammar enforcer + LLM proposer interface |
| W | `tier6-candidate-generation` | INDUCE-050..055 | AMIE/Popper-style candidate enumeration over Cozo atomspace |
| X | `tier6-smt-numeric-fitting` | INDUCE-060..065 | NUMSYNTH-style Z3 parameter fitting |
| Y | `tier6-provenance-sidecar` | PROV-040..045 | PROV-O sidecar + atom citation tracking |
| Z | `tier6-agm-revision` | REVISE-040..045 | Entrenchment + contraction + quarantine |
| AA | `tier6-induce-cli` | AUTHOR-050..055 | `forge induce` + `forge revise` + `forge theory` |
| BB | `tier6-failure-mode-tests` | TEST-040..043 | The 4 regression tests |

Total: ~40 EARS REQ-IDs across 7 OpenSpec change folders + umbrella TDD plan.

## Source synthesis

Two deep-research reports informed this design:
- `~/OneDrive/Desktop/Neurosymbolic Theory Induction Framework.txt` (Gemini Deep Research)
- `~/OneDrive/Desktop/deep-research-report.md` (GPT Deep Research)

Both reports' bibliographies cite ~40 papers across LLM+symbolic loops (AlphaGeometry, LeanDojo, ProofSketcher, AutoVerus, DSP, Explanation-Refiner), ILP (Popper, Aleph, AMIE+, AnyBURL), symbolic regression (PySR, AI Feynman, LaSR), probabilistic logic (PSL, ProbLog, DeepProbLog, NeurASP, Scallop), provenance (PROV-O, provenance semirings, Datalog proof annotations), and belief revision (AGM, ranking theory, possibilistic, paraconsistent). The architecture above is the consensus design extracted from those bibliographies.

Note: hyperon-experimental and OpenCog Hyperon PLN are explicitly excluded per the prior Tier 5 architectural decision (PR #89 closed) and per both reports' "skip" lists.

## Self-review

**Placeholder scan:** No "TBD", no "TODO", no "implement later". Every concrete code/schema block is fully specified.

**Internal consistency:** The 7 phases (V-BB) map 1:1 to the 4-stage architecture: Stage 1 = V+W; Stage 2 = X; Stage 3 = Y+AA partial; Stage 4 = Z; Tests = BB. CLI (AA) spans Stage 3 + Stage 4 surface.

**Scope check:** Tier 6 is a single coherent subsystem — induce → validate → emit → revise. 7 phases is consistent with prior tier decompositions (Tier 1 had 4, Tier 2-4 had 10, Tier 5 had 7). Single-session subagent execution is feasible per the established worktree pattern.

**Ambiguity check:** Every design decision in the table above has a concrete answer. The remaining open gaps (Section "Open gaps after Tier 6") are explicitly marked as out-of-scope, not ambiguity.

**Source fidelity:** Every architectural choice traces to one or both deep-research reports. Where the reports diverged (PSL vs NeuPSL, ProofSketcher vs AutoVerus repair loop), the more conservative choice was taken (no PSL/NeuPSL probabilistic layer in this tier; AutoVerus-style bounded retry).

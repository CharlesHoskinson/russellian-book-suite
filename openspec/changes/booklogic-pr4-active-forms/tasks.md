# Tasks: booklogic-pr4-active-forms

See `docs/plans/2026-05-17-booklogic-pr4.md` for full TDD steps. Phase /
task numbers correspond 1:1.

## Track A

### Phase 1 — `defrule` expander
- [ ] T1.1: Failing CLJS test for defrule expansion. (REQ-DSL-010)
- [ ] T1.2: Implement `defrule` expander. (REQ-DSL-010)

### Phase 2 — `defconstraint` + `axioms.rs` codegen
- [ ] T2.1: Failing CLJS test for defconstraint intermediate edn shape. (REQ-DSL-020)
- [ ] T2.2: Implement defconstraint expander. (REQ-DSL-020)
- [ ] T2.3: Failing Python test for `axioms.rs` codegen output. (REQ-VERIFIER-BUILD-010, REQ-DSL-021)
- [ ] T2.4: Implement Python codegen (incl. `~=` approx-equality desugaring). (REQ-VERIFIER-BUILD-010, REQ-DSL-021, REQ-DSL-022)
- [ ] T2.5: Failing test for generated tracker-map. (REQ-DSL-023)
- [ ] T2.6: Implement tracker-map emit. (REQ-DSL-023)
- [ ] T2.7: `cargo check --features smt` gate; ship as `feat/booklogic-pr4a` if splitting. (REQ-VERIFIER-BUILD-011)

### Decision point — split or continue

## Track B

### Phase 3 — `defquery` + Cozo `kg.rs`
- [ ] T3.1: Failing CLJS test for defquery expansion. (REQ-DSL-030)
- [ ] T3.2: Implement defquery expander. (REQ-DSL-030)
- [ ] T3.3: Replace `kg.rs` stub with Cozo backend. (REQ-VERIFIER-BUILD-020)
- [ ] T3.4: End-to-end query smoke. (REQ-DSL-031, REQ-VERIFIER-BUILD-021)
- [ ] T3.5: `cargo check --features kg` gate. (REQ-VERIFIER-BUILD-022)

### Phase 4 — `defremedy` + writeback adapter
- [ ] T4.1: Failing CLJS test for defremedy expansion. (REQ-DSL-040)
- [ ] T4.2: Implement defremedy expander. (REQ-DSL-040)
- [ ] T4.3: Failing Python test for `propose_writeback` remedy ingestion. (REQ-QA-PIPE-010)
- [ ] T4.4: Implement `propose_writeback` BookLogic adapter. (REQ-QA-PIPE-010, REQ-QA-PIPE-011)
- [ ] T4.5: `:requires :human-review` blocks auto-apply test. (REQ-QA-PIPE-012)

## Phase 5 — Mission spec footer

- [ ] T5.1: Update mission spec § D4 with merge-SHA placeholder. (no REQ — meta)

## Phase 6 — Full template smoke

- [ ] T6.1: Scaffold fresh project, declare one of each form, run pipeline. (no REQ — meta)

## Phase 7 — PR

- [ ] T7.1: Push + open PR. (no REQ — meta)

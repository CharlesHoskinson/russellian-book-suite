# Tasks: booklogic-pr4-active-forms

See `docs/plans/2026-05-17-booklogic-pr4.md` for full TDD steps. Phase /
task numbers correspond 1:1.

## Track A

### Phase 1 — `defrule` expander
- [x] T1.1: Failing CLJS test for defrule expansion. (REQ-DSL-010)
- [x] T1.2: Implement `defrule` expander. (REQ-DSL-010)

### Phase 2 — `defconstraint` + `axioms.rs` codegen
- [x] T2.1: Failing CLJS test for defconstraint intermediate edn shape. (REQ-DSL-020)
- [x] T2.2: Implement defconstraint expander. (REQ-DSL-020)
- [x] T2.3: Failing Python test for `axioms.rs` codegen output. (REQ-VERIFIER-BUILD-010, REQ-DSL-021)
- [x] T2.4: Implement Python codegen (incl. `~=` approx-equality desugaring). (REQ-VERIFIER-BUILD-010, REQ-DSL-021, REQ-DSL-022)
- [x] T2.5: Failing test for generated tracker-map. (REQ-DSL-023)
- [x] T2.6: Implement tracker-map emit. (REQ-DSL-023)
- [x] T2.7: `cargo check --features smt` gate; ship as `feat/booklogic-pr4a` if splitting. (REQ-VERIFIER-BUILD-011)

### Decision point — ship as one PR-4 (Cozo build resolved)

## Track B

### Phase 3 — `defquery` + Cozo `kg.rs`
- [x] T3.1: Failing CLJS test for defquery expansion. (REQ-DSL-030)
- [x] T3.2: Implement defquery expander. (REQ-DSL-030)
- [x] T3.3: Replace `kg.rs` stub with Cozo backend; REQ-VERIFIER-BUILD-020 template-shape test added. (REQ-VERIFIER-BUILD-020)
- [x] T3.4: End-to-end query smoke. (REQ-DSL-031, REQ-VERIFIER-BUILD-021)
- [x] T3.5: `cargo check --features kg` gate + CI job booklogic-template-cargo-check. (REQ-VERIFIER-BUILD-022)

### Phase 4 — `defremedy` + writeback adapter
- [x] T4.1: Failing CLJS test for defremedy expansion. (REQ-DSL-040)
- [x] T4.2: Implement defremedy expander. (REQ-DSL-040)
- [x] T4.3: booklogic_remedies.py + 8 tests + fixtures. (REQ-QA-PIPE-010)
- [x] T4.4: propose_writeback merges remedy proposals; transition_rules extended. (REQ-QA-PIPE-010, REQ-QA-PIPE-011)
- [x] T4.5: apply_writeback gates on requires:human-review; 1 new test. (REQ-QA-PIPE-012)

## Phase 5 — Mission spec footer

- [x] T5.1: Closure log appended to docs/specs/2026-05-14-booklogic-v0.4-mission-design.md. (no REQ — meta)

## Phase 6 — Full template smoke

- [ ] T6.1: Scaffold fresh project, declare one of each form, run pipeline. (no REQ — controller-executed)

## Phase 7 — PR

- [ ] T7.1: Push + open PR. (no REQ — controller-orchestrated)

# Capability delta: cljs-orchestrator — change: booklogic-pr5-bermuda-migration

## ADD

### REQ-CLJS-ORCH-020 — Event-driven

When `bermuda.core` is invoked with the `verify` subcommand against a
workspace containing a built `bermuda-verifier.node` addon, the verifier
shall return a verdict EDN containing `:verdict` (or `:status`) and, on
`:unsat`, a non-empty `:core` vector.

**Rationale:** First real-verifier path in production CLJS.
**Tested by:** `verifiers/bermuda/cljs-orchestrator/test/bermuda/core_test.cljs::verify-real-verdict` (added in pr5 T5.2)

## MODIFY

(none)

## REMOVE

(none)

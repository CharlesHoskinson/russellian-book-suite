# Capability delta: ingest-trace — change: booklogic-d2-wiring

## ADD

### REQ-TRACE-001 — Event-driven

When `verifiers/bermuda/scripts/run_verification.py` is invoked against a
workspace containing `analysis/ingest-trace.edn`, the verifier shall load
its claim atoms from the trace, not from `claims/ledger.jsonl`.

**Rationale:** The trace is the canonical Phase-1 input per mission §D2.
**Tested by:** `verifiers/bermuda/tests/test_run_verification_consumes_trace.py::test_trace_takes_precedence` (added in d2-wiring T1.1, T1.2)

### REQ-TRACE-002 — Event-driven

When `run_verification.py` projects an `ingest-trace.edn` event stream into
the claim shape downstream code expects, only events with head
`claim/verified` (or downstream-aliased `claim/<verified-status>`) shall
contribute claims; `source/ingested` and other heads shall be skipped.

**Rationale:** Only verified claims pass to the Z3 verifier.
**Tested by:** `verifiers/bermuda/tests/test_run_verification_consumes_trace.py::test_only_verified_events` (added in d2-wiring T1.2)

### REQ-TRACE-003 — State-driven

While a workspace contains `claims/ledger.jsonl` and does NOT contain
`analysis/ingest-trace.edn`, `run_verification.py` shall read claims from
the ledger and behave identically to the pre-d2-wiring code path.

**Rationale:** Legacy workspaces must remain operational.
**Tested by:** `verifiers/bermuda/tests/test_run_verification_consumes_trace.py::test_legacy_workspace_still_works` (added in d2-wiring T2.1)

### REQ-TRACE-004 — Event-driven

When the CLJS `bermuda.core` is invoked with subcommand `translate` against
a trace EDN input, the translator shall return a vector of `Formula`s
matching the schema, dispatching on event head.

**Rationale:** D2 wiring spans Python and CLJS. The CLJS side must accept
the trace shape too.
**Tested by:** `verifiers/bermuda/cljs-orchestrator/test/bermuda/nl_to_fol_test.cljs::translate-trace-input` (added in d2-wiring T4.1)

## MODIFY

(none)

## REMOVE

(none)

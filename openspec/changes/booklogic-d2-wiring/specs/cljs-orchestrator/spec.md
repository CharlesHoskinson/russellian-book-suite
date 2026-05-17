# Capability delta: cljs-orchestrator — change: booklogic-d2-wiring

## ADD

### REQ-CLJS-ORCH-010 — Event-driven

When `bermuda.nl-to-fol/event->formula` receives a list whose head is
`source/ingested` or any non-claim head, it shall return `nil` (skip).

**Rationale:** Non-claim events do not produce formulas.
**Tested by:** `verifiers/bermuda/cljs-orchestrator/test/bermuda/nl_to_fol_test.cljs::event->formula-skips-non-claim` (added in d2-wiring T3.2)

### REQ-CLJS-ORCH-011 — Event-driven

When `bermuda.nl-to-fol/event->formula` receives a list whose head is
`claim/verified`, it shall delegate to `claim->formula` after projecting
the event payload into the legacy `Claim` map shape.

**Rationale:** Re-use existing translation rather than duplicating
business logic.
**Tested by:** `verifiers/bermuda/cljs-orchestrator/test/bermuda/nl_to_fol_test.cljs::event->formula-verified-delegates` (added in d2-wiring T3.3)

## MODIFY

(none)

## REMOVE

(none)

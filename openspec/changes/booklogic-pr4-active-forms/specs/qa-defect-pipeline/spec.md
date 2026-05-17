# Capability delta: qa-defect-pipeline — change: booklogic-pr4-active-forms

## ADD

### REQ-QA-PIPE-010 — Event-driven

When `book-qa.scripts.propose_writeback.py` is invoked with a workspace
whose project carries a `rules/remedies.edn`, the writeback pass shall load
the remedies, match the current verdict shape against each remedy's
`:when` pattern, and emit one proposed transition per matched remedy.

**Rationale:** BookLogic remedies are the new auto-proposal source;
`propose_writeback` must know about them.
**Tested by:** `skills/book-qa/tests/test_propose_writeback_booklogic.py::test_remedies_matched` (added in pr4 T4.3, T4.4)

### REQ-QA-PIPE-011 — Event-driven

When a matched remedy emits a proposed transition, the transition entry
in `claims/proposed-transitions.jsonl` shall carry the source remedy's id
in a `:cause-remedy-id` field, in addition to the existing
`:cause-ticket-id` field for verdict-derived remedies.

**Rationale:** Auditability — the writeback log shows which BookLogic
remedy fired which proposal.
**Tested by:** `test_propose_writeback_booklogic.py::test_proposal_carries_cause_remedy_id` (added in pr4 T4.4)

### REQ-QA-PIPE-012 — Unwanted behaviour

If a matched remedy carries `:requires :human-review`, then the proposed
transition shall NOT be auto-applied by `book-qa.scripts.apply_writeback.py`;
the proposal sits in `proposed-transitions.jsonl` until a human invokes
apply manually.

**Rationale:** Sensitive remedies need a human gate.
**Tested by:** `test_propose_writeback_booklogic.py::test_human_review_blocks_auto_apply` (added in pr4 T4.5)

## MODIFY

(none)

## REMOVE

(none)

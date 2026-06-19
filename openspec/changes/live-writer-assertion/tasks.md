## Tasks

- [x] Trace the V1 live draft loop and S2 writer-assertion contract function signatures. (REQ-ATTR-009..014)
- [x] Add live-path tests for assertion recording, faithfulness status, revise/downgrade before assembly, atomic-fact mapping, novel-draft-claim blocking, and stubbed seams. (REQ-ATTR-009..014)
- [x] Bind emitted sentences to scaffold support claim/span pairs deterministically. (REQ-ATTR-009)
- [x] Call S2 `record_generated_sentence` and `resolve_for_publication` from `draft_chapter`. (REQ-ATTR-009, REQ-ATTR-010, REQ-ATTR-011)
- [x] Call S2 `decompose_paragraph`, `record_atomic_facts`, and `evaluate_paragraph_publication` from `draft_chapter`. (REQ-ATTR-012, REQ-ATTR-013)
- [x] Route novel-draft-claim proposals through book-qa `qa/proposed-transitions.jsonl` via `sibling_skills`. (REQ-ATTR-013)
- [x] Keep all model touchpoints injectable and stubbed in tests. (REQ-ATTR-014)
- [x] Update SKILL.md and drafting-playbook so the agent-facing live path records, checks, resolves, decomposes, and gates assertions. (REQ-ATTR-009..014)

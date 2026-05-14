---
persona: domain-expert
chapter_id: readme-v6.1
verdict: NEEDS_WORK
critical_count: 4
important_count: 3
minor_count: 3
reviewed_at: 2026-05-13T03:00:00Z
---

## Critical findings

1. **[Line 614, "59 + 127 + 94 + 19 + 41 + 16 = 356 tests"]:** book-knowledge collects 123, not 127. Verified via `pytest --collect-only`. Corrected total is 352, not 356.

2. **[Lines 540, 596 — Bermuda example framing]:** The README implies a PDF-ingest demonstration. `examples/bermuda-manual/raw/` contains only `manifests/thesis.json` — no PDFs, no markdown. The workspace `CLAUDE.md` admits the ledger was synthesized from the thesis. The "proof" claim is materially weaker than stated.

3. **[Line 540, "claims/ # ledger (6 files)"]:** Bermuda actually has 3 files. README's invariant cites `events.jsonl`, which does not exist in the only shipped workspace.

4. **[Line 197 — graph/ layout]:** README claims `shapes.ttl` and `imports/` exist; Bermuda has only `dataset.trig` and `reports/`.

## Important findings
- **[Line 564, "total_word_count: 36762"]:** `wc -w` on `manuscript.md` returns 28,018. Different counter; state the methodology.
- **[Line 237 state machine]:** Prose is accurate but diagram omits the `disputed → verified` resolution arrow the code permits.
- **[Line 582, "LLM calls happen at three points"]:** Drafting alone fans out across stages 2 and 4; the count undersells the LLM surface for an auditor.

## Minor findings
- **[Line 296, "28 principles"]:** Not verified against the source; consider citing the file.
- **[Line 558 manifest excerpt]:** Omits `sources_bibliography` and `total_claim_count`; abbreviation is fine but the elision hides the thin-source issue.
- **[Bundle C invariant docstring]:** `run_competency_queries.py` docstring contradicts itself on the BLOCKING_DEFEASIBLE default.

## Notes on voice and cadence
Verified: six SKILL.md paths, five persona files, D1-D12 / C1-C15 taxonomy verbatim, five-state machine state names, Bundle C spec path. The skeleton claims are accurate; the framing claims (the Bermuda "proof") are not.

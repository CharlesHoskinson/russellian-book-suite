# Russell corpus expansion (50 → 500) with hallucination-resistant QA

Status: draft
Owner: russellian-style

## Problem

The `russellian-style` skill anchors its vitality calibration on a 50-paragraph Russell corpus indexed at `skills/russellian-style/assets/russell-corpus/index.json`. Each entry stores metadata only — source URL, line hint, a free-form rhetorical-move string, and a one-line calibration lesson — and full paragraphs are fetched from cached Project Gutenberg sources at retrieve time.

Fifty entries cover the dominant rhetorical moves but leave the long tail thin. The corpus needs to grow to roughly 500 paragraphs to give the vitality linters and the persona panel a denser anchor base across modes. Manual curation at the rate that produced the original 50 does not scale by a factor of ten; full automation without controls confabulates paragraphs that do not exist and tags real paragraphs with moves they do not enact.

This spec describes a four-stage extract-and-verify pipeline that grows the corpus to 500 entries under both deterministic source-grounding and an independent LLM rhetorical cross-check, with operator audit as a final safety net.

## Goals

- Grow `skills/russellian-style/assets/russell-corpus/index.json` from 50 to ~500 entries.
- No entry enters the index whose quoted paragraph cannot be matched verbatim against a cached PD Russell source.
- No entry enters the index whose rhetorical-move tag fails an independent fresh-context LLM reader on the same paragraph.
- No entry enters the index whose calibration lesson is generic across most of Russell rather than specific to the paragraph.
- Every rejection records a reason code in an append-only ledger; nothing is silently dropped.
- The runtime `russellian-style` skill API does not change.

## Non-goals

- Replacing or modifying `retrieve_corpus_anchor.py`. Linear scan over 500 entries is fast enough; embedding-based retrieval is a separate change if warranted.
- Migrating the existing 50 free-form `rhetorical_move` strings to the new controlled vocabulary. The existing entries keep their original strings; new entries use the controlled vocabulary. Normalisation can come later.
- Expanding the source set beyond the six PD works listed in the current `russell-corpus-map.md`. The allow-list is structured to permit additions later, but this spec ships against the same six.
- Touching the three system prompts at `skills/russellian-style/assets/system-prompts/`. Those are downstream consumers of the corpus, not part of this expansion.

## Where it lives

A new one-shot tool under `tools/build-russell-corpus/` with its own `.venv` and `pyproject.toml`, matching the AGENTS.md convention that `tools/` holds workspace-synthesis and tagging utilities.

```
tools/build-russell-corpus/
├── pyproject.toml
├── scripts/
│   ├── derive_vocabulary.py
│   ├── extract_candidates.py
│   ├── sentinel.py
│   ├── cross_check.py
│   ├── audit_sample.py
│   ├── append_to_index.py
│   └── corpus_io.py
├── assets/
│   ├── pd-allow-list.yaml
│   ├── vocabulary.json
│   └── extractor-prompt.md
└── tests/
    ├── test_derive_vocabulary.py
    ├── test_sentinel.py
    ├── test_cross_check.py
    ├── test_append_to_index.py
    ├── test_audit_sample.py
    └── fixtures/
        ├── good_candidate.json
        ├── hallucinated_paragraph.json
        ├── wrong_line_hint.json
        ├── duplicate_existing.json
        ├── novel_tag.json
        ├── wrong_tag.json
        ├── generic_lesson.json
        ├── russell_quoting_hume.json
        └── audit_halt_rate.json
```

The tool reads `skills/russellian-style/assets/russell-corpus/index.json`, appends accepted entries to it, and regenerates `skills/russellian-style/references/russell-corpus-map.md` from the augmented index.

## Pipeline

Four stages, append-only, each emits a JSONL ledger that the next stage reads:

```
PD Russell source (cached by scrapling-fetch)
        │
        ▼
extract_candidates.py   ── LLM extractor, one work per run
        │                  → candidates.jsonl
        ▼
sentinel.py             ── deterministic checks (no LLM)
        │                  → passed-sentinel.jsonl
        │                  → rejected.jsonl   (reason codes)
        │                  → pending-tag.jsonl (held for proposed-tag review)
        ▼
cross_check.py          ── independent LLM tag-verifier, fresh context,
        │                  blind to extractor's proposed tag
        │                  → verified.jsonl
        │                  → rejected.jsonl   (more reason codes)
        ▼
audit_sample.py         ── 5% random sample → audit/sample-<batch>.md
        │                  reject-rate >10% halts the pipeline
        ▼
append_to_index.py      ── writes verified entries to russellian-style
                           corpus index.json; regenerates corpus-map.md
```

### Stage 1 — `extract_candidates.py`

Reads one PD Russell work at a time from the `scrapling-fetch` cache. Loads `assets/extractor-prompt.md` and `assets/vocabulary.json` and asks the LLM to propose N candidate paragraphs (default 100 per work; tunable). Each candidate is a JSON object:

```json
{
  "candidate_id": "problems-051",
  "source_id": "problems",
  "source_url": "https://www.gutenberg.org/files/5827/5827-h/5827-h.htm",
  "line_hint": 812,
  "content_locator": "Philosophy, throughout its history,",
  "paragraph_text": "<verbatim quoted paragraph>",
  "rhetorical_move_tag": "concession-then-distinction",
  "calibration_lesson": "<one specific sentence>"
}
```

The `content_locator` is the first 120 characters of the paragraph and serves as the authoritative locator if Gutenberg renumbers lines across editions.

Production code accepts `llm_call: Callable[[str], str]` so tests can stub responses; matches the suite's discipline.

### Stage 2 — `sentinel.py`

Deterministic checks only, no LLM. Each candidate is checked against:

1. **PD allow-list.** `source_id` must appear in `assets/pd-allow-list.yaml`. Reject reason: `not-pd-allowed`.
2. **Verbatim source match.** SHA-256 of `paragraph_text` must match a sliding window over the cached source file referenced by `source_url`. Reject reason: `source-mismatch`.
3. **Content-locator alignment.** `content_locator` must appear in the cached source within ±50 lines of `line_hint`. If the locator is found elsewhere in the source, the entry is accepted but its `line_hint` is corrected. Reject reason: `locator-not-found`.
4. **Vocabulary check.** `rhetorical_move_tag` must appear in `assets/vocabulary.json`. If not, the entry is held in `pending-tag.jsonl` and the novel tag is appended to `proposed-tags.jsonl` with the operator's email for batched review. Reject reason: not rejected, deferred.
5. **Generic-lesson filter.** `calibration_lesson` is compared against a known-generic phrase list (`assets/generic-phrases.yaml`, seeded from manual review of LLM-generated lessons during prompt tuning). Hits on the list reject. Reject reason: `generic-lesson-filter`.
6. **Dedup.** Content-locator hash compared against existing `index.json` and within the current batch. Reject reason: `duplicate`.

All rejections append to `rejected.jsonl` with `{candidate_id, reason, evidence}`. Passes append to `passed-sentinel.jsonl`.

### Stage 3 — `cross_check.py`

Independent fresh-context LLM agent. Receives only the `paragraph_text` and the full controlled vocabulary; does **not** see the extractor's proposed tag or calibration lesson. Returns:

```json
{
  "candidate_id": "problems-051",
  "top1_tag": "concession-then-distinction",
  "top3_tags": ["concession-then-distinction", "last-sentence-reversal", "common-view-then-turn"],
  "is_quotation": false,
  "lesson_specific_to_paragraph": true,
  "lesson_specificity_evidence": "<one-line justification>"
}
```

Reject rules:

- If the extractor's tag is not in the cross-check's `top3_tags`, reject with reason `tag-disagreement`.
- If `is_quotation` is true, reject with reason `russell-quoting-other-author`.
- If `lesson_specific_to_paragraph` is false, reject with reason `lesson-generic-cross-check`.

Production code accepts a separate `llm_call` parameter. The cross-check agent must run with a different system prompt and ideally a different model than the extractor, to reduce shared-bias collusion. Both LLM choices are configured in `assets/llm-config.yaml`.

Passes append to `verified.jsonl`.

### Stage 4 — `audit_sample.py`

Samples 5% of entries in `verified.jsonl` uniformly at random. Writes `audit/sample-<batch>.md` containing the full paragraph, the proposed tag and lesson, and the cross-check's top-3 tags for each sampled entry, formatted for human reading.

The operator runs through the sample and marks each as `accept` / `reject` / `tag-revise`. If the operator-determined reject rate across the audit sample exceeds 10%, the pipeline halts and emits a `halt-summary.md` with the rejection reasons clustered. The operator tunes the extractor prompt (or vocabulary, or generic-phrases list) and re-runs the batch from `extract_candidates`. No partial batches enter the index.

Audit is the last line of defence against shared-bias drift that all four LLM-and-deterministic checks fail to catch. It also feeds the generic-phrases list and vocabulary refinements back into stage 2 inputs.

### Stage 5 — `append_to_index.py`

Reads `verified.jsonl` (or the post-audit accepted subset, if the audit halted on a previous run and the operator manually accepted a fraction). Appends each entry to `skills/russellian-style/assets/russell-corpus/index.json` and regenerates `skills/russellian-style/references/russell-corpus-map.md` from the augmented index. The map regeneration is deterministic Markdown emission from the index; no LLM involvement.

Existing 50 entries are not touched.

## Controlled vocabulary

`derive_vocabulary.py` runs once, before the first extraction batch. Reads the 50 existing entries from `index.json`, clusters their free-form `rhetorical_move` strings into ~30 controlled tags, and writes `assets/vocabulary.json`. The clustering is committed once and reviewed by the operator before any extraction runs. After that, the vocabulary is stable and changes go through the `proposed-tags.jsonl` channel from sentinel stage 2.4.

Sample vocabulary slugs derived from the existing 50 entries:

- `concrete-example-before-abstraction` (from `problems-001`, `analysis-001`)
- `counterexample-before-conclusion` (from `problems-002`)
- `concession-then-distinction` (from `mysticism-005`, `external-003`)
- `last-sentence-reversal` (from `problems-010`, `free-006`)
- `personified-opposing-view` (from `problems-007`, `political-005`)
- `domain-contrast` (from `free-003`)
- `narrowed-inquiry-after-conclusion` (from `problems-003`)
- `analogy-makes-method-visible` (from `external-008`)
- `binary-dissolved-into-relation` (from `mysticism-007`)
- `principle-bounded-by-conditions` (from `political-006`, `political-008`)

Each tag carries a short prose definition and the corpus entries that anchor it. The full controlled vocabulary is itself reviewable as a single artifact at `assets/vocabulary.json`.

## PD allow-list

`assets/pd-allow-list.yaml` is the only mechanism by which a source is accepted. The initial entries match the existing corpus map exactly:

```yaml
allowed:
  - source_id: problems
    title: "The Problems of Philosophy"
    url: "https://www.gutenberg.org/files/5827/5827-h/5827-h.htm"
  - source_id: mysticism
    title: "Mysticism and Logic and Other Essays"
    url: "https://www.gutenberg.org/files/25447/25447-h/25447-h.htm"
  - source_id: external-world
    title: "Our Knowledge of the External World"
    url: "https://www.gutenberg.org/cache/epub/52091/pg52091-images.html"
  - source_id: analysis-mind
    title: "The Analysis of Mind"
    url: "https://www.gutenberg.org/files/2529/2529-h/2529-h.htm"
  - source_id: free-thought
    title: "Free Thought and Official Propaganda"
    url: "https://www.gutenberg.org/files/44932/44932-h/44932-h.htm"
  - source_id: political-ideals
    title: "Political Ideals"
    url: "https://www.gutenberg.org/cache/epub/4776/pg4776-images.html"
```

Future additions go through a manual operator review and append-only commit to this file.

## Failure-mode coverage matrix

| Failure | Stage that catches it | Mechanism |
| --- | --- | --- |
| Paragraph fabricated wholesale | sentinel | SHA-256 verbatim match against cached source |
| Real paragraph, wrong line hint | sentinel | content-locator alignment within ±50 lines |
| Source not actually PD Russell | sentinel | hard allow-list check |
| Duplicate of existing entry | sentinel | content-locator hash dedup |
| Novel rhetorical-move tag | sentinel | deferred to `pending-tag.jsonl`; novel tag itself appended to `proposed-tags.jsonl` for batched operator review (not rejected, held until tag is approved or rejected) |
| Tag in vocabulary but wrong for paragraph | cross-check | extractor's tag absent from cross-check's top-3 |
| Calibration lesson generic, surface-detectable | sentinel | known-generic phrase list |
| Calibration lesson generic, surface-undetectable | cross-check | independent reader's specificity binary |
| Russell quoting another author | cross-check | dedicated `is_quotation` flag |
| Shared bias across all LLM agents | audit | 5% operator sample with halt threshold |

## Testing

TDD pattern matching the rest of the suite — failing test, minimal impl, passing test, commit. No live LLM calls in tests; `extract_candidates` and `cross_check` accept `llm_call: Callable[[str], str]` parameters and tests pass stubs.

Required fixture coverage:

- Happy-path candidate that passes both sentinel and cross-check.
- Hallucinated paragraph (text not in source) → sentinel rejects with `source-mismatch`.
- Wrong line-hint but content locator matches → sentinel passes, line-hint corrected.
- Duplicate of an existing index entry → sentinel rejects with `duplicate`.
- Novel tag not in vocabulary → sentinel holds in `pending-tag.jsonl`, appends to `proposed-tags.jsonl`.
- Source not on PD allow-list → sentinel rejects with `not-pd-allowed`.
- Generic lesson hits the surface-filter list → sentinel rejects with `generic-lesson-filter`.
- Correct paragraph, extractor tagged it `antithesis`, cross-check top-3 doesn't contain `antithesis` → cross-check rejects with `tag-disagreement`.
- Generic calibration lesson, surface filter missed it → cross-check rejects with `lesson-generic-cross-check`.
- Russell quoting Hume → cross-check rejects with `russell-quoting-other-author`.
- Audit reject-rate at 11% → pipeline halts and emits halt-summary.md.

Each ledger I/O path (read existing index, append to rejected/passed/verified/pending-tag, regenerate corpus-map.md) is tested with `tmp_path` fixtures and round-trip assertions.

## Out of scope

- Modifying `retrieve_corpus_anchor.py`.
- Normalising the existing 50 entries' free-form rhetorical-move strings to the controlled vocabulary.
- Expanding the PD source set beyond the six already in the corpus map.
- Modifying the three system prompts at `skills/russellian-style/assets/system-prompts/`.

## Open questions

- The default cross-check LLM should differ from the extractor LLM to reduce collusion. The current spec mandates "ideally a different model" but does not pin specific models, leaving the configuration to the operator at first run. If the suite settles on two specific models, pin them in `assets/llm-config.yaml` and update this section.
- The "generic phrase" seed list at `assets/generic-phrases.yaml` is empty at first run. The operator populates it from the first batch's audit findings. The audit therefore does more work on the first batch than on subsequent batches.

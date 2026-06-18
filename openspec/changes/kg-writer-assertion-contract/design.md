# Design: kg-writer-assertion-contract

## Goal

Make generated prose auditable without changing the claim ledger ownership model.
S2 governs the output side of writing: every generated sentence has a
writer-assertion binding it to claims and source spans, weak citation support is
revised or downgraded before publication, and paragraph-level atomic facts are
mapped to existing claims or blocked as novel draft claims.

## Storage and Ownership

Writer assertions and draft atomic facts describe generated prose, so they are
book-compose-owned append-only artifacts under the chapter draft directory:

- `chapters/drafts/<chapter-id>/writer-assertions.jsonl`
- `chapters/drafts/<chapter-id>/draft-atomic-facts.jsonl`

Book-compose writes only under `chapters/` for S2. It never writes `claims/`,
`graph/`, `wiki/`, or `raw/`.

Novel draft claims are not promoted to the claim ledger. The publication gate
returns proposal records, and book-qa owns the write of those records to:

- `qa/proposed-transitions.jsonl`

`book-knowledge/scripts/apply_writeback.py` consumes `qa/proposed-transitions.jsonl`
and keeps a read-only legacy fallback to `claims/proposed-transitions.jsonl` for
older QA outputs. Unknown proposal kinds, including `novel_draft_claim`, are
human-review proposals and are never auto-applied by this sprint.

No `kg-schema.edn` entity is added in S2. A future read-only projector can mirror
these append-only artifacts into graph relations if a later sprint needs graph
queries over draft prose.

## Record Shapes

`writer-assertion` records carry:

- `id`
- `chapter_id`
- `paragraph_id`
- `sentence_index`
- `sentence_text`
- `asserts_claim`
- `cites_span`
- `citation_check_status`
- `revision_origin`
- `published_text`
- `flags`

`draft-atomic-fact` records carry:

- `id`
- `chapter_id`
- `paragraph_id`
- `text`
- `claim_id` or `novel_draft_claim`

All records are serialized as sorted-key JSONL. Readers use book-knowledge's
`io_utils.read_jsonl` and `latest_per` via `sibling_skills.load_book_knowledge_module`.

## Faithfulness Check Seam

The sentence-to-span checker is an offline seam:

`check_faithfulness(assertion, span_text_by_id, llm_call, prompt_template=...)`

The caller supplies `llm_call`. Tests pass deterministic fakes. The checker builds
a frozen prompt from the sentence and cited span text, calls the injected callable,
and accepts only `full`, `partial`, or `none`. It performs no network or web calls.

## Revise or Downgrade Policy

`resolve_for_publication` applies the policy:

1. Run the faithfulness check.
2. If status is `full`, publish the sentence unchanged and record
   `revision_origin.action = "unrevised"`.
3. If status is `partial` or `none`, request a revision from the cited span
   through an injected `revise_call`.
4. If the revision differs and re-checks as `full`, publish it with
   `revision_origin.action = "revised-from-span"`.
5. Otherwise publish a hedged non-canonical sentence with
   `flags = ["partial-support"]` and
   `revision_origin.action = "downgraded-partial-support"`.

The original unsupported sentence is never published unchanged.

## Atomic Facts and Novel Claims

`decompose_paragraph` takes an injected `llm_call` and maps every returned atomic
fact either to an existing claim id or to a deterministic `novel-draft-claim` id.
No fact is left unmapped.

`evaluate_paragraph_publication` blocks publication when any atomic fact is novel
and returns proposal records for book-qa to write. The proposal is a gate signal,
not a ledger mutation; book-knowledge remains the only writer that can later apply
accepted changes.

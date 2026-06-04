# Russell corpus extractor

You are reading a single public-domain Bertrand Russell text. Your job is to identify N
paragraphs whose rhetorical move is worth capturing as anchors for a writing-style
calibration corpus.

## What counts as a corpus-worthy paragraph

A paragraph qualifies when it performs one of the controlled-vocabulary rhetorical moves
exactly — concession-then-distinction, counterexample-before-conclusion, last-sentence-reversal,
and so on. The full vocabulary is provided in the {{VOCABULARY}} block; only tags from that
block are legal.

A paragraph does NOT qualify when it merely conveys information, lists, summarises, or
introduces a chapter. The corpus is not a Russell anthology; it is a calibration set for
rhetorical moves.

## Output format

For each qualifying paragraph emit one JSON object on its own line (JSONL). Schema:

```
{
  "candidate_id": "<source>-<NNN>",
  "source_id": "<source>",
  "source_url": "<URL from PD allow-list>",
  "line_hint": <int>,
  "content_locator": "<first 120 chars of the paragraph, verbatim, no leading whitespace>",
  "paragraph_text": "<verbatim paragraph text, single line with internal whitespace preserved>",
  "rhetorical_move_tag": "<one slug from {{VOCABULARY}}>",
  "calibration_lesson": "<one sentence specific to THIS paragraph; not a generic Russell virtue>"
}
```

## Constraints

- Quote `paragraph_text` verbatim. Do not paraphrase. Source-match is verified by SHA.
- Pick the SHORTEST self-contained paragraph that performs the move. Sentence-fragment moves do not count.
- Russell quoting another author does NOT count, even if the quoted text is beautiful. The cross-check stage flags quotations.
- The `calibration_lesson` must be diagnostic: a reader looking at this paragraph should be able to point to the specific phrase or move the lesson describes. Avoid phrases like "uses concrete example" or "varies sentence length" — these are generic and reject.

## Source text

{{SOURCE_TEXT}}

## Controlled vocabulary

{{VOCABULARY}}

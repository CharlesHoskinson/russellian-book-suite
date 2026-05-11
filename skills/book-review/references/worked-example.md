# Worked example: Chapter 4 review pass

This walkthrough exercises the full pipeline on a 1500-word draft of
chapter 4, "Why interleaving needs a witness." The draft contains two
characteristic failure modes that the personas should catch: a listicle
abstract and an anaphoric enumeration. The example shows how those failures
become a soft-gate block, how the author revises, and how the chapter
finally ships.

## 1. The bad draft

The chapter's opening section reads, in part:

> The case for an explicit interleaving witness rests on six premises: that
> coroutines may suspend mid-effect; that effects may be runtime, pure, or
> effectful; that the host may inject side-channels; that the verifier
> cannot observe the WASM stack; that the prover must commit to a trace;
> and that the trace must be reconstructible from the witness alone.
>
> A witness binds the prover. A witness binds the verifier. A witness binds
> the runtime. A witness binds the auditor. Without a witness, none of
> these parties can agree on what happened.

Two patterns to flag:

- The "rests on six premises" sentence is a listicle abstract — six clauses
  bolted onto a colon, none of them developed in the paragraph.
- The four "A witness binds X" sentences are an anaphoric enumeration —
  same structure four times, no information added by the repetition.

## 2. Prepare dispatch packets

```python
from book_review.review_pass import prepare_dispatch_packets

packets = prepare_dispatch_packets(workspace="C:/books/starstream", chapter_id="ch-04")
assert len(packets) == 5
for p in packets:
    print(p.persona_id, "->", p.output_path)
```

Output:

```
gottlieb         -> C:/books/starstream/chapters/drafts/ch-04/reviews/gottlieb.md
domain-expert    -> C:/books/starstream/chapters/drafts/ch-04/reviews/domain-expert.md
lay-reader       -> C:/books/starstream/chapters/drafts/ch-04/reviews/lay-reader.md
copyeditor       -> C:/books/starstream/chapters/drafts/ch-04/reviews/copyeditor.md
enjoyment-reader -> C:/books/starstream/chapters/drafts/ch-04/reviews/enjoyment-reader.md
```

Each packet's `prompt` field contains: the persona body verbatim, the
chapter contract excerpt (title, purpose, intended audience), the chapter
draft markdown, and the output-format schema the subagent must produce.

## 3. Subagent dispatch

The orchestrator issues five Task-tool calls in parallel. Each call uses
`description="Persona review: <display_name>"` and `prompt=packet.prompt`.
The subagents read their persona body as their own role, read the chapter
draft, and write a review file at `packet.output_path`.

A representative finding from `reviews/gottlieb.md`:

```yaml
- severity: critical
  location: "section 4.1, paragraph 1, sentence 1"
  problem: |
    Listicle abstract. Six premises promised, none developed. The colon
    plus six clauses is a tell that the paragraph was generated, not
    written. Cut the abstract; let each premise earn its own paragraph.
  suggestion: |
    Open with the strongest premise as a declarative sentence. Develop it.
    Then the next premise. The reader does not need a table of contents.
```

A representative finding from `reviews/lay-reader.md`:

```yaml
- severity: critical
  location: "section 4.1, paragraph 2"
  problem: |
    I read "A witness binds the prover. A witness binds the verifier. A
    witness binds the runtime. A witness binds the auditor." and stopped.
    I cannot tell what binding means here, and the four-fold repetition
    made me think the writer was stalling. I would put the chapter down.
```

## 4. Aggregate

```python
from book_review.aggregate_reviews import aggregate_reviews

report = aggregate_reviews(workspace="C:/books/starstream", chapter_id="ch-04")
print(report.severity_counts)
print(report.per_persona_verdicts)
```

Output:

```
{'critical': 2, 'important': 11, 'minor': 17}
{
  'gottlieb':         'NEEDS_WORK',
  'domain-expert':    'APPROVED_WITH_NOTES',
  'lay-reader':       'NEEDS_WORK',
  'copyeditor':       'APPROVED_WITH_NOTES',
  'enjoyment-reader': 'APPROVED_WITH_NOTES',
}
```

The two critical findings are the listicle abstract (Gottlieb) and the
anaphoric enumeration (Lay Reader). The aggregator's substring-overlap
deduper recognized that Gottlieb and Enjoyment Reader both flagged the
listicle but kept Gottlieb's stronger phrasing as the gate finding;
Enjoyment Reader's version is preserved verbatim under its own section.

## 5. Soft-gate block

`chapter_contract_check ch-04` reads
`chapters/drafts/ch-04/persona-review.md`, sums critical counts (2), and
fails the contract's `persona_critical_count == 0` acceptance test. The
chapter does not advance to release. The author sees:

```
ch-04 release gate: FAIL
  persona_critical_count: 2 (required: 0)
  blocking findings:
    - gottlieb / 4.1 p1 s1 / listicle abstract
    - lay-reader / 4.1 p2 / anaphoric enumeration
```

## 6. Revision

The author rewrites the opening:

> Coroutines suspend mid-effect. The verifier cannot read the WASM stack.
> Without an explicit interleaving witness, the prover and verifier cannot
> agree on what the program did. The rest of this chapter constructs that
> witness.

The listicle is gone — the strongest premise carries the paragraph alone.
The anaphoric enumeration is replaced by a single causal sentence: the
witness binds *every* party to one trace, and that is the only thing worth
saying.

## 7. Re-run

```python
packets = prepare_dispatch_packets(workspace, "ch-04")
# dispatch all five packets...
report = aggregate_reviews(workspace, "ch-04")
print(report.severity_counts)
```

Output:

```
{'critical': 0, 'important': 6, 'minor': 14}
```

Per-persona verdicts: all five `APPROVED_WITH_NOTES`. The contract gate
passes. The chapter ships. The remaining important and minor findings are
left for the author's discretion; they are not blockers.

## 8. What this example demonstrates

- The pipeline is *honest* about its severity counts. Two critical findings
  blocked the chapter; zero unblocked it. There is no negotiation.
- The personas overlapped where they should and diverged where they should.
  Gottlieb and Lay Reader both noticed prose problems but flagged different
  passages; Domain Expert had nothing to say about cadence; Copyeditor had
  nothing to say about the listicle but caught two cross-chapter notation
  inconsistencies (those are in the 11 important findings).
- Revision was inexpensive. Two critical findings translated to two prose
  surgeries. Soft-gating is cheap because it points at specific lines.

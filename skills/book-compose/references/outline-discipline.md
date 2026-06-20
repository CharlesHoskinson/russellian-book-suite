# Outline Discipline

The outline is an axiomatic derivation. The chapter's `purpose` field is axiom zero. Every section is a lemma whose statement and citations descend from the axiom and from earlier sections. Outlining precedes drafting. The user approves the outline before any prose is written.

## The axiomatic-outline rule

Each section depends only on prior sections plus the chapter contract. Forward references are forbidden. A section that references material introduced two sections later is misplaced. A section that introduces material the rest of the chapter does not consume is dead weight.

The outline lives at `chapters/drafts/<chapter_id>/outline.md`. Each section block has the form:

```markdown
## Section N. <title>

Depends on: <section N-1, N-2, ...>
Establishes: <claims this section asserts and supports>
Cited claims: <claim_id list>
Forecast density: <verified claims per 1000 words>
```

The "Depends on" line names earlier sections. The "Establishes" line lists what the next sections may assume. The "Cited claims" line names anchored support claims from the chapter bundle scaffold. The "Forecast density" line predicts the section's contribution to the chapter-wide evidence density.

## Sideways-drift detection

A section drifts sideways when it does not derive from the thesis. Three symptoms diagnose the drift:

1. The section's "Establishes" line names a topic absent from the chapter's `must_include` list and absent from later sections' "Depends on" lines.
2. The section's "Cited claims" list shares no `doc_id` overlap with adjacent sections.
3. Removing the section leaves the chapter's logical flow intact.

When two of three symptoms are present, fold the section into the most adjacent section that subsumes its claims. If no such section exists, drop the section and surface the orphaned claims for placement in another chapter.

## Per-section evidence-density forecasting

Pull the chapter contract's `evidence_density_target` (verified claims per 1000 words). Estimate the target word count of each section. The section's claim allocation should satisfy:

```
allocated_claims >= ceil(target_word_count * evidence_density_target / 1000)
```

A section forecast below `0.7 * evidence_density_target` triggers a warning during outline review. Either reassign claims from neighbouring sections or shorten the section's word target. Below `0.4 * evidence_density_target` is a hard fail; the user is asked to revise the contract or surface more verified claims.

The chapter-wide cited-claim count must satisfy `evidence_requirements.minimum_verified_claims`. Sum the per-section allocations and reject the outline if the total falls short.

## Folding versus splitting

Fold a section when:
- It shares more than half its cited claims with a neighbour.
- It has fewer than four cited claims and the neighbour has spare capacity.
- Its forecast density falls below the warning threshold.

Split a section when:
- Its forecast word count exceeds 2,000.
- It cites more than fifteen claims.
- It establishes two distinct results that subsequent sections consume independently.

Folding and splitting both rewrite the dependency edges. After either operation, re-check that no forward references remain.

## Contract `must_include` to outline mapping

Every entry in the contract's `must_include` array must map to at least one outline section. The mapping is recorded in the outline file as a trailing block:

```markdown
## Must-include coverage

- prerequisites and dependency layout: section 2
- the verifier inner-loop signature: sections 3, 4
- failure-mode triage with worked traces: section 6
```

An entry without coverage blocks outline approval. Coverage by zero or two-plus sections is permitted; coverage by zero is not.

## User-approval gate

After the outline is written, drafting halts. The user is shown:

1. The outline file path.
2. The section-by-section evidence-density forecast.
3. The must-include coverage map.
4. The unallocated anchored support claims from the chapter bundle scaffold.

The user replies with `approve`, `revise <instruction>`, or `abort`. Only `approve` advances the pipeline to Stage 4. `revise` regenerates the outline with the named instruction; the gate then re-fires. `abort` stops the pipeline without writing further artifacts.

The user-approval gate is non-negotiable. A draft generated without an approved outline is treated as a contract violation by `chapter_contract_check.py`, which compares the draft's section headers against the outline file and fails when they diverge.

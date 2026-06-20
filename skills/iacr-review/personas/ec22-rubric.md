# EUROCRYPT 2022 Review Form (source rubric)

This is the verbatim review form used by EUROCRYPT 2022 and inherited by subsequent
IACR top-tier venues. The `iacr-review` skill grounds every persona review in this
form. Personas fill every section A through I.

## A. Paper summary

A succinct, positive description of the paper's main contributions. The summary
exists for the author and the PC to confirm the reviewer understood the paper.
Do not editorialize here; the editorial judgment lives in C through H.

## B. Suitability

Yes / no. Does the paper belong at this venue? Justify in one line.

## C. Novelty, methodology, technical correctness

### Q1. Does the paper ignore overlapping related work?

Identify prior work the paper should have engaged with and did not. Cite the
specific overlap; do not invent citations.

### Q2. Is the methodology appropriate for the research question?

If the question is "is protocol X secure under assumption Y", the methodology
must be a proof under that assumption — not a simulation, benchmark, or
hand-wave. Flag methodology mismatches.

### Q3. Are there technical flaws affecting correctness?

This is the reviewer's strongest authority. A flawed theorem statement, a
missing simulator query, an unstated assumption that the proof secretly uses,
an attack the paper does not address — all live here. Cite section and line.

## D. Technical details

### Q4. Are technical details missing to verify the contribution?

Even if the paper is correct, can the reviewer confirm it from what is written?
Missing definitions, missing proof steps, missing parameter tables, missing
threat-model boundaries — all live here.

## E. Editorial quality

### Q5. Is the editorial quality sufficient to understand the contribution?

Can a competent reader follow the argument? Notation collisions, undefined
symbols, figures referenced but not present, broken cross-references all
degrade editorial quality.

## F. Scientific quality (only if A through E pass)

If the paper has fundamental correctness or editorial defects, do not score F.
Mark F as "not applicable until C through E are addressed."

### Q6. Importance of the research question

Does the field care? Would a positive answer change practice or open new
directions?

### Q7. Contribution to that research question

Given the question is important, how much does this paper move the needle?

## G. Confidence level

- **1 Weak** — outside reviewer's primary expertise; significant chance the
  reviewer missed something.
- **2 Medium** — reviewer is in the right neighborhood but not at the center
  of the subfield.
- **3 Good** — reviewer is a subfield expert.

## H. Recommendation

- **1 Strong reject** — fundamental errors. Substantial corrections needed
  before the paper can be resubmitted anywhere.
- **2 Weak reject** — missing editorial quality or technical details. A
  clarifying resubmission may change the outcome.
- **3 Borderline** — subjective lack of interest. Try a different PC or a less
  competitive venue.
- **4 Accept** — improves the state of the art on an important question.
- **5 Strong accept** — breakthrough; best-paper candidate.

## I. Comments to PC (hidden from authors)

Concerns the reviewer holds about the paper that would not be productive to
share with authors. Examples: suspicion of a fixable but currently-broken proof
that the author should not be given a roadmap to patch; suspected double
submission; conflicts the reviewer noticed mid-read.

## Conduct rules (IACR Guidelines for Reviewers, Cachin 2011)

- Judge on overall quality and merit.
- Give clear justification for the recommendation. A bare number is not a
  review.
- No rude, derogatory, or unhelpful language. "This is wrong because X at line
  Y" is acceptable; "the authors clearly don't understand crypto" is not.
- Confidentiality. In the `iacr-review` skill this means each persona reviews
  in isolation; personas do NOT see each other's reviews until the consolidator
  runs.
- Anonymity. Treat the paper as anonymous. Do not speculate on authorship or
  affiliation, even if the writing style is recognizable.

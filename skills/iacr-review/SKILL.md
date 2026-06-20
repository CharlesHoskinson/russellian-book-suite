---
name: iacr-review
description: Deterministic harsh review of cryptography papers under the EUROCRYPT 2022 review rubric. Dispatches ten expert-persona reviewers in parallel (game-based crypto, UC, concrete security, BFT consensus, P2P networks, TEE hardware, formal methods, applied crypto, post-quantum, economics/MEV), each filing a full A-I review form, then consolidates findings into a single ledger sorted by severity. Use when user says "review this paper to IACR standards", "Eurocrypt review of <paper>", "harsh review the EpochPoET paper", "what would a PC think of this", "run the IACR panel on <paper.pdf>". Do NOT use for prose-only style review (use book-review), chapter drafts (use book-compose), or non-cryptography papers (use review-conductor with a different panel).
license: MIT
metadata:
  author: charles-hoskinson
  version: 0.1.0
  category: review
  workspace-aware: false
---

# iacr-review

Persona-based review of cryptography papers under the EUROCRYPT 2022 review form
(the de facto IACR top-tier rubric). The skill dispatches ten expert subagents in
parallel, each filing a complete sections A through I review of the same paper.
The consolidator merges them into a single ledger with severity-sorted findings
and cross-persona convergence detection.

## When to use

- "Review this paper to IACR / Crypto / Eurocrypt standards."
- "What would a Eurocrypt PC say about this?"
- "Harsh-review `<paper>.pdf` with the full IACR panel."
- "Run the ten-persona review on the EpochPoET draft."
- Pre-submission self-review: drive the personas against a draft before sending
  it to a real PC.

Do not use this skill for:
- Prose-only editorial review of book chapters (use `book-review`).
- Chapter drafting (use `book-compose`).
- Non-cryptography papers (use `review-conductor` with a different persona panel).
- Mechanical-defect gating on built artifacts (use `book-qa`).

## Operating doctrine

1. **Rubric is the EC22 form.** The single source of truth for every persona is
   `personas/ec22-rubric.md`. Personas fill sections A through I. They do not
   invent new sections. They do not omit sections.
2. **Harshness calibration.** IACR top-tier acceptance rates hover near 22
   percent. The default disposition is weak-reject. A persona moves to accept
   only when the paper clearly improves on the state of the art. A persona
   moves to strong-accept only on breakthrough quality. Borderline papers are
   rejected, not passed.
3. **Confidentiality and isolation.** Personas review in isolation. They do NOT
   see each other's reviews. Consolidation happens only after every persona
   has filed.
4. **Anonymity.** Treat the paper as anonymous regardless of what the writing
   style suggests. Do not speculate on authorship or affiliation, even in the
   I-section (PC-only) notes.
5. **No fabrication.** Personas may not invent citations, affiliations, or
   prior work. If a persona believes overlapping work exists but cannot name
   it, the finding is "the paper does not survey adjacent literature" rather
   than a fabricated citation.
6. **Q3 authority.** Section C / Q3 (technical flaws) is the reviewer's
   strongest authority. Use it when the paper is wrong. Do not be diplomatic
   about correctness defects.
7. **Cite or do not claim.** Every finding in C, D, and E cites a section,
   line, theorem, lemma, or page from the paper. A finding without a citation
   does not survive consolidation.
8. **F is conditional.** Score sections F (scientific quality) only if C
   through E have no unresolved defects. Otherwise mark F "not applicable
   until C through E are addressed."

## Workflow

1. **Read the paper.** Confirm the PDF exists at the path the user supplied.
   Note the page count for the persona prompts.
2. **Prepare the output directory.** Default is `paper/reviews/` relative to
   the paper's workspace; override with an explicit `--output-dir` flag if the
   user requests one.
3. **Dispatch ten persona subagents in parallel.** For each persona
   `personas/0N-<slug>.md`, send the verbatim "Persona prompt" section as a
   subagent prompt via the `Agent` tool, substituting `${PAPER_PATH}`,
   `${PAPER_PAGES}`, `${PERSONA_INDEX}`, and `${OUTPUT_DIR}`. Each subagent
   writes a completed review form to
   `${OUTPUT_DIR}/persona-${PERSONA_INDEX}-<slug>.md` and returns its
   recommendation plus top three findings.
4. **Consolidate.** After all ten personas have filed, run
   `python -m scripts.consolidate --reviews-dir <output-dir> --paper <name>
   --version <vNNN> --output <output-dir>/<vNNN>-review-ledger.md`. The
   consolidator parses each persona file, severity-tags every finding, sorts,
   and detects cross-persona convergence on shared section/line citations.
5. **Surface the ledger.** Return the ledger path, the recommendation
   distribution, and the median + confidence-weighted mean to the user.

## Persona dispatch

The ten personas, with their distinct concerns:

| N | Slug | Reading lens (one line) |
|---|---|---|
| 01 | game-based-crypto | Game-hop accounting, advantage bounds, simulator query types |
| 02 | uc-crypto | Ideal-functionality specification, simulator constructiveness, composition hybrids |
| 03 | concrete-security | Tightness, parameter tables, bit-security accounting |
| 04 | bft-consensus | Safety vs liveness separation, network model, finality definition |
| 05 | p2p-network | Eclipse / Erebus resistance, AS-bucketing, gossip-protocol DoS |
| 06 | tee-hardware | TCB declaration, side channels, attestation flow, rollback resistance |
| 07 | formal-methods | Mechanization completeness, realisability, spec-to-prose mapping |
| 08 | applied-crypto | Ciphersuite identifiers, hash-to-curve domain separation, KES erasure |
| 09 | complexity-pq | Quantum adversary class, QROM gaps, NIST-aligned parameter selection |
| 10 | economics-mev | Equilibrium concept, slashing-vs-payoff sizing, bribery resistance |

Each persona file ends with a "Persona prompt (verbatim to send to subagent)"
section. That string is the literal subagent prompt; placeholders are filled
per dispatch.

## Severity rubric

The consolidator assigns severity by inspecting each persona's recommendation
and the section the finding appeared in:

- **strong-reject** — persona recommended 1 (strong reject); the finding is
  fundamental.
- **weak-reject** — persona recommended 2 (weak reject); fixable on
  clarifying resubmission.
- **borderline** — section C or D finding by a persona that did not reject;
  substantive concern but not alone sufficient to reject.
- **nit** — section E finding by a persona that did not reject; editorial
  polish.

Severity-sort order is strong-reject > weak-reject > borderline > nit. Within
a severity tier, sort by persona index then finding ID.

## Ledger format

Output: `templates/ledger.md` shape. One row per finding:

```
| ID | Persona | Severity | Category | Location | Claim | Evidence | Suggested fix |
```

The ledger also contains:
- Recommendation distribution across the ten personas.
- Median and confidence-weighted mean recommendation.
- Cross-persona convergence: which paper sections drew findings from two or
  more personas (this is where the panel's signal is strongest).
- A deferred-fixes section for findings the consolidator marks as out of
  scope for the next revision.

## What this skill owns

- The EC22 rubric encoding in `personas/ec22-rubric.md`.
- The ten expert personas and their verbatim subagent prompts.
- The review form and ledger templates.
- The consolidation script and its severity-sort discipline.

## What this skill does NOT own

- Spawning the subagents themselves. That is Claude's responsibility at the
  parent layer; this skill provides the prompts.
- Mechanical defect-gating on artifacts (owned by `book-qa`).
- Prose-quality review (owned by `book-review` / `russellian-style`).
- Multi-skill orchestration where the IACR panel is one component of a
  larger pipeline (owned by `review-conductor` if extended).

## Composes with

- `review-conductor` — can wrap this skill as one panel option.
- `book-knowledge` — can supply the paper's claim ledger so personas can
  cross-check references.
- `russellian-style` — usually runs BEFORE this skill, on the paper's prose,
  so that editorial defects do not consume the personas' attention budget.

## Harshness reminder

The user's intent in invoking this skill is to receive a deterministic harsh
review, not a polite one. If every persona returns accept, suspect either a
genuinely breakthrough paper or a calibration failure; verify against the EC22
rubric before reporting. If every persona returns strong-reject, that is the
expected modal outcome for a draft that has not yet been through one round of
peer review.

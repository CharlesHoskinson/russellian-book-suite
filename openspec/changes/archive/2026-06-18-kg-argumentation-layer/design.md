# KG Argumentation Layer Design

## Scope

S3 adds a read-only grounded-argumentation pass in `book-knowledge`. The pass
derives labels and warnings from existing graph facts; it writes no claim,
counter-claim, conflict, support, or thesis edge.

## Attack Model

The attack relation is derived from two existing inputs:

- `claim-conflict`: a directional attack from `claim-id` to `other-id`. This
  matches the stored graph and the existing contradiction scan; the reverse attack
  exists only when the reverse row is present.
- `counter-claim`: only latest-per-id rows with `cc-status = "open"` are attacks.
  `addressed` and `dismissed` counter-claims are answered and do not attack.

An open counter-claim is modeled as an external standing attacker with no claim
node. It is always undefeated because there is no in-graph claim label that can
reject it. This choice is explicit so writer warnings do not silently dismiss an
open rebuttal.

## Grounded Labelling

The pass computes grounded semantics only. A claim is:

- accepted when every attacker is rejected;
- rejected when some attacker is accepted, or when it has an open counter-claim
  attacker;
- undecided otherwise.

Cozo rejects the direct recursive-negation form as unstratifiable, so the compiler
generates an equivalent stratified stage program. Stage 0 accepts unattacked
claims. Each later stage carries forward prior accepted/rejected rows, rejects
claims attacked by a previously accepted claim, rejects claims under an open
counter-claim, and accepts claims whose attackers are rejected at that stage. The
number of stages is bounded by the number of in-scope claims; the grounded least
fixed point stabilizes within that bound for finite argument frameworks.

The stage program is authored as an EDN `defrules` file and compiled by
`booklogic_kg.compile_argumentation_rules`, keeping the path EDN-to-Cozo through
the existing compiler and store seam.

## Derived Relations

The pass exposes:

- `attacked(claim, attacker, attacker-type)`
- `defended(claim, attacker, defender)`
- `undefeated-attacker(claim, attacker, attacker-type)`
- `grounded-accepted(claim)`
- `grounded-rejected(claim)`
- total `label(claim, accepted|rejected|undecided)`

No preferred or stable extension relation is compiled or materialized.

## Warnings

Warnings are bounded, writer-facing rows:

- `contested-load-bearing-with-undefended-attack`: emitted for a load-bearing
  claim with an undefeated attacker. The justification is the singleton defeater
  set for that warning row.
- `axiom-only-support`: emitted when every support for a load-bearing claim is an
  axiom. The justification names the axiom support.
- `unsupported-load-bearing`: emitted when a load-bearing claim has no support
  edge. The justification is a missing-support note.

Claim-to-claim support is read from the existing `claim-implies` relation as
`claim-id` supporting `target-id`. Thesis support context is read from
`paragraph-supports` joined to `sub-argument`; that context does not by itself
name a supporting claim, so it is not used for the axiom-only claim-support
warning.

## Determinism

Rows are canonicalized before being returned. The same snapshot produces
result-set-equal labels and warnings across runs, and the generated CozoScript is
purely a function of the EDN rule file, schema, stage bound, and requested output.

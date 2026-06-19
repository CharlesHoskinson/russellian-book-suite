# KG Contradiction Workbench Design

## Scope

S4 adds a deterministic contradiction workbench alongside the existing lexical
detector and thesis consistency pass. It does not replace `detect_conflicts.py`
or `consistency_cozo.py`. The symbolic core is LLM-free and reads the append-only
claim ledger without mutating it.

## Normalized Fact Provenance

The four normalized helper relations are derived relations projected from the
existing claim record. No claim-record JSON Schema change is needed.

- `claim-quantity`: one parsed quantity per claim when the claim text contains a
  conservative quantity assertion.
- `claim-unit`: the declared unit and the canonical unit/dimension used for
  conversion.
- `claim-time-interval`: one parsed interval when the claim text declares a
  bounded year interval and a required temporal relation.
- `claim-normal-form`: the canonical subject/predicate key, plus references to
  the quantity and interval helper rows.

The parser is deterministic and conservative. If a claim text does not match the
declared grammar, no helper row is emitted. It never guesses.

## Subject And Predicate Keys

The parser recognizes simple assertion forms such as:

- `<subject> <predicate> is <number> <unit>`
- `<subject> <predicate> is <number> <unit> from <year> to <year> requires <overlap|disjoint>`
- `<subject> <predicate> from <year> to <year> requires <overlap|disjoint>`

The subject and predicate are lower-cased, whitespace-collapsed text captured by
that grammar. This deliberately avoids broad semantic matching; two claims share
a subject/predicate only when their normalized surface keys match exactly.

## Unit Conversion

The unit registry is hand-rolled, offline, and small. It covers the dimensions
needed by the corpus tests: length, mass, and time. Quantity values are converted
to a canonical unit per dimension (`m`, `kg`, `s`) before comparison. The declared
tolerance is `1e-6` in canonical units.

## Symbolic Rules

The normalized rows feed EDN-authored rule declarations compiled by
`booklogic_kg.compile_contradiction_workbench_rules` into CozoScript:

- Quantity clashes compare two claims with the same normal-form subject and
  predicate. A clash is emitted only when canonical values differ outside the
  tolerance.
- Interval inconsistencies compare same subject/predicate intervals. They emit
  when disjoint intervals are found under `requires overlap`, or overlapping
  intervals under `requires disjoint`.
- Supersession checks are deterministic over the ledger snapshot because the
  source relation is the append-only ledger's latest-per-id records. They flag
  stale links, missing targets, and cycles.

## NLI Residue Seam

Candidate pairs come from existing `claim-conflict` rows. Pairs already resolved
by a symbolic check are not routed to the NLI seam. Remaining pairs are
paraphrastic residue. The seam is an injected callable; tests pass stubs. If the
callable is absent or raises `NLIUnavailable`, residue rows are marked
`unresolved` and the symbolic defect set is unchanged.

## Alerts

Symbolic defects and residue rows are emitted as dictionaries compatible with
S0's `contradiction-alerts` side-product slot. Each alert carries a type, rule,
claim ids, severity/status, and bounded evidence.

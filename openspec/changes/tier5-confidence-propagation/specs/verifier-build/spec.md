# Capability delta: verifier-build — change: tier5-confidence-propagation

## ADD

### REQ-CONFIDENCE-040 — Ubiquitous

The verdict produced by `smt::check_all` SHALL gain a per-defect
`:defect-confidence` field — a float in `[0, 1]` computed as the
minimum `:confidence` of the atoms whose claim ids appear in that
defect's unsat core. The min SHALL be over the set of distinct
claim ids in the core; duplicate references to the same claim
SHALL NOT alter the result.

**Rationale:** A defect's evidentiary strength is bounded by the
weakest claim it relies on. A `:confidence 0.95` regulatory anchor
combined with a `:confidence 0.3` extraction-noise claim should be
reported with `0.3` confidence, not the average; the min rule
preserves operator intuition and is order-invariant across solver
runs.
**Tested by:**
`verifiers/osmotic_pressure/rust-verifier/src/smt.rs::tests::defect_confidence_is_min_of_core`
(added in S2.2)

### REQ-CONFIDENCE-041 — Optional feature

WHERE every atom in a defect's unsat core has `:confidence`
strictly below `VERIFIER_CONFIDENCE_THRESHOLD` (env var, default
`0.5`), the defect SHALL be downgraded from its declared severity
to `:severity :advisory`, and the verdict entry SHALL preserve the
original severity in `:declared-severity`. The downgrade SHALL NOT
fire if any single atom in the core meets or exceeds the
threshold.

**Rationale:** Low-confidence chains are likely false positives
from extraction noise; surfacing them at the same red-banner
severity as high-confidence violations trains authors to ignore
the framework. A single high-confidence anchor is enough to
preserve declared severity because anchor-grounded defects are
trustworthy regardless of noise on adjacent claims.
**Tested by:**
`verifiers/osmotic_pressure/rust-verifier/src/smt.rs::tests::all_low_confidence_chain_downgrades_to_advisory`
(added in S4.2)

### REQ-CONFIDENCE-042 — Ubiquitous

The top-level verdict SHALL gain a `:verdict-confidence` field —
the geometric mean of every defect's `:defect-confidence`. A
verdict with zero defects SHALL report `:verdict-confidence 1.0`.

**Rationale:** Operators need a single number to summarise "how
much do I trust this verdict?"; the geometric mean penalises
low-confidence defects more aggressively than the arithmetic mean
would, matching the operational intuition that the verdict is
only as good as its weakest defect chain.
**Tested by:**
`verifiers/osmotic_pressure/rust-verifier/src/smt.rs::tests::verdict_confidence_is_geometric_mean`
(added in S3.2)

### REQ-CONFIDENCE-043 — Unwanted behaviour

IF a claim's `:confidence` field is missing, non-numeric, or
outside the closed interval `[0, 1]`, THEN `ingest_ledger.py` in
the relevant verifier SHALL raise `IngestConfidenceError` and
abort the ingest. The error message SHALL name the offending
claim id and the observed value (or the absence thereof).

**Rationale:** Silently defaulting missing confidence to `0.0`
poisons every downstream computation (the min-of-chain rule, the
geometric mean, the downgrade test) without the author knowing.
Failing loudly at ingest is recoverable; a silent default isn't.
**Tested by:**
`tests/test_ingest_ledger.py::test_missing_confidence_raises`,
`tests/test_ingest_ledger.py::test_out_of_range_confidence_raises`
(added in S1.2)

### REQ-CONFIDENCE-044 — Ubiquitous

`verdict_to_qa.py` in every verifier SHALL partition the verdict's
defects into two JSON arrays: `defects` for entries with
`:severity` other than `:advisory`, and `advisory_defects` for
entries whose post-downgrade severity is `:advisory`. Both arrays
SHALL include the entry's `defect_confidence`; the JSON's top
level SHALL include `verdict_confidence` carried through from the
verdict.

**Rationale:** Author-facing tooling needs to render advisory
defects differently from hard defects; routing them into separate
JSON arrays lets the renderer apply distinct CSS or layout
without re-reading each entry's `:severity` field.
**Tested by:**
`tests/test_verdict_to_qa.py::test_advisory_defects_routed_to_separate_array`
(added in S5.2)

### REQ-CONFIDENCE-045 — Ubiquitous

A unit test suite SHALL exercise three confidence-chain cases:
(a) a defect whose core atoms all have confidence `>= 0.9` —
defect-confidence equals the min, severity unchanged; (b) a
defect whose core mixes `0.95` and `0.4` atoms —
defect-confidence is `0.4`, severity unchanged because one atom
exceeds the threshold; (c) a defect whose core atoms are all
below `0.5` — severity downgraded to `:advisory`,
`:declared-severity` preserves the original.

**Rationale:** The three branches of the downgrade rule are the
behaviour that the rest of the framework consumes; a single
fixture exercising all three keeps the regression coverage tight
and the rule legible to future contributors.
**Tested by:**
`verifiers/osmotic_pressure/rust-verifier/src/smt.rs::tests::confidence_propagation_three_chains`
(added in S4.2)

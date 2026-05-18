# Design: tier1-fact-extraction-preview

## Architecture

A single Python entry-point (`scripts/extract_preview.py`) reuses the
existing `ingest_ledger.ingest()` function — which already returns a
list of atoms — to produce a summary report instead of writing
`claims.edn`. The scaffolded project's `scripts/` directory already has
`ingest_ledger.py`; the preview is a thin reporter on top.

The OPAQUE-fraction gate is a hard exit condition because any fraction
above zero is a *correctness* signal, not a *quality* signal: an OPAQUE
claim is one where the regex didn't match, so the verifier has no
predicate to bind. The default 50 % threshold is chosen to allow
context/non-fact atoms (claims that legitimately carry no SMT-relevant
information) to pass while flagging the regex-broken case where most or
all expected claims OPAQUE out.

## Interfaces

```
extract_preview.py [--threshold PCT] [--dry-run] [--no-fail-gate]
                   --claims PATH --predicates PATH

Output (human + machine-readable JSON tail):
  Predicate                Facts  Sample value
  vant-hoff-i_s              412  2.0
  molarity_s                 412  0.154
  temperature-k_s            412  298.15
  osmotic-pressure-pa_s      412  780202.5
  ────────────────────────────────────
  Total claims                500
  Atoms emitted (expression)  412
  OPAQUE / unmatched           88   (17.6 %)

  ✓ OPAQUE fraction 17.6 % is within threshold 50.0 %.
  JSON: {"opaque":88,"total":500,"by_predicate":{...}}
```

## Makefile contract

```
extract: build
	@python scripts/extract_preview.py \
	  --claims fixtures/claims_clean.jsonl \
	  --predicates rules/predicates.edn

ci: build extract smoke
```

The `ci` target now depends on `extract` between `build` and `smoke`,
so a regex-broken lifts.edn fails CI at the extract gate before the
verifier ever runs.

## Why not just inspect `claims.edn`?

Reading `claims.edn` requires the author to know the EDN shape and
distinguish `:kind :expression` atoms from `:kind :symbol` (OPAQUE)
atoms. The preview is the same data in a one-screen summary, callable
from `make`, gated in CI.

## Why not enforce 0 % OPAQUE?

Some fixtures legitimately include context-bearing claims with no
extractable predicate (e.g., bibliographic claims that are flagged as
`:claim_type "context"`). The threshold lets the author calibrate per
domain.

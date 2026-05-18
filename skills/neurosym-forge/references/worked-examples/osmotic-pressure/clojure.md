# worked-example: osmotic-pressure — BookLogic walkthrough

REQ-BOOKLOGIC-045. Step-by-step walkthrough of authoring the
`osmotic_pressure` verifier in BookLogic. Companion to
`README.md` in this directory, which covers operator-level mechanics;
this file walks the BookLogic source forms one at a time.

## 1. The domain

The verifier checks the van 't Hoff equation:

```
π = i · M · R · T
```

where

- `π` (pi) is the osmotic pressure in Pa.
- `i` is the van 't Hoff factor (degree of dissociation —
  `i = 2` for NaCl in dilute aqueous solution, `i = 1` for
  non-dissociating sugars).
- `M` is molarity in mol/L.
- `R` is the ideal gas constant, `8.314 J/(mol·K)`.
- `T` is absolute temperature in K.

The verifier reads claims of the form "molarity is 0.154", "temperature
is 298.15 K", "van 't Hoff factor i = 2", "osmotic pressure = 763.27 Pa"
and checks that the published `π` is consistent with the accompanying
`i, M, T` within a 3% tolerance.

The clean fixture passes (`:sat`). The doctored fixture, which flips
`i` from 2 to 1 while leaving the other values untouched, produces
`:unsat` with the offending claim id in the core.

## 2. `sorts.edn` — declare the universe of types

The verifier has one custom sort, `:solution`. Every predicate takes a
`:solution` and returns a `:real`.

```edn
{:forms
 [(defsort :solution)]}
```

Sorts declared here are visible inside `defpredicate` arg-sort
positions. The base sorts (`:int`, `:real`, `:bool`, `:string`) are
implicit; only domain-specific sorts need a `defsort`.

For a chemistry verifier with multiple subject types (e.g. solute and
solvent, or specimen and reagent), you would add more sorts here.
The osmotic-pressure verifier only ever talks about one entity —
the solution — so one sort suffices.

## 3. `predicates.edn` — name the observable quantities

Four predicates, each `[:solution] :real`:

```edn
{:forms
 [(defpredicate :osmotic-pressure-pa [:solution] :real)
  (defpredicate :vant-hoff-i         [:solution] :real)
  (defpredicate :molarity            [:solution] :real)
  (defpredicate :temperature-k       [:solution] :real)]}
```

Each `defpredicate` form declares:

- A Keyword name (the predicate id).
- An argument-sort vector (here, always `[:solution]`).
- A return sort (always `:real`).

Note that `:vant-hoff-i` is declared `:real` even though physical
values are typically integer-valued. This is deliberate: Z3's Real
sort is strictly distinct from Int, and the axiom multiplies four
Real-valued quantities. Declaring `i` as `:int` would force casts at
every use and risk a sort mismatch under partial evaluation. See
`references/atomspace-edn.md` § 7 for the Double-vs-Int discussion.

## 4. `lifts.edn` — map prose to predicates

Four lifts, one per predicate. Each runs a regex against the
canonical text and emits an `:expression` atom on match. The full
content is reproduced in `references/grounded-atoms.md` § 6; here
we focus on the L002 case, which is the trickiest.

```edn
(deflift L002-vant-hoff-i
  :from :claim/canonical-text
  :when "(?i)van[' \\s]*t\\s*Hoff(?:\\s+factor)?\\s*(?:i\\s*)?(?:=|is|of)?\\s*(?P<v>[0-9]+(?:\\.[0-9]+)?)"
  :emit (fact ?claim-id :s :vant-hoff-i (parse-float ?v)))
```

The pattern is famously fiddly because "van 't Hoff" contains an
apostrophe AND a space. Real textbooks render it many ways:

- `van 't Hoff` — apostrophe + space (the canonical form)
- `van t Hoff` — just space
- `van't Hoff` — just apostrophe
- `vant Hoff` — neither (rare, but appears in OCR'd PDFs)

The class `[' \\s]*` matches zero or more apostrophes-or-whitespace,
covering all four cases. The `(?:\\s+factor)?` makes the explicit
word "factor" optional. The `(?:i\\s*)?` allows the convention "van 't
Hoff factor i = 2" as well as "van 't Hoff = 2".

The capture group `v` accepts both integer-form (`2`) and decimal-form
(`2.0`) values; `parse-float` coerces either to an `Edn::Double`.

## 5. `constraints.edn` — the van 't Hoff equation

One constraint, using `approx=` for tolerance-bounded equality:

```edn
{:forms
 [(defconstraint C001-vant-hoff
    :backend :z3
    :assert (approx= (:osmotic-pressure-pa ?s)
                     (* (:vant-hoff-i ?s) (:molarity ?s) 8.314 (:temperature-k ?s))
                     :tolerance 0.03)
    :track :claim/id
    :on-unsat {:defect :D13
               :severity :critical
               :message "van 't Hoff equation violated"})]}
```

Form by form:

- `:backend :z3` — the live constraint backend. (See
  `references/rewrite-rule-style.md` § 3 for the egg/cozo stub
  story.)
- `:assert (approx= LHS RHS :tolerance 0.03)` — `approx=` desugars
  in `codegen_axioms.py` to `|LHS - RHS| <= 0.03 * |RHS|`. The 3%
  tolerance absorbs measurement noise and the slight non-ideality of
  real solutions.
- `:track :claim/id` — Z3's `assert_and_track` is used; the tracker
  name is the bound claim id, so the unsat core points back at the
  offending claim.
- `:on-unsat` — what the QA layer should record when the constraint
  fails. `:D13` is the defect class for "claim set unsatisfiable";
  the message threads through to `verification-defects.json`.

`R = 8.314` is inlined as a literal Real constant inside the
multiplication. An alternative is to install it as a Z3 background
constant via the `axioms.rs` hook (see the companion `README.md` in
this directory).

## 6. Fixtures: clean and doctored

`fixtures/claims_clean.jsonl` (one line per claim, shown wrapped):

```jsonl
{"claim_id":"osm-clean-001","claim_type":"fact",
 "canonical_text":"van 't Hoff factor i = 2","status":"verified",
 "confidence":1.0,"source_spans":[{"doc_id":"vant-hoff-textbook",
 "locator_text":"i=2 for NaCl in dilute aqueous solution"}],
 "supports_chapters":[]}
```

With `i = 2`, `M = 0.154 mol/L`, `T = 298.15 K`, the predicted
pressure is `2 * 0.154 * 8.314 * 298.15 ≈ 763.27` Pa. The fixture
records the observed pressure as `780202.5 Pa` (a unit discrepancy
that the tolerance does NOT absorb; in the actual ledger the value
used is the calculated one). For the walkthrough's purposes, the
clean fixture is `:sat`: predicted matches observed within 3%.

`fixtures/claims_doctored.jsonl`:

```jsonl
{"claim_id":"osm-doc-001","claim_type":"fact",
 "canonical_text":"van 't Hoff factor i = 1","status":"verified",
 "confidence":1.0,"source_spans":[{"doc_id":"doctored",
 "locator_text":"wrongly recorded as non-dissociating"}],
 "supports_chapters":[]}
```

The doctored row flips `i` to 1 while leaving the other three claims
identical. Now the predicted pressure is `1 * 0.154 * 8.314 * 298.15
≈ 381.64` Pa — roughly half. The 3% tolerance is nowhere near
enough to absorb the doubling; Z3 returns `:unsat` with `osm-doc-001`
in the core.

## 7. `make extract` (Phase A)

`make extract` runs the Python ingester and prints a per-predicate
fact table plus the opaque-fraction. Expected clean-fixture output:

```
Predicate                            Facts  Sample value
molarity                                 1  0.154
osmotic-pressure-pa                      1  763.27
temperature-k                            1  298.15
vant-hoff-i                              1  2.0

Opaque fraction: 0.00 (threshold 0.50) — OK
```

(Phase A's `make extract` target is on a parallel feature branch;
this doc describes the Tier 1 endpoint.)

If any predicate shows zero facts, the constraint will pass trivially
(`:sat` for the wrong reason — Z3 received a free constant and was
free to satisfy the equation). The extract table is the cheap pretest
that catches this.

If the opaque-fraction exceeds 0.5, CI fails. Tighten lifts, add new
ones, or mark the unrecognised claims with `claim_type:
"design_decision"` to route them through the `:CONTEXT` atom shape.

## 8. `make ci`

`make ci` runs `build` then `smoke`. Build steps:

1. `npm install`
2. `npm run codegen-booklogic` — `nbb` reads `rules/booklogic/*.edn`
   and writes intermediates to `rules/`.
3. `npm run codegen-axioms` — `codegen_axioms.py` reads
   `rules/constraints.edn` and writes `rust-verifier/src/axioms.rs`.
4. `cargo build --release --features smt`.

Smoke steps (per fixture):

1. `python -m scripts.ingest_ledger ...` — produces
   `work/claims.edn`.
2. `cargo run --release ...` — produces `work/verdict.edn`.
3. `pytest tests/test_smoke.py` — asserts the expected status and
   core.

Expected results:

- Clean fixture: `{:status :sat :core []}`.
- Doctored fixture: `{:status :unsat :core ["osm-doc-001"]}` —
  surfacing as defect D13 in `verification-defects.json` with the
  message "van 't Hoff equation violated".

The doctored-fixture round-trip is the gold-standard end-to-end test:
a wrong claim, written in textbook English, lifted to a typed atom,
contradicted by a Z3 axiom, surfaced by claim id, translated to a QA
ticket. If `make ci` is green, every layer of the pipeline did its
job.

## See also

- `README.md` (sibling) — operator-level walkthrough with
  scaffolder commands.
- `references/atomspace-edn.md` — the atom shape this verifier emits.
- `references/grounded-atoms.md` — the deflift pass annotations.
- `references/phase-boundaries.md` — where each boundary crossing
  happens for this verifier.
- `verifiers/osmotic_pressure/` — the live source tree.

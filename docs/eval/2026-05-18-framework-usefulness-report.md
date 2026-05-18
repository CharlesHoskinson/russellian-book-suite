# Framework Usefulness Report — After Third Verifier

REQ-EVAL-047. Synthesised from the third-verifier build log
(`2026-05-18-third-verifier-build-log.md`) and the two prior
verifier builds (osmotic_pressure, bermuda).

**Question being answered:** Is the russellian-book-suite verifier
framework general-purpose, or is it an artefact custom-fit to the
domains it was scaffolded around?

**Answer in one paragraph:** The framework is general-purpose for
first-order algebraic domains expressible as `=` or `approx=`
relations between Real-valued predicates extracted from prose. It is
*not yet* general-purpose for domains that need ordered comparisons
(`>=` / `<=`), division, quantifiers, or non-arithmetic constraint
classes (rewrite rules, datalog, temporal logic). Concretely, three
domains tried (osmotic pressure, Bermuda Triangle stats, R0 herd
immunity) all built end-to-end, but the third domain required eight
documented gaps to be worked around and one of the workarounds
(algebraic elimination of `/`) is not always available.

## What worked first-try

The following worked on the epidemiology verifier without any
modification or workaround:

| Framework piece                          | Worked? |
| ---------------------------------------- | ------- |
| `scaffold_project.py` end-to-end         | yes     |
| `defsort :foo` declaration               | yes     |
| `defpredicate :foo [:arg-sorts] :ret`    | yes     |
| `deflift L001 :from K :when REGEX :emit` | yes     |
| Python-form `(?P<v>...)` regexes         | yes     |
| Three lifts firing on three claims       | yes     |
| `make extract` reporting 0% OPAQUE       | yes     |
| `npm install` on a fresh checkout        | yes     |
| `cargo build --release --features smt`   | yes     |
| `shadow-cljs release main`               | yes     |
| Z3 SAT verdict on the clean fixture      | yes     |
| Z3 UNSAT verdict on the two doctored     | yes     |
| Unsat core reporting offending claim ids | yes     |
| `axioms-tracker-map.edn` emission        | yes     |

That's a substantial first-try working surface. The framework's
"happy path" for a Real-valued, algebraic, approximate-equality
domain is real.

## What required workarounds

The third verifier surfaced eight gaps. Five are framework-substantive
(closing them requires Tier 2 / Tier 3 work), two are template
hygiene, one is environmental:

| Gap | Severity | Tier closing it          | Workaround feasible? |
| --- | -------- | ------------------------ | -------------------- |
| 1 — `>=` / `>` not assert heads | substantive | Tier 2 Phase F (encoder) | yes (with semantic compromise — encodes ≈ not ≥) |
| 2 — `/` not arithmetic head     | substantive | Tier 2 Phase F (encoder) | yes (algebraic — not always) |
| 3 — subtree-local float typing  | substantive | Tier 2 (encoder hygiene) | yes (ugly anchor) |
| 4 — EDN writer rounds 0.0 → 0   | substantive | Tier 2 (intermediate writer) | yes (use 0.5) |
| 5 — template recognises `'~=` only | hygiene  | Tier 2 (template lag) | yes (hand-patch CLJS) |
| 6 — defconstraint docstring wrong | hygiene | Tier 2 (template docs) | yes (use symbol) |
| 7 — `ingest_ledger.py` not vendored | hygiene | Tier 2 (template) | yes (copy from osmotic) |
| 8 — Windows can't load Linux .so | env    | n/a (CI on Linux) | yes (run smoke via WSL) |

The two hygiene gaps (5 and 6) particularly worry me: they indicate
that **the scaffold template is not exercised by the framework's own
CI**, otherwise these mismatches would have been caught when
osmotic_pressure got its fixes. The next verifier to be scaffolded
from the template will rediscover the same gaps.

## What the framework is genuinely useful for TODAY

These domain classes can be built end-to-end with the framework as it
stands (i.e. requiring at most "use approx= relative tolerance" and
"vendor ingest_ledger"):

1. **Algebraic first-order relations.** Any domain whose constraints
   reduce to `(approx= LHS RHS :tolerance ε)` over `*`, `+`, `-`,
   real predicates, and real literals. Osmotic pressure (van 't Hoff
   equation), R0/herd immunity (after algebraic re-encoding), the
   ideal gas law, simple stoichiometry, Hooke's law, simple
   electrical circuits, exchange-rate triangulation, simple
   compound-interest checks. This is a non-trivial class.

2. **Equality-only categorical checks.** Domains where the constraint
   is `(= PREDICATE LITERAL)` and the lift maps prose to discrete
   values. Bermuda Triangle is an existence proof: I001 fires when a
   claim asserts a tally that contradicts the ledgered tally.

3. **Lift-based fact extraction from a verified claim ledger.** The
   `deflift` regex pipeline + `extract_preview` OPAQUE gate is robust;
   3/3 lifts fired on the epidemiology fixtures with zero OPAQUE.
   This is the framework's most consistent strength.

## What the framework is still missing

These domain classes are not handled even with workarounds:

1. **Ordered-comparison domains.** Anything where `<`, `<=`, `>`, `>=`
   is the *natural* relation rather than a contrivance. Examples:
   safety bounds ("temperature must not exceed X"), threshold tests
   ("dose must be at least Y"), eligibility predicates ("age >= 18"),
   herd immunity itself if encoded honestly. The `approx=`
   workaround conflates "below threshold" with "above threshold by
   too much" — fine for the eval fixtures, not OK for production.

2. **Division-heavy rate expressions.** Many domains (kinetics,
   epidemiology beyond R0, pharmacokinetics, fluid dynamics, finance
   beyond compound interest) compose ratios. The algebraic re-encoding
   trick used for C002 (multiply through) only works if division
   nests linearly. `a/b + c/d` cannot be cleared without introducing
   new variables.

3. **Quantified / universal statements.** "For all populations P,
   coverage[P] ≥ threshold[disease]" cannot be expressed; the lift
   binds a single subject `?p` per fact and constraints quantify
   only via free variables, not `∀`/`∃`.

4. **Rewrite-rule and datalog domains.** `defrule` and `defquery`
   compile to intermediates but the egg / Cozo backends silently
   drop them at codegen time (`SUPPORTED_BACKENDS` is documented
   but the implementations are stubs). Domains that need
   normalisation (algebraic simplification, term canonicalisation)
   or relational queries (graph reachability, citation chains)
   cannot be verified end-to-end today.

5. **Temporal / hybrid logic.** Anything LTL-shaped ("eventually
   coverage rises", "always X then Y") has no surface in the
   framework. The verifier is one-shot per fixture.

## Final verdict

The framework is general-purpose **for first-order algebraic
approximate-equality domains with prose-extracted Real-valued facts**.
The third verifier built end-to-end in ~3 hours of human time
(including the gap-discovery loop). Two domains (osmotic, bermuda) are
existence proofs; the third (epidemiology) demonstrates the framework
extends beyond its original target with a documented and finite gap
set. Three out of three domains is not statistically conclusive but it
is the strongest available signal that the framework's design admits
extension.

The framework is **not yet general-purpose** for ordered-comparison,
division-heavy, quantified, rewrite-rule, datalog, or temporal
domains. Closing Gap 1 (`>=`) and Gap 2 (`/`) — both squarely in
Tier 2 Phase F — would more than double the addressable domain class:
ordered comparisons unlock safety / eligibility / threshold domains,
and direct division unlocks rate and ratio expressions.

Quantitative justification:

- 14 framework pieces worked first-try in the third domain.
- 8 gaps required workarounds; 0 truly blocked.
- 4 substantive framework gaps; 3 hygiene gaps; 1 environmental.
- 5 future domain classes still inaccessible without further Tier 2/3
  work.
- Estimated effort to close the two highest-impact gaps (`>=`, `/`)
  is small enough to be a single Phase F PR.

The hypothesis ("the framework is general-purpose") survives the
third-verifier test for its declared domain class. The hypothesis
fails for domain classes outside that scope. The next eval (a fourth
verifier in an ordered-comparison domain — e.g. safety bounds in
nuclear-medicine dosing — done AFTER Phase F lands) would be the
right way to confirm whether the framework's generality is
asymptotic or hard-bounded.

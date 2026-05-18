# Design: eval-third-verifier

## Domain choice

**Chosen:** epidemiology — R0 thresholds and herd immunity.

A two-axis comparison with the existing verifiers:

| Axis                       | bermuda                | osmotic_pressure       | epidemiology (new)         |
|----------------------------|------------------------|------------------------|----------------------------|
| Primary value-kind         | `:int`                 | `:real`                | `:real` (rates, fractions) |
| Constraint shape           | equality (= n 9)       | one equation (approx=) | threshold inequality (>=)  |
| Cross-document consistency | no                     | no                     | yes (same disease, two chapters → same R0) |
| Lift complexity            | word-to-int            | parse-float            | parse-percentage + parse-float |
| Aggregation                | none                   | none                   | per-disease grouping       |

Two axes the existing verifiers do not exercise:

1. **Threshold inequalities.** Herd immunity requires
   `vaccination-coverage >= herd-immunity-threshold`. Equality (`=`) and
   approximate equality (`approx=`) are already wired. `>=` may or may not
   be in the encoder — if not, the build log records the workaround
   (`(not (< a b))` or a constraint composed of two `<=` halves).
2. **Cross-document consistency.** "Disease X has R0 = 12 in chapter 3 and
   R0 = 18 in chapter 7" should fail consistency without either chapter
   being internally wrong. This forces the verifier to range over subject
   identities and assert pairwise equality across the entity set —
   exactly the partitioning shape Tier 4 of the roadmap addresses.

Alternative considered: carbon accounting (Scope 1 + 2 + 3 = total). Rejected
for this change because the additive equation is structurally close to
osmotic's product equation; the framework's response would be too similar.

## Verifier structure

Standard project layout, cloned from `verifiers/osmotic_pressure/` and
`verifiers/bermuda/`:

```
verifiers/epidemiology/
├── Makefile
├── README.md
├── SKILL.md
├── cljs-orchestrator/
├── deps.edn
├── fixtures/
│   ├── claims_clean_measles.jsonl
│   ├── claims_clean_polio.jsonl
│   ├── claims_clean_pertussis.jsonl
│   ├── claims_doctored_measles_below_threshold.jsonl
│   └── claims_doctored_measles_inconsistent_r0.jsonl
├── nbb.edn
├── package.json
├── pyproject.toml
├── rules/
│   └── booklogic/
│       ├── constraints.edn
│       ├── lifts.edn
│       ├── predicates.edn
│       ├── queries.edn
│       ├── remedies.edn
│       ├── rules.edn
│       └── sorts.edn
├── rust-verifier/
├── scripts/
└── tests/
```

Predicate set:

```edn
(defpredicate :basic-reproduction-number     [:disease] :real)
(defpredicate :vaccination-coverage          [:disease] :real)
(defpredicate :herd-immunity-threshold       [:disease] :real)
```

The herd-immunity threshold is `1 - 1/R0` (derived; the constraint can either
assert the derived equality, or accept the threshold as published and check
coverage against it).

## Fixture strategy

Three clean fixtures, one per disease, all with consistent published R0,
threshold, and coverage figures that satisfy the inequality.

Two doctored fixtures, each exercising one distinct failure axis:

1. `claims_doctored_measles_below_threshold.jsonl` — coverage 0.91 against
   herd-immunity threshold 0.94 (measles R0=18). The verifier surfaces a
   single defect: the constraint `(>= coverage threshold)` is violated.
2. `claims_doctored_measles_inconsistent_r0.jsonl` — chapter 3 quotes R0=12
   and chapter 7 quotes R0=18 for the same disease. Neither value is wrong
   in isolation; cross-document consistency fails. Surfaces a partitioning
   defect.

## Build-log structure

`docs/eval/2026-05-XX-third-verifier-build-log.md` is a chronological diary,
not a tidy retrospective. Every entry has the same shape:

```
### 2026-05-XX HH:MM — <one-sentence roadblock summary>

**Symptom:** what the build did that I didn't expect
**Root cause:** what was actually going on
**Resolution:** one of
  - `fixed` — pushed a patch to the framework
  - `workaround` — wrote around it; see follow-up issue #NNN
  - `deferred-to-tier-N` — known limitation, planned change is <link>
**Time impact:** <approximate>
**Tier link:** if applicable, link to the OpenSpec change folder that closes it
```

Examples of plausible log entries (illustrative — not the actual content):

- `:patterns` regex with `(?<v>)` failed silently before Tier 2 → workaround
  via `(?P<v>)`; flagged as already deferred to tier2-strict-regex-dialect.
- `>=` not in encoder vocabulary → workaround via `(not (< a b))`; filed
  as candidate Tier 2 enhancement.
- Cross-document consistency requires `defquery` with a join; `defquery`
  is `wired-builder` per SUPPORT_MATRIX.md but not consumed by default
  `make ci`. Workaround: drive the query manually from the test, surface
  results into the unsat path.

## Usefulness-report synthesis

`docs/eval/2026-05-XX-framework-usefulness-report.md` is the human-facing
condensation. Three buckets:

1. **Worked first-try.** Every form/feature the third-verifier author
   reached for and got working from documentation alone. This is the
   evidence supporting "general-purpose".
2. **Required workaround.** Roadblocks resolved within the verifier without
   touching the framework. Each workaround → planned Tier 2-4 change.
3. **Still missing.** Capabilities the third verifier ended up *not* using
   because no acceptable workaround existed. These are open framework gaps,
   either filed as new OpenSpec changes or flagged as known unplanned.

The report is short (1-2 pages). It is the public-facing answer to
"is the framework general-purpose?" with concrete evidence.

## Success criteria

- `make ci` green with the fixture set above.
- Doctored fixtures surface defects; clean fixtures do not.
- Every workaround in the build log has a roadmap link or a new issue.
- The usefulness report names the three buckets with a non-empty
  "worked first-try" set.

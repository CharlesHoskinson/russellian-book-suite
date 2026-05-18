# phase-boundaries

REQ-BOOKLOGIC-042. Three-language pipeline diagram plus per-boundary
schema and per-boundary test coverage.

## 1. Pipeline diagram

The verifier pipeline crosses three language boundaries. Each is an
EDN-on-disk handoff; nothing crosses an FFI line.

```
+----------------+         +----------------+        +----------------+
|     AUTHOR     |         |   ClojureScript|        |     PYTHON     |
| edits BookLogic|         |  (nbb compiler)|        |  (ingester)    |
|   sources      |         |                |        |                |
+----------------+         +----------------+        +----------------+
        |                          |                          |
        | rules/booklogic/         | reads booklogic/*.edn    |
        |   sorts.edn              | emits intermediate       |
        |   predicates.edn         | rules/*.edn:             |
        |   lifts.edn              |   predicates.edn         |
        |   constraints.edn        |   constraints.edn        |
        |   rules.edn              |   queries.edn            |
        |   queries.edn            |   remedies.edn           |
        |   remedies.edn           |   rules.edn              |
        |                          |   booklogic-schema.edn   |
        |                          |     (Phase C)            |
        v                          v                          v
+------------------------------------------------------------------+
|              `nbb -m <slug>.booklogic .`                         |
|              (BookLogic compiler in cljs-orchestrator)           |
+------------------------------------------------------------------+
                                   |
                                   | reads predicates.edn
                                   | + claims_*.jsonl
                                   v
                            +----------------+
                            |  ingest_ledger |
                            |  Python; runs  |
                            |  deflifts      |
                            +----------------+
                                   |
                                   | writes work/claims.edn
                                   |  {:version 1 :atoms [...]}
                                   v
                            +----------------+
                            |   RUST         |
                            | rust-verifier  |
                            | reads          |
                            |  claims.edn    |
                            |  constraints   |
                            |  -> axioms.rs  |
                            |    via codegen |
                            +----------------+
                                   |
                                   | writes work/verdict.edn
                                   |  {:status :sat|:unsat|:unknown
                                   |   :core ["osm-doc-001" ...]}
                                   v
                            +----------------+
                            |   AUTHOR /     |
                            |   book-qa      |
                            |   reads verdict|
                            +----------------+
```

## 2. Per-boundary schema

### 2.1 Author -> BookLogic source

Seven EDN files under `verifiers/<project>/rules/booklogic/`. Each is a
`{:forms [...]}` map containing one or more of:

- `(defsort :name)` — declare a sort
- `(defpredicate :name [arg-sorts...] :return-sort)`
- `(deflift L###-name :from ... :when ... :emit ...)`
- `(defconstraint C###-name :backend ... :assert ... :on-unsat ...)`
- `(defrule R###-name LHS RHS ...)` — stub today (see
  `references/rewrite-rule-style.md`)
- `(defquery Q###-name ...)` — stub
- `(defremedy W###-name ...)` — stub

Schema validation: the BookLogic compiler `phases.cljs` enforces basic
shape. Phase C adds a stricter schema in
`rules/booklogic-schema.edn` (EdnVector / EdnList typed shape).

### 2.2 nbb-compiled intermediates

After `npm run codegen-booklogic` (or `nbb -m <slug>.booklogic .`),
the intermediate layer appears under `rules/`:

- `predicates.edn` — `{:version 1 :predicates {<name> {:value-kind :real
  :arg-sorts [:solution] :patterns [...]}}}`. Consumed by the Python
  ingester.
- `constraints.edn` — `{:version 1 :constraints [<defconstraint maps>]}`.
  Consumed by `codegen_axioms.py`.
- `queries.edn`, `remedies.edn`, `rules.edn` — stubs in v1.
- `booklogic-schema.edn` — Phase C; the EdnVector/EdnList schema for
  the above intermediates.

These are EDN data files, not atom containers. `:version 1` at the top.

### 2.3 Python atom stream

`work/claims.edn` is the only file with the atom-container shape:

```edn
{:version 1
 :atoms [
   {:kind :expression :id "..." :predicate :X :subject :s :value <D>}
   {:kind :symbol     :id "..." :name :OPAQUE  ...}
   {:kind :symbol     :id "..." :name :CONTEXT :context true ...}
 ]}
```

See `references/atomspace-edn.md` for the full atom field reference.

### 2.4 Rust verdict

`work/verdict.edn` carries the Z3 result:

```edn
{:status :unsat            ; :sat | :unsat | :unknown
 :core ["osm-doc-001"]      ; tracker names = claim ids
 :explanation "C001-vant-hoff violated by claim osm-doc-001"
 :graph-summary {:claim-count 4 :contradictions []}}
```

`:status :unknown` means Z3 timed out — Phase B's
`VERIFIER_SOLVER_TIMEOUT_MS` env var controls the cap; default
`5_000` ms. Tier 1 wires the env var through `smt.rs`; Tier 2 ties
it to the orchestrator.

## 3. Per-boundary tests

Test coverage maps to the boundary it guards:

- **BookLogic source -> intermediates.** Schema validation in
  `verifiers/<project>/cljs-orchestrator/test/.../booklogic_test.cljs`
  exercises `nbb -m <slug>.booklogic .` on each fixture and checks
  the emitted intermediate shape.
- **Intermediates -> ingester.** REQ-EDN-042 lives in
  `skills/neurosym-forge/tests/test_canonical_var_name.py` — the
  Tier 1 canonical-variable-name pass that normalises `:s` / `:sol`
  / `?s` subjects before the ingester reads them.
- **Ingester output gate.** Phase A's
  `verifiers/<project>/scripts/tests/test_extract_preview.py`
  (REQ-INGEST-040..043) asserts: opaque-fraction below threshold,
  per-predicate fact counts non-zero, sample-value emission.
- **Rust round-trip.** `verifiers/<project>/rust-verifier/src/smt.rs`
  mod tests cover REQ-OSMOTIC-040 (deflift -> axiom path) and
  REQ-OSMOTIC-041 (doctored fixture -> :unsat with the right
  tracker in the core).
- **EDN golden round-trip.** REQ-EDN-044 — golden files exercised by
  `skills/neurosym-forge/tests/test_edn_round_trip.py` to keep the
  writer and reader in lock-step.

## 4. Where failures usually surface

Most regressions show up as one of four failure shapes:

- **Silent OPAQUE.** Lift regex compiles but does not match; atom
  emits as `{:kind :symbol :name :OPAQUE}`. Caught by Phase A's
  extract gate (`make extract` prints per-predicate counts plus
  opaque-fraction; CI fails if opaque-fraction >= 0.5).
- **Unbound predicate.** Predicate in the constraint never appears
  in the atom stream, so Z3 has no axiom to falsify and the solver
  returns `:sat` for the wrong reason. Caught by the sample-value
  table in `make extract` — a predicate with zero facts is a red
  flag.
- **Unknown predicate.** Constraint references a predicate the
  ingester does not know about. Phase C's schema validator catches
  it at compile time. Today the failure surfaces as Z3 receiving a
  free constant and silently picking arbitrary values.
- **Regex compile failure.** A `deflift` `:when` pattern is malformed.
  Surfaces as a `re.error` exception during `make extract`, with the
  lift name in the traceback.

## 5. Boundary-by-boundary debugging recipe

A quick map from observed symptom to which boundary to inspect first:

- **CI passes locally but fails in CI on the same commit.** Suspect
  the `nbb` intermediates — `rules/predicates.edn` etc. are in
  `.gitignore` for new projects. If a developer ran `make build`
  once and forgot, the intermediates exist locally but CI regenerates
  them from scratch. Re-run `npm run codegen-booklogic` clean to
  reproduce.
- **Clean fixture returns `:unsat`.** Inspect `work/claims.edn`. If
  the `:value` for a `:real` predicate is `Edn::Int` (integer literal
  with no decimal point), the writer is broken and `_emit_float`
  needs fixing (REQ-EDN-050).
- **Doctored fixture returns `:sat`.** Inspect `work/claims.edn`. If
  `:predicate` arrives as `Edn::Str` rather than `Edn::Key`, the
  Rust dispatch silently fails and Z3 has no axiom to violate.
  REQ-EDN-049 closes this.
- **Both fixtures return `:unknown`.** Z3 timed out. Bump
  `VERIFIER_SOLVER_TIMEOUT_MS` (Phase B). Default is 5_000 ms; a
  pathological constraint set can need 30_000 ms.

## 6. Phase ordering and tier dependencies

The Tier 1 endpoint is the combined state of all five phases. As
written, Phase D (this docs work) ships on its own branch with
forward-references to the other phases:

- **Phase A** adds `make extract` and `extract-preview.py`.
- **Phase B** adds `VERIFIER_SOLVER_TIMEOUT_MS` wiring through
  `smt.rs`.
- **Phase C** adds `canonical_var_name`, the EdnVector/EdnList
  schema, and `booklogic-schema.edn` validation.
- **Phase D** (here) writes the reference docs against the
  combined endpoint.
- **Phase E** integrates the four phases on `main`.

When a reader of these docs hits a forward-reference (e.g. "Phase A's
extract gate") on a non-`main` branch, they should expect the feature
to appear once Phase E merges. The docs are written against the
endpoint, not the snapshot of the branch they land on.

## See also

- `references/atomspace-edn.md` — the wire shape that crosses these
  boundaries.
- `references/grounded-atoms.md` — the deflift pass that produces
  the atoms.
- `verifiers/osmotic_pressure/Makefile` — `ci: build smoke` is the
  reference orchestration of the boundary crossings (Phase A adds an
  `extract` target before `smoke`).

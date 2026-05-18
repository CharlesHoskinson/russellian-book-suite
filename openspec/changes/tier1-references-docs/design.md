# Design: tier1-references-docs

## Reference files (skills/neurosym-forge/references/)

Six files referenced by SKILL.md but absent today. The minimal viable
content for each:

- **`metta-idioms.md`** — Crisp summary of which MeTTa concepts the
  framework borrows (atomspace, grounded atoms, rewrite rules) and
  which it does NOT (full unification, dynamic dispatch). Cross-link
  to the actual implementation files.
- **`atomspace-edn.md`** — The wire format. One section per atom kind
  (`:expression`, `:symbol :OPAQUE`, `:symbol :CONTEXT`), with a
  golden example per kind, the type of every field, and a "field
  asymmetry" callout (`Edn::Key` vs `Edn::Str`, integer-vs-float
  discriminator).
- **`grounded-atoms.md`** — How `deflift` extracts a ground atom from
  prose: regex dialect (`(?P<v>)` not `(?<v>)`), the `?claim-id`
  binding, the `:s` subject placeholder convention, the `parse-float`
  / `parse-int` value functions.
- **`phase-boundaries.md`** — The three-language pipeline diagram:
  CLJS author → `nbb -m booklogic .` → intermediate EDN → Python
  codegen → Rust verifier. Per-boundary: what flows, what schema
  validates the flow, what tests cover it.
- **`rewrite-rule-style.md`** — Conventions for writing `defrule`
  forms (egg-bound, currently stub but documented for the day
  Tier 3 lands).
- **`worked-examples/osmotic-pressure/clojure.md`** — Step-by-step
  walkthrough of the existing osmotic_pressure verifier from `sorts.edn`
  through `make ci`. The "if you read one document, read this".

Length budget: each file 200–400 lines.

## Seed template annotations

Every `.edn.tmpl` seed file currently looks like:
```edn
{:forms []}
```

Tomorrow:
```edn
;; rules/booklogic/predicates.edn — schema declarations for this verifier.
;;
;; Form syntax:
;;   (defpredicate :predicate-name [:arg-sort-1 :arg-sort-2 ...] :return-sort)
;;
;; Valid return sorts: :real :int :bool :string :entity
;; Arg sorts must be declared in sorts.edn or be one of the primitive set.
;;
;; Example (commented out — uncomment + edit for your domain):
;; (defpredicate :osmotic-pressure-pa [:solution] :real)
;;
;; Common silent failures:
;;   - return sort :int when the regex extracts "2.5" → unbound predicate
;;   - predicate name with uppercase → ingest emits OPAQUE, all claims drop
;;
{:forms []}
```

Same pattern for sorts.edn, lifts.edn, rules.edn, constraints.edn,
queries.edn, remedies.edn.

## docs/booklogic-dsl-reference.md

Top-level structure:
```
1. DSL philosophy (3 paragraphs)
2. Form reference (7 sections, one per form family)
   - Surface syntax (BNF-like)
   - Every keyword arg (table: keyword, type, required, semantics)
   - Compilation target (which intermediate EDN file, which solver)
   - Worked example
   - Anti-pattern / silent-failure recipes
3. Sort system (defsort + primitive sorts)
4. Cross-language conventions (canonical_var_name, regex dialect, etc.)
5. Debugging
   - VERIFIER_DEBUG_SMT
   - make extract (the new tool)
   - Reading the unsat core
6. Cookbook: 6 small domains expressed in BookLogic
```

Length budget: ~800–1200 lines.

## SUPPORT_MATRIX.md

Single table at skill root:

```
| Form family  | CLJS compile | Codegen path  | Solver wired | Status |
|--------------|--------------|---------------|--------------|--------|
| defsort      | ✓            | (validation)  | n/a          | wired  |
| defpredicate | ✓            | (validation)  | n/a          | wired  |
| deflift      | ✓            | regex IR      | n/a          | wired  |
| defrule      | ✓            | none          | egg (stub)   | stub   |
| defconstraint :backend :z3   | ✓ | codegen_axioms.py | Z3 | wired  |
| defconstraint :backend :egg  | ✓ | none silently  | egg stub   | DROP   |
| defconstraint :backend :cozo | ✓ | none silently  | n/a        | DROP   |
| defquery     | ✓            | codegen_kg.py | Cozo         | wired but not in default `npm run build` |
| defremedy    | ✓            | none          | n/a          | external consumer (book-qa) |
```

Plus a paragraph per row explaining what "stub" / "DROP" means and
which Tier of the roadmap addresses it.

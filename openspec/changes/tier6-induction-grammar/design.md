# Design: tier6-induction-grammar

## Grammar BNF reference

The enforcer carries a literal BNF for the
`defconstraint` AST it accepts. Shape (abbreviated):

```
constraint  ::= '(' 'defconstraint' rule-id keyword-map ')'
keyword-map ::= ':scope' scope-kw ':backend' backend-kw
                ':assert' body
                [':on-unsat' defect-map]
scope-kw    ::= ':subject' | ':corpus'
backend-kw  ::= ':z3' | ':egg' | ':cozo'
body        ::= '(' op arg+ ')'
op          ::= '='  | '<' | '<=' | '>' | '>='
              | '+' | '-' | '*' | '/'
              | 'approx=' | 'and' | 'or' | 'not'
              | 'forall' | 'exists' | 'implies'
arg         ::= literal | predicate-call | '(' op arg+ ')'
predicate-call ::= '(' predicate-name binding+ ')'
binding     ::= '?' var-name        ;; canonical per Phase O
```

The BNF lives in
`skills/neurosym-forge/scripts/_induction_grammar.cljs`
as a top-level `^:const` declaration; the drift lint reads
it and compares against `codegen_axioms.py`'s dispatch list.

## Schema-to-prompt transformation

The proposer receives a structured system-prompt section
generated from `booklogic-schema.edn`:

```
You may use ONLY these predicates:
  - :basic-reproduction-number  (?d :document) -> :real
  - :herd-immunity-threshold    (?d :document) -> :real
  - :vaccine-efficacy           (?d :document) -> :real
  ...

You may use ONLY these operators (BookLogic grammar):
  =, <, <=, >, >=, +, -, *, /, approx=,
  and, or, not, forall, exists, implies

Emit exactly one EDN `defconstraint` form. Do not include
prose. Do not include code fences. Output starts with `(`.
```

The atom cluster from Phase Q `SemanticIndex` is appended as
a user-prompt section listing the cited atoms with their
canonical predicate-arg shapes.

## Failure surface (5 categories)

The enforcer returns a tagged map on rejection:

| Tag | Trigger | Example |
|---|---|---|
| `:grammar-fail/non-edn` | Reader error | `LLM emits "Sure, here's..."` |
| `:grammar-fail/wrong-head` | Head is not `defconstraint` | `(deflift ...)` |
| `:grammar-fail/unknown-predicate` | Predicate not in schema | `(:made-up-pred ?d)` |
| `:grammar-fail/wrong-sort` | Arg sort mismatch | `(:r0 :hello)` where `:r0` expects `?d :document` |
| `:grammar-fail/illegal-op` | Op outside BNF | `(mod a b)` |

Each rejection carries `{:tag <kw> :detail <map> :raw <str>}`
so the orchestrator's failure log surfaces the offending
form without burning a solver call.

## Drift lint

`tests/test_induction_grammar_drift.py` parses
`codegen_axioms.py`'s `OPERATOR_DISPATCH` dict and the
`_induction_grammar.cljs` BNF block, asserting set equality.
If a future change adds `(mod a b)` to codegen without
updating the BNF, `make lint` fails with a structured
message naming the missing operator.

## Integration with `_llm_lift.py`

The Phase P `LLMLiftProvider` abstraction is reused
verbatim. A new `propose_constraint` method on
`LLMLiftProvider` returns a single EDN string per call;
existing `extract_atoms` is untouched. The Stub provider
gains a `propose_constraint` implementation reading from
`tests/fixtures/llm-responses/constraint-*.edn` so the test
suite is offline-deterministic.

`NEUROSYM_LLM_PROVIDER=stub` selects the deterministic
backend; tests rely on this by default. Real-provider
exercises remain opt-in via `make test-llm-online`.

## Dry-run switch

`NEUROSYM_INDUCTION_DRY_RUN=1` short-circuits the
orchestrator AFTER grammar validation but BEFORE solver
dispatch. The proposer's output is printed to stdout in
ordered EDN form; no Cozo or Z3 call is made. Useful for:

- Verifying the prompt template change produces
  grammar-clean candidates
- Capturing the candidate set for a regression fixture
- Iterating on the schema-to-prompt transformation without
  paying solver cost

## Cost discipline

The grammar gate is the first filter in the propose-validate
loop. Per the design spec, every rejected proposal saves a
Z3 / Cozo invocation; the deep-research reports estimated
30–50% pre-solver rejection on a closed-predicate scope.

Per-rule LLM cost cap (≤3 LLM repair calls) is enforced by
the orchestrator (Phase W), not here. This change is the
inner gate; it does not count or budget LLM calls.

## Why not bundle into Phase W (candidate generation)?

Phase W produces candidates from three sources (Horn-body
mining, Popper-style search, LLM). The grammar enforcer
must run on every source's output uniformly. Bundling the
gate into the LLM-specific source would let Horn-body and
Popper candidates bypass the same type discipline. The gate
lives one level up; this change ships only the gate plus
its LLM-source binding.

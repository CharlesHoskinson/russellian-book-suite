# rewrite-rule-style

REQ-BOOKLOGIC-043. `defrule` conventions for the BookLogic DSL.
This document is explicit about what works today (CLJS string
substitution) versus what is intended (egg equality saturation, Tier 3).

## 1. `defrule` surface syntax

The `defrule` form lives in `verifiers/<project>/rules/booklogic/rules.edn`:

```edn
(defrule R001-commute-plus
  :tags [:algebraic :commutative]
  :confidence 1.0
  :doc "Addition is commutative."
  :lhs (+ ?a ?b)
  :rhs (+ ?b ?a))
```

Fields:

- `name` — `R###-kebab-case`, e.g. `R042-vant-hoff-expand`. The
  `R###` prefix is global across rule files; allocate sequentially.
- `:lhs` — the left-hand pattern. Free variables are `?a`, `?b`,
  `?s`, etc. The shape mirrors the atom stream (head + args).
- `:rhs` — the right-hand pattern. Every free variable on the
  `:rhs` MUST also appear on the `:lhs`. Phase A's
  `lint_atomspace.py` flags unbound variables.
- `:tags` — a vector of Keywords used by linters to filter rules
  and by the scaffolder to organise rule files.
- `:confidence` — Double in `[0.0, 1.0]`. Convention: `1.0` for
  algebraic identities, lower for heuristic rewrites.
- `:doc` — single English sentence stating intent. Do NOT embed
  proofs in the doc string; the fixture test is the proof.

Conventional tags:

- `:algebraic` — pure math identity
- `:commutative` — symmetric in both arguments
- `:associative` — re-bracketable
- `:eliminating` — `:lhs` introduces a variable unused on `:rhs`
- `:domain-<name>` — domain-specific group, e.g. `:domain-osmotic`

## 2. Intent: egg equality saturation

The rules are conceptually consumed by an
[egg](https://egraphs-good.github.io/) e-graph for canonical-form
rewriting. The motivating use case: take an author-written constraint
like `(approx= (:osmotic-pressure-pa ?s) (* (:vant-hoff-i ?s) (:molarity ?s) 8.314 (:temperature-k ?s)))`
and produce its canonical algebraic form before handing it to Z3 — so
that two constraints describing the same physics canonicalise to the
same Z3 assertion.

In the egg world:

- Each `defrule` becomes an `egg::Rewrite` pair (`:lhs` and `:rhs`).
- The verifier runs equality saturation to compute the equivalence
  class of each constraint expression.
- Extraction picks a cost-minimal representative as the form passed to
  Z3.

That world is not what ships in Tier 1.

## 3. CURRENT STATUS: STUB

The `:egg` backend is registered but not implemented. Read this section
carefully before adding rules.

In `skills/neurosym-forge/scripts/codegen_axioms.py`:

```python
SUPPORTED_BACKENDS = {Keyword("z3"), Keyword("egg"), Keyword("cozo")}

# ... later, in _codegen_one_constraint:
if backend != Keyword("z3"):
    # :egg and :cozo constraints flow through other backends.
    continue
```

In words: a `(defconstraint ... :backend :egg ...)` form passes the
`SUPPORTED_BACKENDS` validation, but `codegen_axioms` silently drops
it. No Z3 assertion is emitted, no egg run happens. This is the
"silent egg" gap documented in `SUPPORT_MATRIX.md`.

Tier 3 of the roadmap promotes egg from stub to live by:

1. Adding `verifiers/<project>/rust-verifier/src/eqsat.rs` with a
   real `egg::Runner`.
2. Switching `codegen_axioms` to emit a separate
   `eqsat_constraints.rs` for `:egg`-backed constraints, and wiring
   `smt.rs` to call `eqsat::canonicalise` before assertion.
3. Replacing this paragraph with an "egg is live" note.

## 4. What rules DO today

Rules in `rules.edn` are consumed by `phases.cljs` for
string-substitution canonicalisation during CLJS compilation. They
participate in:

- Author-facing prettification of constraint forms before display.
- A best-effort canonicalisation pass that catches trivial duplication
  (`(+ a b)` vs `(+ b a)`).

Rules do NOT reach Rust. They do NOT participate in Z3 axiom codegen.
They are a CLJS-only convenience.

Today, `rules.edn` in the osmotic_pressure verifier is `{:forms []}` —
no rules are needed because the single constraint is hand-written in
canonical form. The slot exists for future domain-specific rewrites.

## 5. Convention: rule naming

ID prefixes are namespaced by form family:

- `R###` — `defrule` (rewrite rules)
- `C###` — `defconstraint`
- `L###` — `deflift`
- `Q###` — `defquery`
- `W###` — `defremedy` (W for "workaround")

Allocate IDs sequentially within a project. IDs persist across edits;
deleting a rule does not free its ID for reuse — that would break
git-blame for old verdicts that reference it in the unsat core.

## 6. Fixture tests

Every rule in `rules.edn` SHOULD have a fixture test under
`cljs-orchestrator/test/rules/test_<ID>.cljs`. The scaffolder
`add_rewrite_rule.py` emits a stub with a `:TODO` placeholder for the
input form; fill it in with a `meander.epsilon` rewrite check.

`skills/neurosym-forge/scripts/lint_rewrite_coverage.py` flags rules
without fixtures. Today, with `rules.edn` empty, the linter has
nothing to flag.

## 7. Worked sketch: an algebraic identity

For a chemistry verifier that wants to canonicalise the order of factors
in a multiplication, a rule like:

```edn
(defrule R001-commute-mult
  :tags [:algebraic :commutative]
  :confidence 1.0
  :doc "Multiplication is commutative."
  :lhs (* ?a ?b)
  :rhs (* ?b ?a))
```

is the simplest possible rule. The fixture test would assert that
`(* M (:vant-hoff-i ?s))` rewrites to `(* (:vant-hoff-i ?s) M)` —
trivial under string substitution, but useful once egg gives it
saturation semantics. With egg live, the rule plus associativity would
collapse every permutation of `(* i M R T)` to a single canonical form
before Z3 asserts it.

A more substantive rule — expanding the van 't Hoff equation:

```edn
(defrule R042-vant-hoff-expand
  :tags [:algebraic :domain-osmotic]
  :confidence 1.0
  :doc "van 't Hoff: pi = i * M * R * T"
  :lhs (:osmotic-pressure-pa ?s)
  :rhs (* (:vant-hoff-i ?s) (:molarity ?s) 8.314 (:temperature-k ?s)))
```

This is NOT how the osmotic-pressure verifier is structured today — the
constraint hand-asserts the equation directly, which is more reliable
under the stub-egg world. The rule above is what the project WOULD ship
when egg lands.

## 8. Rule files vs constraint files

A subtle convention: `defrule` belongs in `rules/booklogic/rules.edn`;
`defconstraint` belongs in `rules/booklogic/constraints.edn`. The
distinction is:

- **Rules** are equality declarations consumed by a rewrite engine.
  They have no `:on-unsat` field; failing to apply is fine.
- **Constraints** are sat/unsat predicates consumed by a solver.
  They carry `:on-unsat` with a defect class and message.

Keeping the two files separate keeps the egg path (rules) and the
Z3 path (constraints) cleanly distinguishable in the source tree even
while egg is a stub.

## 9. Failure modes specific to rules

While the `:egg` path is a stub, the CLJS rewrite pass is live and
can still misbehave. Known failure modes:

- **Unbound variable on `:rhs`.** A `?x` appears on the right but
  not the left. `lint_atomspace.py` flags it; the CLJS rewriter
  would silently leave the unbound variable in the output.
- **Non-terminating rule.** A rule like `(* ?a 1) -> ?a` is safe;
  one like `?x -> (* ?x 1)` rewrites indefinitely. Today the CLJS
  pass is one-shot so this only loops at author-test time; once
  egg lands, the saturation iter cap is the safeguard.
- **Tag clash with the linter.** A rule tagged `:eliminating`
  permits `:rhs`-only variables, suppressing the unbound check.
  Use this tag deliberately; it is the only way to disable the
  free-variable lint.

## See also

- `references/metta-idioms.md` — MeTTa's `=` form, which `defrule`
  mirrors.
- `references/phase-boundaries.md` — where rules sit in the pipeline.
- `skills/neurosym-forge/SUPPORT_MATRIX.md` — the live/stub table that
  notes egg as stub.

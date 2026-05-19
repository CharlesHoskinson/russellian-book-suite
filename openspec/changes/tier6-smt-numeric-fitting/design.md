# Design: tier6-smt-numeric-fitting

## Z3 Optimize API call shape

The fitter encodes the rule as a `ForAll`-quantified
implication over the training atoms with ε as a free
existential variable; the Z3 `Optimize` solver minimises ε
subject to the conjunction of per-atom instantiations.

```python
def fit_tolerance(rule_ast, atoms):
    eps = Real("eps")
    opt = Optimize()
    opt.add(eps > 0)
    for atom in atoms:
        lhs_val, rhs_val = evaluate_lhs_rhs(rule_ast, atom)
        opt.add(Abs(lhs_val - rhs_val) <= eps)
    opt.minimize(eps)
    opt.set("timeout", VERIFIER_INDUCTION_FIT_TIMEOUT_MS)
    result = opt.check()
    if result == sat:
        return float(opt.model()[eps].as_decimal(10))
    if result == unknown:
        return None  # caller logs :smt-timeout
    return None      # unsat — no finite ε works
```

The `evaluate_lhs_rhs` helper substitutes atom values into
the rule's LHS / RHS expressions using `_canonical.py`'s
existing variable-binding logic; the result is a pair of Z3
`Real` expressions (constant on each atom).

## Pareto-front discipline for multi-parameter rules

For `(>= (:x ?d) N)` with N to fit, the fitter prefers
smaller N (tighter rule). For `(approx= LHS RHS :tolerance ε)`
with both LHS-parameter and ε, the fitter prefers tighter
ε first, smaller absolute threshold second:

```python
def fit_numeric_params(rule_ast, atoms):
    params = extract_numeric_params(rule_ast)
    opt = Optimize()
    z3_vars = {p: Real(p.name) for p in params}
    add_constraints(opt, rule_ast, atoms, z3_vars)
    # Pareto: minimise tolerance-flavoured params first
    for p in sorted(params, key=tolerance_first_then_size):
        opt.minimize(z3_vars[p])
    result = opt.check()
    if result != sat:
        return None
    return {p.name: float(opt.model()[z3_vars[p]].as_decimal(10))
            for p in params}
```

Z3's `Optimize` natively handles multi-objective lex-min
under the constraint set; the sort key fixes the priority
order.

## Timeout handling

`VERIFIER_INDUCTION_FIT_TIMEOUT_MS` (default 10000) is
passed to Z3 via `opt.set("timeout", ...)`. On timeout,
Z3 returns `unknown`; the fitter returns `None` with a
structured `{:phase :smt-fit :reason :smt-timeout
:timeout-ms <int>}` reason attached to the candidate's
post-mortem.

CRITICAL: a timeout does NOT trigger a retry with a looser
ε. The candidate is dropped. Loosening ε on timeout would
silently weaken the theory; a candidate Z3 cannot tighten
inside 10s is not a candidate worth keeping in the induced
theory. The orchestrator records the drop in the candidate
queue's `:rejection-reason :smt-timeout`.

## Substitution into the rule AST

After a successful fit, the orchestrator substitutes the
fitted ε into the candidate's `:assert` form:

```clojure
;; Before fit
(approx= (:r0 ?d) (- 1.0 (/ 1.0 (:hit ?d))) :tolerance ε)

;; After fit (ε ≈ 0.0426)
(approx= (:r0 ?d) (- 1.0 (/ 1.0 (:hit ?d))) :tolerance 0.0426)
```

The post-fit form is what flows to the validation stage
(later phases run document-held-out 5-fold validation, AGM
revision, etc.). This change ships ONLY the parameter-
finding step; downstream validation is an orchestrator
concern.

## Why not bundle into Phase W (candidate generation)?

The generation stage produces structural candidates (the
shape is fixed; numeric placeholders are ε / N variables).
Numeric fitting is a SEPARATE transformation that requires
Z3 — Phase W's three sources do not touch Z3. Bundling
would couple Cozo / Popper / LLM dispatch with Z3
optimisation; the fitter sits in its own boundary so the
orchestrator can decide whether to fit (default) or skip
(future flag for structural-only experiments).

## Why not LLM-guessed tolerances?

Both deep-research reports flagged this as the framework's
weakest induction surface. The LLM has no access to the
atomspace's numeric distribution; its tolerance guesses
either fail on training data or are vacuously loose. SMT
fitting is exact: Z3 finds the minimum ε that satisfies the
rule across all atoms or proves no finite ε works.

The 10-second budget is generous for a single-rule
quantifier-free arithmetic optimisation; Z3 typically
returns sub-second on the herd-immunity benchmark. The
timeout is the safety net, not the expected path.

## Integration point in the orchestrator pipeline

```
candidate (Phase W)
    ↓
grammar enforcer (Phase V) — drops out-of-grammar candidates
    ↓
SMT numeric fitter (THIS CHANGE) — drops un-fittable candidates
    ↓
validation (later phases) — drops candidates failing held-out tests
    ↓
emission (later phases) — surviving rule lands in induced-theory.edn
```

The fitter is the second filter. Order matters: grammar
rejection is cheap (no solver call); SMT fitting is
expensive (Z3 invocation); held-out validation is most
expensive (Z3 across folds). Cheapest gate first.

# Design: tier5-metta-onboarding-eval

## The grandparent prompt

`skills/neurosym-forge/eval/prompts/grandparent-metta.md`:

> Build a verifier for a small genealogy domain. The book provides
> `Parent(x, y)` facts for a family. Your verifier SHALL assert the
> two-hop relation `Grandparent(x, z) :- Parent(x, y), Parent(y, z)`
> and check at least one grandparent claim made in the source text.
> Use the BookLogic DSL and the neurosym-forge scaffold. The
> grandparent relation is multi-hop graph reachability, not arithmetic;
> consult the SUPPORT_MATRIX before picking a backend. Land at a
> passing `make ci`.

The prompt is one paragraph, like the existing three. It deliberately
does not name `:backend :metta` — that's the affordance the eval
measures. The MeTTa-runtime rule the agent should converge on:

```
(= (Grandparent $x $z) (, (Parent $x $y) (Parent $y $z)))
```

The agent has to (a) discover from the docs that multi-hop reachability
is the `:backend :metta` shape (versus `:z3` for arithmetic, `:cozo`
for tabular reachability), (b) author the rule in MeTTa surface syntax,
(c) bind the rule to a `defconstraint` with `:backend :metta`. Three
discrete steps that each test docs clarity along a different axis.

## Harness extension

The bench harness already tails run logs for milestone events. The new
column is derived after the run completes:

```python
def metta_backend_used(workspace: Path) -> bool:
    constraints = workspace / "rules" / "constraints.edn"
    if not constraints.exists():
        return False
    return ":backend :metta" in constraints.read_text(encoding="utf-8")
```

Truth on this column does not gate success on its own; it joins the
existing `ci_at_seconds` and `terminal_state` columns to drive the
new SUCCESS taxonomy.

## SUCCESS taxonomy for the MeTTa prompt

| Outcome | Definition |
| --- | --- |
| `SUCCESS` | `make ci` PASS AND `:backend :metta` in constraints.edn AND `:metta-results` in verdict surface |
| `SUCCESS_WITHOUT_METTA` | `make ci` PASS AND no `:backend :metta` form — the agent translated the relation to `:z3` |
| `STUB_SUCCESS` | The run used the stub backend (deterministic test path); SUCCESS without measuring docs clarity |
| `TIMEOUT_extract` / `TIMEOUT_ci` | Same as REQ-EVAL-053 |
| `EXIT_NONZERO` | Agent ended its session without reaching `make ci` |

`SUCCESS_WITHOUT_METTA` is not a hard failure. It's a meaningful
signal: the docs either underdescribe when `:metta` is the right
tool, or the `:z3` path is genuinely a valid alternative for this
specific relation. The aggregator reports both rates so a maintainer
can decide which interpretation applies.

## CSV column placement

Add `metta_backend_used` after `error_recovery_count` and before
`asks_for_help_count`. The CSV header line in `eval/onboarding-bench.py`
gains the column; readers that depend on positional indices will need
to update — but the existing tests already consume the header by name
(REQ-EVAL-051 specified the schema), so the change is non-breaking
for downstream readers.

## Aggregator report extension

`docs/eval/onboarding-bench-report.md` already aggregates per-domain
milestone-reach rates. The new section appends after that:

```
## MeTTa-backend-uptake (grandparent-metta prompt only)

| Outcome | Count | Percent |
|---|---|---|
| SUCCESS (used `:backend :metta`) | N | NN% |
| SUCCESS_WITHOUT_METTA (translated to `:z3`) | N | NN% |
| Failed (no `make ci` PASS) | N | NN% |
| STUB_SUCCESS (stub backend only) | N | NN% |

**Interpretation:** if SUCCESS_WITHOUT_METTA dominates, the docs
should be reviewed for clarity on when `:metta` is the right tool
versus an over-engineered choice for arithmetic relations.
```

The interpretation paragraph is part of the report template, not
generated per-run. The framework's maintainers read the numbers and
decide.

## Why a single-domain extension

The bench already has the harness machinery, the CSV writer, the
isolation logic, the workspace-escape detector. Adding a fourth
prompt is a low-risk surface extension. The alternative — a fully
separate MeTTa eval — would duplicate the harness for no analytical
gain. The single domain measures the single new affordance.

# Design: tier5-framing-reckoning

## The three layers of MeTTa-ness

After Tier 5 the framework's surface stratifies into three layers. The
docs need to name them:

| Layer | What it is | Examples |
| --- | --- | --- |
| **MeTTa-runtime-grounded** | Phase O's embedded interpreter actually runs MeTTa. The framework dispatches to it. | `defconstraint :backend :metta`; the `(neighbors ...)`, `(hybrid-match ...)`, `(neighbors-only ...)` grounded atoms; the Atomspace handle objects from Phase P |
| **MeTTa-shaped, not runtime** | Uses MeTTa idioms in EDN-on-disk without running a MeTTa interpreter. | EDN atom encoding; `defrule` (egg-backed); `:backend :z3` / `:cozo` constraints |
| **Pre-Tier-5 promotional drift** | Sentences in older docs that implied the framework "runs MeTTa" without qualifier — to be retired. | Older copy in SKILL.md, references/metta-idioms.md |

## The new concepts doc

`docs/concepts/metta-runtime-grounded-vs-shaped.md` (~150 lines):

```
1. The drift problem in one paragraph
2. What's MeTTa-runtime-grounded after Tier 5 (bulleted list +
   crate version)
3. What's MeTTa-shaped (EDN, egg, Z3, Cozo) — same surface idioms,
   different runtime
4. What earlier docs implied that isn't true (explicit retraction
   block)
5. How to tell at a glance which layer a feature lives in (the
   `(alpha)` qualifier convention)
6. The deprecation path (links to docs/operations/deprecate-metta-backend.md)
```

The doc is short on purpose — it's a wayfinder, not a tutorial.

## SKILL.md before/after

Before (one offending sentence to retire):
> The framework uses MeTTa-style atomspace conventions to give a
> uniform surface across the EDN forms.

After:
> The framework uses MeTTa-shaped EDN conventions for its on-disk
> atoms (see `references/metta-idioms.md`). Tier 5 adds an embedded
> MeTTa runtime (hyperon-experimental 0.2.x, alpha) reachable via
> `defconstraint :backend :metta` and a small set of grounded atoms
> — see
> [docs/concepts/metta-runtime-grounded-vs-shaped.md](../../docs/concepts/metta-runtime-grounded-vs-shaped.md)
> for the line between MeTTa-runtime-grounded and MeTTa-shaped.

Top-of-file `(alpha)` callout under the new "MeTTa runtime" subsection.

## SUPPORT_MATRIX.md row

Add to the form-family table:

```
| `defconstraint :backend :metta` | wired (alpha) | `kg.rs::evaluate_metta_constraint` | hyperon-experimental 0.2.x |
```

Plus a "wired (alpha)" status-legend entry explaining the
hyperon-experimental alpha caveat: API may change incompatibly; the
framework will pin the crate version and the deprecation runbook
covers migration.

## references/metta-idioms.md rewrite

Section 1: "What we borrow from MeTTa" (unchanged surface, but lift the
"atomspace" / "grounded atoms" subsections to acknowledge they describe
the EDN encoding, not a runtime).

Section 2: "What we don't borrow" (unchanged).

Section 3 (NEW): "What we now embed at runtime".
- The hyperon-experimental crate version + alpha status.
- The `:backend :metta` constraint path.
- The Phase P EDN↔MeTTa bijection + Atomspace dedup.
- The Phase Q `(neighbors ...)` grounded atom.
- The Phase R `(hybrid-match ...)` and `(neighbors-only ...)` grounded
  atoms.

Retraction block at the bottom: list any earlier sentence (with a
`git blame` pointer) that implied the framework "runs MeTTa" and mark
it superseded.

## Drift lint shape

`tests/test_support_matrix.py` already pins SUPPORT_MATRIX.md against
codegen reality. The new assertion is narrower:

```python
def test_metta_row_not_described_as_production_or_stable():
    text = SUPPORT_MATRIX.read_text(encoding="utf-8")
    metta_row = extract_row_for(":backend :metta")
    for forbidden in ("production", "production-ready", "stable", "GA"):
        assert forbidden not in metta_row.lower(), (
            f"SUPPORT_MATRIX.md ':metta' row contains '{forbidden}' "
            f"while hyperon-experimental remains alpha. Update the doc "
            f"or the crate version."
        )
```

The same shape applies to SKILL.md and references/metta-idioms.md
within their `:metta`-adjacent sections.

## Deprecation runbook outline

`docs/operations/deprecate-metta-backend.md`:

1. Trigger conditions (hyperon-experimental API break; security
   advisory; performance regression beyond acceptable bounds).
2. Migration paths per constraint shape:
   - Arithmetic constraints → `:backend :z3`.
   - Reachability constraints → `:backend :cozo` (when expressible
     as Datalog) or hand-rewrite as Z3 axioms.
3. Test impact: which `tests/test_metta_*.py` files become obsolete
   and which (the bijection tests) survive.
4. SUPPORT_MATRIX.md update: mark the row "DROP" with a date.
5. Communication template for the changelog and the framework's
   external README.

The runbook is documentation, not code. It exists so the framework
isn't paralysed if hyperon-experimental moves under it.

## §2.5 row in docs/booklogic-dsl-reference.md

The `defconstraint` backend table in §2.5 grows one row:

```
| :metta | hyperon-experimental | alpha | Phase O |
```

The `(alpha)` qualifier is the wayfinder readers use to know they're
on the runtime-grounded edge of the framework, not on a hardened
core surface.

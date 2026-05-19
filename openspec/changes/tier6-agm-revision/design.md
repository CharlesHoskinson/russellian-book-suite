# Design: tier6-agm-revision

## The AGM frame

AGM (Alchourrón / Gärdenfors / Makinson) gives three
operations on a belief set: expansion (`+`), contraction
(`-`), and revision (`*`). The Levi identity defines
revision in terms of contraction and expansion:

```
K * φ = (K - ¬φ) + φ
```

For the induction layer this maps onto:

- The induced theory is the belief set `K`.
- A retracted paper or contradicting atom is the contracting
  signal.
- Entrenchment ranks each rule; less-entrenched rules are
  given up first during contraction.
- Status (`:active` / `:tentative` / `:quarantined`)
  records the post-revision standing.

Promote-up (turning a `:quarantined` rule back into
`:active` when new supporting evidence arrives) is the dual
operation. Tier 6 implements contract-down only; promote-up
is Tier 7 because it requires the AST-aware semantic
distance metric the design spec flagged as open research.

## API shape — `revise_theory`

`skills/neurosym-forge/scripts/_agm_revision.py` exposes one
top-level function and one dataclass:

```python
@dataclass
class RevisionReport:
    rules_affected: int
    rules_active: int
    rules_tentative: int
    rules_quarantined: int
    diff_summary: str
    full_quarantine_warning: bool

def revise_theory(
    induced_path: Path,
    prov_path: Path,
    retracted_docs: list[str] | None = None,
    contradicting_atoms: list[str] | None = None,
) -> RevisionReport: ...
```

Either or both of `retracted_docs` and `contradicting_atoms`
may be passed. The function loads the induced theory and the
sidecar, mutates the sidecar in-place, writes the sidecar
back to `prov_path`, and returns the report. The induced
theory file itself is NOT rewritten — the rules persist; only
their provenance status changes.

## The revision algorithm

For every rule in the sidecar:

1. Compute the set of affected atoms: rule's
   `:prov/derived-from-atoms` ∩ `contradicting_atoms`.
2. Compute the set of affected docs: rule's
   `:prov/source-documents` ∩ `retracted_docs`.
3. If both sets are empty, the rule is unaffected; continue.
4. Remove the affected atoms from the support; remove the
   affected docs from the document list.
5. Re-run the validation step (5-fold document-held-out
   from Phase X) on the diminished support. This produces a
   new `held-out-sat-rate`.
6. Recompute entrenchment per the formula below.
7. Look up the new status from the threshold table.
8. Update the sidecar entry: new
   `:prov/derived-from-atoms`, new
   `:prov/source-documents`, new
   `:prov/entrenchment`, new `:prov/status`. The
   `:prov/validated-by` list gains a new entry recording
   the revision pass.

## Entrenchment formula

```
entrenchment = held_out_sat_rate × min(support_doc_count / 10.0, 1.0)
```

- `held_out_sat_rate ∈ [0.0, 1.0]` from the 5-fold
  document-held-out validation pass (Phase X).
- `support_doc_count` is the number of distinct documents
  remaining in `:prov/source-documents` after contraction.
- The `min(..., 1.0)` cap: rules supported by ≥10 documents
  saturate the document-diversity term; beyond that, only
  held-out-sat-rate moves entrenchment.

The result is bounded in `[0.0, 1.0]`. The 10-document
saturation is a design choice (not a deep-research-report
prescription): it matches the "≥10 papers cite the
relationship" rule-of-thumb authors apply when curating
hand-written constraints, and it prevents a single
high-support rule from dominating the threshold cliff.

## Status thresholds

```
entrenchment >= 0.7        →  :active
0.4 <= entrenchment < 0.7  →  :tentative
entrenchment < 0.4         →  :quarantined
```

The choice of 0.7 / 0.4 mirrors the conventional
"high-confidence" / "advisory" split used elsewhere in the
framework (e.g., Phase S's confidence propagation). A rule
that drops from `:active` to `:tentative` retains its
defect plumbing but is rendered as advisory in Phase T's
manuscript annotations; a rule that drops to
`:quarantined` is excluded from `make ci` but still appears
in `forge theory` output for human review.

The thresholds are NOT user-tunable in this tier. A future
Tier 7 may expose them per-project; today the discipline is
"one number, framework-wide."

## RevisionReport shape

The report dict surfaced through `forge revise` carries:

```python
RevisionReport(
    rules_affected=3,         # count of rules whose status changed
    rules_active=12,          # post-revision counts by status
    rules_tentative=4,
    rules_quarantined=2,
    diff_summary="herd-immunity-threshold: :active -> :tentative; "
                 "vaccine-efficacy-r0: :active -> :quarantined; "
                 "trial-cohort-size: :tentative -> :quarantined",
    full_quarantine_warning=False,
)
```

`rules_affected` is the count whose status transitioned (NOT
the count whose entrenchment merely changed). The
`diff_summary` is a one-line `; `-separated string ordered
by rule id; the CLI re-formats for display.

## Full-quarantine warning

If a single revision moves every rule in the induced theory
to `:quarantined`, `full_quarantine_warning` is set true
and a structured log entry fires naming the revision input
(retracted docs / contradicting atoms). The likely
interpretations: the new evidence is itself in error, the
theory was overfit, or the corpus changed in a way the
inducer should re-run from scratch on. The framework does
not auto-resolve; surfacing the warning is the discipline.

## Per-corpus scoping

When `:prov/induced-from-corpus` is present on a rule
(REQ-PROV-046), the revision uses it to scope retraction. A
`retracted_docs` argument is applied only to rules whose
`:prov/induced-from-corpus` matches the corpus the
retracted doc belongs to. The corpus → doc-list mapping
comes from the corpus's `claims.jsonl` manifest. Without
the corpus field, retractions apply globally — the
backward-compatible default for single-corpus projects.

## Why never silent-overwrite?

The AGM postulates of recovery and consistency together
imply: a contraction must preserve enough of `K` that
expansion can re-add information, and the result must be
consistent with the new input. Silent overwrite violates
recovery (the old support is gone) and breaks the audit
trail (a reviewer can't trace why a rule changed). The
sidecar-mutation discipline — record every change in the
provenance entry — is the operational form of recovery.

## Test surface

The Phase Z test suite covers four primary cases per
REQ-REVISE-046:

1. Retract a paper that supports 1 rule → that rule's
   entrenchment recomputes; status may drop.
2. Retract a paper that supports 5 rules → all 5 rules
   contract; ≥1 status drop is expected.
3. Contradicting atom present on an `:active` rule → rule
   transitions to `:tentative` (or `:quarantined`
   depending on entrenchment).
4. Synthetic scenario where every rule's support shrinks
   below the quarantine threshold → `full_quarantine_warning`
   fires; structured log entry present.

# Design: tier6-provenance-sidecar

## Sidecar shape

The companion file `rules/booklogic/induced-theory.prov.edn`
mirrors the rule-id keyset of `induced-theory.edn` exactly:

```edn
{:version 1
 :rules
 {:induced/herd-immunity-threshold
  {:prov/derived-from-atoms ["adsc-001-A12" "adsc-014-B03"]
   :prov/source-documents ["pmid:12345" "pmid:67890"]
   :prov/contradiction-atoms ["adsc-099-X07"]
   :prov/proposed-by {:lineage :llm
                      :model "claude-haiku-4-5"
                      :provider :anthropic}
   :prov/validated-by [{:backend :z3 :held-out-folds 5
                        :sat-rate 0.89 :tolerance-fit 0.043}
                       {:backend :cozo :support-rate 0.94}]
   :prov/entrenchment 0.83
   :prov/status :active
   :prov/llm-repair-calls 2
   :prov/cost-usd 0.018
   :prov/semantic-neighbours ["c-203" "c-411"]
   :prov/induced-from-corpus "verifiers/adsc-clinical/.../claims_clean.jsonl"}}}
```

This is the verbatim schema from
`docs/specs/2026-05-19-tier6-theory-induction-design.md`
§"Schema: induced-theory.prov.edn".

## API shape — `ProvenanceSidecar`

`skills/neurosym-forge/scripts/_provenance.py` ships a
single class with five methods:

```python
class ProvenanceSidecar:
    def __init__(self, version: int = 1): ...
    @classmethod
    def load(cls, path: Path) -> "ProvenanceSidecar": ...
    def save(self, path: Path) -> None: ...
    def add_rule_provenance(self, rule_id: str, prov: dict) -> None: ...
    def lookup(self, rule_id: str) -> dict | None: ...
    def iter_rules(self) -> Iterator[tuple[str, dict]]: ...
    def remove_rule(self, rule_id: str) -> None: ...
```

`add_rule_provenance` validates the `:prov/*` field set on
insertion: required keys per REQ-PROV-041 must be present;
optional keys per REQ-PROV-042 and REQ-PROV-046 may be
present. Unknown keys raise `ValueError` — the schema is
closed by design so future drift is loud.

## Round-trip discipline

EDN round-trip uses the existing `_edn_reader` / `_edn_writer`
modules. Keywords (`Keyword(:prov/status)`) round-trip
verbatim; floats avoid scientific notation per REQ-EDN-050;
lists vs vectors preserve their delimiter per REQ-EDN-051.
The round-trip test (REQ-PROV-045) writes a 10-rule sidecar,
re-reads it, then asserts dict equality on every rule's
provenance — byte-identity flows from the underlying EDN
guarantees.

## Semantic-neighbours integration

Phase Q's `_semantic_index.SemanticIndex` exposes
`similar_atoms(atom_id, k)`. When present, the inducer
records the top-3 most-similar atoms NOT already in the
support set as `:prov/semantic-neighbours`. A human reviewer
reading a rule's provenance gets a "did you also consider
these?" prompt. When the index is absent (e.g., the project
hasn't built one), the key is omitted; the sidecar is still
valid.

## Graceful-degrade error path

If `rules/booklogic/induced-theory.prov.edn` is missing or
malformed, `ProvenanceSidecar.load` raises
`ProvenanceSidecarError` carrying the file path and the
parse-error detail. `forge theory` catches this through the
existing `_cli_errors.interpret` table and prints a
hand-readable error pointing at the file, then continues
with an empty `ProvenanceSidecar()` instance. The rule list
in `induced-theory.edn` is unaffected — the human reviewer
still sees the rules, just without provenance.

The rationale: a corrupted sidecar must not block inspection
of the theory itself. Sidecar corruption is an authoring
bug, not a verification correctness bug.

## Per-corpus tracking

When a project ingests two corpora and induces from each,
the `:prov/induced-from-corpus` field records the corpus
path on each rule. A later `forge revise --retracted-paper`
can scope its contraction to the corpus the paper belongs
to, leaving rules induced from other corpora untouched. This
is the precondition for Tier 7's promote-up logic (Phase Z
defers promote-up; this change does not need it for
contract-down).

## Scaffolded-project vendor

`scaffold_project.py` already copies the rules/ directory
tree from `assets/project-template/rules/`. Tier 6 adds
`assets/project-template/rules/booklogic/induced-theory.prov.edn.tmpl`
containing the empty `{:version 1 :rules {}}` shape so a
freshly scaffolded project can run `forge induce`
immediately without a chicken-and-egg "sidecar does not
exist" path.

## Why a separate file, not an extra key in `induced-theory.edn`?

Two reasons:

1. The provenance data is at least one order of magnitude
   larger than the rule data (lists of 100+ atom IDs per
   rule). Folding it into the same file makes the rule file
   unreadable in a diff.
2. The sidecar is the AGM-revision target (Phase Z). A
   contraction recomputes the sidecar atomically; the rule
   file is unchanged until the rule itself is rewritten.
   Two files = two independent diffs.

## Cost discipline

The sidecar is pure I/O; no LLM calls, no solver dispatch.
This change adds zero cost-USD to the induction loop.

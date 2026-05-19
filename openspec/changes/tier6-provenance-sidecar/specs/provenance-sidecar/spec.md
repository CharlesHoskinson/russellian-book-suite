# Capability delta: provenance-sidecar — change: tier6-provenance-sidecar

This change introduces a new capability `provenance-sidecar`,
a companion EDN file to `induced-theory.edn` carrying PROV-O
fields for every induced rule. The sidecar is the audit
target a human reviewer reads to answer "which atoms and
source documents supported this constraint?"; it is also the
AGM-revision target Phase Z mutates on paper retraction.

## ADD

### REQ-PROV-040 — Ubiquitous

The framework SHALL ship
`skills/neurosym-forge/scripts/_provenance.py` exposing
`class ProvenanceSidecar` with methods
`add_rule_provenance(rule_id, prov_dict)`,
`lookup(rule_id) -> dict | None`,
`iter_rules() -> Iterator[tuple[str, dict]]`,
`remove_rule(rule_id)`,
`save(path: Path)`, and a class method
`load(path: Path) -> "ProvenanceSidecar"`.

**Rationale:** A single class owning the sidecar's read /
write / mutate surface keeps the validation discipline (the
closed `:prov/*` key set) in one place and lets Phase Z
contract entries through the same surface Phase Y populates.
**Tested by:**
`tests/test_provenance_round_trip.py::test_sidecar_api_shape`
(added in Y1.1)

### REQ-PROV-041 — Ubiquitous

Each rule's provenance entry SHALL include AT MINIMUM the
following keys: `:prov/derived-from-atoms` (list of atom
ids), `:prov/source-documents` (list of document ids),
`:prov/contradiction-atoms` (list of atom ids that fail the
rule but were retained as advisory), `:prov/proposed-by`
(map of `:lineage`, `:model`, `:provider`),
`:prov/validated-by` (list of solver-run maps each carrying
`:backend` and outcome fields), `:prov/entrenchment` (float
in `[0.0, 1.0]`), `:prov/status` (one of `:active`,
`:tentative`, `:quarantined`),
`:prov/llm-repair-calls` (integer in `[0, 3]`), and
`:prov/cost-usd` (float `>= 0.0`). `add_rule_provenance`
SHALL raise `ValueError` on missing required keys, on unknown
extra keys outside the closed schema, on an out-of-enum
`:prov/status`, on `:prov/llm-repair-calls` outside the
0-3 range, or on `:prov/entrenchment` outside `[0.0, 1.0]`.

**Rationale:** PROV-O is the W3C standard provenance
vocabulary; closing the key set means future drift surfaces
as a `ValueError` at insertion time rather than as a missing
field at audit time. The repair-call cap mirrors the
AutoVerus per-rule discipline the design spec inherited from
both deep-research reports.
**Tested by:**
`tests/test_provenance_round_trip.py::test_required_fields_present`,
`tests/test_provenance_round_trip.py::test_unknown_key_rejected`,
`tests/test_provenance_round_trip.py::test_status_enum_enforced`
(added in Y2.1-Y2.3)

### REQ-PROV-042 — Optional feature

WHERE Phase Q's `SemanticIndex` is available to the inducer,
the provenance entry MAY include
`:prov/semantic-neighbours` listing the top-3 most-similar
atoms NOT in the rule's support set; the field SHALL be a
list of atom ids of length at most 3. When the
`SemanticIndex` is absent the field SHALL be omitted (it is
not required by REQ-PROV-041).

**Rationale:** A human reviewer auditing an induced rule
benefits from a "see also" prompt pointing at semantically
adjacent atoms the inducer considered but did not cite; the
field is advisory and the sidecar is still well-formed
without it on projects that have not built a semantic index.
**Tested by:**
`tests/test_provenance_round_trip.py::test_semantic_neighbours_optional_round_trip`
(added in Y3.1)

### REQ-PROV-043 — Ubiquitous

The sidecar SHALL persist at the path
`rules/booklogic/induced-theory.prov.edn` relative to a
verifier project; the top-level shape SHALL be the EDN map
`{:version 1 :rules {<rule-id> <prov-dict>}}` and SHALL be
written by `ProvenanceSidecar.save` via the
framework's existing `_edn_writer.dumps` (so EDN float-emit,
keyword-emit, and list-vs-vector conventions per the
edn-boundary capability apply transitively).

**Rationale:** A predictable file path lets Phase AA
(`forge theory` / `forge revise`) and Phase Z (AGM
revision) locate the artifact without per-call wiring; the
top-level `:version` field future-proofs the schema if a
later tier extends the PROV-O field set.
**Tested by:**
`tests/test_provenance_round_trip.py::test_sidecar_file_path_and_top_level_shape`
(added in Y4.1)

### REQ-PROV-044 — Unwanted behaviour

IF the sidecar file at
`rules/booklogic/induced-theory.prov.edn` is missing or
malformed (unreadable EDN, missing `:version`, missing
`:rules`), THEN `ProvenanceSidecar.load` SHALL raise
`ProvenanceSidecarError` carrying the file path and the
underlying parse error, AND `forge theory` SHALL surface
the error through the existing `_cli_errors.interpret`
table as a hand-readable user message naming the file path,
AND `forge theory` SHALL continue with an empty
`ProvenanceSidecar()` instance so the rules in
`induced-theory.edn` remain inspectable.

**Rationale:** A corrupted sidecar must not block inspection
of the rules themselves; sidecar corruption is an authoring
bug, not a verification correctness bug. Surfacing the file
path in the user message lets a reviewer fix or delete the
file in one step.
**Tested by:**
`tests/test_provenance_graceful_degrade.py::test_missing_sidecar_continues_with_empty`,
`tests/test_provenance_graceful_degrade.py::test_malformed_sidecar_surfaces_path_in_error`
(added in Y5.3)

### REQ-PROV-045 — Ubiquitous

A round-trip test SHALL write a sidecar containing at least
10 rules each populated with every required key from
REQ-PROV-041 and every optional key from REQ-PROV-042 and
REQ-PROV-046, then read the sidecar back via
`ProvenanceSidecar.load`, then assert that every rule's
provenance dict equals the original dict by Python `==`
comparison.

**Rationale:** EDN round-trip stability is a precondition
for AGM revision; if a rule's `:prov/source-documents` list
silently reorders on save / load, Phase Z's set-intersection
on retracted-paper ids becomes nondeterministic. The
10-rule, every-field test is the regression boundary.
**Tested by:**
`tests/test_provenance_round_trip.py::test_ten_rule_byte_stable_round_trip`
(added in Y4.3)

### REQ-PROV-046 — Optional feature

WHERE multiple corpora have been ingested into the same
project (`forge induce` invoked twice with different
`--corpus` arguments), the provenance entry SHALL include
`:prov/induced-from-corpus` carrying the corpus path used
to induce the rule; the field SHALL be a string and SHALL be
omitted on rules induced from a single-corpus project.

**Rationale:** Phase Z's AGM revision needs to scope a
paper retraction to the corpus the paper belongs to; without
per-rule corpus tracking, a contraction on one corpus would
spuriously demote rules induced from another corpus that
happens to share the retracted paper id by coincidence.
**Tested by:**
`tests/test_provenance_round_trip.py::test_induced_from_corpus_round_trip`
(added in Y3.2)

### REQ-PROV-047 — Ubiquitous

`skills/neurosym-forge/scripts/scaffold_project.py` SHALL
vendor a starter sidecar
`rules/booklogic/induced-theory.prov.edn` containing the
empty shape `{:version 1 :rules {}}` into every freshly
scaffolded verifier project via the existing
`assets/project-template/` template-walk pattern.

**Rationale:** A freshly scaffolded project must be able to
run `forge induce` immediately without a chicken-and-egg
"sidecar does not exist" path; the empty starter file gives
the inducer a well-formed target on the first invocation.
**Tested by:**
`tests/test_scaffold_project.py::test_starter_sidecar_present_in_scaffold`
(added in Y6.2)

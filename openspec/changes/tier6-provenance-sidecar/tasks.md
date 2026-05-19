# Tasks: tier6-provenance-sidecar

See `docs/plans/2026-05-19-tier6-theory-induction.md` Phase Y
for full TDD steps. Task numbers correspond 1:1.

## Phase Y.1 — Sidecar module skeleton

- [ ] Y1.1: New
  `skills/neurosym-forge/scripts/_provenance.py` declaring
  `class ProvenanceSidecar` with stub methods `load`, `save`,
  `add_rule_provenance`, `lookup`, `iter_rules`,
  `remove_rule`. (REQ-PROV-040)
- [ ] Y1.2: Declare `class ProvenanceSidecarError(Exception)`
  for graceful-degrade surface (REQ-PROV-044).

## Phase Y.2 — Required-field validation

- [ ] Y2.1: `add_rule_provenance` validates the required key
  set (`:prov/derived-from-atoms`,
  `:prov/source-documents`, `:prov/contradiction-atoms`,
  `:prov/proposed-by`, `:prov/validated-by`,
  `:prov/entrenchment`, `:prov/status`,
  `:prov/llm-repair-calls`, `:prov/cost-usd`); raises
  `ValueError` on missing required keys or unknown keys
  outside the closed schema. (REQ-PROV-041)
- [ ] Y2.2: Status enum check: `:prov/status` must be one of
  `:active`, `:tentative`, `:quarantined`. (REQ-PROV-041)
- [ ] Y2.3: Repair-call cap check: `:prov/llm-repair-calls`
  is an integer in `[0, 3]`. (REQ-PROV-041)

## Phase Y.3 — Optional fields

- [ ] Y3.1: Accept `:prov/semantic-neighbours` (list of atom
  ids, optional). (REQ-PROV-042)
- [ ] Y3.2: Accept `:prov/induced-from-corpus` (string,
  optional). (REQ-PROV-046)

## Phase Y.4 — EDN round-trip

- [ ] Y4.1: `save(path)` writes via `_edn_writer.dumps` to
  `rules/booklogic/induced-theory.prov.edn` with top-level
  shape `{:version 1 :rules {<rule-id> <prov-dict>}}`.
  (REQ-PROV-043)
- [ ] Y4.2: `load(path)` reads via `_edn_reader.loads`,
  validates `:version` field, returns a populated
  `ProvenanceSidecar`. (REQ-PROV-043)
- [ ] Y4.3: New `tests/test_provenance_round_trip.py` writes
  a 10-rule sidecar covering every required + optional key,
  reads it back, asserts every rule's provenance dict equals
  the original. (REQ-PROV-045)

## Phase Y.5 — Graceful-degrade error path

- [ ] Y5.1: `load(path)` on missing file raises
  `ProvenanceSidecarError(path, "missing")`; on malformed
  EDN raises `ProvenanceSidecarError(path, parse_err)`.
  (REQ-PROV-044)
- [ ] Y5.2: Extend `_cli_errors.interpret` to render
  `ProvenanceSidecarError` as a structured user message
  pointing at the file path. (REQ-PROV-044)
- [ ] Y5.3: Test
  `tests/test_provenance_graceful_degrade.py::test_missing_sidecar_continues_with_empty`.
  (REQ-PROV-044)

## Phase Y.6 — Scaffold integration

- [ ] Y6.1: Author
  `skills/neurosym-forge/assets/project-template/rules/booklogic/induced-theory.prov.edn.tmpl`
  with the empty `{:version 1 :rules {}}` shape.
  (REQ-PROV-047)
- [ ] Y6.2: Verify `scaffold_project.py` copies the new
  template into freshly scaffolded projects via the existing
  template-walk loop. (REQ-PROV-047)

## Phase Y.7 — Commit

- [ ] Y7.1: Commit sidecar module + tests + scaffold
  template once Y1-Y6 are green.

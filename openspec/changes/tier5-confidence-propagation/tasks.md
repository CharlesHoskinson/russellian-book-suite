# Tasks: tier5-confidence-propagation

See `docs/plans/2026-05-19-tier5-scale-author.md` Phase S for full
TDD steps. Task numbers track that document.

## Phase S.1 — Ingest validation

- [ ] S1.1: `verifiers/osmotic_pressure/scripts/ingest_ledger.py` and
  `verifiers/bermuda/scripts/ingest_ledger.py` replace the
  `claim.get("confidence", 0.0)` default with a strict check;
  raise `IngestConfidenceError` on missing, out-of-range, or
  non-numeric values with the offending claim id in the message.
  (REQ-CONFIDENCE-043)
- [ ] S1.2: Unit test exercises (a) missing field, (b)
  `confidence = -0.1`, (c) `confidence = 1.4`, (d)
  `confidence = "high"`; each raises with the expected message.

## Phase S.2 — Defect-confidence field

- [ ] S2.1: `smt::check_all` in both verifiers, after the unsat
  core is materialised, computes
  `min(atom.confidence for atom in core)` and attaches it to the
  defect's verdict entry as `:defect-confidence`. (REQ-CONFIDENCE-040)
- [ ] S2.2: Unit test: build a synthetic core with confidences
  `[0.9, 0.4, 0.7]`; assert `defect-confidence` is `0.4`.

## Phase S.3 — Verdict-level confidence

- [ ] S3.1: After all per-subject + shared + corpus defects are
  collected, compute the geometric mean of their
  `:defect-confidence` values into `:verdict-confidence`. Zero
  defects yields `1.0`. (REQ-CONFIDENCE-042)
- [ ] S3.2: Unit test: a verdict with defect-confidences
  `[0.9, 0.81]` has `:verdict-confidence ≈ 0.854`.

## Phase S.4 — Advisory downgrade

- [ ] S4.1: Read `VERIFIER_CONFIDENCE_THRESHOLD` (default `0.5`)
  in `smt::check_all`; for each defect whose unsat core has every
  atom below the threshold, set `:severity :advisory` and
  preserve the original in `:declared-severity`.
  (REQ-CONFIDENCE-041)
- [ ] S4.2: Unit test exercises high-conf chain (severity
  preserved), mixed chain (defect-conf = min, severity
  preserved), all-low chain (downgraded to `:advisory`).
  (REQ-CONFIDENCE-045)

## Phase S.5 — `verdict_to_qa.py` advisory routing

- [ ] S5.1: Both verifiers' `verdict_to_qa.py` partition the
  defects list into `defects` and `advisory_defects` arrays based
  on `:severity`; preserve `defect_confidence` and pass
  `verdict_confidence` to the top level. (REQ-CONFIDENCE-044)
- [ ] S5.2: Snapshot test: a fixture verdict with one hard and
  one advisory defect produces a JSON with one entry in each
  array.

## Phase S.6 — Docs

- [ ] S6.1: `docs/booklogic-dsl-reference.md` §1.4 documents the
  `:confidence` field's flow: ingest validation, weakest-link
  rule, geometric-mean verdict, and the env-var threshold knob.
- [ ] S6.2: `skills/neurosym-forge/SUPPORT_MATRIX.md` adds a
  "confidence propagation" row marked `wired`.

## Phase S.7 — PR

- [ ] S7.1: Push `plan/tier5-scale-author` (confidence slice) and
  open the PR.
- [ ] S7.2: Merge on green CI.

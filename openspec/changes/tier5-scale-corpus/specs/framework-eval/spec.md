# Capability delta: framework-eval — change: tier5-scale-corpus

Phase M (`eval-third-verifier`) added REQ-EVAL-040..047
establishing build-log discipline at 1× scale (~100 claims).
This change extends the same capability with REQ-CORPUS-040..046
at 10× scale on a real 1000+ claim corpus.

## ADD

### REQ-CORPUS-040 — Ubiquitous

The framework SHALL ship a fourth domain verifier under
`verifiers/adsc-clinical/` following the standard project
structure: `rules/booklogic/`, `fixtures/`, `rust-verifier/`,
`cljs-orchestrator/`, `scripts/`, `tests/`, `Makefile`,
`package.json`, `pyproject.toml`, `deps.edn`, `nbb.edn`,
`shadow-cljs.edn`, `README.md`, `SKILL.md`.

**Rationale:** The first three verifiers (bermuda, osmotic,
epidemiology) all operate at ~100-claim scale. A fourth
verifier against a real 1000+ claim corpus is the minimum bar
for the "general-purpose" framing extending past one order of
magnitude.
**Tested by:** `tests/test_scale_verifier_layout.py::test_standard_project_files_present` (added in O1.1).

### REQ-CORPUS-041 — Ubiquitous

The verifier SHALL ingest at least 1000 claims from the
source corpus
(`~/OneDrive/Desktop/stemCells/ADSC_Complete_Report.md`); a
`make extract` step SHALL report a non-empty by-predicate
distribution covering at least 8 distinct predicates.

**Rationale:** "1000 claims" without predicate diversity
collapses to a microbenchmark; the 8-predicate floor ensures
the corpus exercises the framework's typed-atom surface, not
a single hot-path.
**Tested by:** `tests/test_scale_corpus_distribution.py::test_at_least_1000_claims_eight_predicates` (added in O2.3).

### REQ-CORPUS-042 — Ubiquitous

The verifier SHALL pass `make ci` end-to-end with at least 5
clean fixtures (no defects expected) and 3 doctored fixtures
(defects expected); each doctored fixture SHALL target a
distinct defect class (inconsistent cohort size, p-value
drift, misquoted endpoint).

**Rationale:** Three distinct defect classes prove the
verifier discriminates among failure modes rather than firing
on a single brittle pattern. Mirrors Phase M's three-clean +
two-doctored bar, scaled up.
**Tested by:** `tests/test_scale_corpus_fixtures.py::test_make_ci_green_on_five_clean_three_doctored` (added in O3.3).

### REQ-CORPUS-043 — Ubiquitous

A build log SHALL be authored at
`docs/eval/2026-05-19-scale-corpus-build-log.md` recording
every framework gap surfaced only at 1000-claim scale. Each
entry SHALL include the symptom, root cause, resolution
(`fixed`, `workaround`, `deferred-to-issue-N`), the claim
count at which the issue appeared, and a tier-link where one
applies.

**Rationale:** Phase M's build-log discipline at 1× scale is
the artefact, not the verifier. Phase O extends the same
discipline at 10× scale; scale-only gaps are precisely the
ones the existing eval bench cannot surface.
**Tested by:** `tests/test_scale_build_log.py::test_build_log_has_entries_with_required_fields` (added in O2.1).

### REQ-CORPUS-044 — Unwanted behaviour

IF the verifier hits a performance cliff (any phase taking
longer than 5 minutes wall-clock), THEN the build log SHALL
include profiling output naming the slow path. Profile
artefacts SHALL live under `docs/eval/profiles/` and the
build-log entry SHALL link them.

**Rationale:** A naked "Phase X is slow" without a profile is
not actionable. Forcing profile capture at the cliff is the
discipline that produces fixable issues rather than vague
complaints.
**Tested by:** `tests/test_scale_build_log.py::test_slow_phases_link_profile_artefacts` (added in O4.2).

### REQ-CORPUS-045 — Optional feature

WHERE the corpus contains cross-paragraph consistency claims
(the same trial referenced in two sections with overlapping
quantitative claims), the verifier SHALL produce at least one
constraint targeting that consistency — exercising Phase R's
`:scope :corpus` work. If `:scope :corpus` is not yet wired,
the build log SHALL log the gap and link Phase R's OpenSpec
change folder.

**Rationale:** Phase R (cross-chapter consistency) needs a
real-world consumer to drive its design; the ADSC corpus
provides natural cross-paragraph pairs. This REQ binds the
two phases together so Phase R's design is grounded in Phase
O's evidence.
**Tested by:** `tests/test_scale_corpus_constraints.py::test_at_least_one_scope_corpus_constraint_or_logged_gap` (added in O3.1).

### REQ-CORPUS-046 — Ubiquitous

A scale-eval report SHALL be authored at
`docs/eval/2026-05-19-scale-eval-report.md` synthesising six
metrics: claims-per-minute throughput, peak RSS in MB, defect
detection rate on doctored fixtures, false-positive rate on
clean fixtures, the phase with longest runtime, and a
named-scaling-profile section identifying which phases scaled
linearly and which hit cliffs.

**Rationale:** Phase M's usefulness report named three
qualitative buckets. Phase O's scale-eval report adds
quantitative ground truth — the public-facing answer to
"does the framework scale?" backed by numbers, not assertions.
**Tested by:** `tests/test_scale_eval_report.py::test_six_metrics_present_and_scaling_profile_named` (added in O4.3).

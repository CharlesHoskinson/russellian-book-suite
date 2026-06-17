# Internal adversarial audit — homoiconic-KG C0 + P2

Date: 2026-06-17
Branch: `feat/homoiconic-kg-cutover`
Scope: commits `796f131..HEAD` — C0.1/C0.2/C0.3 characterization goldens, P2.1
status single-source, P2.2 defconstraint compiler, P2.3 Cozo-backed
`validate_shacl` + parity.
Method: read the code cold; ran the book-knowledge (304 pass) and book-thesis
suites; wrote ~6 probe scripts in both venvs to exercise behaviour the committed
tests do not (out-of-range/out-of-enum/wrong-datatype injections on BOTH engines,
real-bermuda runs on both backends, determinism across 3 runs and 3 hash seeds,
golden re-capture). All probes removed; tracked files restored via `git checkout`;
only the four pre-existing untracked `competency-*.md` reports remain.

## Executive verdict

**C0+P2 is sound enough to build P3 on.** The compiler is pure and deterministic,
the status single-source (P2.1) is genuinely de-duplicated and faithfully
preserves the old transition matrix, the D9–D11 violating golden (C0.3) is
non-vacuous and reproducible, and the public `validate_shacl` contract is
preserved. The cross-engine equivalence holds for every case the data contract can
actually produce.

But the parity story is weaker than the commit messages and the divergence note
claim, and two real semantic divergences exist between the engines:

- The **single most important finding**: the rdflib path's conformance verdict
  and the Cozo path's verdict **disagree on three classes of out-of-contract data**
  (confidence `< 0.0`; wrong-datatype confidence; and — by construction — anything
  the message-remap collapses). The committed parity test never exercises any of
  them, so "rdflib == golden == cozo" is proven only on the four violations the one
  fixture happens to inject. When P5.3 flips the default to `cozo`, the SHACL gate
  silently weakens for that data. **It does not affect real bermuda data** (the
  JSON-schema record contract rejects all three at write time), so it is not a
  release blocker, but it is a latent correctness gap the migration must own before
  the legacy stack is deleted, not a thing to discover in P5.

Everything below is tagged by severity, with file:line evidence, how it was
verified, whether it touches REAL data, and a fix calibrated against real bermuda.

---

## Findings

### [CRITICAL] C-1 — `confidence < 0.0` conforms under Cozo but fails under rdflib (engine `conforms` divergence)

**What's wrong.** `assets/kg-constraints/confidence-range.edn` only ports the
`sh:maxInclusive 1.0` arm (`:filter [[> ?conf 1.0]]`). pyshacl's `ClaimShape`
enforces BOTH `sh:minInclusive 0.0` AND `sh:maxInclusive 1.0`
(`assets/shapes.ttl:21-26`). A claim with `confidence = -0.5`:

- rdflib path → `conforms=False`, 1 violation (`#confidence`).
- Cozo path → `conforms=True`, 0 violations.

This is a `conforms`-flag divergence, not just a message difference — the two
engines return opposite release verdicts for the same input. The `_DEFERRED.md`
and the EDN comment both call the `< 0.0` arm "out of scope," but the spec
(REQ-KG-012) lists `tbf:confidence ... 0.0..1.0 range` as a covered constraint, and
REQ-KG-013 requires "the same `conforms` verdict the pyshacl path returned." It is
not reproduced.

**Evidence.** `assets/kg-constraints/confidence-range.edn:30` (`[[> ?conf 1.0]]`),
`assets/shapes.ttl:23-25` (both `sh:minInclusive`/`sh:maxInclusive`).

**How verified.** Injected a `confidence=-0.5` claim into the projected TriG and ran
the rdflib path (→ non-conforming, 1 violation); loaded the same logical row into a
`CozoStore` and ran `_evaluate_constraints` (→ `[]`, conforming). Opposite verdicts.

**Real vs synthetic.** **Synthetic-fixture-only.** `claim-record.schema.json:13`
pins `confidence` to `{minimum: 0.0, maximum: 1.0}` and `append_claim`→`validate_claim`
rejects `-0.5` and `1.5` at write time (verified directly). `project_ledger` can
therefore never emit an out-of-range confidence row, so real bermuda is unaffected
and both backends conform on it (verified end-to-end below). The divergence is
reachable only by bypassing the ledger writer.

**Recommended fix (calibrated against bermuda).** Add the second rule — author a
`confidence-range-low.edn` (`:filter [[< ?conf 0.0]]`) and add it to
`ACTIVE_CONSTRAINTS` in `validate_shacl.py:64` and to `CONSTRAINT_NAMES` in
`test_booklogic_constraint_compile.py` — OR explicitly scope REQ-KG-012 down and
record in the divergence note that the range constraint is `maxInclusive`-only
because the record contract owns the lower bound. Either is bermuda-safe (bermuda
has no out-of-range confidence). The cheap, honest fix is the second rule plus a
synthetic-fire test, so the EDN constraint set is not strictly weaker than the
SHACL it claims to replace. Do this before P5.3 flips the default.

---

### [IMPORTANT] I-1 — the parity proof is partly circular: the "characterization" golden was rewritten by the port it gates

**What's wrong.** REQ-KG-005/014 require the golden to freeze pre-port behaviour so
the port is gated by equivalence, not assertion. At C0.2 (`46790fe`)
`shacl_report_violating.json` held pyshacl's RAW output — full URIs and
auto-generated messages (`"Value is not <= Literal(\"1.0\", datatype=xsd:decimal)"`,
`"Less than 1 values on <...>->tbf:hasSourceSpan"`). P2.3 (`b1cfbc6`) **overwrote**
that golden with the canonical form (bare ids + the EDN-authored messages). So the
committed golden no longer characterizes pyshacl; it records the normalizer's
output.

The P2.3 parity test (`test_constraint_ports.py:128-135`) asserts
`rdflib(normalized) == golden`. But `rdflib_report.violations` is ALREADY normalized
inside `_validate_rdflib` (`validate_shacl.py:207`), and the golden was generated by
the same `capture_shacl`→`validate_shacl`→`_normalize_pyshacl_violations` path
(`capture_characterization.py:85`). Two of the three legs flow through the same
normalization code; the golden is not an independent oracle. The genuinely
cross-engine content is just `cozo == normalized-rdflib` for the four violations the
fixture injects.

**Evidence.** `git show 46790fe:.../shacl_report_violating.json` (raw form) vs the
current canonical golden; `validate_shacl.py:204-207` (rdflib path normalizes before
returning); `capture_characterization.py:85` (capture calls `validate_shacl`, i.e.
the normalized path).

**How verified.** Diffed the golden across the two commits; confirmed C0.2's
`validate_shacl.py` had no `_normalize_pyshacl_violations`/`_strip_focus_uri`
(grep count 0). Re-derived the normalized set in a probe and confirmed it equals the
committed golden.

**Real vs synthetic.** Synthetic-fixture-only (it is about the golden/test, not
production data). But it weakens the audit trail the whole migration leans on.

**Recommended fix.** Keep BOTH goldens: a raw-pyshacl `shacl_report_violating_raw.json`
(the true C0 characterization, never edited) plus the canonical
`shacl_report_violating.json` (the reconciled P2.3 oracle). Assert the Cozo path
against the canonical one and assert that the raw→canonical mapping is exactly
`_normalize_pyshacl_violations` applied to the raw golden — that makes the
normalizer itself the audited artifact instead of an unstated identity. This is the
REQ-KG-017 "record the divergence + keep the pre-port golden" discipline the query
ports are supposed to follow.

---

### [IMPORTANT] I-2 — the path-keyed message remap mislabels and silently collapses distinct pyshacl violations

**What's wrong.** `_normalize_pyshacl_violations` remaps a violation's message to the
authored EDN message keyed ONLY on `path` (`validate_shacl.py:150`,
`canonical.get(v.path, v.message)`). pyshacl can emit several semantically distinct
violations sharing one `sh:path`. A claim whose `confidence` is a non-numeric string
fires three pyshacl violations on `tbf:confidence`: `sh:maxInclusive`,
`sh:minInclusive`, and `sh:datatype`. After normalization all three become the
identical tuple `(focus, "#confidence", "Claim confidence must be <= 1.0.")` — a
message that is factually wrong for the datatype and lower-bound violations — and the
result-SET dedupes them to ONE. A real datatype error is thus relabelled as a
range error and two of three violations vanish.

Corollary: any pyshacl violation on a path NOT in the six-constraint map keeps
pyshacl's raw message while the Cozo path (which only emits the six authored
messages) would never produce it — a silent message/identity mismatch. The map
currently covers exactly the six constraint paths, so this is latent, not active,
but it is one new SHACL property constraint away from biting.

**Evidence.** `validate_shacl.py:139-154` (`_normalize_pyshacl_violations`, keyed on
`v.path`); `_build_canonical_messages:106-136` (one message per path).

**How verified.** Injected `confidence="not-a-number"` (xsd:string) into the TriG;
raw pyshacl returned three distinct `#confidence` violations; after normalization all
three printed the same "must be <= 1.0" message. The Cozo path on the same logical
row **raised `QueryException`** (the typed Float column rejects a string at load),
i.e. it neither conforms nor reports — a third divergence mode (crash vs violation).

**Real vs synthetic.** Synthetic-fixture-only — `claim-record.schema.json:13` makes
`confidence` a `number` in `[0,1]`, so wrong-datatype/out-of-range confidence cannot
reach the ledger; real bermuda conforms on both engines. But the mislabel is a real
representation bug the divergence note does not acknowledge (the note claims the
remap is safe because callers read only `conforms`/`len(violations)` — true for the
current callers, but the note presents the canonical messages as faithful, and they
are not under datatype/lower-bound failures).

**Recommended fix.** Key the remap on `(path, shacl_source_constraint)` (pyshacl
exposes `sh:sourceConstraintComponent` on each result) instead of `path` alone, so
minInclusive/maxInclusive/datatype map to distinct messages; or drop the message
remap entirely and compare engines on `(focus_node, path)` only, documenting that
message text is engine-specific and not part of the parity contract. The second is
simpler and bermuda-safe (bermuda has zero violations, so no message is ever
compared on real data).

---

### [IMPORTANT] I-3 — REQ-KG-012's 6th constraint (`chapter-cites-verified`) has no production data path

**What's wrong.** `project_ledger` loads `chapter-section` EMPTY
(`project_ledger_cozo.py:337`), exactly like `chapter-wiki-ref` and
`rebuttal-window-ok`. There is no projector that sources chapter-section/usesClaim
rows from a workspace. So `chapter-cites-verified` (REQ-KG-012's 6th constraint) can
only ever fire on rows hand-loaded in the test (`test_constraint_ports.py:101-103`,
`_load_violating_rows`). The constraint compiles, executes, and is "active," but it
is wired to nothing — a reader scanning the `_DEFERRED.md` "Active constraints (6)"
table or the spec would reasonably believe chapter-citation validation is live.

**Evidence.** `project_ledger_cozo.py:331-337` (loaded empty, with comment);
`assets/kg-constraints/chapter-cites-verified.edn:23-28` ("no production projector
emits chapter-section rows yet"); `_DEFERRED.md` "No production data source (still
future work)."

**How verified.** Read the projector; confirmed `store.load("chapter-section", [])`.
The bermuda run produced 0 violations through this constraint because there are no
rows. The committed parity covers it only via synthetic loaded rows.

**Real vs synthetic.** Affects the **claim** of coverage, not real data behaviour:
on real bermuda the constraint is a guaranteed no-op. Honestly disclosed in the EDN
and `_DEFERRED.md`, so this is "partial," not "false." Still, REQ-KG-012's scenario
says "chapter sections must cite only verified claims ... result-set equal ... on the
bermuda workspace," and that end-to-end path does not exist.

**Recommended fix.** Mark REQ-KG-012 as PARTIAL in the spec-coverage tracking until
P5 (or a dedicated task) adds a real `chapter-section` projector, and add a test that
asserts the constraint fires on a workspace whose chapters genuinely cite a
non-verified claim — sourced through the projector, not `store.load`. Until then do
not advertise it as a wired gate. Bermuda-safe: bermuda's chapters cite nothing
through this relation today.

---

### [MINOR] M-1 — `text-cardinality` and `status-enum` are vacuously ported (never fire in any committed fixture)

**What's wrong.** Neither the C0.1 violating fixture nor the synthetic
`_load_violating_rows` injects an out-of-enum status or a missing canonical-text, so
`status-enum` and `text-cardinality` never appear in the violating golden (4
violations, none from these two). REQ-KG-014's non-vacuity guard fires for the SHACL
report as a whole, but 2 of 6 constraints are individually unexercised by the parity
oracle.

**How verified.** Built a fixture injecting a `frobnicated` status and a text-less
claim; ran BOTH engines. **They agree exactly** — both produce the canonical
`#status` and `schema.org/text` violations with identical authored messages. So the
ports are CORRECT; they are merely untested by the committed goldens. (This is why
this is MINOR, not CRITICAL: probing showed no bug, only a coverage gap.)

**Real vs synthetic.** Synthetic — like all five claim-shape constraints, these
cannot fire on real ledger data (see "what's genuinely solid → the gate is a no-op on
real data").

**Recommended fix.** Add the two missing injections to `_load_violating_rows` (a
status `"frobnicated"` row and a `canonical-text: None` row) and extend the violating
golden, so all six constraints are exercised by the non-vacuity oracle. Bermuda-safe.

---

### [MINOR] M-2 — `test_callers_import_unchanged` does not import the callers it is named for

**What's wrong.** REQ-KG-013's scenario says this test "asserts the three book-compose
callers import and call it with no signature change." The body
(`test_validate_shacl.py:75-83`) only checks that `validate_shacl` is callable and the
two dataclasses have the expected fields — it never imports `preflight.py`,
`book_preflight.py`, or `build_release_bundle.py`. The test name and the spec promise
a cross-skill smoke the body does not perform; it gives false assurance.

**How verified.** Read the test; separately grepped the three callers — they DO exist
and DO call `validate_shacl_mod.validate_shacl(layout)` consuming `.conforms`
(`preflight.py:36`, `book_preflight.py:73`, `build_release_bundle.py:36`). So the
contract is in fact preserved; only the test is hollow.

**Real vs synthetic.** Test-only. The contract holds in practice.

**Recommended fix.** Import the three modules via `sibling_skills.load_book_knowledge_module`
(or the book-compose import shim) and assert they reference `validate_shacl` and read
`.conforms`, matching the scenario. Bermuda-safe.

---

### [MINOR] M-3 — `_validate_cozo` / `_validate_rdflib` derive `conforms` from different sources

**What's wrong.** The Cozo path sets `conforms = not violations`
(`validate_shacl.py:265`), i.e. conformance is derived from the (normalized,
post-filter) violation list. The rdflib path returns pyshacl's OWN `conforms` flag
(`validate_shacl.py:212`), independent of the normalized list. These can in principle
disagree: if pyshacl reports `conforms=False` but every violation it found sits on a
path the remap drops or on a focus the strip mishandles, the rdflib report could carry
`conforms=False` with a `violations` list that, after Cozo-side filtering, the Cozo
path would call conforming. Not observed in practice (the six paths line up), but the
two paths do not compute `conforms` the same way, which is a latent inconsistency the
divergence note does not flag.

**Evidence.** `validate_shacl.py:212` (`conforms=conforms` from pyshacl) vs `:265`
(`conforms = not violations`).

**How verified.** Code read; on bermuda both are `True`, on the 4-violation fixture
both are `False`, so no live mismatch — but the derivation differs.

**Real vs synthetic.** Synthetic/latent. Real bermuda conforms on both.

**Recommended fix.** Derive `conforms = not violations` on BOTH paths (after
normalization) so the verdict is a pure function of the canonical violation set the
contract exposes; or assert `pyshacl_conforms == (not normalized_violations)` in the
rdflib path and raise if they disagree (a normalization-correctness guard).

---

### [MINOR] M-4 — `capture_consistency` is documented as side-effect-free but `run()` writes to the workspace

**What's wrong.** `capture_consistency.py:5-8` says it "changes no production
behaviour -- it only calls `run` and serializes." But `datalog_consistency.run`
writes `qa/datalog-defects.json` into the target workspace
(`datalog_consistency.py` tail, `out.write_text(...)`). Re-capturing the bermuda
golden therefore mutates a tracked file under `examples/bermuda-manual/qa/`.

**How verified.** Ran `capture_consistency ../../examples/bermuda-manual ...`; it
dirtied `examples/bermuda-manual/qa/datalog-defects.json` (restored via `git checkout`).
Also note `run(bermuda)` first raises `FileNotFoundError` because the bermuda
`.knowledge/thesis-triples.ttl` is gitignored/untracked — the golden is only
regenerable after `compile_thesis` runs.

**Real vs synthetic.** Touches real bermuda `qa/` if anyone re-captures. Output is the
same `run` always writes, so it is not corruption — but the "read-only" claim is wrong
and the regeneration step (compile-thesis-first) is undocumented.

**Recommended fix.** Either pass a writable temp `qa/` to the capture, or correct the
docstring to state that capture runs the full consistency pass (which writes
`qa/datalog-defects.json`) and that the bermuda golden is regenerated by
`compile_thesis(bermuda) && capture_consistency`. Bermuda-safe.

---

### [MINOR] M-5 — `status-enum` rule emits a redundant `!is_null(status)` per filter clause

**What's wrong.** The compiler emits one `!is_null(<var>)` guard per `:filter` clause
even when clauses reuse the same variable. `status-enum.cozoscript` carries
`!is_null(status)` five times (once before each `!=`). Harmless (idempotent) and
deterministic, but bloats the rule and the byte-golden, and could matter if a future
constraint has many filters.

**Evidence.** `tests/golden/kg-constraints/status-enum.cozoscript` (five
`!is_null(status)`); `booklogic_kg.py:304` emits the guard inside the per-clause loop.

**Real vs synthetic.** Output-shape only; no behavioural effect.

**Recommended fix.** Dedupe guards per variable across a constraint's filter block
(emit `!is_null(v)` once per distinct operand). Regenerate the affected goldens.
Bermuda-safe.

---

## Spec coverage — REQ-KG-001..014 (C0 + P2 scope)

REQ-KG-001..008/011 are P0/P1 surface (queries/seam/projector), out of this PR's
substantive scope; listed for completeness from the committed tests.

| REQ | Topic | C0+P2 status | Note |
|---|---|---|---|
| REQ-KG-001 | Unified EDN schema | satisfied (pre-existing) | `chapter-section` entity added P2.3 (`kg-schema.edn:179`) |
| REQ-KG-002 / 002b | Cozo seam / no pycozo bypass | satisfied | `validate_shacl`/`booklogic_kg` never import pycozo (verified) |
| REQ-KG-003 | Pure EDN→CozoScript compiler | **satisfied** | pure, deterministic across runs + 3 hash seeds; undeclared-entity error path tested |
| REQ-KG-004 | Ledger→Cozo projection | satisfied (pre-existing) | — |
| REQ-KG-005 | Characterization fixtures precede port | **partial** | see I-1: the SHACL violating golden was rewritten by P2.3, so it no longer freezes pre-port pyshacl output |
| REQ-KG-006 | 8 SPARQL queries reproduced | out of scope here | P1 |
| REQ-KG-007 | Backend swappable | satisfied (pre-existing) | — |
| REQ-KG-008 | Deterministic load+query | **satisfied** | compiler + both goldens reproduce byte-identically; canonical sort neutralizes Cozo/pyDatalog row order |
| REQ-KG-009 / 009b | Status enum single source | **satisfied** | `claim_validator` derives from `status-enum.edn`; no second Python copy; JSON-schema copy drift-guarded as a set |
| REQ-KG-011 | Store relations conform to schema | satisfied (pre-existing) | — |
| REQ-KG-012 | SHACL shapes reproduced via EDN | **partial** | 4/6 constraints proven equivalent on the firing fixture; `status-enum`+`text-cardinality` correct but unexercised (M-1); `confidence` lower-bound NOT ported (C-1); `chapter-cites-verified` has no data path (I-3) |
| REQ-KG-013 | `validate_shacl` contract preserved | **partial** | shape preserved and callers do consume it unchanged; but non-conforming cross-engine `conforms` parity is only tested via synthetic loaded rows, not end-to-end (and M-2's caller test is hollow, M-3's verdict derivation differs) |
| REQ-KG-014 | Violating goldens precede + non-empty | **satisfied** | SHACL violating golden = 4; D9–D11 violating golden = 6 (≥1 each class + invariant_violation), reproducible and deterministic |
| REQ-KG-020 | Transition matrix from single source | **satisfied** | matrix derived; out-of-source status rejected (`ClaimVocabularyError`); old matrix preserved exactly |

---

## What's genuinely solid (credit where due)

- **The pure compiler (P2.2).** `compile_constraint` is genuinely pure (schema file
  only, no store) and deterministic — byte-identical output across 5 runs and
  PYTHONHASHSEED ∈ {default, 0, 12345}. The free-var minCount → `!is_null`-guarded
  helper-rule lowering is correct and the dedup test (`present_0[focus]`, not
  `[focus, focus]`) guards a real footgun. Schema attrs are read into a set but only
  for membership, so no nondeterminism leaks into emission.
- **The status single-source (P2.1).** `VALID_TRANSITIONS` is derived from
  `status-enum.edn` and byte-for-byte preserves the old literal matrix (verified
  against `796f131`). `_load_status_enum_text` actively rejects a transition naming an
  out-of-`:states` status. The JSON-schema enum is drift-guarded against the EDN as a
  set. This genuinely removes the documented off-by-one footgun for the Python copies
  (shapes.ttl `sh:in` remains, but its removal is correctly deferred to P5).
- **The D9–D11 characterization (C0.3).** The violating golden is non-vacuous and
  meaningful: it exercises the recursive D10 transitive-contradiction rule (the
  flagged P3 risk), and the canonical `(class, rule, json.dumps(facts))` sort makes it
  deterministic across 3 runs (verified). The non-vacuity test asserts ≥1 of each
  class plus an invariant_violation. The bermuda baseline re-captures byte-identically.
- **Determinism and LF discipline.** Goldens are written `indent=2, sort_keys=True,
  newline="\n"`; `.gitattributes` pins `eol=lf`; the compile goldens read back
  through universal-newline translation, so even a CRLF checkout would match. No
  determinism bug found anywhere I probed.
- **The honest no-op disclosure.** The team correctly documents (in the EDN comments,
  `_DEFERRED.md`, the divergence note, and `project_ledger_cozo.py`) that the
  chapter-section relation is empty and that several relations have no production
  source. The migration does NOT worsen the pre-existing property that the SHACL gate
  is vacuous on real data — see below.

### The SHACL gate is a no-op on real data — pre-existing, faithfully preserved

`claim-record.schema.json` is strictly stronger than every claim-shape SHACL
constraint: `confidence` ∈ `[0,1]` (number), `status` ∈ the 5-value enum (so an
out-of-enum status is impossible), `canonical_text` required `minLength 4` (so
text-cardinality can't fire), and `source_spans` required with `minItems 1` (so
`source-span-present` and `verified-derives` can't fire). Therefore `validate_shacl`
on ANY workspace whose claims came through `append_claim` always conforms. Verified
end-to-end: on real `examples/bermuda-manual`, both `KG_BACKEND=rdflib` and
`KG_BACKEND=cozo` return `conforms=True, 0 violations`. This was already true of the
pyshacl path (the constraints only ever fire on synthetic injected RDF/rows), so the
migration does not introduce the no-op — it preserves it exactly. The practical
consequence: the entire C0/P2 SHACL parity story rests on synthetic fixtures, which
is acceptable AS LONG AS the synthetic fixtures actually exercise the constraints
(they exercise 4 of 6 — see M-1) and the divergences in C-1/I-2 are reconciled before
the rdflib safety net is removed in P5.

---

## Bottom line for P3

Build P3 on this — the compiler, the projector seam, the status source, and the
D9–D11 golden are trustworthy. Before P5.3 flips the default and P5.4 deletes the
rdflib net, close C-1 (confidence lower bound) and I-2 (message remap), and downgrade
the REQ-KG-012/013 claims to PARTIAL in the change tracking until the
`chapter-section` projector (I-3) exists. None of these block P3, and none affect real
bermuda data.

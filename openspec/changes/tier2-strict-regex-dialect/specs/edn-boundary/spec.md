# Capability delta: edn-boundary — change: tier2-strict-regex-dialect

## ADD

### REQ-INGEST-050 — Ubiquitous

The framework SHALL accept only Python-dialect regex (`re` module) in
the `:patterns` vector of any `defpredicate` lift form: every pattern
SHALL compile via `re.compile(pat)` without any silent dialect rewrite
performed by the ingester.

**Rationale:** A silent rewrite of JS-form `(?<v>)` to Python-form
`(?P<v>)` masks a class of cross-language drift between the CLJS
compiler (which uses JS `RegExp`) and the Python ingester. Removing
the rewrite makes the regex dialect contract explicit at the input
boundary.
**Tested by:** `verifiers/osmotic_pressure/scripts/tests/test_strict_regex_dialect.py::test_python_named_group_compiles_unchanged` (added in E1.1.4)

### REQ-INGEST-051 — Unwanted behaviour

IF a `:patterns` entry contains a JS-style named group of the form
`(?<NAME>...)` where `NAME` matches `[A-Za-z_][A-Za-z0-9_]*`, THEN
the ingester SHALL raise an `EdnReadError`-shaped exception at the
moment the pattern is first consumed, with a message that:
1. quotes the offending pattern,
2. names the JS vs. Python dialect distinction, and
3. links to `references/grounded-atoms.md` § "Regex dialect".

**Rationale:** Surfaces the exact authoring error in the exact authoring
file. The original silent converter rewrote the pattern under the
ingester's feet and left no trace; the strict gate makes the dialect
rule discoverable through its own failure.
**Tested by:** `test_strict_regex_dialect.py::test_js_named_group_raises_with_dialect_message` (added in E1.1.1)

### REQ-INGEST-052 — Ubiquitous

The existing OPAQUE-fraction gate (REQ-INGEST-041) SHALL continue to
fire on the orthogonal failure mode: a regex that is syntactically
Python-dialect-valid but matches none of the input claims. The
introduction of the strict-dialect gate (REQ-INGEST-050, REQ-INGEST-051)
SHALL NOT alter the OPAQUE-fraction code path or its threshold semantics.

**Rationale:** The two gates are complementary: REQ-INGEST-051 catches
input-shape errors at the boundary; REQ-INGEST-041 catches semantic
mismatch between regex and claim text. Both must survive this change.
**Tested by:** `test_strict_regex_dialect.py::test_opaque_gate_still_fires_on_non_matching_regex` (added in E1.2.1)

### REQ-INGEST-053 — Ubiquitous

The bug7 regression test (formerly
`test_bug7_regex_break_caught_by_extract_gate`, the surrogate cited in
REQ-INGEST-048) SHALL be renamed to
`test_bug7_js_named_group_caught_by_dialect_gate` and SHALL mutate a
baked project's `rules/booklogic/lifts.edn` to introduce the genuine
JS-style `(?<v>...)` named-group mutation that triggered the sprint-5
incident; the test SHALL assert that `make ci` fails at the dialect
gate (REQ-INGEST-051) before reaching `make extract`.

**Rationale:** Completes the regression path REQ-INGEST-048 prose
described but its surrogate test could not cover. The genuine
mutation is now a hard error, so the regression can finally exercise
the real bug shape.
**Tested by:** `skills/neurosym-forge/tests/regression/test_sprint5_bug_catches.py::test_bug7_js_named_group_caught_by_dialect_gate` (added in E1.3.2; supersedes the surrogate added under REQ-INGEST-048)

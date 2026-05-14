# neurosym-forge — operator runbook

This runbook walks an operator through the full neurosym-forge cycle:
scaffold a verifier project, wire it to a book workspace, extend it
with new sorts and rules, run it end-to-end, and feed its verdict into
`book-qa` as defect class D13. The worked example is the Bermuda
verifier at `verifiers/bermuda/`.

Conceptual overview lives in `docs/concepts/neurosym-forge.md`. Read it
first if you have not already. The same recipe scaffolds a non-book
verifier (chemistry, legal, math) with one flag toggled; the worked
example at `skills/neurosym-forge/references/worked-examples/osmotic-pressure/README.md`
walks through the chemistry case end to end.

---

## Prerequisites

You will need Python 3.13 with `pip` and `venv` on the path, plus a
working venv at `skills/neurosym-forge/.venv/`. For live verification
you also need Cargo 1.85+ and Node.js 22+; the stub path
(`--stub --stub-verdict sat`) needs neither.

To prepare the skill venv, from the skill root:

```
cd skills/neurosym-forge
python -m venv .venv
.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

The repo's CLAUDE.md notes that skill venvs are junction-linked to the
installed-skill venvs under `~/.claude/skills/<name>/.venv/`. If the
local `.venv/` is missing, either rebuild it as above or junction-link
to the installed copy.

Confirm the helpers run:

```
.venv\Scripts\python.exe -m scripts.scaffold_project --help
```

Expected: a usage line listing `--out`, `--slug`, `--book-knowledge-bridge`.

---

## Scaffold a project

`scaffold_project.py` writes the full CLJS+Rust skeleton plus a
project-local `SKILL.md` so the resulting verifier is itself a Claude
Code skill. Run from the skill root.

For a book-workspace verifier (the Bermuda pattern):

```
.venv\Scripts\python.exe -m scripts.scaffold_project \
  --name "Bermuda Verifier" \
  --slug bermuda \
  --out ../../verifiers/bermuda \
  --book-knowledge-bridge
```

For a non-book verifier (chemistry, legal, math), drop the bridge
flag:

```
.venv\Scripts\python.exe -m scripts.scaffold_project \
  --name "Osmotic Pressure Verifier" \
  --slug osmotic_pressure \
  --out ../../verifiers/osmotic_pressure
```

`--name` is the human-readable project name (used in the generated
`SKILL.md` and `README.md`); `--slug` is the snake_case identifier
used in paths and namespaces. The `--book-knowledge-bridge` flag adds
`scripts/ingest_ledger.py`. Without it, the operator writes the
Phase-1 input themselves; the rest of the pipeline runs unchanged.

After scaffold, the output tree contains:

```
verifiers/<slug>/
├── SKILL.md
├── README.md
├── deps.edn
├── package.json
├── shadow-cljs.edn
├── cljs-orchestrator/src/main/<slug>/
│   ├── core.cljs
│   ├── phases.cljs
│   ├── ir.cljs
│   ├── nl_to_fol.cljs
│   ├── unify.cljs
│   └── bridge.cljs
├── rust-verifier/
│   ├── Cargo.toml
│   ├── build.rs
│   └── src/
│       ├── lib.rs
│       ├── axioms.rs      ← v0.3 no-op hook; override per project
│       ├── ir.rs
│       ├── smt.rs
│       ├── eqsat.rs
│       ├── kg.rs
│       └── typeset.rs     ← feature-gated under `pdf`
├── rules/
│   ├── seed.edn
│   ├── grounded.edn
│   ├── predicates.edn     ← populated by the operator
│   ├── .forge-version.edn
│   └── .checksums.edn
├── templates/
│   ├── report.tex.tera
│   └── claim_table.tex.tera
└── scripts/
    └── ingest_ledger.py    ← only with --book-knowledge-bridge
```

The scaffold ships exactly one Python driver — `ingest_ledger.py`,
emitted only in bridge mode. Every other workspace driver
(`extract_prose.py`, `verdict_to_qa.py`, `run_verification.py`) lives
per project; an operator copies them from the Bermuda verifier at
`verifiers/bermuda/scripts/` and adapts each to the new domain.

The `axioms.rs` file ships as a no-op stub. Domain-specific verifiers
replace its body; the scaffold contract requires that
`smt.rs::check_all` call `crate::axioms::assert_axioms(&ctx, &solver)`
before the per-atom walk. See the concepts doc for the rationale.

About the `--out` policy (v0.3): the scaffolder accepts relative paths
with `..` segments when the resolved path stays under the current
working directory. Absolute paths pass unconditionally. A relative path
that escapes the cwd fails with a useful error.

---

## Ingest a ledger

For book-workspace verifiers, `scripts/ingest_ledger.py` reads the
workspace claim ledger and emits `work/claims.edn`. Predicate patterns
in `rules/predicates.edn` decide which claims become Z3-tracked atoms
and which stay as provenance-only `:CONTEXT` or `:OPAQUE` records.

From the scaffolded project root:

```
cd verifiers/bermuda
.venv\Scripts\python.exe -m scripts.ingest_ledger \
  --ledger ../../examples/bermuda-manual/claims/ledger.jsonl \
  --predicates rules/predicates.edn \
  --out work/claims.edn
```

Expected output: a count of tracked vs context atoms and the path to
the EDN file.

The predicate-map file is JSON-shaped EDN. From Bermuda's
`rules/predicates.edn`:

```json
{
  "version": 1,
  "predicates": {
    "parishes": {
      "patterns": ["(?P<n>\\d+|nine|eight)\\s+parishes"],
      "predicate": ":parishes-count",
      "subject": ":Bermuda",
      "value_kind": "int",
      "word_to_int": {"nine": 9, "eight": 8}
    },
    "currency_peg": {
      "patterns": ["Bermudian\\s+dollar.*pegged.*US\\s+dollar"],
      "predicate": ":currency-pegged-at-parity",
      "subject": ":BMD",
      "value_kind": "bool",
      "value": true
    }
  }
}
```

Each pattern is a regex over the claim's `canonical_text` field. The
named capture group `n` (or a positional group) carries the raw
value; `value_kind` decides the coercion (`int`, `bool`, `string`,
`entity`). For `int` predicates with word forms, `word_to_int` maps
spelled-out numbers to digits. Claims that do not match any pattern
fall to `:CONTEXT` and never participate in Z3 assertions. Claims
marked `:status :OPAQUE` skip ingestion.

---

## Extract prose

Chapter prose carries assertions that the ledger does not. The
ch-02 line "Bermuda counts eight parishes along its arc" contradicts
the canonical nine; the verifier needs the prose claim, not just the
ledger claim, to flag the drift.

`scripts/extract_prose.py` walks the chapter bundles and runs the same
predicate patterns over the prose text. From the project root:

```
.venv\Scripts\python.exe -m scripts.extract_prose \
  --bundles ../../examples/bermuda-manual/book/releases/6.0.0/chapter-bundles \
  --out work/prose-facts.edn
```

The script does two passes. Pass A is regex-only and runs always.
Pass B is an optional LLM disambiguator that turns ambiguous prose
into a structured value; it runs only when the caller passes an
`llm_call` callable into `extract_prose.run`. The CLI form skips
Pass B by default. Pass A alone catches the Bermuda parish-count
drift.

Output: `work/prose-facts.edn` with one atom per matched prose span,
each atom carrying a `:source` field pointing at the chapter file and
line range.

---

## Add a sort, rule, or grounded atom

Three helpers extend the verifier without touching `rules/*.edn` by
hand. All three live in the *skill* (not the scaffolded project) and
write into the project at `--project <path>`.

### Add a sort

Sorts are the type vocabulary. The seed set is `:int`, `:real`,
`:bool`, plus the domain sorts you need. Add a new one:

```
cd skills/neurosym-forge
.venv\Scripts\python.exe -m scripts.add_sort \
  --project ../../verifiers/bermuda \
  --sort :parish
```

The `--sort` argument accepts either a bare keyword literal
(`:parish`) for a primitive sort or a JSON object for function and
enum sorts:

```
.venv\Scripts\python.exe -m scripts.add_sort \
  --project ../../verifiers/bermuda \
  --sort '{"kind":"enum","members":[":sat",":unsat",":unknown"]}'
```

The helper validates the sort, appends it to the `:sorts` vector in
`rules/seed.edn`, and refreshes the checksum.

### Add a rewrite rule

Rules are the `(= lhs rhs)` records. Each one carries an ID
(`R<NNN>`), a doc string, and a set of tags. The helper reads the
rule body from a JSON file; write the body first:

```json
{
  "id": "R042",
  "lhs": {"kind": "expression", "sort": ":bool",
          "head": {"kind": "symbol", "name": ":currency-peg",
                   "sort": {"kind": "fn", "args": [":entity"], "ret": ":bool"}},
          "args": [{"kind": "variable", "name": "?c", "sort": ":entity"}]},
  "rhs": {"kind": "expression", "sort": ":bool",
          "head": {"kind": "symbol", "name": ":pegged-to-usd",
                   "sort": {"kind": "fn", "args": [":entity"], "ret": ":bool"}},
          "args": [{"kind": "variable", "name": "?c", "sort": ":entity"}]},
  "doc": "currency-peg unfolds to pegged-to-usd",
  "tags": ["algebraic", "domain-bermuda"]
}
```

Then append it:

```
.venv\Scripts\python.exe -m scripts.add_rewrite_rule \
  --project ../../verifiers/bermuda \
  --rule-file R042.json
```

The helper checks variable balance (every free `?v` on `:rhs` also
occurs on `:lhs` unless the rule carries the `:eliminating` tag),
validates the sorts against the registry, appends the rule to
`rules/seed.edn`, refreshes the checksum, and writes a fixture stub
at `tests/rules/test_R042.cljs` in the scaffolded project. The
fixture is a stub the operator fills in to assert the rewrite
produces the expected term.

`lint_rewrite_coverage.py` flags any rule without a fixture test.

### Add a grounded atom

Grounded atoms expose Rust functions to CLJS. Adding one:

```
.venv\Scripts\python.exe -m scripts.add_grounded_atom \
  --project ../../verifiers/osmotic_pressure \
  --slug osmotic_pressure \
  --name :gas-constant \
  --lib z3 \
  --fn gas_constant \
  --sort '{"kind":"fn","args":[],"ret":":real"}' \
  --doc "ideal-gas constant R = 8.314 J/(mol*K)"
```

The helper appends a `#[napi]` stub to
`rust-verifier/src/<lib>.rs` with `todo!()` as the body, wires
`mod <lib>;` into `lib.rs` if absent, appends a CLJS bridge shim to
`cljs-orchestrator/src/main/<slug>/bridge.cljs`, appends a grounded
record to `rules/grounded.edn`, and refreshes the checksum.

Then edit the Rust stub to replace `todo!()` with the real backend
call. Run `cargo build --release` to compile (or
`cargo build --release --no-default-features --features smt,kg` to
skip tectonic and its libpng requirement). The CLJS side picks the
new function up the next time `shadow-cljs` reloads.

When in doubt about the rule conventions, read
`skills/neurosym-forge/references/rewrite-rule-style.md`. When in
doubt about the grounded-atom contract, read
`skills/neurosym-forge/references/grounded-atoms.md`.

---

## Wire D13 into book-qa

The verifier writes its findings into the workspace as
`qa/verification-defects.json`. `book-qa.lint_artifact` reads this
file when the workspace `qa-config.yaml` opts in:

```yaml
enable_verification: true
```

The translation happens via `scripts/verdict_to_qa.py` in the
scaffolded project. The `run_verification.py` driver invokes it after
the CLJS+Rust pipeline produces `work/verdict.edn`; you do not
ordinarily call it by hand. A `:sat` verdict produces an empty defects
file; a `:unsat` verdict produces one critical ticket per claim ID in
the unsat core, each ticket carrying the atom's source span.

To verify the wiring without a real run:

```
cd verifiers/bermuda
.venv\Scripts\python.exe -m scripts.run_verification \
  --workspace ../../examples/bermuda-manual \
  --release 6.0.0 \
  --stub --stub-verdict unsat
```

This writes a synthetic `qa/verification-defects.json` with one
ticket. Then run book-qa:

```
cd ../../skills/book-qa
python -m scripts.lint_artifact ../../examples/bermuda-manual 6.0.0
```

Expected: one D13 critical ticket in `qa/lint-report.json`.

With `enable_verification: false` (the default), book-qa ignores
the verification file entirely. A verifier can run and write defects
without gating the build; toggling the flag is the single switch that
turns the gate on.

---

## Run end-to-end against Bermuda

The Bermuda verifier is the reference workspace integration. Two
paths: stubbed (no Rust toolchain needed) and real (full Z3 walk).

### Stubbed path

```
cd verifiers/bermuda
.venv\Scripts\python.exe -m scripts.run_verification \
  --workspace ../../examples/bermuda-manual \
  --release 6.0.0 \
  --stub --stub-verdict sat
```

Output: `work/verdict.edn` carrying `{:verdict :sat}` and an empty
`qa/verification-defects.json` in the workspace. Use this to exercise
the file-flow without paying for a Z3 build.

### Real path

Build the Rust addon, skipping tectonic so the build needs no libpng:

```
cd verifiers/bermuda/rust-verifier
cargo build --release --no-default-features --features smt,kg
```

Build the CLJS orchestrator:

```
cd ..
npm install
npm run build:cljs
```

Run the full pipeline:

```
.venv\Scripts\python.exe -m scripts.run_verification \
  --workspace ../../examples/bermuda-manual \
  --release 6.0.0
```

Expected outcome on a manuscript carrying the ch-02 "eight parishes"
drift: `:unsat` with either `prose-ch-02-NNN` or `clm-2026-000008` in
the unsat core. The verdict translates into one D13 critical ticket
in `qa/verification-defects.json`. Run book-qa over the workspace and
the ticket lands in `qa/lint-report.json`.

Expected outcome on a clean manuscript: `:sat`, an empty defects
file, no D13 tickets.

The Bermuda `axioms.rs` is a thin re-export shim:

```rust
pub use crate::canonical::assert_bermuda_axioms as assert_axioms;
```

The Bermuda-specific Z3 axioms live in `canonical.rs`. This is the
documented pattern for letting a domain-meaningful module name
persist while still satisfying the v0.3 hook contract.

---

## Troubleshoot

### tectonic build failure (libpng / pkg-config)

The default Cargo features include `pdf`, which pulls in `tectonic`,
which links against `libpng` via `pkg-config`. On Windows and many
Linux dev machines this fails. Two options:

```
cargo build --release --no-default-features --features smt,kg
```

The `kg` feature carries cozo (Datalog); `smt` carries z3. The `pdf`
feature is optional and supports only `render_pdf`, which the verify
path never calls.

If you want PDF rendering for the final report, install libpng and
`pkg-config` on the host and then `cargo build --release --features pdf`.

### `--out` rejected with "..  outside cwd"

The v0.3 `--out` policy accepts relative paths with `..` segments as
long as the resolved path stays under the current working directory.
A relative path that escapes the cwd fails with this message. Two
options:

- Run the scaffolder from a higher directory so the target stays
  under the cwd.
- Pass an absolute path. The policy accepts any absolute path; the
  operator is opting in by being explicit.

### Manual edit to `rules/*.edn` flagged

`lint_rewrite_coverage.py` reads the checksums in `rules/.checksums.edn`
and compares against the file content on disk. A mismatch means
someone (the operator, an agent, a merge conflict) edited the file
without going through an `add_*.py` helper.

Recovery: undo the manual edit, then re-apply the change through the
helper. If the manual edit is correct and the helpers do not yet
support the shape, the workaround is to remove the file's entry from
`rules/.checksums.edn` and let the next helper-mediated write
regenerate it. Doing so disables drift detection for that file until
the next helper run.

### `:unknown` verdict from Z3

The solver timed out. The driver writes the verdict regardless;
`book-qa` does not gate the build on `:unknown` (only `:unsat` fires
D13). To investigate, bump `:smt-timeout-ms` in `work/config.edn` and
re-run; if the timeout still fires, the cause is one of three
shapes that defeat the solver — a rewrite rule with no termination
condition, a quantifier pattern that explodes the search space, or a
missing axiom that lets the model wander far from the intended
domain.

### z3.rs bundled build fails

`z3 = { version = "0.20", features = ["bundled"] }` requires CMake and
a working C++ toolchain. On a fresh Windows install, the missing
piece is Visual Studio Build Tools. On Linux it is `build-essential`
plus `cmake`. If you cannot install the toolchain locally, the
fallback is to run the build inside the project's GitHub Actions
workflow on `ubuntu-latest` and pull the verdict artefact back down.

---

## Acceptance recap

A scaffolded project is operator-ready when:

- `scripts/scaffold_project.py` produces a tree that builds end-to-end
  (Python, Rust under `--no-default-features --features smt,kg`, and
  CLJS).
- The project's `axioms.rs` either ships the v0.3 no-op stub or
  installs domain axioms (the Bermuda re-export pattern).
- `lint_atomspace.py` and `lint_rewrite_coverage.py` both return zero
  findings on the populated `rules/*.edn`.
- The workspace's `qa-config.yaml` opts into verification, and
  `run_verification.py --stub` produces the expected
  `qa/verification-defects.json`.
- A real run against a known-bad manuscript produces `:unsat` with the
  drift atom in the unsat core.

When all five hold, the verifier sits inside the workspace and the
build gates on its findings.

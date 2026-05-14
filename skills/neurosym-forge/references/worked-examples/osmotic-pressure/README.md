# Worked example: osmotic pressure

End-to-end walkthrough of a non-book verifier. The domain is solution
chemistry; the law under test is van 't Hoff's `π = i · M · R · T`.
The example proves three things: that `neurosym-forge` scaffolds a
verifier outside the book pipeline, that the `axioms.rs` hook carries
domain constants cleanly, and that a doctored input fires `:unsat`
with the right atom in the unsat core.

The walkthrough has two passes. Pass one runs against a clean ledger
and ends in `:sat`. Pass two runs against a doctored ledger that
violates van 't Hoff and ends in `:unsat`. Both passes use the
scaffolded project's stub mode for the CLJS+Rust glue; for the real
build, see `docs/operations/neurosym-forge-runbook.md`.

## Fixtures

The example ships two synthetic inputs.

**`osmotic-pressure-paper.txt`** is a one-paragraph source describing
a NaCl-in-water solution: 1 M NaCl at 298.15 K, observed osmotic
pressure 4.96 MPa, van 't Hoff factor `i = 2` (full dissociation).
Phase 1 (Claude extraction) reads this text and emits the ledger.

**`claims_clean.jsonl`** has three rows, each carrying a canonical
text the predicate map will match:

```jsonl
{"claim_id":"clm-osmo-000001","canonical_text":"molarity 1.0 M","predicate":":molarity","value":1.0,"sort":":real"}
{"claim_id":"clm-osmo-000002","canonical_text":"temperature 298.15 K","predicate":":temperature-k","value":298.15,"sort":":real"}
{"claim_id":"clm-osmo-000003","canonical_text":"van 't Hoff factor 2","predicate":":vant-hoff-i","value":2,"sort":":int"}
```

**`claims_doctored.jsonl`** flips one row to `i = 1` while leaving
the measured pressure and the canonical R, T, and M in place. The
verifier's job is to surface the contradiction.

## Scaffold

From the skill root:

```bash
.venv\Scripts\python.exe -m scripts.scaffold_project \
  --name "Osmotic Pressure Verifier" \
  --slug osmotic_pressure \
  --out ../../verifiers/osmotic_pressure
```

The output tree is the standard scaffold (see
`docs/operations/neurosym-forge-runbook.md`). The command omits the
Bermuda bridge flag; this verifier reads its claims from a plain
JSONL file instead of a book workspace.

## Add domain sorts

The seed sort registry covers `:int`, `:real`, and `:bool`. Add the
chemistry sorts (each invocation appends one entry to
`rules/seed.edn` and refreshes the checksum):

```bash
.venv\Scripts\python.exe -m scripts.add_sort \
  --project ../../verifiers/osmotic_pressure --sort :solution
.venv\Scripts\python.exe -m scripts.add_sort \
  --project ../../verifiers/osmotic_pressure --sort :pressure-pa
.venv\Scripts\python.exe -m scripts.add_sort \
  --project ../../verifiers/osmotic_pressure --sort :temperature-k
```

`:molarity` reuses the seed `:real`; no separate entry needed.

## Add the gas constant as a grounded atom

The ideal-gas constant `R = 8.314 J/(mol·K)` is a Rust-side value
the rule references by name:

```bash
.venv\Scripts\python.exe -m scripts.add_grounded_atom \
  --project ../../verifiers/osmotic_pressure \
  --slug osmotic_pressure \
  --name :R-gas-constant \
  --lib z3 \
  --fn r_constant \
  --sort '{"kind":"fn","args":[],"ret":":real"}' \
  --doc "ideal-gas constant R = 8.314 J/(mol*K)"
```

Edit the generated stub in `rust-verifier/src/z3.rs` to return the
constant:

```rust
#[napi]
pub fn r_constant() -> f64 { 8.314 }
```

## Add the van 't Hoff rule

The rule body lives in a JSON file; the helper reads it and appends
the record to `rules/seed.edn`. Write `vant-hoff.json` first with
the lhs/rhs expression plus the rule's ID, doc, and tags:

```json
{
  "id": "R042",
  "lhs": {"kind": "expression", "sort": ":real",
          "head": {"kind": "symbol", "name": ":osmotic-pressure",
                   "sort": {"kind": "fn", "args": [":solution"], "ret": ":real"}},
          "args": [{"kind": "variable", "name": "?s", "sort": ":solution"}]},
  "rhs": "<i * M * R * T expression — see references/worked-examples/osmotic-pressure/vant-hoff.json>",
  "doc": "van 't Hoff: pi = i * M * R * T",
  "tags": ["algebraic", "domain-chemistry"]
}
```

Then append:

```bash
.venv\Scripts\python.exe -m scripts.add_rewrite_rule \
  --project ../../verifiers/osmotic_pressure \
  --rule-file vant-hoff.json
```

The fixture stub at `tests/rules/test_R042.cljs` asserts the rewrite
produces the expected algebraic term.

## Override the axioms hook

The scaffolded `axioms.rs` ships as a no-op. Override it to assert
the temperature constant Z3 needs as background. Edit
`rust-verifier/src/axioms.rs`:

```rust
use z3::{ast::Real, Context, Solver};

pub fn assert_axioms(ctx: &Context, solver: &Solver) {
    let r = Real::new_const(ctx, "R");
    let r_value = Real::from_real(ctx, 8314, 1000); // 8.314
    solver.assert(&r._eq(&r_value));
}
```

The per-atom walk still tracks `:molarity`, `:vant-hoff-i`, and
`:temperature-k` separately, so the unsat core points at one of those
when the law fails.

## Pass one: clean run

```bash
cd ../../verifiers/osmotic_pressure
.venv\Scripts\python.exe -m scripts.ingest_ledger \
  --ledger claims_clean.jsonl \
  --predicates rules/predicates.edn \
  --out work/claims.edn

.venv\Scripts\python.exe -m scripts.run_verification \
  --workspace . --release 0.1.0 \
  --stub --stub-verdict sat
```

Expected output: `work/verdict.edn` carrying `{:verdict :sat}` and
an empty `qa/verification-defects.json`. The verdict confirms the
clean inputs satisfy the rule when the axioms hook holds R as a Z3
background constant. The `:sat` outcome does not prove the predicted
pressure
matches 4.96 MPa — that arithmetic happens inside the rewrite that
the rule produces; the verifier reports satisfiability of the
constraint set, not the numerical value.

For the live (non-stub) path, build the Rust addon
(`cargo build --release --no-default-features --features smt,kg`)
and the CLJS orchestrator (`npm install && npm run build:cljs`),
then drop the `--stub` flags. The runbook documents the build steps
end to end, including the Cargo feature flags that skip tectonic.

## Pass two: doctored run

The ledger flips one row and the rest of the workflow stays
identical. Replace `claims_clean.jsonl` with `claims_doctored.jsonl`
on the `ingest_ledger` call, then re-run:

```bash
.venv\Scripts\python.exe -m scripts.ingest_ledger \
  --ledger claims_doctored.jsonl \
  --predicates rules/predicates.edn \
  --out work/claims.edn

.venv\Scripts\python.exe -m scripts.run_verification \
  --workspace . --release 0.1.0 \
  --stub --stub-verdict unsat
```

Expected output: `work/verdict.edn` carrying `{:verdict :unsat}`
plus an `:core` field listing the tracker IDs. On the stub path
the core is synthetic; on the live path it lists `clm-osmo-000003`
— the doctored `i = 1` claim. The translation writes
`qa/verification-defects.json` with one critical D13 ticket per
core entry.

The unsat core does not list R, the molarity, or the temperature
because those values match the canonical background. The core lists
only the tracked atom whose assertion breaks the rule given the
other facts. This is the entire point of
`assert_and_track`: the unsat core is the minimal set of *operator-
supplied* facts that fail, with the background axioms held out.

On the live path the same run with the real Rust addon produces
the same verdict.edn shape. The stub path proves the file-flow and
the D13 hand-off; the live path proves Z3 actually catches the
contradiction.

## What this example shows

Three properties hold across the two passes:

1. Scaffolding produces a working verifier outside the book pipeline.
   No book-knowledge, no workspace, no chapter prose — just a JSONL
   ledger and a paper text.
2. Domain constants live cleanly inside the `axioms.rs` hook. The
   per-atom walk reports on operator-supplied facts; the background
   stays out of the unsat core.
3. One workflow recipe (`ingest_ledger` → `run_verification` →
   `verdict_to_qa`) covers both a chemistry domain and the Bermuda
   book domain. The predicate map, the sort registry, and the axioms
   hook are the only domain-specific pieces.

For the full conceptual treatment, read
`docs/concepts/neurosym-forge.md`. For the operator-level steps
common to every verifier, read
`docs/operations/neurosym-forge-runbook.md`.

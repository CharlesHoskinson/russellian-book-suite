# Bermuda verifier

A neurosymbolic verifier for the Bermuda manual. Encodes the six canonical
facts (parish count, island count, currency peg, airport location, cedar
binomial) as Z3 axioms; ingests the book-knowledge claim ledger and
chapter prose; reports unsat verdicts as `book-qa` defect class D13.

## Quickstart

From this directory:

```bash
# Install Python helpers
python -m venv .venv
.venv/Scripts/python.exe -m pip install -e ".[dev]"

# Run end-to-end (stubbed verifier, no Rust toolchain required)
.venv/Scripts/python.exe -m scripts.run_verification \
  --workspace ../../examples/bermuda-manual \
  --release 6.0.0 \
  --stub --stub-verdict sat

# Then book-qa picks up qa/verification-defects.json:
cd ../../skills/book-qa && python -m scripts.lint_artifact \
  ../../examples/bermuda-manual 6.0.0
```

## Full verification (requires Rust + Node)

```bash
# Build the Rust addon
cd rust-verifier && cargo build --release
cp target/release/libbermuda_verifier.* ../cljs-orchestrator/native/

# Build the CLJS orchestrator
cd ../ && npm install && npm run build:cljs

# Run real verification
.venv/Scripts/python.exe -m scripts.run_verification \
  --workspace ../../examples/bermuda-manual --release 6.0.0
```

## Layout

- `rules/predicates.edn` — Bermuda predicate map (parishes, islands, currency, etc.)
- `rules/seed.edn` — atomspace seed
- `rust-verifier/src/canonical.rs` — Z3 hard constraints encoding canonical-facts.md
- `scripts/ingest_ledger.py` — `claims/ledger.jsonl` → `work/claims.edn`
- `scripts/extract_prose.py` — `book/releases/N/chapter-bundles/` → `work/prose-facts.edn`
- `scripts/verdict_to_qa.py` — `work/verdict.edn` → `<workspace>/qa/verification-defects.json`
- `scripts/run_verification.py` — end-to-end driver

## Composition with book-qa

`book-qa.lint_artifact` reads `<workspace>/qa/verification-defects.json` as defect
class **D13**. Enable per workspace via `qa-config.yaml: enable_verification: true`.
A `:unsat` verdict emits one critical D13 ticket per claim ID in the unsat core.

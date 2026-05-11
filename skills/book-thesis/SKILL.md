---
name: book-thesis
description: |
  Metabook reasoning layer for the book-* skill suite. Owns the intent
  substrate: a thesis tree, paragraph back-pointers to thesis nodes,
  per-paragraph entailment checks, and a Datalog pass over claim triples
  for transitive cross-chapter contradictions.

  Use when a book needs to enforce three properties simultaneously:
  factual accuracy, cross-chapter consistency, and preservation of the
  core point across revisions. Composes with book-knowledge (facts),
  russellian-style (prose), book-compose (orchestrator), book-review
  (qualitative), book-qa (mechanical gate).

  Do NOT use for chapter drafting (use book-compose), claim ingestion
  (use book-knowledge), or sentence-grain prose discipline (use
  russellian-style).
license: MIT
---

# book-thesis

The metabook reasoning layer. Owns the *intent substrate* of a book — the thesis statement, the sub-arguments that decompose it, and the requirement that every paragraph in the manuscript trace back to some node in that tree. Sibling to `book-knowledge` (which owns the fact substrate).

## What it owns

- The thesis tree: a YAML/RDF graph rooted at `:Thesis`, with sub-arguments and required-evidence slots.
- Paragraph back-pointers: every paragraph in a draft carries a `supports:` field naming a tree node.
- The entailment loop: a per-paragraph LLM-critic dispatch that asks "does this paragraph actually advance its declared supports node?"
- The Datalog consistency pass: a small rule set that derives transitive contradictions across chapter-level claim triples.
- The exemplar pack: synthetic (supports-node, claim, paragraph) triples injected into the drafting prompt.

## What it does NOT own

- Claim ingestion or claim-ledger maintenance. That is `book-knowledge`.
- Sentence-grain prose linting (hedges, passive voice, modifier budget). That is `russellian-style`.
- Chapter orchestration, bundling, and book release. That is `book-compose`.
- Qualitative editorial review by personas. That is `book-review`.
- Mechanical D1–D8 defect gating. That is `book-qa`. (`book-thesis` *contributes* D9–D12.)

## Architecture (4 layers)

`book-thesis` sits as **Layer 2–4** on top of `book-knowledge`'s **Layer 1**:

```
┌─────────────────────────────────────────────────────────────┐
│ Layer 4  Datalog consistency pass                            │
│          rules/consistency.dl over claim triples             │
└────────────────────────┬────────────────────────────────────┘
┌────────────────────────▼────────────────────────────────────┐
│ Layer 3  Verifier-generator entailment loop                  │
│          per-paragraph LLM critic, grounded against the KG   │
└────────────────────────┬────────────────────────────────────┘
┌────────────────────────▼────────────────────────────────────┐
│ Layer 2  Thesis spine                                        │
│          YAML / RDF tree + paragraph back-pointers           │
└────────────────────────┬────────────────────────────────────┘
┌────────────────────────▼────────────────────────────────────┐
│ Layer 1  Claim ledger + RDF + SHACL (book-knowledge)         │
└─────────────────────────────────────────────────────────────┘
```

## Components

- `scripts/compile_thesis.py` — read `thesis/<book-id>.yaml`, emit RDF triples into the book-knowledge graph.
- `scripts/lint_supports.py` — walk every paragraph in the manuscript; flag orphans (no `supports:`), broken supports (node doesn't exist), and chains that don't transitively reach `:Thesis`.
- `scripts/dispatch_entailment.py` — prepare per-paragraph payloads for an LLM entailment critic. Returns `entailed | weakly-entailed | unrelated | contradicts`.
- `scripts/datalog_consistency.py` — load claim triples + thesis tree into pyDatalog, run `rules/consistency.dl`, emit derived contradictions.
- `scripts/synthesize_exemplars.py` — Symbolic→LLM exemplar pack generator. Given the thesis tree + claim slice for a chapter, writes a few-shot exemplar bundle used by the drafting agent.
- `rules/consistency.dl` — the initial Datalog rule set (~15 rules) covering transitive contradiction, orphan paragraphs, thesis-reachability.

## Composes with

- [`book-knowledge`](../book-knowledge/SKILL.md) — fact substrate. `book-thesis` reads claim triples from book-knowledge's RDF graph and writes thesis triples back into it.
- [`book-compose`](../book-compose/SKILL.md) — the chapter contract gains a `thesis_advances:` field naming sub-arguments. `compile_thesis.py` runs at the start of `build_book`.
- [`book-qa`](../book-qa/SKILL.md) — defines four new defect classes (D9 orphan-paragraph, D10 transitive-contradiction, D11 failed-entailment, D12 unadvanced-sub-argument). `lint_supports.py` and `datalog_consistency.py` feed those gates.
- [`book-review`](../book-review/SKILL.md) — orthogonal. `book-review`'s personas do qualitative review; `book-thesis` does formal-structural check.
- [`russellian-style`](../russellian-style/SKILL.md) — orthogonal. `russellian-style` polices sentence-grain; `book-thesis` polices argument-level.

## Usage

```bash
# Compile a thesis spec into RDF triples
python scripts/compile_thesis.py <workspace> <book-id>

# Lint paragraph back-pointers against the thesis tree
python scripts/lint_supports.py <workspace> <release-version>

# Run the Datalog consistency pass
python scripts/datalog_consistency.py <workspace>

# Generate an exemplar pack for a chapter
python scripts/synthesize_exemplars.py <workspace> <chapter-id>

# Prepare entailment payloads (one per paragraph) for an LLM critic
python scripts/dispatch_entailment.py <workspace> <release-version>
```

## Tests

Fixture-based pytest cases under `tests/`. Run with:

```bash
python -m pytest tests/ -v
```

Coverage:
- compile_thesis: round-trip YAML → triples → SPARQL query
- lint_supports: known-orphan paragraph fixture; known-good paragraph fixture
- datalog_consistency: contradicting-claim fixture (A→B in ch-1, B→¬A in ch-2)
- dispatch_entailment: payload-shape contract
- synthesize_exemplars: exemplar pack shape contract

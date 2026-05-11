# v6: book-thesis — Metabook Reasoning Layer

Date: 2026-05-11
Status: Draft (synthesises 3 research-agent surveys + the LAMDA neuro-symbolic survey, arXiv 2508.13678)

## Goal

Add a reasoning layer over the existing book pipeline that enforces three properties simultaneously:

1. **Factual accuracy** — every claim traces to a verified source. (Today: `book-knowledge` claim ledger + SHACL.)
2. **Cross-chapter consistency** — no contradictions across chapters, including transitive ones (`A → B` in Ch.2 vs `B → ¬A` in Ch.7). (Today: not enforced.)
3. **Preservation of the core point** — the book's thesis survives every revision; every paragraph still serves a sub-argument that supports the thesis; orphaned paragraphs flagged. (Today: not enforced.)

The proposed skill name is **`book-thesis`**. It owns the *intent substrate* of the book; together with the existing `book-knowledge` (fact substrate) it forms the metabook.

## What the literature says

Three convergent surveys (May 2026) and the LAMDA IJCAI 2025 neuro-symbolic survey (arXiv 2508.13678) agree on the architecture:

- **Hierarchical plan with explicit thesis** — Re3 (Yang 2022), DOC (Yang 2023), LongEval (2025), NovelCrafter Codex pattern. Every paragraph back-pointers to a plan node; orphans are flagged.
- **Verifier-generator with KG-grounded critic** — Self-RAG, GraphCheck (PMC12360635), KGV. Critic checks against the external KG, not self-critique (avoids the model-collapse failure mode of pure Constitutional AI per arXiv 2504.04918).
- **Symbolic consistency pass over claim triples** — Logic-LM (Pan 2023), LoCo (ICLR 2025), LoRP, ProofOfThought + Z3.
- **Domain-aware drafting** — exemplar synthesis from claims/plan (Symbolic→LLM pattern in the LAMDA survey: AlphaGeometry-style trace synthesis).

The LAMDA survey's formalism `A = f(Q, K)` via `Z = {zᵢ = gᵢ(Q, K, z₁,…,zᵢ₋₁)}` with `g ∈ {ApplyLogicRules, InducePattern, GenerateHypothesis}` (deductive, inductive, abductive) maps directly onto book-chapter compile: each `zᵢ` is a paragraph-level claim, `K` is the wiki + thesis tree.

The literature does NOT use "world model" language for text — that vocabulary is open for this skill.

## Architecture: four layers stacked on `book-knowledge`

```
┌────────────────────────────────────────────────────────────────────────┐
│ Layer 4 — Datalog/SMT consistency pass            (NEW, in book-thesis)│
│   Derives transitive contradictions across chapter-level claim triples │
│   pyDatalog or Souffle rules over the existing RDF graph               │
└─────────────────────────────────┬──────────────────────────────────────┘
                                  │
┌─────────────────────────────────▼──────────────────────────────────────┐
│ Layer 3 — Verifier-generator entailment loop      (NEW, in book-thesis)│
│   Per-paragraph LLM critic that asks: "does this paragraph entail its  │
│   declared supports: node?" Grounded against the claim ledger, not     │
│   self-critique. Modeled on Self-RAG/GraphCheck.                       │
└─────────────────────────────────┬──────────────────────────────────────┘
                                  │
┌─────────────────────────────────▼──────────────────────────────────────┐
│ Layer 2 — Thesis spine                            (NEW, in book-thesis)│
│   YAML/RDF: thesis statement -> sub-arguments -> required evidence     │
│   slots. Every chapter contract names which sub-arguments it advances. │
│   Every paragraph carries `supports:` frontmatter pointing at a node.  │
└─────────────────────────────────┬──────────────────────────────────────┘
                                  │
┌─────────────────────────────────▼──────────────────────────────────────┐
│ Layer 1 — Claim ledger + RDF + SHACL              (EXTANT, book-knowledge)│
│   Facts with provenance, SHACL shapes, SPARQL queries                  │
└────────────────────────────────────────────────────────────────────────┘
```

## Skill: `book-thesis`

Lives at `~/.claude/skills/book-thesis/`. Owns the intent substrate; reads from `book-knowledge`'s graph.

### Components

**Thesis spec** (`thesis/<book-id>.yaml`):
```yaml
book_id: bermuda-manual
thesis:
  statement: "Contemporary Bermuda is a self-governing British Overseas Territory whose economy, society, and institutions are shaped by its geography (an isolated mid-Atlantic island chain) and its history (slavery, emancipation, 1968 constitution)."
  polarity: descriptive
sub_arguments:
  - id: geography-shapes-economy
    parent: thesis
    statement: "The lack of arable land, the mid-ocean position, and the reef shelter together explain Bermuda's economic structure."
    required_evidence: [geography.area, geography.location, history.salt-trade]
  - id: history-shapes-government
    parent: thesis
    statement: "The 1968 Constitution Order is the founding instrument of contemporary self-government."
    required_evidence: [history.constitution-1968, government.cabinet, government.governor]
  # ...
```

The thesis spec compiles to RDF triples added to the `book-knowledge` graph:

```turtle
:Thesis a :ThesisNode ; :statement "..." ; :polarity "descriptive" .
:geography-shapes-economy :supports :Thesis ; :requires-evidence :geography.area , ... .
```

**Paragraph back-pointers** (in chapter draft frontmatter):
```markdown
::: paragraph supports="history-shapes-government" evidence="clm-2026-000148"
The Bermuda Constitution Order 1968 closes the chain at its modern end.
:::
```

Pandoc fenced div, parsed by `book-thesis` and joined against the thesis tree.

**Scripts** in `book-thesis/scripts/`:

- `compile_thesis.py` — reads `thesis/<book-id>.yaml`, emits RDF triples into the book-knowledge graph.
- `lint_supports.py` — walks every paragraph in the assembled manuscript; flags orphans (no `supports:`), broken supports (node doesn't exist), and chains that don't transitively reach `:Thesis`.
- `dispatch_entailment.py` — Layer 3: prepares one-paragraph payloads for an LLM critic. Payload contains the paragraph, the supports-node statement, and the cited claim text. The critic returns `entailed | weakly-entailed | unrelated | contradicts`.
- `datalog_consistency.py` — Layer 4: loads claim triples + thesis tree into pyDatalog, runs a small ruleset, emits derived contradictions. Rules expressed in `rules/consistency.dl`.
- `synthesize_exemplars.py` — Symbolic→LLM: given the thesis tree + claim slice for a chapter, generates a few-shot exemplar pack the drafting agent always sees. Each exemplar is a (supports-node, claim, well-formed paragraph) tuple — synthetic at first, replaced by real exemplars after the first chapter ships.

**Rules** in `book-thesis/rules/consistency.dl`:

Initial ruleset (~15 rules), examples:
```prolog
% transitive contradiction
contradicts(A, B) :- claim(A, S, true), claim(B, S, false).
contradicts(A, C) :- contradicts(A, B), implies(B, C).

% every paragraph must reach the thesis
reaches_thesis(P) :- supports(P, N), is_thesis(N).
reaches_thesis(P) :- supports(P, N), supports(N, M), reaches_thesis(M).
orphan(P) :- paragraph(P), not reaches_thesis(P).
```

## Integration with existing skills

### `book-knowledge` (Layer 1)
No structural change. New optional claim subtypes already scoped in v4 spec (`chart-data`, `map-region`, `photo-license`) accommodate thesis evidence. Add helper: `add_thesis_triples(graph, thesis_spec)`.

### `book-compose`
The chapter contract gains optional `thesis_advances:` field listing which sub-arguments the chapter is supposed to advance. The pre-build preflight checks that every sub-argument is advanced by at least one chapter (otherwise: orphan sub-argument, hard-fail).

### `book-qa`
New defect classes:
- **D9** `paragraph-orphan` — paragraph has no `supports:` or the supports-node is unreachable from `:Thesis`. Critical.
- **D10** `transitive-contradiction` — Datalog derives a contradiction between two chapters. Critical.
- **D11** `failed-entailment` — Layer 3 critic returned `contradicts` or `unrelated` for the paragraph's declared supports node. Critical.
- **D12** `unadvanced-sub-argument` — a thesis sub-argument has no paragraph claiming `supports:` it. Important.

These fold into the existing `book-qa.lint_artifact` and the per-chapter swarm.

### `book-review`
No change for v6.0. The narrative-craft persona (planned v4) could be told to check "is this chapter on-thesis?" as a soft signal, but the hard check lives in `book-thesis`.

## Domain training (the "trained on the domain" question)

Two tracks, sequential:

### v6.0 — Symbolic→LLM exemplar synthesis (ship first)
`synthesize_exemplars.py` writes a `<workspace>/exemplars.json` file containing ~10–30 synthetic (supports-node, claim, paragraph) triples generated from the thesis tree and the claim ledger. These are injected into every drafting agent prompt as the "house style" anchor. No weight updates. Local-only. Cheap.

This is the LAMDA survey's **Symbolic→LLM** integration pattern (AlphaGeometry's 100M synthetic proofs scaled down to book scale).

### v6.1 — LoRA on Gemma 4 26B A4B (ship later)
Train a per-book LoRA adapter that bakes the thesis + claim ledger into a small open model. The adapter handles entailment checks (Layer 3) and contradiction-rewrite (heal patches from Layer 4). Local inference on the author's machine — no API.

**Model choice** (verified May 2026): **Gemma 4 26B A4B** (MoE), instruction-tuned. Released April 2026 under Apache 2.0.

- HF id: `google/gemma-4-26B-A4B-it` (or `unsloth/gemma-4-26B-A4B-it-GGUF` for pre-quantized)
- Architecture: 26B total parameters, 4B active per forward pass (MoE)
- Reasoning benchmarks: MMLU Pro 82.6, GPQA Diamond 82.3, AIME 2026 88.3 — within 2–3 points of dense 31B
- Quantization: int4 (NF4 for LoRA training, Q4_K_M GGUF for inference)
- VRAM at inference on RTX 4090: ~17 GB, leaving ~7 GB for LoRA adapters + 128k-token KV cache
- Tokens/sec on 4090: comfortable 2–5+ (MoE routing makes inference behave like a ~7B dense model)
- LoRA toolchain: **Unsloth** (~2× faster training, ~70% less VRAM than vanilla `peft`+`trl` on Gemma 4; first-class support); `peft`+`trl` as fallback

Why Gemma 4 26B A4B over the other variants:
- E2B / E4B (~2–4B effective) are too small for cross-claim contradiction detection at 250-claim scale (MMLU Pro 60 / 69)
- Dense 31B requires int4 to fit at all on a 4090 and leaves no headroom for LoRA + long-context KV
- The MoE 26B-A4B is the only point that gives 31B-class reasoning with 7B-class inference cost on this hardware

The LAMDA survey covers the training pattern under SFT-on-solver-traces (Procedure Cloning, LOGIPT, AlphaGeometry) and RL-with-symbolic-reward (SyreLM, RLSF, RBR). Our reward signal: the Layer-3 entailment check returns `entailed` → +1; `contradicts` → -1; `unrelated` → 0; `weakly-entailed` → +0.3.

**Caveat**: no public FOLIO / FActScore / LongEval numbers exist for Gemma 4 specifically. We will need to build a small held-out entailment evaluation set (~30 paragraph-supports pairs from a finished book) before tuning the LoRA's reward weights. v6.1's first task is to ship that eval harness.

## Open questions

- **Polarity arithmetic**: when a sub-argument is "descriptive vs prescriptive", what does "contradicts the thesis" mean for a descriptive book? Probably: a paragraph that asserts the opposite polarity of an ancestor sub-argument. Concretely: if the thesis says "X explains Y" and a paragraph says "X does not explain Y", that's a critical contradiction. Needs a polarity-label vocabulary.
- **Sub-argument granularity**: how many sub-arguments per book? Bermuda has 10 chapters; somewhere between 5 (one per major theme) and 30 (one per chapter section) is plausible. Author-judgement; tool stays agnostic.
- **Datalog backend**: `pyDatalog` is convenient but slow; Soufflé is fast but requires a separate binary. v6.0 ships `pyDatalog`; v6.1 evaluates Soufflé if perf matters.
- **Translation from prose to logical form**: who decides? Options: (a) author writes the claim ledger triples by hand, (b) `book-knowledge` extracts them via an LLM at ingest, (c) `book-thesis` extracts paragraph-level claims at lint time. v6.0 goes with (b) for source-document claims and (a) for thesis-tree commitments.
- **Polarity learning vs declared**: do we ask the author to declare polarity (rigorous, friction-inducing) or infer it (cheap, lossy)? v6.0 asks; v6.1 may infer with a polarity classifier.

## Acceptance criteria for v6.0

- A `thesis/bermuda.yaml` written for the Bermuda manual; compiles cleanly into the existing RDF graph.
- `lint_supports.py` runs against the v3.0.0 manuscript and reports the orphan-paragraph count (expected non-zero — the existing prose was not authored with `supports:` frontmatter; we surface the gap).
- `datalog_consistency.py` runs against the existing claim ledger and the bermuda thesis; reports any transitive contradictions.
- `dispatch_entailment.py` produces well-formed payloads for at least one chapter; the entailment check can run via the existing agent dispatch mechanism.
- Three new D-class defect types wired into `book-qa.lint_artifact`.
- All packaged as `~/.claude/skills/book-thesis/` and copied into the repo at `skills/book-thesis/`.

## v6.1 and beyond

- Gemma LoRA adapter for entailment + contradiction-rewrite, trained per book.
- Polarity inference classifier.
- Soufflé Datalog backend if pyDatalog perf bottlenecks.
- Integration with the planned `book-craft` skill (v4): the thesis tree becomes the source of truth for `scene_anchoring` (which thesis node does this scene serve?).

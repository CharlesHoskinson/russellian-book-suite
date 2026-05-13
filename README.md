# russellian-book-suite

A family of six Claude Code skills that produces non-fiction books from a local claim-ledger and chapter contracts. Russell-style prose discipline, multi-persona editorial review, deterministic post-build QA. Local-only — no paid APIs.

## What this is

Six skills that compose into a book pipeline. Data flows top-to-bottom; every
arrow is labelled with what crosses the stage boundary.

```
  sources (PDFs, .md, .txt, .pdf)         chapter contracts (.yaml)
            │                                       │
            │ raw text + provenance                 │ topics, evidence,
            ▼                                       │ acceptance tests
  ┌──────────────────────┐                          │
  │ 1. INGEST            │                          │
  │   book-knowledge     │                          │
  │   SHACL · PROV-O     │                          │
  └──────────┬───────────┘                          │
             │ claim-ledger.jsonl                   │
             │ (claims + spans + status)            │
             ▼                                      ▼
            ┌──────────────────────────────────────────┐
            │ 2. AUTHOR + STYLE                        │
            │    russellian-style                      │
            │    hedges · passive · modifier budget    │
            │    listicle · rhythm · humanizer pass    │
            └──────────────────┬───────────────────────┘
                               │ chapter-NN.md
                               │ (Russell-clean prose)
                               ▼
            ┌──────────────────────────────────────────┐
            │ 3. REVIEW                                │
            │    book-review                           │
            │    Gottlieb · Lay · Domain · Copy ·      │
            │    Enjoyment  (5 personas)               │
            │    soft-gate: critical_count == 0        │
            └──────────────────┬───────────────────────┘
                               │ persona-findings.json
                               │ + revised chapter-NN.md
                               ▼
            ┌──────────────────────────────────────────┐
            │ 4. COMPILE                               │
            │    book-compose                          │
            │    manuscript.md → React/Tailwind HTML   │
            │                  → Playwright PDF         │
            └──────────────────┬───────────────────────┘
                               │ manuscript.{md,html,pdf}
                               │ + book-manifest.yaml
                               ▼
            ┌──────────────────────────────────────────┐
            │ 5. RELEASE GATE                          │
            │    book-qa                               │
            │    Stage-1 D1–D8 (deterministic)         │
            │    Stage-2 C1–C15 swarm (per chapter)    │
            │    Stage-3 Sentinel · Stage-4 Healer     │
            │    hard-gate: D1–D8 == 0                 │
            └──────────────────┬───────────────────────┘
                               │ release/ bundle
                               ▼
                       manuscript.pdf
                       manuscript.html
                       manuscript.md
                       chapter-bundles/
                       claims-bibliography.md
                       qa/swarm-findings.md
```

## Lifecycle stages

**1. Ingest — [book-knowledge](skills/book-knowledge/SKILL.md).** Inputs: source
documents (PDFs, markdown, transcripts) plus chapter contracts. The skill
extracts claims, attaches PROV-O provenance, validates the graph with SHACL, and
emits a JSONL claim ledger. No hard gate; SHACL violations surface as warnings.

**2. Author + Style — [russellian-style](skills/russellian-style/SKILL.md).**
Inputs: a chapter draft in markdown plus the claim ledger slice for that
chapter. The skill enforces sentence-grain analytic prose: zero hedges,
modifier budget, no passive without cause, parallel structure on lists, rhythm
variance, listicle abstraction, citation-token hygiene, plus a humanizer pass
for AI-fingerprint removal. Output: a Russell-clean `chapter-NN.md`. Soft gate
on configured thresholds.

**3. Review — [book-review](skills/book-review/SKILL.md).** Inputs: the styled
chapter and the chapter contract. Five personas (Robert Gottlieb, Lay Reader,
Domain Expert, Copyeditor, Enjoyment Reader) read independently and return
severity-tagged findings. Output: `persona-findings.json` and a revised chapter
draft. Soft-gates chapter release on `persona_critical_count == 0`.

**4. Compile — [book-compose](skills/book-compose/SKILL.md).** Inputs: the
reviewed chapter set, the book-manifest, and the claim bibliography. The
orchestrator assembles `manuscript.md`, renders a React/Tailwind/shadcn HTML
browser view, and prints the canonical PDF via Playwright's bundled Chromium.
Output: `manuscript.{md,html,pdf}` plus per-chapter bundles. No gate here; the
gate runs in stage 5.

**5. Release gate — [book-qa](skills/book-qa/SKILL.md).** Inputs: the compiled
manuscript bundle. Stage-1 runs the deterministic D1–D8 linter (orphan citation
tokens, heading leakage, etc.). Stage-2 dispatches a per-chapter C1–C15 LLM
swarm. Stage-3 (Sentinel) triages findings; Stage-4 (Healer) optionally patches.
**Hard gate**: D1–D8 must be zero before "ship." Output: the final
`release/` bundle.

## The six skills

| Skill | One-line purpose | Lifecycle stage |
|---|---|---|
| **[`russellian-style`](skills/russellian-style/SKILL.md)** | Enforce sentence-grain analytic prose (hedges, passive, modifier budget, listicle, rhythm) | 2 — author + style |
| **[`book-knowledge`](skills/book-knowledge/SKILL.md)** | Ingest sources, maintain claim ledger with provenance, RDF graph, SHACL validation | 1 — ingest |
| **[`book-compose`](skills/book-compose/SKILL.md)** | Orchestrator. Read chapter contract → claim slice → draft → bundle → book release (Markdown + React/Tailwind HTML + Playwright PDF) | 4 — compile |
| **[`book-review`](skills/book-review/SKILL.md)** | Five-persona qualitative editorial review (Gottlieb, Lay Reader, Domain Expert, Copyeditor, Enjoyment Reader) — soft-gates chapter release | 3 — review |
| **[`book-qa`](skills/book-qa/SKILL.md)** | Post-build defect gate: deterministic Stage-1 linter (D1–D8) + per-chapter swarm (C1–C15) + Sentinel-Healer loop | 5 — release gate |
| **[`book-thesis`](skills/book-thesis/SKILL.md)** | Metabook reasoning: thesis tree, paragraph back-pointers, entailment loop, Datalog cross-chapter consistency | Layer 2-4 on top of book-knowledge; contributes D9-D12 to book-qa |

Skill source: `skills/<skill>/`. Each skill is a self-contained directory with `SKILL.md`, `scripts/`, `tests/`, and (where applicable) `personas/`, `checklists/`, `references/`, `assets/`.

## Quickstart

```bash
# Clone
git clone https://github.com/CharlesHoskinson/russellian-book-suite.git
cd russellian-book-suite

# Install one skill into Claude Code
cp -r skills/book-qa ~/.claude/skills/book-qa
cd ~/.claude/skills/book-qa
python -m venv .venv
.venv/Scripts/python -m pip install -e .[dev]

# Or install all six
for skill in russellian-style book-knowledge book-compose book-review book-qa book-thesis; do
  cp -r skills/$skill ~/.claude/skills/$skill
done
```

In a Claude Code session, the skills are now discoverable. Invoke them by their slash names: `/russellian-style`, `/book-qa`, etc.

## Example: the Bermuda manual

A 78-page non-fiction book on contemporary Bermuda was produced end-to-end through this pipeline. The released artifact and supporting reports live under `examples/bermuda-manual/`:

- `book/releases/6.0.0/manuscript.pdf` — the final 78-page book (1.4 MB)
- `book/releases/6.0.0/summary.json` — book metadata
- `book/releases/6.0.0/book-manifest.yaml` — release manifest
- `chapters/contracts/ch-NN.yaml` — the 10 chapter contracts that drove the build
- `reports/V*.md` — release reports (v3, v4, v4.1, v4.2, v4.3, v5)
- `qa/v5-swarm-findings.md` — most recent QA pass results
- `qa/chapter-tickets/ch-NN.json` — per-chapter swarm tickets

## Repository layout

```
russellian-book-suite/
├── README.md                       this file
├── LICENSE                         MIT
├── .gitignore
├── skills/
│   ├── book-compose/               orchestrator + MEMORY.md
│   ├── book-knowledge/             claim ledger
│   ├── book-qa/                    deterministic + swarm QA
│   ├── book-review/                5-persona qualitative review
│   ├── book-thesis/                metabook reasoning
│   └── russellian-style/           sentence-grain discipline
├── tools/                          one-shot scripts (figure gen, hero tables, footnote post-process, etc.)
├── examples/
│   ├── bermuda-manual/             the proof (PDF + contracts + reports + QA findings)
│   └── tiny-example-book/          synthetic 3-chapter quickstart (TBD)
└── docs/
    ├── retros/                     v3-to-v4.3 retrospective
    ├── specs/                      v4 + v5 design docs
    └── plans/                      v4 implementation plan
```

## Pipeline at a glance

A book is produced in roughly five passes:

1. **Ingest** sources via [`book-knowledge`](skills/book-knowledge/SKILL.md) — extract claims into a JSONL ledger with provenance, status, source spans.
2. **Author** chapter drafts in markdown. Each chapter has a `contract.yaml` that lists must-include topics, must-not-do constraints, evidence requirements, and acceptance tests (linter thresholds).
3. **Style** with [`russellian-style`](skills/russellian-style/SKILL.md) — every chapter linted for atomic sentences, no hedges, modifier budget, parallel structure, listicle abstraction, sentence rhythm, citation-token leakage, plus AI-fingerprint detection via the `humanizer` skill.
4. **Review** with [`book-review`](skills/book-review/SKILL.md) — five-persona LLM editorial swarm. Soft-gates on `persona_critical_count == 0`.
5. **Compile + Release** with [`book-compose`](skills/book-compose/SKILL.md) — assemble manuscript markdown, render React/Tailwind/shadcn HTML browser, print PDF via Playwright. Then [`book-qa`](skills/book-qa/SKILL.md) runs a final post-build defect sweep (D1–D8 deterministic + C1–C15 chapter swarm) before "ship."

## Local-only constraint

No paid APIs. No data leaves the host machine. The pipeline composes:

- Python (matplotlib, geopandas, great_tables, spaCy, plottable, css-inline, pypdf)
- Node (`@mermaid-js/mermaid-cli` via Playwright's bundled Chromium)
- Playwright (HTML → PDF rendering)

Image sources for visuals come from OpenStreetMap (ODbL), Wikimedia Commons (where photos are needed), and programmatic charts from the claim ledger.

## Documentation

- **Retrospective**: `docs/retros/2026-05-11-v3-to-v4.3-retrospective.md` — defect inventory + four root-cause patterns observed across the Bermuda build
- **v4 design**: `docs/specs/2026-05-10-book-craft-v4-design.md` — proposed `book-craft` skill (chapter craft: scenes, structural variety, visuals manifest, narrative-craft persona)
- **v5 design**: `docs/specs/2026-05-11-book-qa-v5-design.md` — the `book-qa` Generator-Verifier with Sentinel-Healer pattern
- **v4 plan**: `docs/plans/2026-05-10-book-craft-v4-and-bermuda-regen.md` — 28-task implementation plan
- **Bundle C design**: `docs/specs/2026-05-11-bundle-c-closed-loop-ledger-design.md` — closed-loop claim ledger with abductive counter-claims, Bayesian propagation, writeback adapter
- **Bundle C plan**: `docs/plans/2026-05-11-bundle-c-closed-loop-ledger.md` — 30-task TDD implementation plan
- **Bundle C runbook**: `docs/operations/2026-05-12-bundle-c-runbook.md` — Phase-4 operator runbook

## Lessons (from the Bermuda build)

See `skills/book-compose/MEMORY.md` for the full list. Selected highlights:

- **Orphan citation tokens leak** between source and renderer. Strip on chapter draft AND assembled manuscript AND merged HTML — skipping any of the three re-introduces them on next build.
- **HTML block break rule**: every `</section>`, `</div>`, `</aside>` must be followed by a blank line before any markdown block can resume. Omitting it lets `# Chapter N:` render as literal text.
- **Tailwind preflight** resets `h1,h2,h3 { font-size: inherit }`. Heading-override CSS must live AFTER the preflight in the cascade.
- **Middle-chapter quality dip**: chapters 4–8 in any 10-chapter batch return lower-quality agent output than chapters 1–3 and 9–10. Mitigations: one fresh-context agent per chapter, randomised dispatch order, keep per-agent prompts ≤500 words.

## License

MIT. See `LICENSE`.

## Acknowledgements

- Bertrand Russell — the analytic-prose standard the suite enforces
- John McPhee, Bill Bryson — the scene-craft model the `book-craft` design (v4, planned) is built around
- Anthropic's "Building Effective AI Agents" + "Multi-agent coordination patterns" research — the Generator-Verifier + Sentinel-Healer pattern the v5 `book-qa` skill implements
- The Tufte CSS family — typography reference for the v4.3 prose-furniture treatment
- OpenStreetMap contributors (ODbL) — base data for the parish + ferry-route maps

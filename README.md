# russellian-book-suite

A family of five Claude Code skills that produces non-fiction books from a local claim-ledger and chapter contracts. Russell-style prose discipline, multi-persona editorial review, deterministic post-build QA. Local-only — no paid APIs.

## What this is

Five skills that compose into a book pipeline.

```
   chapter contracts (.yaml)
            │
            ▼                                            ┌──────────────────────────────────┐
   ┌─────────────────┐                                   │  Composes-with:                  │
   │  book-knowledge │  ◄──  sources (PDFs, .md, .txt)   │   - russellian-style (prose)     │
   │  claim ledger   │       SHACL + PROV-O + SPARQL     │   - book-knowledge (claims)      │
   └────────┬────────┘                                   │   - book-compose (orchestrator)  │
            │                                            │   - book-review (5 personas)     │
            ▼                                            │   - book-qa (defect gate)        │
   ┌─────────────────┐                                   └──────────────────────────────────┘
   │ chapter draft   │  ◄──  Russell-style prose +
   │   (markdown)    │       McPhee/Bryson scene craft
   └────────┬────────┘
            │
            ▼
   ┌──────────────────────────┐    ┌────────────────────────┐
   │  russellian-style        │    │  book-craft (planned)  │
   │  hedges, passive, signal │    │  scenes, transitions,  │
   │  density, parallel,      │    │  structural variety,   │
   │  listicle, rhythm        │    │  visuals manifest      │
   └────────┬─────────────────┘    └────────────┬───────────┘
            │                                   │
            └──────────────┬────────────────────┘
                           ▼
                  ┌──────────────────────┐
                  │  book-review         │
                  │  5+1 personas        │
                  │  (Gottlieb, Lay      │
                  │  Reader, Domain      │
                  │  Expert, Copyeditor, │
                  │  Enjoyment Reader,   │
                  │  Narrative-Craft)    │
                  └────────┬─────────────┘
                           ▼
                  ┌──────────────────────┐
                  │  book-compose        │
                  │  build_book →        │
                  │   manuscript.md      │
                  │   manuscript.html    │
                  │   manuscript.pdf     │
                  └────────┬─────────────┘
                           ▼
                  ┌──────────────────────┐
                  │  book-qa             │
                  │  Stage-1: D1–D8      │
                  │  Stage-2: 15-item    │
                  │           swarm      │
                  │  Stage-3: Sentinel   │
                  │  Stage-4: Healer     │
                  └────────┬─────────────┘
                           ▼
                  ┌──────────────────────┐
                  │  release bundle      │
                  │  manuscript.pdf      │
                  │  manuscript.html     │
                  │  manuscript.md       │
                  │  chapter-bundles/    │
                  │  claims-bibliography │
                  └──────────────────────┘
```

## The five skills

| Skill | One-line purpose | Lifecycle stage |
|---|---|---|
| **`russellian-style`** | Enforce sentence-grain analytic prose (hedges, passive, modifier budget, listicle, rhythm) | pre-compile |
| **`book-knowledge`** | Ingest sources, maintain claim ledger with provenance, RDF graph, SHACL validation | pre-compile |
| **`book-compose`** | Orchestrator. Read chapter contract → claim slice → draft → bundle → book release (Markdown + React/Tailwind HTML + Playwright PDF) | compile |
| **`book-review`** | Five-persona qualitative editorial review (Gottlieb, Lay Reader, Domain Expert, Copyeditor, Enjoyment Reader) — soft-gates chapter release | review |
| **`book-qa`** | Post-build defect gate: deterministic Stage-1 linter (D1–D8) + per-chapter swarm (C1–C15) + Sentinel-Healer loop | release |

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

# Or install all five
for skill in russellian-style book-knowledge book-compose book-review book-qa; do
  cp -r skills/$skill ~/.claude/skills/$skill
done
```

In a Claude Code session, the skills are now discoverable. Invoke them by their slash names: `/russellian-style`, `/book-qa`, etc.

## Example: the Bermuda manual

A 78-page non-fiction book on contemporary Bermuda was produced end-to-end through this pipeline. The released artifact and supporting reports live under `examples/bermuda-manual/`:

- `manuscript.pdf` — the final 78-page book (1.4 MB)
- `summary.json` — book metadata
- `book-manifest.yaml` — release manifest
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
│   ├── russellian-style/           sentence-grain discipline
│   ├── book-knowledge/             claim ledger
│   ├── book-compose/               orchestrator + MEMORY.md
│   ├── book-review/                5-persona qualitative review
│   └── book-qa/                    deterministic + swarm QA
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

1. **Ingest** sources via `book-knowledge` — extract claims into a JSONL ledger with provenance, status, source spans.
2. **Author** chapter drafts in markdown. Each chapter has a `contract.yaml` that lists must-include topics, must-not-do constraints, evidence requirements, and acceptance tests (linter thresholds).
3. **Style** with `russellian-style` — every chapter linted for atomic sentences, no hedges, modifier budget, parallel structure, listicle abstraction, sentence rhythm, citation-token leakage, plus AI-fingerprint detection via the `humanizer` skill.
4. **Review** with `book-review` — five-persona LLM editorial swarm. Soft-gates on `persona_critical_count == 0`.
5. **Compile + Release** with `book-compose` — assemble manuscript markdown, render React/Tailwind/shadcn HTML browser, print PDF via Playwright. Then `book-qa` runs a final post-build defect sweep (D1–D8 deterministic + C1–C15 chapter swarm) before "ship."

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

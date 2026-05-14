# russellian-book-suite

You give the suite a folder of sources and a chapter contract. It fact-checks every claim against the sources and drafts the chapter. Then it lints the prose against Bertrand Russell's analytic style, dispatches a seven-persona editorial panel to review the draft, and refuses to ship until every gate passes. The output is a non-fiction book — Markdown, HTML, and PDF — that did not roll off an AI prose mill.

The `examples/bermuda-manual/` workspace is the proof: a 78-page book on contemporary Bermuda compiled end-to-end through the pipeline, with a SHACL-conformant knowledge graph and zero open competency-query failures at release.

> *"A book by Bertrand Russell may be hard to follow, but it cannot be misunderstood."* — A. J. Ayer
>
> The suite enforces a weaker version of the same standard: every sentence atomic, every claim sourced, every paragraph earning its place.

## Who this is for

- **Non-fiction authors** who want a local, auditable pipeline rather than a hosted AI writing service.
- **Research teams** who need reference manuals, internal handbooks, or technical books drawn from a vetted source corpus.
- **Pipeline builders** who want to study how seven Claude Code skills compose into a single editorial workflow.

The suite is **local-only by construction**. No paid APIs. No telemetry. No network egress at runtime. Every LLM call is parameterised through a callable; tests pass fake LLM functions and run offline.

## Contents

1. [The pipeline](#the-pipeline)
2. [The seven skills](#the-seven-skills)
3. [Core concepts](#core-concepts)
   - [The book workspace](#the-book-workspace)
   - [The claim ledger and PROV-O provenance](#the-claim-ledger-and-prov-o-provenance)
   - [Russellian prose discipline](#russellian-prose-discipline)
   - [The thesis tree](#the-thesis-tree)
   - [Multi-persona review](#multi-persona-review)
   - [The defect taxonomy](#the-defect-taxonomy)
   - [Bundle C: the closed-loop ledger](#bundle-c-the-closed-loop-ledger)
4. [Quickstart](#quickstart)
5. [End-to-end: the Bermuda manual](#end-to-end-the-bermuda-manual)
6. [Local-only constraint](#local-only-constraint)
7. [Repository layout](#repository-layout)
8. [Lessons learned](#lessons-learned)
9. [Documentation](#documentation)
10. [License and acknowledgements](#license-and-acknowledgements)

## The fingerprint problem

Large language models leave a fingerprint. Sentences average eighteen words. Paragraphs come in threes. The opening adjective is always "comprehensive" or "robust," and em-dashes do the work that connectives should. The prose reads competent and forgettable; a domain reader spots an error in the second paragraph and stops trusting the rest. This suite was built because a hosted AI tool will not catch any of that, and a manuscript that lands on a publisher's desk with a thousand small AI tells will be rejected before page ten.

The fix is not a smarter prompt. The fix is a pipeline that separates fact ingestion, drafting, prose linting, persona review, and defect gating into distinct stages. Each stage runs its own discipline; each refuses to pass the artefact downstream until its gate clears.

## The pipeline

```
   sources (PDF · MD · TXT)       chapter contracts (YAML)
            │                              │
            ▼                              │
   ┌────────────────────┐                  │
   │  1. INGEST         │                  │
   │  book-knowledge    │                  │
   │  fact-check + RDF  │                  │
   └──────────┬─────────┘                  │
              │ claims/ledger.jsonl        │
              │ graph/dataset.trig         │
              ▼                            ▼
   ┌──────────────────────────────────────────────┐
   │  2. AUTHOR + STYLE                            │
   │  book-compose  →  russellian-style            │
   │  per-section: hedges · passive · density ·    │
   │  parallel · rhythm · listicle  →  humanizer   │
   └──────────────────┬────────────────────────────┘
                      │ chapter-NN.md
                      ▼
   ┌──────────────────────────────────────────────┐
   │  3. REVIEW                                    │
   │  review-conductor → book-review (7 personas)  │
   │  Gottlieb · Lay · Domain · Copy · Enjoyment   │
   │  · AI-slop · First-time visitor               │
   │  per-persona severity gate                    │
   └──────────────────┬────────────────────────────┘
                      │ panel-review.md + verdict.json
                      ▼
   ┌──────────────────────────────────────────────┐
   │  4. COMPILE                                   │
   │  book-compose                                 │
   │  manuscript.md  →  React/Tailwind HTML        │
   │                 →  Playwright PDF             │
   └──────────────────┬────────────────────────────┘
                      │ manuscript.{md,html,pdf}
                      ▼
   ┌──────────────────────────────────────────────┐
   │  5. RELEASE GATE                              │
   │  book-qa                                      │
   │  D1-D12 linter  ·  C1-C15 chapter swarm       │
   │  sentinel  ·  healer                          │
   │  hard-gate: D1-D8 == 0                        │
   └──────────────────┬────────────────────────────┘
                      │
                      ▼
                  release/
                    manuscript.{md,html,pdf}
                    chapter-bundles/
                    claims-bibliography.md
                    qa/swarm-findings.md
```

The pipeline is sequential. Stage N reads stage N-1's outputs and writes its own. Two side-channels close the loop: persona findings can return a chapter to stage 2 for redraft; post-build QA at stage 5 can propose write-backs to the claim ledger at stage 1, so a defect surfaced in the final book corrects the underlying facts for the next release.

## The seven skills

Each skill is a self-contained Claude Code skill at `skills/<name>/` with its own `SKILL.md`, `scripts/`, `tests/`, and (where needed) `personas/`, `panels/`, `references/`.

| Skill | Stage | What it does | Tests |
|---|---|---|---:|
| [`book-knowledge`](skills/book-knowledge/SKILL.md) | 1 — ingest | Reads source PDFs and Markdown, extracts claims with PROV-O provenance, projects them into an RDF graph, validates the graph with SHACL, runs competency queries, manages the append-only ledger, propagates Bayesian belief across the provenance DAG | 133 |
| [`russellian-style`](skills/russellian-style/SKILL.md) | 2 — style | Sentence-grain prose linters: hedges, passive voice, signal density, parallel structure, rhythm, listicle abstraction. Twenty-six principles across five domains, drawn from Russell's analytic style | 59 |
| [`book-compose`](skills/book-compose/SKILL.md) | 2 + 4 — author + compile | Chapter orchestrator. Reads the contract, slices the claim ledger, generates an outline and section drafts, applies russellian-style and humanizer per section, assembles the book release (Markdown + React/Tailwind HTML + Playwright PDF) | 95 |
| [`book-review`](skills/book-review/SKILL.md) | 3 — review | Seven editorial personas with markdown role descriptions: Gottlieb (cadence, AI sloppy), Lay Reader (accessibility), Domain Expert (facts), Copyeditor (mechanics), Enjoyment Reader (momentum), AI-Slop Detector (24-pattern Wikipedia catalog), First-Time Visitor (30-second drive-by) | 24 |
| [`review-conductor`](skills/review-conductor/SKILL.md) | 3 — review orchestration | Reads a panel YAML, calls book-review's dispatch primitives, applies per-persona severity gates (gating vs advisory), aggregates findings, emits `panel-review.md` + `verdict.json` | 32 |
| [`book-qa`](skills/book-qa/SKILL.md) | 5 — release gate | Post-build defect gate. D1-D8 deterministic linter on the built artefact, D9-D12 from book-thesis, C1-C15 per-chapter agent swarm, Sentinel-Healer patch loop | 41 |
| [`book-thesis`](skills/book-thesis/SKILL.md) | layer-2/3/4 over book-knowledge | Thesis tree, paragraph back-pointers, per-paragraph entailment loop, Datalog cross-chapter consistency. Contributes defect classes D9-D12 to book-qa | 16 |

**Total: 400 tests** across the seven skills. All green at HEAD.

The skills compose by shared workspace, not by direct API call. Each skill owns a subtree and treats the others as read-only inputs:

```
                 ┌──────────────────────┐
                 │   sources, papers    │
                 └──────────┬───────────┘
                            │
                            ▼
                 ┌──────────────────────┐
                 │   book-knowledge     │
                 │  raw/ wiki/ claims/  │
                 │       graph/         │
                 └──────────┬───────────┘
                            │
                            │ claims · wiki · graph
                            ▼
                 ┌──────────────────────┐
                 │     book-thesis      │
                 │ thesis · entailment  │
                 │   datalog rules      │
                 └──────────┬───────────┘
                            │
                            │ thesis triples · D9-D12 inputs
                            ▼
                 ┌──────────────────────┐         ┌────────────────────┐
                 │     book-compose     │ ◀────── │  russellian-style  │
                 │  contracts · drafts  │  per-   │ hedges · passive · │
                 │       releases       │ section │   density · …      │
                 └──────────┬───────────┘         └────────────────────┘
                            │ chapter-NN.md
                            ▼
                 ┌──────────────────────┐
                 │   review-conductor   │
                 │  panel orchestration │
                 │   (gating/advisory)  │
                 └──────────┬───────────┘
                            │ panel + verdict
                            ▼
                 ┌──────────────────────┐
                 │     book-review      │
                 │  7 personas (||el)   │
                 │  severity rubric     │
                 └──────────┬───────────┘
                            │ persona reports
                            ▼
                 ┌──────────────────────┐
                 │       book-qa        │
                 │  D1-D12 · C1-C15 ·   │
                 │  sentinel · healer   │
                 └──────────┬───────────┘
                            │  release bundle
                            ▼
                       manuscript.pdf
                       manuscript.html
                       manuscript.md
                       chapter-bundles/
```

Two side-arrows close the loop:

```
   book-qa  ─→  proposed-transitions.jsonl  ─→  book-knowledge.apply_writeback
   review-conductor  ─→  verdict.json  ─→  book-compose (redraft if soft-gate-fail)
```

## Core concepts

### The book workspace

A workspace is a directory. Eight subtrees, four append-only ledgers, one RDF graph. Cloning the directory clones the book.

```
<workspace>/
├── CLAUDE.md                # workspace marker; book-id and style profile
├── raw/                     # book-knowledge owns; immutable source corpus
│   ├── pdf/
│   ├── markdown/
│   └── manifests/           # one source-manifest.json per source
├── wiki/                    # book-knowledge owns; append-only synthesis pages
│   ├── index.md
│   ├── log.md
│   ├── current-status.md
│   ├── sources/  concepts/  entities/  chapters/
├── claims/                  # book-knowledge owns; append-only claim ledger
│   ├── ledger.jsonl                     # claim records + state-transition records
│   │                                    # (n.b. transitions live here in v6;
│   │                                    #  events.jsonl below is reserved for a
│   │                                    #  future split-out — not yet in use)
│   ├── counter-claims.jsonl
│   ├── conflicts.jsonl                  # (created on first conflict)
│   ├── events.jsonl                     # (reserved; transition log split planned)
│   ├── proposed-transitions.jsonl
│   ├── snapshots/
│   └── address-checks/                  # (created on first counter-claim
│                                        #  address check; absent in bermuda v6)
├── graph/                   # book-knowledge owns; projected RDF dataset
│   ├── dataset.trig                     # the projected graph
│   └── reports/                         # SHACL reports, competency-query results
│                                        # (SHACL shapes ship with the skill at
│                                        #  skills/book-knowledge/assets/shapes.ttl
│                                        #  and are referenced at validate-time)
├── chapters/                # book-compose owns
│   ├── contracts/           # chapter-NN.yaml
│   ├── drafts/              # chapter-NN/{outline.md, draft.md, panel-review.md, verdict.json}
│   └── releases/            # chapter-NN-vX.Y/{draft.md, manifest.yaml, ...}
├── book/                    # book-compose owns; book-level release bundles
│   ├── preflight/
│   └── releases/<version>/
│       ├── manuscript.md
│       ├── manuscript.html
│       ├── manuscript.pdf
│       ├── book-manifest.yaml
│       └── chapter-bundles/
├── qa/                      # book-qa owns
│   ├── lint-findings.json
│   ├── swarm-findings.json
│   ├── chapter-tickets/
│   ├── ledger-writeback-<version>.md
│   └── panels/                          # optional per-workspace panel overrides
├── thesis/                  # book-thesis owns
│   ├── <book-id>.yaml
│   └── schema.yaml
└── reports/                 # cross-skill release reports
```

Five invariants hold by skill contract and by test:

- `book-knowledge` is the only writer of `raw/`, `wiki/`, `claims/`, `graph/`.
- `book-compose` is the only writer of `chapters/` and `book/`.
- `book-qa` is the only writer of `qa/`.
- `book-thesis` is the only writer of `thesis/`.
- `claims/ledger.jsonl`, `claims/counter-claims.jsonl`, and `claims/events.jsonl` are append-only.

The SHACL shapes file (`shapes.ttl`) and the JSON Schema for the source manifest stay in lockstep. An off-by-one in the status enum would break both gates silently, so the test suite checks that the SHACL `sh:in` list and the JSON Schema enum match exactly.

### The claim ledger and PROV-O provenance

A **claim** is a statement extracted from a source: subject, predicate, object, plus a source pointer, a span, a status, and a Bayesian posterior. **PROV-O** is the W3C provenance ontology — a vocabulary for saying *this fact was derived from that source by that extractor at that time*. The suite uses PROV-O so every claim in the manuscript can be traced back to a specific line in a specific source.

The ledger is an append-only JSONL log. Each line is either a new claim or a state transition on an existing claim.

A **triple** in this context is the RDF concept of subject-predicate-object, the same atomic unit the Semantic Web is built on. `project_graph.py` projects the claim ledger into an RDF dataset (in the TriG format — a flavour of Turtle with named graphs). `validate_shacl.py` runs **SHACL** — the W3C Shapes Constraint Language — against `shapes.ttl` to enforce the structural rules.

The status field follows a five-state machine. New claims arrive `proposed`. `verify_claim.py` promotes a proposed claim to `verified` once it cross-checks the locator text against the source span. `detect_conflicts.py` flips a verified claim to `disputed` when it finds an antonym-pair contradiction; if a later ingest resolves the contradiction, the claim returns to `verified`. A newer source can supersede an older claim about the same triple, sending the older one to `superseded`. When post-build QA finds a verified claim contradicted by a source added after the chapter was drafted, the write-back proposes a transition to `refuted`. Both `superseded` and `refuted` are terminal.

```
                   ┌─────────────┐
                   │  proposed   │
                   └──────┬──────┘
                          │ verify_claim.py
                          ▼
                   ┌─────────────┐
            ┌─────▶│  verified   │◀──── resolution restores verified
            │      └──────┬──────┘     │
            │             │ detect_conflicts.py
            │             ▼            │
            │      ┌─────────────┐     │
            │      │  disputed   │─────┘
            │      └──────┬──────┘
            │             │
            │      ┌──────┴───────┐
            │      ▼              ▼
            │ newer claim      refuting source
            │ arrives          arrives
            │      │              │
            │      ▼              ▼
            │ ┌─────────────┐  ┌─────────────┐
            └─│ superseded  │  │   refuted   │
              │ (terminal)  │  │ (terminal)  │
              └─────────────┘  └─────────────┘
```

Every claim carries PROV-O provenance: which source, which extractor, which version, when. A SHACL violation surfaces as a warning at ingest time and as a hard fail at release gate.

**Bayesian belief propagation** (added in Bundle C) reads the ledger plus the conflict log and writes a posterior probability to each claim, conditioned on its supporting and refuting evidence. Claims dropping below a configurable floor get a `pin_low_confidence` axiom; they surface in the `posterior-floor` **competency query** — a SPARQL query that asks "what claims have we accepted with insufficient evidence?" Bundle C also introduced **abductive counter-claim generation**: *abductive reasoning* is inference to the best alternative explanation, so given a load-bearing claim, the system synthesises a plausible rival hypothesis and writes it to `counter-claims.jsonl`. Any chapter whose contract references the original claim must address the rival before its release gate passes.

### Russellian prose discipline

Bertrand Russell wrote sentences that survive a hundred years because each one stands on its own. `russellian-style` enforces **twenty-six principles across five domains**, each backed by a deterministic Python linter that reads markdown and emits a JSON report.

Russell's own prose makes the test case. Compare his sentence

> *"The point of philosophy is to start with something so simple as not to seem worth stating, and to end with something so paradoxical that no one will believe it."*

with a typical AI-generated version of the same idea:

> *"Philosophy can be understood as a discipline that leverages foundational simplicity to navigate toward profound, often counterintuitive conclusions, ensuring readers undergo a transformative intellectual journey."*

The Russell version has zero hedges, zero promotional adjectives, an active verb in each clause, and a closing turn the reader could not have predicted. The AI version has three of the suite's hard-blocked patterns in one sentence: AI vocabulary (*leverage*, *navigate*, *transformative*), a superficial -ing analysis (*ensuring readers undergo...*), and a paragraph that does not earn its place.

The principles translate into six deterministic linters. Each linter takes a markdown file and emits a JSON report; `russellian-style/scripts/` also ships two infrastructure modules (`lint_common.py` for sentence iteration and `style_pass_report.py` for the aggregated report), which is why the skill carries eight scripts rather than six.

| Linter | What it catches |
|---|---|
| `lint_hedges.py` | Hedge vocabulary against a closed rule registry: *might*, *may*, *perhaps*, *arguably*, *in some sense*, *to a certain extent* |
| `lint_passive_voice.py` | Passive constructions via spaCy dependency parse |
| `lint_signal_density.py` | Adjective and adverb ratio per sentence against budget |
| `lint_parallel_structure.py` | Grammatical-opening parity across bullet lists |
| `lint_sentence_rhythm.py` | Sentence-length variance and cadence defects (e.g., five consecutive sentences with word counts within three of each other) |
| `lint_listicle_abstract.py` | Abstract-noun listicles masquerading as argument (*rests on N premises*, *consists of N components*) |

A Russell pass produces `style-pass-report.md` with per-rule findings and a single pass/fail verdict against configurable thresholds. `book-compose` invokes the linters after each section draft; the `humanizer` sibling skill runs an AI-fingerprint sweep afterwards to catch what the deterministic rules cannot.

### The thesis tree

A book has a thesis. The thesis decomposes into sub-arguments. Each sub-argument cites supporting claims. Every paragraph in the manuscript should trace back to one sub-argument by an explicit `supports:` field. `book-thesis` owns this *intent substrate* — the argument structure of the book — and pairs it with the *fact substrate* that `book-knowledge` owns.

The four layers (with the new terms defined inline):

```
┌─────────────────────────────────────────────────────────────┐
│ Layer 4  Datalog consistency pass                            │
│          (Datalog = a declarative logic-programming language │
│          for deriving facts from rules; the pass runs ~15    │
│          rules over the claim graph to find transitive       │
│          contradictions like "ch-1 says A → B, ch-2 says     │
│          B → ¬A")                                            │
└────────────────────────┬────────────────────────────────────┘
┌────────────────────────▼────────────────────────────────────┐
│ Layer 3  Verifier-generator entailment loop                  │
│          (an LLM critic asks per paragraph: does this        │
│          paragraph actually entail what its `supports:` node │
│          claims? verdict ∈ {entailed, weakly-entailed,       │
│                             unrelated, contradicts})          │
└────────────────────────┬────────────────────────────────────┘
┌────────────────────────▼────────────────────────────────────┐
│ Layer 2  Thesis spine                                        │
│          YAML/RDF tree rooted at :Thesis with sub-arguments   │
│          and required-evidence slots; every paragraph carries │
│          a `supports: <node>` back-pointer                    │
└────────────────────────┬────────────────────────────────────┘
┌────────────────────────▼────────────────────────────────────┐
│ Layer 1  Claim ledger + RDF + SHACL  (book-knowledge)        │
└─────────────────────────────────────────────────────────────┘
```

Each layer contributes a defect class to `book-qa`. D9 (orphan-paragraph) fires when a paragraph carries no `supports:`. D10 (transitive-contradiction) fires when the Datalog pass derives a contradiction across chapters. D11 (failed-entailment) fires when the entailment critic returns `contradicts` or `unrelated`. D12 (unadvanced-sub-argument) fires when a sub-argument node has no paragraphs that advance it.

D9, D10, and D11 are critical and hard-gate the release. D12 is important and surfaces in the post-build report.

### Multi-persona review

After a chapter passes Russellian linting, seven editorial personas read it. Each persona lives in `skills/book-review/personas/*.md` as a full role description: identity, lens, severity rubric, tone, example review. `review-conductor` loads a panel YAML, dispatches one packet per persona to a parallel sub-agent, and aggregates the severity-tagged reports into a single verdict.

| Persona | Reads for | Critical patterns | Gate |
|---|---|---|---|
| **Robert Gottlieb** | voice, cadence, AI-sloppy patterns | listicle abstracts; mechanical thesis enumeration; voice slips; 4+ consecutive same-shape sentences; paragraphs that do not earn their place | gating |
| **Lay Reader** | accessibility, vocabulary, unexplained jumps | terms used without first-appearance definition; logical jumps a generalist cannot bridge; conclusions resting on undefined concepts | advisory |
| **Domain Expert** | factual accuracy, contested-as-settled, missing nuance | claims that contradict the verified ledger; oversimplifications stated as fact; field-internal disputes elided | gating |
| **Copyeditor** | cross-chapter consistency, mechanics | terminology drift; broken cross-references; orthography splits; unbalanced quotation marks | gating |
| **Enjoyment Reader** | momentum, where the reader stops | unreadable passages; dead zones (4+ paragraphs of pure recitation); flat openings; flat endings | advisory |
| **AI-Slop Detector** | 24-pattern AI-fingerprint catalog (delegates to humanizer) | inflated symbolism; listicle abstracts; mechanical thesis enumeration; superficial -ing analyses | gating |
| **First-Time Visitor** | 30-second drive-by | first paragraph fails to say what or why; jargon density before the value prop; Quickstart looks infeasible in under ten minutes | advisory |

Severity is taken at face value. **`review-conductor`** distinguishes between **gating** personas (a single `critical` from any of them returns the chapter for redraft) and **advisory** personas (criticals surface in the report but do not block). The panel YAML configures who is which; the shipped `chapter-default.yaml` makes Gottlieb, Domain Expert, Copyeditor, and AI-Slop Detector gating; the other three advisory.

The personas do not rewrite. They flag. Revisions return to `book-compose` for the writer — human or agent — to apply.

The conductor also injects **Outcomes exemplars** — actual past findings from a real review — into each persona's prompt as few-shot context. The library at `book-review/references/outcomes/readme-pass-2026-05-13/` ships seven exemplars drawn from a real seven-persona review run on an earlier draft of this README. Each persona sees one representative finding from its own rubric before reading the new chapter.

### The defect taxonomy

`book-qa` defines two parallel taxonomies. **Mechanical defects (D1-D12)** are caught by a deterministic linter or by `book-thesis`; **editorial defects (C1-C15)** are caught by a per-chapter agent swarm.

```
                       Defect Taxonomy
                      ┌────────┴────────┐
                      │                 │
                Mechanical          Editorial
                (D1-D12)            (C1-C15)
                      │                 │
            ┌─────────┴─────────┐       │
            │                   │       │
       from book-qa       from book-thesis
       (D1-D8,            (D9-D12,
       deterministic      routed via
       linter)            book-qa)
            │                   │       │
            ▼                   ▼       ▼
      lint_artifact.py     book-thesis  per-chapter
                           scripts      swarm
```

Mechanical defects:

| ID | Class | Source | Severity |
|---|---|---|---|
| D1 | orphan citation tokens (`[clm-…]`, bare `clm-NNNN-NNNNNN`, "Claim ledger:") | book-qa linter | critical |
| D2 | raw Markdown bleed inside HTML blocks | book-qa linter | critical |
| D3 | broken cross-references (figure paths, footnote ref/def, ToC vs heading drift) | book-qa linter | critical |
| D4 | heading hierarchy violations | book-qa linter | critical |
| D5 | count-contract failures (word, footnote, figure counts outside bands) | book-qa linter | important |
| D6 | paragraph-length variance outside [0.4, 1.2] | book-qa linter | important |
| D7 | CSS reset clobber (Tailwind preflight overriding heading sizes) | book-qa linter | critical |
| D8 | asset 404s | book-qa linter | critical |
| D9 | paragraph-orphan (no `supports:` field) | book-thesis | critical |
| D10 | transitive-contradiction | book-thesis Datalog pass | critical |
| D11 | failed-entailment (`contradicts` / `unrelated`) | book-thesis entailment loop | critical |
| D12 | unadvanced-sub-argument | book-thesis | important |

D1-D8 are the eight checks `lint_artifact.py` runs on the built artefact; these are the **hard gate** — the release fails if any one returns non-zero. D9-D12 are the four classes `book-thesis` contributes to book-qa; D9, D10, and D11 are also critical-severity and block release, but through the soft-gate path (book-qa records them on the verdict; the operator can override with a documented waiver in `qa-waivers.yaml`). D12 is important-severity and surfaces in the post-build report.

The "hard-gate: D1-D8 == 0" label on the pipeline ASCII at the top of this README describes only the deterministic mechanical hard-gate; the D9-D11 soft-gate path is in addition, not instead.

Editorial defects, per-chapter swarm of fresh-context agents:

| ID | Class |
|---|---|
| C1 | heading hierarchy |
| C2 | cross-references |
| C3 | footnote quality (substantive content, semantic names) |
| C4 | citation noise (no internal IDs in print) |
| C5 | HTML block hygiene |
| C6 | terminology consistency against `house-style.yaml` |
| C7 | scene anchoring |
| C8 | sidebar quality (≤ 3 sentences) |
| C9 | table quality (numeric right-align) |
| C10 | paragraph length variance |
| C11 | Russell-style discipline (hedges, em-dash-as-comma) |
| C12 | citation completeness for numeric and surprising claims |
| C13 | closing strength |
| C14 | image alt-text quality |
| C15 | print-ready format (≤ 120-char lines) |

The Sentinel-Healer loop:

```
   build_book artefact
            │
            ▼
   ┌──────────────────┐
   │ 1. Linter (D)    │  lint_artifact.py
   │    pure Python   │  hard-fail on D1-D8 critical
   └────────┬─────────┘
            ▼
   ┌──────────────────┐
   │ 2. Chapter swarm │  dispatch_chapter_qa.py
   │    C1-C15        │  fresh-context agents, JSON tickets only
   └────────┬─────────┘
            ▼
   ┌──────────────────┐
   │ 3. Sentinel      │  sentinel.py
   │    aggregate +   │  set-diff over D + C tickets
   │    classify      │
   └────────┬─────────┘
            ▼
   ┌──────────────────┐
   │ 4. Healer        │  healer.py
   │    patch         │  isolated-context agent per defect class
   │    max 3 iters   │  sees ticket + span only
   └────────┬─────────┘
            ▼
     release bundle
```

Three healer outcomes propose **ledger write-backs** back to `book-knowledge`: `unsupported_claim` (claim lacking verified sources post-healer), `refuted_by_new_source` (claim contradicted by a source added during healing), and `addressed_rival` (counter-claim addressed in the healer patch). `propose_writeback.py` emits `claims/proposed-transitions.jsonl`; `book-knowledge.apply_writeback` is the only mutator outside the ingest path and is the only consumer of that file.

### Bundle C: the closed-loop ledger

The pipeline as described so far is acyclic: ingest produces claims, drafting consumes them, QA gates the release. Bundle C closes the loop. Post-build QA proposes ledger transitions, abductive counter-claims become drafting targets, and Bayesian propagation re-scores claim posteriors after each new source.

```
   ┌─────────────────┐
   │   sources       │
   └────────┬────────┘
            │
            ▼
   ┌─────────────────┐    abductive generation
   │  claims/ledger  │────────────────────────────┐
   └────────┬────────┘                            │
            │ propagate_belief                    ▼
            │ (PROV-O DAG)              ┌─────────────────┐
            ▼                           │ counter-claims  │
   ┌─────────────────┐                  └────────┬────────┘
   │ p_posterior     │                           │
   │ snapshots       │                           │
   └────────┬────────┘                           │
            │                                    │
            ▼                                    ▼
   ┌─────────────────────────────────────────────────────┐
   │             book-compose drafts a chapter           │
   │      must_address: open counter-claims targeting    │
   │      claims in the chapter contract                 │
   └────────┬────────────────────────────────────────────┘
            │
            ▼
   ┌─────────────────────────────────────────────────────┐
   │  book-qa: lint + swarm + sentinel + healer           │
   │   →  claims/proposed-transitions.jsonl               │
   └────────┬────────────────────────────────────────────┘
            │
            ▼
   ┌─────────────────────────────────────────────────────┐
   │  book-knowledge.apply_writeback                      │
   │  commits transitions:                                │
   │   · unsupported_claim     → disputed                 │
   │   · refuted_by_new_source → refuted (terminal)       │
   │   · addressed_rival       → counter-claim addressed  │
   └────────┬────────────────────────────────────────────┘
            │
            └──────────  loops back into claims/ledger
```

Three Bundle C invariants make the loop safe:

- `propagate_belief.run` deduplicates counter-claims to the latest record per claim ID (the ledger is append-only, so the same counter-claim ID can appear multiple times with successive states) before *damping* — the Bayesian step that reduces the weight of repeated evidence so a single source cannot double-count. A promoted counter-claim must not damp twice.
- `apply_writeback` is the only mutator of `claims/` outside `book-knowledge`'s ingest path, preserving the ledger-ownership invariant.
- A *defeasible* claim is one that can be defeated by stronger counter-evidence — verified, but rebuttable. `BLOCKING_DEFEASIBLE = True` is the default; a critical defeasible-query result hard-fails the QA gate (a chapter that cites a load-bearing claim whose rival has not been addressed cannot ship).

The Bundle C runbook (`docs/operations/2026-05-12-bundle-c-runbook.md`) walks the four phases on the Bermuda workspace.

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

# Or install all seven
for skill in russellian-style book-knowledge book-compose book-review review-conductor book-qa book-thesis; do
  cp -r skills/$skill ~/.claude/skills/$skill
done
```

The skills are now discoverable in a Claude Code session. Invoke them by slash name: `/russellian-style`, `/book-qa`, and so on.

Initialise a book workspace:

```bash
.venv/Scripts/python.exe -m scripts.workspace init /path/to/my-book
```

Ingest the first source and project the graph:

```bash
.venv/Scripts/python.exe -m scripts.ingest_pdf source.pdf /path/to/my-book
.venv/Scripts/python.exe -m scripts.verify_claim /path/to/my-book
.venv/Scripts/python.exe -m scripts.project_graph /path/to/my-book
.venv/Scripts/python.exe -m scripts.validate_shacl /path/to/my-book
```

After these commands you should see:
- `raw/pdf/source.pdf` and `raw/manifests/source.json` (the ingested file plus its manifest)
- new entries in `claims/ledger.jsonl` (one JSON object per extracted claim, status `proposed` then promoted to `verified`)
- `graph/dataset.trig` with the projected RDF graph
- `graph/reports/shacl-latest.txt` reporting `shacl_conforms: True`

Now write a chapter contract at `chapters/contracts/ch-01.yaml` listing the topic, must-include claims, must-not-do constraints, evidence requirements, and acceptance thresholds. Then in Claude Code: `"draft chapter ch-01"`. The orchestrator runs stages 1-7 of the pipeline and writes `chapters/drafts/ch-01/draft.md`.

When all chapters pass: `"build the book release v1.0"`. `book-compose` assembles the manuscript, renders the React/Tailwind HTML browser, prints the PDF via Playwright's bundled Chromium, and hands off to `book-qa` for the release gate.

## End-to-end: the Bermuda manual

A 78-page non-fiction book on contemporary Bermuda was produced end-to-end through this pipeline. The workspace at `examples/bermuda-manual/` is the proof.

A note on what "proof" means here. The current Bermuda ledger was **synthesised from a thesis YAML**, not ingested from a PDF corpus. The thesis describes the argument structure; `tools/synthesize_bermuda_ledger.py` produced a claim ledger matching that argument, which the rest of the pipeline then drafted, reviewed, and shipped end-to-end. This validates the pipeline's drafting → review → release chain on a real-shaped workload. The PDF-ingest path is exercised by `book-knowledge`'s own test suite but not yet by a full Bermuda-scale build. A future release will rebuild the workspace from primary sources (Bermuda Government statistics, Department of Tourism reports, Association of Bermuda Insurers and Reinsurers (ABIR) data).

What the v6.0.0 release contains:

```
examples/bermuda-manual/
├── CLAUDE.md                          # workspace marker
├── raw/manifests/thesis.json          # the synthesized source
├── claims/                            # ledger (10 claims, 1 thesis source)
├── graph/dataset.trig                 # projected RDF graph
├── graph/reports/competency-*.md      # competency-query results (all clean)
├── chapters/contracts/ch-01..10.yaml  # 10 chapter contracts
├── book/releases/
│   ├── 3.0.0/                         # earlier release for comparison
│   └── 6.0.0/                         # current release
│       ├── manuscript.pdf             # 78 pages, 1.4 MB
│       ├── manuscript.html            # React/Tailwind browser
│       ├── manuscript.md
│       ├── book-manifest.yaml
│       ├── summary.json
│       └── chapter-bundles/ch-01..10-v6/
├── qa/                                # swarm findings, chapter tickets
├── reports/                           # cross-version release reports
└── thesis/                            # bermuda thesis YAML
```

The v6.0.0 manifest declares the gate results:

```yaml
book_id: bermuda-manual
built_at: '2026-05-13T01:22:49+00:00'
title: Life in Bermuda
version: 6.0.0
chapters_included: [ch-01, …, ch-10]
chapter_versions: {ch-01: v6, …, ch-10: v6}
total_word_count: 36762                # counted on the assembled HTML;
                                       # `wc -w` on the .md returns 28,018
sources_bibliography:
  - thesis
shacl_conforms: true                   # graph validates against shapes.ttl
competency_clean: true                 # all 8 competency queries return zero rows
outputs: [manuscript.md, manuscript.html, manuscript.pdf]
```

`shacl_conforms: true` means the projected RDF graph validates against the SHACL shapes. `competency_clean: true` means all eight competency queries return zero rows (no orphan wiki pages, no unsupported claims, no transitive contradictions, no posterior-floor violations, no open rebuttals against load-bearing claims).

## Local-only constraint

No paid APIs. No telemetry. No network egress at runtime. The full stack:

- **Python**: pdfplumber (PDF ingest), markdown-it-py (Markdown ingest), rdflib (graph), pyshacl (SHACL validation), jsonschema (claim validation), spaCy (dependency parsing for Russellian linters), pypdf (PDF post-processing), matplotlib (figures), geopandas (maps), great_tables and plottable (tables), css-inline (HTML rendering), pyDatalog (the consistency pass in book-thesis).
- **Node**: `@mermaid-js/mermaid-cli` for Mermaid diagrams, called from Playwright's bundled Chromium.
- **Playwright**: HTML → PDF rendering with Chromium.

Image sources for visuals come from OpenStreetMap (under the Open Database Licence), Wikimedia Commons (Creative Commons licences), and programmatic charts generated from the claim ledger. No image is fetched at runtime; assets ship with the workspace.

LLM calls happen at three points in the pipeline: section drafting (`book-compose` calls a sibling skill or external agent for the first-pass prose), per-paragraph entailment (`book-thesis` Layer 3), and the per-chapter editorial swarm (`book-qa` Stage 2). Every call uses a callable parameter (`llm_call=`); tests pass fake LLM functions. No live network call in any test.

## Repository layout

```
russellian-book-suite/
├── README.md                       this file
├── AGENTS.md                       autonomous-agent instruction file (Codex)
├── CLAUDE.md                       repo-level conventions for AI collaborators
├── LICENSE                         MIT
├── .gitignore
├── .github/
│   └── workflows/ci.yml            per-skill pytest jobs + smoke pipeline
├── skills/
│   ├── book-knowledge/             ledger + graph + SHACL (22 scripts, 133 tests)
│   ├── book-compose/               orchestrator + book release (19 scripts, 95 tests)
│   ├── book-qa/                    D + C defect gate (6 scripts, 41 tests)
│   ├── book-review/                7-persona definitions (5 scripts, 24 tests)
│   ├── review-conductor/           panel orchestration (6 scripts, 32 tests)
│   ├── book-thesis/                metabook reasoning (5 scripts, 16 tests)
│   └── russellian-style/           prose discipline (8 scripts, 59 tests)
├── tools/                          one-shot scripts (figure generation, hero tables,
│                                   footnote post-process, deterministic healer,
│                                   ledger synthesiser, load-bearing tagger)
├── examples/
│   └── bermuda-manual/             the proof: PDF + contracts + reports + QA
└── docs/
    ├── specs/                      design documents (v4, v5, v6, Bundle C, review-conductor)
    ├── plans/                      TDD implementation plans
    ├── operations/                 runbooks
    └── retros/                     post-release retrospectives
```

Test totals: 59 + 133 + 95 + 24 + 41 + 16 + 32 = **400 tests** across the seven skills. All green at HEAD.

## Lessons learned

Four patterns recur across the v3-to-v4.3 retrospective, the Bermuda build, and the Bundle C rollout. The full list lives in `skills/book-compose/MEMORY.md`; the load-bearing four are:

**Orphan citation tokens leak through three layers.** `[clm-…]` tokens appear in chapter drafts, in the assembled manuscript, and in the merged HTML. Stripping at any single layer leaves residue at the others. The release-gate D1 check strips at all three; skipping any one re-introduces tokens on the next build.

**HTML block break rule.** Every `</section>`, `</div>`, and `</aside>` must be followed by a blank line before any Markdown block can resume. Omitting the blank line causes the next `# Heading` to render as literal text.

**Tailwind preflight resets heading sizes.** Tailwind's preflight CSS sets `h1, h2, h3 { font-size: inherit }`. Any heading-override CSS must live after the preflight in the cascade, or every heading renders at body size. D7 catches this.

**Middle chapters degrade.** Chapters 4-8 in a ten-chapter batch return lower-quality agent output than chapters 1-3 and 9-10. The mitigation is structural: one fresh-context agent per chapter, randomised dispatch order, per-agent prompts capped at 500 words.

## Documentation

Design specs in `docs/specs/`:

- `2026-05-10-book-craft-v4-design.md` — `book-craft` skill (chapter craft, scene structure, visuals manifest, narrative-craft persona)
- `2026-05-11-book-qa-v5-design.md` — `book-qa` Generator-Verifier with Sentinel-Healer pattern
- `2026-05-11-book-thesis-v6-design.md` — `book-thesis` four-layer metabook reasoning
- `2026-05-11-bundle-c-closed-loop-ledger-design.md` — closed-loop ledger with abductive counter-claims and Bayesian propagation
- `2026-05-13-review-conductor-design.md` — multi-panel review orchestration

Implementation plans in `docs/plans/`:

- `2026-05-10-book-craft-v4-and-bermuda-regen.md` — 28-task TDD plan
- `2026-05-11-bundle-c-closed-loop-ledger.md` — 30-task TDD plan
- `2026-05-13-review-conductor-and-personas.md` — review-conductor + personas + outcomes

Operator runbooks in `docs/operations/`:

- `2026-05-12-bundle-c-runbook.md` — Phase-4 operator runbook for Bundle C end-to-end
- `codex-review-protocol.md` — autonomous whole-repo review protocol for Codex-style agents

Retrospective in `docs/retros/`:

- `2026-05-11-v3-to-v4.3-retrospective.md` — defect inventory and four root-cause patterns across the Bermuda build

## License and acknowledgements

MIT. See `LICENSE`.

Acknowledgements:

- **Bertrand Russell** — the analytic-prose standard the suite enforces
- **A. J. Ayer** — for the epigraph above ("hard to follow, cannot be misunderstood"), which sets the bar this suite aims at
- **John McPhee and Bill Bryson** — the scene-craft model behind the planned `book-craft` skill
- **Anthropic** — the Generator-Verifier and Sentinel-Healer patterns the v5 `book-qa` skill implements, and the Parallelization pattern `review-conductor` is built on
- **The Tufte CSS family** — typography reference for the v4.3 prose-furniture treatment
- **The W3C PROV-O working group** — the provenance ontology the claim ledger projects into
- **OpenStreetMap contributors (ODbL)** — base data for the parish and ferry-route maps
- **The pyShacl, rdflib, spaCy, and pyDatalog maintainers** — the validation and parsing stack
- **The Wikipedia editors of "Signs of AI writing"** — the AI-fingerprint catalog the `humanizer` skill encodes and the AI-Slop Detector persona delegates to

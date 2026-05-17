# russellian-book-suite

You give the suite a folder of sources and a chapter contract. Between input and output it fact-checks every claim against those sources, drafts the chapter, lints the prose under Bertrand Russell's analytic discipline, dispatches a multi-persona editorial panel, and refuses to ship until every gate passes. The output is a non-fiction book in Markdown, HTML, and PDF that did not roll off an AI prose mill.

<!-- lint-disable: no-hedging, active-voice reason="A.J. Ayer quote, source material" -->
> *"A book by Bertrand Russell may be hard to follow, but it cannot be misunderstood."* — A. J. Ayer
>
> The suite enforces a weaker version of the same standard: every sentence atomic, every claim sourced, every paragraph earning its place.

## For readers in a hurry

Authors want a working book, not an architecture tour. If that's you, read [Quickstart](#quickstart): it walks from a folder of PDFs to a gated chapter draft in under ten minutes, with no code changes required. By design, the pipeline enforces one configuration choice at the start: the chapter contract YAML.

Engineers who want to understand how the skills compose, what the dependency contract between them is, or how to add a linter or persona should start at [The pipeline](#the-pipeline) for the sequencing diagram, then [Repository layout](#repository-layout) for the source tree. The three-tier grouping in both sections names the same categories, so a reading of one reinforces the other.

## Reader questions

### For authors

<!-- lint-disable: listicle-abstract, listicle-anaphora reason=reader-questions index by design -->

- **Q1.** Will this write my book for me, or am I doing the work? → [The fingerprint problem](#the-fingerprint-problem) · [Quickstart](#quickstart)
- **Q2.** What's the minimum I have to provide? → [Quickstart](#quickstart)
- **Q3.** What does local-only mean — do I host my own LLM? → [Local-only constraint](#local-only-constraint)
- **Q4.** Can I use just one skill (russellian-style as a prose linter) without the full pipeline? → [The skills](#the-skills)
- **Q5.** Does this only work for technical manuals like Bermuda? Novels, grant proposals, academic papers? → [End-to-end: the Bermuda manual](#end-to-end-the-bermuda-manual)
- **Q6.** What gets shipped at the end? PDF? Editable Markdown? Both? → [The book workspace](#the-book-workspace)
- **Q7.** How do I revise after the first draft? → [Bundle C: the closed-loop ledger](#bundle-c-the-closed-loop-ledger)
- **Q8.** What happens when two sources contradict each other? → [The claim ledger and PROV-O provenance](#the-claim-ledger-and-prov-o-provenance)
- **Q9.** What does Russell voice actually mean? Is this just no AI fluff? → [Russellian prose discipline](#russellian-prose-discipline)
- **Q10.** Can I customise the linters or style rules? → [The skills](#the-skills)
- **Q11.** The Bermuda example — where is it? How do I read it? → [End-to-end: the Bermuda manual](#end-to-end-the-bermuda-manual)

### For engineers

<!-- lint-disable: listicle-abstract, listicle-anaphora reason=reader-questions index by design -->

- **Q12.** How do the skills compose? Subprocess? Python import? Message passing? → [The pipeline](#the-pipeline) · [The skills](#the-skills)
- **Q13.** Can I use `scrapling-fetch` standalone (not as part of the suite)? → [The skills](#the-skills)
- **Q14.** What's the dependency tree between skills? → [The skills](#the-skills) · [Repository layout](#repository-layout)
- **Q15.** How are skill APIs versioned? What's the compatibility story? → [The skills](#the-skills)
- **Q16.** How does the JSON/EDN bridge to booklogic work? → [The booklogic JSON/EDN boundary](#the-booklogic-jsonedn-boundary)
- **Q17.** Where do I add a new linter? A new persona? → [The skills](#the-skills)
- **Q18.** How are tests organised? Test count? Fast or slow? → [Contributing](#contributing)
- **Q19.** Is there CI? What are the gates? → [Contributing](#contributing)
- **Q20.** How does the closed-loop ledger work, concretely? → [Bundle C: the closed-loop ledger](#bundle-c-the-closed-loop-ledger)
- **Q21.** Releases — semantic versioning? → [Contributing](#contributing)
- **Q22.** PR review style? Memory feedback files? OpenSpec change folders? → [Contributing](#contributing)

### For both

<!-- lint-disable: listicle-abstract, listicle-anaphora reason=reader-questions index by design -->

- **Q23.** What's the relationship between this suite and Anthropic's Claude Code? → [For readers in a hurry](#for-readers-in-a-hurry)
- **Q24.** What other tools are like this? How is this different? → [The fingerprint problem](#the-fingerprint-problem)
- **Q25.** License — MIT? Are persona texts also MIT? → [License and acknowledgements](#license-and-acknowledgements)

## The fingerprint problem

Hosted AI prose tools leave a signature that trained readers identify in under a paragraph. Sentences average eighteen words [Hugging Face Prose Survey, 2024]. Paragraphs cluster in threes. The first adjective is "comprehensive" or "robust," and em-dashes carry connective work that a colon or period should do instead. A domain editor at a serious publisher, opening a manuscript at page one, sees the pattern before the second heading and stops trusting the facts that follow it.

Separate stages defeat the pattern. Fact ingestion, drafting, prose linting, persona review, and defect gating each run under their own discipline; each stage refuses to pass the artefact forward until its gate clears. No single prompt can enforce that discipline across five distinct tasks, which is the reason the fix is a pipeline and not a smarter system message.

## The three tiers

### Tier 1 — Acquisition + world model

Acquisition determines what the pipeline can claim. The two skills in this tier, `scrapling-fetch` and `syntopical-metabook`, work in sequence: `scrapling-fetch` traverses citation graphs from a seed set of papers and returns structured records; `syntopical-metabook` synthesises those records into a world model above the canonical claim ledger, reconciling disputed questions, mapping concepts across sources, and projecting per-chapter lenses that the drafting pipeline reads. Both share the `sibling_skills` package for version-safe API calls. The external parallel project `booklogic` handles EDN-to-JSON projection for sources that emit Clojure data; the tier communicates with it through a four-subcommand CLI, not through Python import.

### Tier 2 — Drafting pipeline

A chapter contract in, a gated release out: that is the tier's scope. Seven skills carry a chapter from raw claim ledger to published manuscript. Claim extraction and verification belong to `book-knowledge`, which writes PROV-O provenance for every assertion. The argument spine is `book-thesis` territory: it runs an entailment loop that confirms each paragraph advances a sub-argument. Drafting and final assembly run through `book-compose`, which calls `russellian-style` per section for voice discipline and `humanizer` for a final AI-pattern pass. Editorial review belongs to `book-review` (seven personas dispatched in parallel) and `review-conductor` (severity aggregation and panel gate); `book-qa` closes the tier with the D1-D8 deterministic linter, D9-D12 thesis-derived defects, and the C1-C15 per-chapter agent swarm.

### Tier 3 — Optional verification

Logical verification sits outside the default pipeline, enabled by a single flag. The skill `neurosym-forge` scaffolds a ClojureScript-plus-Rust verifier project alongside the workspace: it emits an EDN-as-atomspace intermediate representation, an `axioms.rs` hook for Z3 hard constraints, and a per-atom walk that traces each claim to an operator-supplied assertion. When the workspace `qa-config.yaml` carries `enable_verification: true`, `book-qa` reads the verifier's output as defect class D13 (claim-set-unsatisfiable). The tier is off by default because the scaffold requires a manual domain-axiom pass before verification produces useful verdicts.

## The pipeline

The pipeline is sequential within each tier: stage N reads stage N-1's outputs and writes its own, and no stage reaches backwards. Tier 1 produces the acquisition manifest and the world-model slice; Tier 2 consumes both and drives a chapter contract through claim extraction, thesis validation, drafting, persona review, and release gating; Tier 3 sits outside the default path, activated by setting `enable_verification: true` in `qa-config.yaml`.

Two side-arrows and a feed-back path close the loop. Persona findings can return a chapter to drafting before a release clears its gate. Post-build QA can write back to the claim ledger, so a defect surfaced at the release stage corrects the underlying facts for the next run. The syntopical layer has its own cycle: Gap Report appends uncovered thesis-node statements to `acquisition/pending-seeds.txt`, seeding the next Acquire run and tightening coverage before the following draft begins.

```
   sources, papers (PDFs · papers · URLs)
        │
        ▼
┌────────────────────────────────────────────┐
│   Tier 1                                   │  scrapling-fetch · syntopical-metabook
│   acquisition + world model                │  (sibling_skills loader · booklogic veto)
└────────┬───────────────────────────────────┘
         │ syntopical/lenses/*.md
         ▼
┌────────────────────────────────────────────┐
│   Tier 2                                   │  book-knowledge → book-thesis → book-compose
│   drafting pipeline                        │  ↕ russellian-style · book-review · review-conductor
│                                            │  ↓ book-qa (D1-D12 · C1-C15)
└────────┬───────────────────────────────────┘
         │ manuscript.md · manuscript.html · manuscript.pdf
         ▼
   release bundle

   ┌─ optional ─┐
   │  Tier 3    │  neurosym-forge → verifier project → D13 defects (claim-set-unsatisfiable)
   └────────────┘
```

```
book-qa  ─→  proposed-transitions.jsonl  ─→  book-knowledge.apply_writeback
review-conductor  ─→  verdict.json  ─→  book-compose (redraft if soft-gate-fail)
syntopical-metabook  ─→  syntopical/acquisition/pending-seeds.txt  ─→  next Acquire run
```

## The skills

### Tier 1 — Acquisition + world model

<!-- mini-tutorial: scrapling-fetch         (stage 3 task 3.1) -->
<!-- mini-tutorial: syntopical-metabook     (stage 3 task 3.2) -->
<!-- mini-tutorial: sibling_skills          (stage 3 task 3.3) -->
<!-- mini-tutorial: booklogic (interface)   (stage 3 task 3.4) -->

### Tier 2 — Drafting pipeline

<!-- mini-tutorial: book-knowledge          (stage 3 task 3.5) -->
<!-- mini-tutorial: book-thesis             (stage 3 task 3.6) -->
<!-- mini-tutorial: book-compose            (stage 3 task 3.7) -->
<!-- mini-tutorial: russellian-style        (stage 3 task 3.8) -->
<!-- mini-tutorial: book-review             (stage 3 task 3.9) -->
<!-- mini-tutorial: review-conductor        (stage 3 task 3.10) -->
<!-- mini-tutorial: book-qa                 (stage 3 task 3.11) -->

### Tier 3 — Optional verification

<!-- mini-tutorial: neurosym-forge          (stage 3 task 3.12) -->

## Core concepts

### The book workspace

A workspace is a directory. Eight subtrees, four append-only ledgers, one RDF graph: cloning the directory clones the book.

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
│                                        # (resolved by book-compose's wrapper at
│                                        #  scripts/persona_review_pass.py:_resolve_panel_path;
│                                        #  absent in bermuda v6, which uses the
│                                        #  shipped chapter-default.yaml)
├── thesis/                  # book-thesis owns
│   ├── <book-id>.yaml
│   └── schema.yaml
├── syntopical/              # syntopical-metabook owns; world-model layer
│   ├── config.yaml
│   ├── topic-map.md
│   ├── disputed-questions/
│   ├── concepts/
│   ├── lenses/
│   ├── reports/
│   └── acquisition/
└── reports/                 # cross-skill release reports
```

Five ownership invariants hold by skill contract and by test. `book-knowledge` is the only writer of `raw/`, `wiki/`, `claims/`, `graph/`. `book-compose` is the only writer of `chapters/` and `book/`. `book-qa` is the only writer of `qa/`. `book-thesis` is the only writer of `thesis/`. `syntopical-metabook` is the only writer of `syntopical/`, and its CI plugin enforces this by failing any test that opens a write handle on the other four subtrees. The SHACL shapes file (`shapes.ttl`) and the JSON Schema for the source manifest stay in lockstep: an off-by-one in the status enum would break both gates silently, so the test suite checks that the SHACL `sh:in` list and the JSON Schema enum match exactly.

### The claim ledger and PROV-O provenance

A claim is a statement extracted from a source: subject, predicate, object, plus a source pointer, a span, a status, and a Bayesian posterior. PROV-O is the W3C provenance ontology, which records for every fact the source, the extractor, and the timestamp. Every claim in the manuscript traces back to a specific line in a specific source because PROV-O is what makes that trace possible.

The ledger is an append-only JSONL log. Each line is either a new claim or a state transition on an existing claim. `project_graph.py` projects the claim ledger into an RDF dataset in the TriG format, a flavour of Turtle with named graphs. `validate_shacl.py` runs SHACL — the W3C Shapes Constraint Language — against `shapes.ttl` to enforce the structural rules.

The status field follows a five-state machine. New claims arrive `proposed`. `verify_claim.py` promotes a proposed claim to `verified` once it cross-checks the locator text against the source span. `detect_conflicts.py` flips a verified claim to `disputed` when it finds an antonym-pair contradiction; if a later ingest resolves the contradiction, the claim returns to `verified`. A newer source can supersede an older claim about the same triple, sending the older one to `superseded`. When post-build QA finds a verified claim that a later source contradicts, the write-back proposes a transition to `refuted`. Both `superseded` and `refuted` are terminal.

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

Every claim carries PROV-O provenance: which source, which extractor, which version, when. A SHACL violation surfaces as a warning at ingest time and as a hard fail at the release gate.

Bayesian belief propagation, added in Bundle C, reads the ledger plus the conflict log and writes a posterior probability to each claim, conditioned on its supporting and refuting evidence. Claims dropping below a configurable floor receive a `pin_low_confidence` axiom and surface in the `posterior-floor` competency query — a SPARQL query that asks which claims the ledger accepted with insufficient evidence. Bundle C also introduced abductive counter-claim generation: given a load-bearing claim, the system synthesises a plausible rival hypothesis and writes it to `counter-claims.jsonl`. Any chapter whose contract references the original claim must address the rival before its release gate passes.

### Russellian prose discipline

Russell's sentences survive a hundred years because each one stands on its own. `russellian-style` enforces a closed catalog of analytic-prose principles covering vocabulary, voice, atomicity, flow, and structure, each backed by a deterministic Python linter that reads Markdown and emits a JSON report. The catalog lives at `skills/russellian-style/references/russellian-style-guide.md`.

Russell's own prose makes the test case. Compare his sentence:

> *"The point of philosophy is to start with something so simple as not to seem worth stating, and to end with something so paradoxical that no one will believe it."*

with a typical AI-generated version of the same idea:

```
Philosophy can be understood as a discipline that leverages foundational simplicity
to navigate toward profound, often counterintuitive conclusions, ensuring readers
undergo a transformative intellectual journey.
```

The Russell version has zero hedges, zero promotional adjectives, an active verb in each clause, and a closing turn no reader anticipated. The AI version has three of the suite's hard-blocked patterns in one sentence: AI vocabulary (*leverage*, *navigate*, *transformative*), a superficial -ing analysis (*ensuring readers undergo...*), and a paragraph that does not earn its place.

| Linter | What it catches |
|---|---|
| `lint_hedges.py` | A closed registry of hedge tokens; the full list lives in `references/russellian-style-guide.md` §2.1 |
| `lint_passive_voice.py` | Passive constructions via spaCy dependency parse |
| `lint_signal_density.py` | Adjective and adverb ratio per sentence against budget |
| `lint_parallel_structure.py` | Grammatical-opening parity across bullet lists |
| `lint_sentence_rhythm.py` | Sentence-length variance and cadence defects (e.g., five consecutive sentences with word counts within three of each other) |
| `lint_listicle_abstract.py` | Abstract-noun listicles masquerading as argument — pattern-matched against `rests on N X` and `N Y` sentence frames |

#### The vitality layer

The six linters above describe the patterns to remove. Russell's prose has a second, harder dimension: motion. Concrete examples earn abstractions. Antithesis exposes a distinction. The last sentence changes pressure. The vitality layer adds five advisory linters that detect the *absence* of these moves, not the *presence* of bloat. All five are advisory in v1 — they surface in the report but do not block release. A calibration study will correlate their findings with the persona panel's verdicts before any promotion to gating.

| Linter | What it measures |
|---|---|
| `lint_burstiness.py` | Fano factor (variance-to-mean ratio) of the sentence-length distribution; a document with sentences clustered between twelve and seventeen words carries the AI signature |
| `lint_ai_vocabulary.py` | Three lexical pattern families: false-certainty markers, magic adverbs, and transition-adverb openers; augmented by the humanizer 24-pattern catalog when installed |
| `lint_concrete_instance_density.py` | spaCy NER per paragraph plus an occupational-noun matcher for Russell stock figures; fires when three or more consecutive paragraphs carry zero concrete instances |
| `lint_epistemic_precision.py` | Three-tier classification: banned-vague tokens, allowed-bounded phrases (e.g. `within five percent`), and unattributed numeric claims flagged as implicit hedges |
| `lint_paragraph_motion.py` | Paragraph-shape rubric: assertion-only, concession-turn, contrast, definition-by-pressure, question-answer, or example-inference; fires when 70%+ of a section's paragraphs are pure assertion-stack |

When a vitality linter fires, the report retrieves one paragraph reference from a fifty-paragraph index of public-domain Russell texts at `skills/russellian-style/references/russell-corpus-map.md`. The reference matches the flagged section's rhetorical mode and arrives as a citation plus a one-sentence lesson. A reader who wants the passage in front of them fetches it from Project Gutenberg using the URL and line hint in the citation.

#### Mode-keyed system prompts

`book-compose`'s drafter loads a system prompt matching the chapter contract's `prose_mode` field. Three prompts ship in `skills/russellian-style/assets/system-prompts/`:

- `technical-exposition.md` — chapters that explain, define, or argue from evidence. Default.
- `narrative-editorial.md` — narrative chapters and book introductions; room for hyperbaton, conjunction-starts, and concrete sensory anchors.
- `polemic.md` — op-ed-style work; antithesis-led, sharper turns, dry irony where compression earns it.

Each prompt declares banned-word registries, structural mandates, preferred rhetorical devices, and closing rules adapted from the PDF *"AI Prose: From Terseness to Cadence"* with Russell-specific overlays. A Russell pass produces `style-pass-report.md` with per-rule findings, a `vitality_metrics` block, and one or more corpus anchors when vitality linters fire. `book-compose` invokes the negative linters after each section draft; the vitality linters run on the assembled chapter; the `humanizer` sibling skill catches what the deterministic rules cannot. The positive doctrine companion lives at `skills/russellian-style/references/russellian-vitality-guide.md`: open with a difficulty not a system noun; concrete examples earn abstractions; permit exact uncertainty; antithesis to expose distinction; vary paragraph motion; let the last sentence change pressure.

### The thesis tree

A book has a thesis. The thesis decomposes into sub-arguments; each sub-argument cites supporting claims; every paragraph in the manuscript traces back to one sub-argument by an explicit `supports:` field. `book-thesis` owns this intent substrate and pairs it with the fact substrate that `book-knowledge` owns.

```
┌─────────────────────────────────────────────────────────────┐
│ Layer 4  Datalog consistency pass                            │
│          (Datalog = a declarative logic-programming language │
│          for deriving facts from rules; the pass runs ~15    │
│          rules over the claim graph to find transitive       │
│          contradictions like "ch-1 says A → B, ch-2 says    │
│          B → ¬A")                                            │
└────────────────────────┬────────────────────────────────────┘
┌────────────────────────▼────────────────────────────────────┐
│ Layer 3  Verifier-generator entailment loop                  │
│          (an LLM critic asks per paragraph: does this        │
│          paragraph actually entail what its `supports:` node │
│          claims? verdict ∈ {entailed, weakly-entailed,       │
│                             unrelated, contradicts})         │
└────────────────────────┬────────────────────────────────────┘
┌────────────────────────▼────────────────────────────────────┐
│ Layer 2  Thesis spine                                        │
│          YAML/RDF tree rooted at :Thesis with sub-arguments  │
│          and required-evidence slots; every paragraph carries│
│          a `supports: <node>` back-pointer                   │
└────────────────────────┬────────────────────────────────────┘
┌────────────────────────▼────────────────────────────────────┐
│ Layer 1  Claim ledger + RDF + SHACL  (book-knowledge)        │
└─────────────────────────────────────────────────────────────┘
```

Each layer contributes a defect class to `book-qa`. D9 fires when a paragraph carries no `supports:` field. D10 fires when the Datalog pass derives a transitive contradiction across chapters — a chain the per-chapter linter would miss because it only sees one chapter at a time. D11 fires when the entailment critic returns `contradicts` or `unrelated`. D12 fires when a node has no paragraphs advancing it.

D9, D10, and D11 are critical and hard-gate the release. D12 is important and surfaces in the post-build report, but the chapter can still ship with a documented waiver — though a sub-argument with nothing advancing it is a structural admission that the book has not earned its own thesis node.

### The syntopical layer

The `syntopical/` directory holds the world model the drafting pipeline reads before writing a single sentence. Six file types live there. `topic-map.md` holds one row per concept, grouped by thesis-tree top-level node, with source IDs and a count of verified claims per concept. `disputed-questions/<topic>.md` holds booklogic-produced contradiction tables — one question header per detected dispute, one row per position, with claim IDs and rewrite-witness rule IDs. `concepts/<canonical-slug>.md` holds the canonical-concept reconciliation for each concept cluster booklogic detects: the canonical slug, alternate surface forms per source, and the rules that unify them. `lenses/<chapter-id>.md` is the world-model slice `book-compose` reads when drafting a chapter — a tag-filtered projection of topics, disputed questions, and concept notes, with a YAML frontmatter block carrying the coverage score. `reports/gaps-<chapter>-<ts>.md` holds per-thesis-node coverage gaps, sorted ascending by score, with uncovered nodes flagged as seeds for the next Acquire run. `acquisition/manifest.jsonl` is the append-only audit trail of every Acquire run: seeds, candidates, triage outcomes, download results, and failures.

The syntopical layer sits above the canonical claim ledger without touching it. `book-knowledge` owns `raw/`, `claims/`, `wiki/`, `graph/`; the metabook reads all four. It never writes to any of them. The metabook's sole write target is `syntopical/`. A pytest plugin enforces this no-shadow-writes invariant on every commit by intercepting `open()` calls from metabook scripts and failing the test if any such call targets the canonical subtrees. The distinction matters: the canonical ledger records what the sources say; the syntopical layer records what the sources disagree about, how concepts map across sources, and where the thesis is undercovered. Holding the two at separate subtree boundaries lets them evolve at different rates without corrupting each other.

Triage gives each acquisition candidate a cosine-similarity score in [0, 1] against the chapter contract. Candidates at or above T_high (default 0.75) enter the auto-approve bucket. Before download, the metabook runs a booklogic reachability check against the chapter's thesis tree: any candidate whose extracted concepts have no rewrite path to any thesis node drops to manual-review, the triage file receiving the full rule trace alongside the demotion record. If `SYNTOPICAL_NO_BOOKLOGIC=1`, the metabook skips the veto and ships the embedding-only triage outcome; Synthesize falls back to `book-knowledge.detect_conflicts` for disputed questions and surface-form overlap clustering for concept reconciliation, each output carrying a "Legacy mode — booklogic disabled" banner. The two-layer design is intentional: the embedding score gives a fast topical signal, while the symbolic veto catches candidates that score high on vocabulary similarity but have no logical path to the argument the chapter is building.

### The booklogic JSON/EDN boundary

ClojureScript owns EDN for a practical reason. The Python EDN ecosystem stalled: `edn_format` has not shipped a PyPI release in over a year, `kim-edn` carries a discontinued label, and the [EDN implementations wiki](https://github.com/edn-format/edn/wiki/Implementations) lists no actively maintained Python alternative. ClojureScript ships `cljs.tools.reader.edn` and `cljs.core/pr-str` as part of the language. Booklogic is already a shadow-cljs `:node-script` project scaffolded by `neurosym-forge`. The lowest-risk seam puts EDN handling on the CLJS side and exposes a JSON projection at the cross-language boundary — a decision that is both lower-risk and idiomatic, since EDN is Clojure's native data syntax and the host language has the strongest tooling for it.

The wire format is JSON. The `booklogic` CLI takes `--io {edn|json}` (default `edn`); the metabook adapter always passes `--io json`. JSON is the bijective projection of EDN defined in spec §11.4.4: keywords keep their colon prefix as a string (`:finality` becomes `":finality"`); lists vs sets disambiguate via `{"$list": [...]}` and `{"$set": [...]}` envelopes; tagged literals use `{"$tag": "...", "$value": ...}`. Python uses stdlib `json` and `subprocess` on the consumer side. No external EDN library enters the Python venv.

Until the real booklogic CLI ships, `tests/fixtures/booklogic_stub.py` carries the wire contract. The stub accepts `--io json` only — EDN mode is deliberately out of scope, because EDN handling is the real CLI's responsibility, not the stub's. It returns empty lists for `disputed-questions` and `reconcile-concepts`, an always-reachable verdict for `reachable-from-thesis`, and a fixed `"0.0.0-stub"` version atom. Tests set `BOOKLOGIC_BIN="python booklogic_stub.py"`; the real CLI swaps in by unsetting the variable so `booklogic` on `PATH` takes over. A conformance suite of golden JSON I/O pairs at `tests/conformance/booklogic/` runs against the stub on every commit and nightly against the real CLI once it ships. The round-trip bijectivity check IF-BL-15 confirms that `edn → json → edn` is identity for every atom shape in the protocol.

### Multi-persona review

After a chapter passes Russellian linting, seven editorial personas read it. Each persona lives in `skills/book-review/personas/*.md` as a full role description: identity, lens, severity rubric, tone, and one example review. `review-conductor` loads a panel YAML, dispatches one packet per persona to a parallel sub-agent, and aggregates the severity-tagged reports into a single verdict.

| Persona | Reads for | Critical patterns | Gate |
|---|---|---|---|
| **Robert Gottlieb** | voice, cadence, AI-sloppy patterns | listicle abstracts; mechanical thesis enumeration; voice slips; 4+ consecutive same-shape sentences; paragraphs that do not earn their place | gating |
| **Lay Reader** | accessibility, vocabulary, unexplained jumps | terms used without first-appearance definition; logical jumps a generalist cannot bridge; conclusions resting on undefined concepts | advisory |
| **Domain Expert** | factual accuracy, contested-as-settled, missing nuance | claims that contradict the verified ledger; oversimplifications stated as fact; field-internal disputes elided | gating |
| **Copyeditor** | cross-chapter consistency, mechanics | terminology drift; broken cross-references; orthography splits; unbalanced quotation marks | gating |
| **Enjoyment Reader** | momentum, where the reader stops | unreadable passages; dead zones (4+ paragraphs of pure recitation); flat openings; flat endings | advisory |
| **AI-Slop Detector** | 24-pattern AI-fingerprint catalog (delegates to humanizer) | inflated symbolism; listicle abstracts; mechanical thesis enumeration; superficial -ing analyses | gating |
| **First-Time Visitor** | 30-second drive-by | first paragraph fails to say what or why; jargon density before the value prop; Quickstart looks infeasible in under ten minutes | advisory |

`review-conductor` distinguishes gating personas from advisory ones: a single `critical` finding from any gating persona returns the chapter for redraft; criticals from advisory personas surface in the report but do not block. The shipped `chapter-default.yaml` makes Gottlieb, Domain Expert, Copyeditor, and AI-Slop Detector gating; the other three advisory.

The personas do not rewrite. They flag. Revisions return to `book-compose` for the writer — human or agent — to apply. The conductor also injects Outcomes exemplars into each persona's prompt as few-shot context: seven exemplars drawn from a real seven-persona review run on an earlier draft of this README, each persona seeing one representative finding from its own rubric before reading the new chapter.

### The defect taxonomy

`book-qa` defines two parallel taxonomies. A deterministic linter or `book-thesis` catches mechanical defects (D1-D12); a per-chapter agent swarm catches editorial defects (C1-C15).

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

<!-- lint-disable: listicle-abstract, listicle-anaphora reason="defect taxonomy table, not prose" -->

| ID | Class | Source | Sev |
|---|---|---|---|
| D1 | orphan citation tokens (`[clm-…]`, bare `clm-NNNN-NNNNNN`, "Claim ledger:") | book-qa linter | crit |
| D2 | raw Markdown bleed inside HTML blocks | book-qa linter | crit |
| D3 | broken cross-references (figure paths, footnote ref/def, ToC vs heading drift) | book-qa linter | crit |
| D4 | heading hierarchy violations | book-qa linter | crit |
| D5 | count-contract failures (word, footnote, figure counts outside bands) | book-qa linter | imp |
| D6 | paragraph-length variance outside [0.4, 1.2] | book-qa linter | imp |
| D7 | CSS reset clobber (Tailwind preflight overriding heading sizes) | book-qa linter | crit |
| D8 | asset 404s | book-qa linter | crit |
| D9 | paragraph-orphan: missing `supports:` | book-thesis | crit |
| D10 | transitive-contradiction | book-thesis (Datalog) | crit |
| D11 | failed-entailment: `contradicts` or `unrelated` | book-thesis (entailment) | crit |
| D12 | unadvanced sub-argument | book-thesis | imp |

D1-D8 are the eight checks `lint_artifact.py` runs on the built artefact; these form the hard gate, and the release fails if any one returns non-zero. D9-D12 are the four classes `book-thesis` contributes. D9, D10, and D11 block release through the soft-gate path: book-qa records them on the verdict, and the operator can override with a waiver in `qa-waivers.yaml`. D12 surfaces in the post-build report. The "hard-gate: D1-D8 == 0" label on the pipeline diagram covers only the deterministic linter gate; D9-D11 add a second blocking path on top of it.

Editorial defects, per-chapter swarm of fresh-context agents:

<!-- lint-disable: listicle-abstract, listicle-anaphora reason="defect taxonomy table, not prose" -->

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

Three healer outcomes propose ledger write-backs to `book-knowledge`: `unsupported_claim` (claim lacking verified sources post-healer), `refuted_by_new_source` (claim contradicted by a source added during healing), and `addressed_rival` (counter-claim addressed in the healer patch). `propose_writeback.py` emits `claims/proposed-transitions.jsonl`; `book-knowledge.apply_writeback` is the only mutator outside the ingest path and the only consumer of that file.

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

Three Bundle C invariants make the loop safe. `propagate_belief.run` deduplicates counter-claims to the latest record per claim ID before damping — the Bayesian step that reduces the weight of repeated evidence so a single source cannot double-count; a promoted counter-claim must not damp twice. `apply_writeback` is the only mutator of `claims/` outside `book-knowledge`'s ingest path, preserving the ledger-ownership invariant. `BLOCKING_DEFEASIBLE = True` is the default: a critical defeasible-query result hard-fails the QA gate, blocking any chapter that cites a load-bearing claim with an unaddressed rival.

The Bundle C runbook (`docs/operations/2026-05-12-bundle-c-runbook.md`) walks the four phases on the Bermuda workspace.

## Quickstart

<!-- drafted in stage 2 task 2.9 -->

## End-to-end: the Bermuda manual

<!-- drafted in stage 2 task 2.10 -->

## Local-only constraint

<!-- drafted in stage 2 task 2.11 -->

## Repository layout

<!-- drafted in stage 2 task 2.12 -->

## Deep QA: how this README was made

<!-- drafted in stage 5 task 5.2 (after the full-doc sweep generates the QA report) -->

## Documentation

<!-- drafted in stage 2 task 2.13 -->

## Contributing

<!-- drafted in stage 2 task 2.13 -->

## License and acknowledgements

<!-- drafted in stage 2 task 2.14 (port existing) -->

# Syntopical Metabook — Design

- Date: 2026-05-16
- Status: Draft, pending user approval
- Author: Charles Hoskinson
- Requirements: `2026-05-16-syntopical-metabook-requirements.md` (EARS reference, authoritative for behavior)
- Related: `2026-05-08-russellian-book-forge-design.md` (existing suite)

This document is the technical-approach companion to the EARS requirements. Behavior is specified there; this file describes how the pieces fit together, why each decision was made, and how the project is broken into shippable phases.

## 1. Purpose

Build a self-curating world model that sits one layer above the existing book workspace. The metabook acquires papers from citation graphs, maintains a syntopical (cross-source) layer over the claim ledger, and projects per-chapter lenses that `book-compose` reads when drafting. The work introduces two new sibling skills and one shared package, and depends on a fourth sibling project — `booklogic` — that is being authored in parallel.

The skill name "Syntopical" follows Adler's term for the highest level of reading: comparing how different authors handle the same question. "Metabook" makes the layer explicit — it is a knowledge layer above the book under construction, not a feature of any one chapter.

## 2. Skills and shared package

Four pieces, each with one responsibility.

### 2.1 `syntopical-metabook` (new)

A workflow skill. Owns four sub-workflows — Acquire, Synthesize, Project Lens, Gap Report — and the audit manifest. Reads the workspace's `raw/`, `wiki/`, `claims/`, `graph/`, `chapters/`. Writes only `syntopical/`. Never touches the network directly; never mutates `book-knowledge`'s canonical workspace state.

### 2.2 `scrapling-fetch` (new)

The suite's sole network-touching skill. Wraps [Scrapling 0.4.8](https://github.com/D4Vinci/Scrapling) and ships four source-specific adapters (`arxiv`, `openalex`, `semantic_scholar`, `doi`) plus a streaming `download_pdf`. Rate limiting, retries, response caching, and `robots.txt` are inherited from Scrapling's native features rather than re-implemented. Every other skill in the suite imports HTTP only through this one.

### 2.3 `sibling_skills` (new shared package)

A small Python package — under twenty lines of meaningful logic — exposing `load_skill_api(name) -> module` and `IncompatibleSkillApiVersion`. Each consumer skill declares it as a venv requirement. This is the only sanctioned cross-skill import path; direct relative imports between sibling skill roots are prohibited and CI-enforced.

### 2.4 `booklogic` (sibling project, authored in parallel)

A ClojureScript-on-Node CLI built with shadow-cljs target `:node-script`, scaffolded by `neurosym-forge`. Owns symbolic rewrite rules over the EDN atomspace. Exposes four subcommands — `disputed-questions`, `reconcile-concepts`, `reachable-from-thesis`, `version` — accessible to the metabook via a JSON projection of the canonical EDN. The metabook calls booklogic only through `scripts/booklogic_adapter.py`, which uses stdlib `json` and `subprocess` and imports no EDN library.

## 3. Directory layout

### 3.1 Skills tree

```
C:\Users\charl\.claude\skills\
├── syntopical-metabook\
│   ├── SKILL.md
│   ├── skill_api.py
│   ├── scripts\
│   │   ├── acquire\
│   │   │   ├── expand_seeds.py
│   │   │   ├── rank_candidates.py
│   │   │   ├── triage.py
│   │   │   ├── download_and_ingest.py
│   │   │   └── manifest.py
│   │   ├── synthesize\
│   │   │   ├── topic_map.py
│   │   │   ├── disputed_questions.py
│   │   │   ├── concept_reconcile.py
│   │   │   └── citation_linter.py
│   │   ├── lens\
│   │   │   └── project_lens.py
│   │   ├── gap\
│   │   │   └── coverage_report.py
│   │   ├── booklogic_adapter.py
│   │   └── config.py
│   ├── references\
│   │   ├── acquire-playbook.md
│   │   ├── synthesize-playbook.md
│   │   ├── lens-and-gap-playbook.md
│   │   ├── booklogic-integration.md
│   │   └── automation-and-audit.md
│   ├── assets\
│   │   ├── triage-template.md
│   │   ├── topic-map-template.md
│   │   ├── disputed-question-template.md
│   │   └── lens-template.md
│   ├── tests\
│   │   ├── unit\
│   │   ├── integration\
│   │   ├── conformance\booklogic\        # golden JSON I/O pairs for IF-BL-1..15
│   │   └── fixtures\
│   │       ├── booklogic_stub.py
│   │       └── workspaces\<fixture>\
│   └── .venv\
│
├── scrapling-fetch\
│   ├── SKILL.md
│   ├── skill_api.py
│   ├── scripts\
│   │   ├── fetch.py
│   │   ├── download.py
│   │   ├── session.py
│   │   ├── exceptions.py
│   │   └── adapters\
│   │       ├── arxiv.py
│   │       ├── openalex.py
│   │       ├── semantic_scholar.py
│   │       └── doi.py
│   ├── references\
│   ├── tests\
│   │   ├── unit\
│   │   ├── live\
│   │   └── fixtures\cassettes\
│   └── .venv\
│
└── sibling_skills\
    ├── __init__.py
    ├── loader.py
    └── tests\
```

### 3.2 Workspace tree (per book)

```
<book-workspace-root>\                    (book-knowledge owns the layout)
├── raw\                                  read by metabook; written only by book-knowledge
├── wiki\                                 read-only to metabook
├── claims\                               read-only to metabook
├── graph\                                read-only to metabook
├── chapters\<id>\contract.yaml           read-only to metabook
└── syntopical\                           sole write target of syntopical-metabook
    ├── config.yaml
    ├── topic-map.md
    ├── disputed-questions\<topic-slug>.md
    ├── concepts\<canonical-slug>.md
    ├── lenses\<chapter-id>.md
    ├── reports\gaps-<chapter-id>-<ts>.md
    └── acquisition\
        ├── incoming\
        ├── triage-<run-id>.md
        ├── manifest.jsonl
        ├── pending-seeds.txt
        └── HALT
```

`syntopical/` is the contract between metabook outputs and downstream consumers (`book-compose`, `book-thesis`). The layout is fixed because `book-compose` parses lens files by path and section order.

## 4. Data flow

### 4.1 Acquire

```
                    ┌─────────────────┐
   seeds  ─────────▶│  expand_seeds   │  scrapling-fetch.openalex.references/citations
                    └────────┬────────┘
                             │ List[PaperRef]
                             ▼
                    ┌─────────────────┐
                    │ rank_candidates │  local sentence-transformer; reads chapter contract
                    └────────┬────────┘
                             │ scored List[PaperRef]
                             ▼
                    ┌─────────────────┐
                    │     triage      │  partitions by T_high/T_low; writes triage-<run>.md
                    └────────┬────────┘
                             │ auto-approve subset
                             ▼
                    ┌─────────────────────────────┐
                    │  booklogic_adapter.         │  IF-BL-6 reachability verdict
                    │  reachable_from_thesis      │  (skipped if SYNTOPICAL_NO_BOOKLOGIC=1)
                    └────────┬────────────────────┘
                             │ veto demotions applied; capped at max_auto_per_run
                             ▼
                    ┌─────────────────────────────┐
                    │  download_and_ingest        │  scrapling-fetch.download_pdf → incoming/
                    │   ├─ is_source_ingested?    │  IF-BK-3 dedup
                    │   └─ book-knowledge.ingest_pdf │  IF-BK-1 canonical ingest
                    └────────┬────────────────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │    manifest     │  append JSON line to manifest.jsonl
                    └─────────────────┘
```

Embedding-based ranking gives an ordinal score for triage thresholds. The booklogic veto is a categorical post-rank check — it can demote a high-scoring candidate that is off-thesis under the symbolic rule set, but it cannot promote a low-scoring one. The two layers are complementary and never compete for the same decision.

### 4.2 Synthesize / Lens / Gap

```
       claim ledger ── book-knowledge.query_claims ──┐
       concept pages ── book-knowledge.list_concepts ┤
       thesis tree ── book-thesis.read_thesis_tree ──┤
       booklogic_adapter.disputed_questions ─────────┤
       booklogic_adapter.reconcile_concepts ─────────┤
                                                     ▼
                                          ┌──────────────────┐
                                          │   Synthesize     │  writes topic-map.md,
                                          │                  │  disputed-questions/*,
                                          │                  │  concepts/*
                                          └────────┬─────────┘
                                                   │
                                                   ▼
                                          ┌──────────────────┐
                                          │  Project Lens    │  one per chapter
                                          │                  │  writes lenses/<C>.md
                                          └────────┬─────────┘
                                                   │
                                                   ▼
                                          ┌──────────────────┐
                                          │   Gap Report     │  writes reports/gaps-<C>-<ts>.md
                                          │                  │  optionally appends pending-seeds.txt
                                          └──────────────────┘
                  citation linter: every prose paragraph must link to a claim-ID, wiki slug, or rule-ID
                  russellian-style: lint_fragment on each prose paragraph (IF-RS-1)
```

If booklogic is unavailable (env var or stub returning empty), `REQ-SYN-6` triggers the legacy heuristics — book-knowledge's `detect_conflicts` for disputed questions, surface-form overlap for concept reconciliation — with a `Legacy mode` banner on the affected artifacts.

## 5. Booklogic integration

### 5.1 Why ClojureScript owns EDN

The Python EDN ecosystem (`edn_format`, `kim-edn`, `dreid/edn`) is stale. ClojureScript ships first-class EDN handling via `cljs.tools.reader.edn` and `cljs.core/pr-str`. Booklogic is already CLJS+Rust, scaffolded by `neurosym-forge`. The lowest-risk seam is to let CLJS handle every EDN byte and expose JSON at the cross-language boundary.

### 5.2 Wire format

- The booklogic CLI takes a `--io {edn|json}` flag (default `edn`). The metabook always passes `--io json`.
- JSON is the bijective projection of EDN defined in §11.4.4 of the requirements doc. Keywords keep their colon prefix as a string; lists vs sets disambiguate via `{"$list": ...}` and `{"$set": ...}` envelopes; tagged literals use `{"$tag": ..., "$value": ...}`.
- The bijection is testable: round-tripping `json→edn→json` is the identity (IF-BL-15).
- Python uses stdlib `json` and `subprocess`. No external dependency required for cross-language I/O.

### 5.3 Adapter

`syntopical-metabook/scripts/booklogic_adapter.py` wraps subprocess invocation, JSON (de)serialization, and dataclass conversion. Four public functions: `disputed_questions`, `reconcile_concepts`, `reachable_from_thesis`, `version`. Resolves the binary through `BOOKLOGIC_BIN` so the dev stub substitutes by changing one env var.

### 5.4 Dev stub

`tests/fixtures/booklogic_stub.py` ships as part of the metabook. It speaks only JSON (the format the Python adapter uses) and returns empty results for disputed-questions and reconcile-concepts, plus an always-reachable verdict for the post-rank veto. It is deliberately not an EDN implementation — that is booklogic's job. The stub exists so the metabook pipeline can be developed and tested before booklogic v0.1 lands.

### 5.5 Conformance suite

`tests/conformance/booklogic/` holds golden JSON input/output pairs covering every IF-BL-3 through IF-BL-15. The same suite runs against the stub on every commit (must pass — defines the lower bound) and against the real booklogic CLI nightly via `pytest -m live` (initially marked `xfail` until the CLI ships; flipped to required once it does). This is the seam that lets the two projects ship asynchronously.

## 6. Skill-to-skill ABI

### 6.1 `skill_api.py`

Every skill exposes its public surface in one module: `<skill-root>/skill_api.py`. Declares `__all__: list[str]` and `API_VERSION: tuple[int, int]`. All public functions are fully type-hinted, accept the workspace root as an explicit argument where state is required, and return primitives, `pathlib.Path`, or `@dataclass` objects. Untyped dicts as return types are prohibited.

### 6.2 `sibling_skills.load_skill_api`

```python
from sibling_skills import load_skill_api
bk = load_skill_api("book-knowledge")            # raises IncompatibleSkillApiVersion on mismatch
claims = bk.query_claims(filter_=..., workspace_root=...)
```

The loader resolves the skill by name through a small registry (initially: walk `~/.claude/skills/<name>/skill_api.py`), validates `API_VERSION` major against the caller's expected major, and returns the module. CI lints reject any other cross-skill import path.

### 6.3 Version compatibility

Skill APIs start at `(0, 1)`. Major bumps signal breaking changes; the loader refuses to bridge across mismatched majors. Minor bumps add functions without removing or changing signatures; consumers expressing a minimum minor can require a newer field set.

## 7. Configuration

### 7.1 Workspace `syntopical/config.yaml`

```yaml
acquire:
  citation_depth: 2
  triage:
    t_high: 0.75
    t_low: 0.55
    max_auto_per_run: 25
  embedding:
    model: sentence-transformers/all-MiniLM-L6-v2
ranking:
  query_template: |
    {chapter.title}

    {chapter.summary}

    {thesis_statements}
booklogic:
  enabled: true
  ruleset_dir: null        # null = use BOOKLOGIC_RULESET_DIR or default
```

### 7.2 Env vars

| Variable | Effect |
|---|---|
| `BOOKLOGIC_BIN` | Path to booklogic binary or to the dev stub. |
| `BOOKLOGIC_RULESET_DIR` | Override the active rules directory (IF-BL-14). |
| `SCRAPLING_OFFLINE=1` | Force scrapling-fetch into cache-only mode (REQ-SF-5). |
| `SYNTOPICAL_NO_BOOKLOGIC=1` | Skip booklogic veto and use legacy synthesis heuristics (REQ-VETO-2, REQ-SYN-6). |

## 8. Test strategy

### 8.1 Layers

- **Unit**, hermetic, every commit. Pure-function tests of ranking math, threshold partitioning, manifest shape, lens schema, coverage scoring, exception translation, JSON projection bijection, EDN/JSON conformance.
- **Integration**, hermetic, every commit. End-to-end Acquire → Synthesize → Lens → Gap against a fixture workspace with three pre-built fake PDFs. Scrapling's development-mode cache replay covers all network reads; booklogic stub covers the symbolic path.
- **Live**, `pytest -m live`, nightly. Hits real arxiv, OpenAlex, Semantic Scholar HTML pages for a stable set of arxiv IDs (catches site-layout drift). Runs the booklogic conformance suite against the real CLI to catch EDN/JSON projection drift.

### 8.2 Cross-cutting discipline

- **No-shadow-writes**: a pytest plugin watches every `open()` of paths under `raw/`, `claims/`, `wiki/`, `graph/` and fails any write originating from a metabook script (NFR-5).
- **No-direct-http**: an import-linter rule rejects `requests`, `httpx`, `urllib3`, `aiohttp`, `playwright` from any skill other than `scrapling-fetch` (NFR-4).
- **API-version compatibility**: every consumer of `load_skill_api` declares its expected major; the test suite injects a mismatched version and asserts `IncompatibleSkillApiVersion` fires.
- **Idempotence**: Synthesize is run twice on a frozen workspace with a frozen booklogic ruleset checksum; the second run must produce zero file diffs (REQ-SYN-4).
- **Citation coverage**: every prose paragraph the metabook writes must link to a claim-ID, wiki slug, or booklogic rule-ID. A linter walks every artifact and fails on uncited prose (REQ-SYN-5).

### 8.3 Hermetic vs live

The two are deliberately separate. Hermetic tests give fast, deterministic CI signal. Live tests give an early warning when an upstream changes shape — arxiv tweaks markup, Semantic Scholar throttles harder, booklogic renames a rule. A failure in live without a failure in hermetic localises the problem to the boundary.

## 9. Error handling

### 9.1 Acquire failures are per-candidate

Network failures, schema-violation responses from scrapling-fetch adapters, booklogic timeouts, dedup-mismatch from book-knowledge — all of these are logged into `manifest.jsonl` and the loop continues. A run never aborts because one paper failed.

### 9.2 Booklogic failures are typed

The Python adapter catches the four subprocess exit codes (1 schema violation, 2 rule failure, 3 internal, 4 timeout, 5 api-version mismatch) and translates them into named Python exceptions. Synthesize is allowed to fall through to legacy mode (REQ-SYN-6) if `SYNTOPICAL_NO_BOOKLOGIC=1`; otherwise booklogic failures are surfaced. The Acquire veto is silently skipped on booklogic timeout (a candidate cannot be vetoed if we cannot get a verdict in time) — but the skip is recorded in the manifest.

### 9.3 Workspace invariants are loud

The metabook never silently mutates `raw/`, `claims/`, `wiki/`, or `graph/`. If a script ever attempts such a write, the test plugin fails the run; in production the script raises rather than swallowing. Synthesize/Lens/Gap fail loud on missing inputs (absent chapter contract, missing thesis tree) rather than emitting partial artifacts.

## 10. OpenSpec integration

### 10.1 Repo and root

[OpenSpec](https://github.com/Fission-AI/OpenSpec) v1.3.1 is initialized at `C:\Users\charl\russellian-book-suite\openspec\`. The directory is tracked in the GitHub repo `CharlesHoskinson/russellian-book-suite`. The first implementation task in Phase 1 is `git clone` followed by `openspec init`.

### 10.2 Change folder

```
openspec\changes\add-syntopical-metabook\
├── proposal.md
├── design.md                        # this document, mirrored
├── tasks.md                         # sprint-organized checklist (writing-plans authors this)
└── specs\
    ├── syntopical-metabook\spec.md  # ADDED: REQ-ACQ-*, REQ-VETO-*, REQ-SYN-*, REQ-LENS-*, REQ-GAP-*, NFR-1..3, NFR-5..6, NFR-8
    ├── scrapling-fetch\spec.md      # ADDED: REQ-SF-*, NFR-4, NFR-7
    ├── skill-abi\spec.md            # ADDED: REQ-ABI-*
    ├── booklogic\spec.md            # ADDED: IF-BL-*
    ├── book-knowledge\spec.md       # ADDED: IF-BK-1..4 (new public surface)
    ├── book-thesis\spec.md          # ADDED: IF-BT-1
    ├── russellian-style\spec.md     # ADDED: IF-RS-1
    └── book-compose\spec.md         # ADDED: IF-BC-1 (lens reader contract)
```

### 10.3 EARS → OpenSpec translation

Each EARS requirement in the requirements doc transcribes mechanically into one `### Requirement: <Name>` block plus one or more `#### Scenario:` blocks under the relevant domain spec. The translation rules and a worked example for REQ-ACQ-3 live in §10.2 and §10.3 of the requirements doc. Requirement-IDs (e.g. `REQ-ACQ-1`) do not appear in OpenSpec spec bodies — OpenSpec names requirements by their `Requirement:` title — but they are preserved in `design.md` and `tasks.md` for traceability.

### 10.4 Phase plan

Nine phases, in strict dependency order:

| Phase | Theme |
|---|---|
| 1 | Foundation + ABI (`sibling_skills`, CI lints, `skill_api.py` scaffolds) |
| 2 | `scrapling-fetch` core (fetch, sessions, retries, offline, exceptions) |
| 3 | `scrapling-fetch` adapters (arxiv, OpenAlex, Semantic Scholar, DOI, download_pdf) |
| 4 | Existing-skill `skill_api.py` shims (book-knowledge, book-thesis, russellian-style) |
| 5 | Booklogic adapter + dev stub + conformance suite |
| 6 | Metabook Acquire + Veto |
| 7 | Metabook Synthesize |
| 8 | Metabook Lens + Gap |
| 9 | Book-compose integration + release validation |

Phases 6, 7, 8 ship against the booklogic dev stub. The nightly live job catches integration drift once the real CLI is on `PATH`.

## 11. Operational notes

### 11.1 First run on a new workspace

1. Initialize the book workspace with `book-knowledge` (existing flow).
2. Add `syntopical/config.yaml` with project-specific thresholds.
3. Invoke `syntopical-metabook` Acquire with seed papers — usually three to five papers the author already knows are core to a chapter.
4. Review the audit manifest. The first run typically produces tens of new ingests.
5. Run Synthesize. The disputed-question and concept-reconciliation pages appear (empty if booklogic is not yet available — that is expected).
6. Project a lens for the first chapter. Review.

### 11.2 Steady-state per chapter

For each chapter drafted by `book-compose`: Acquire with the chapter contract as seed → Synthesize delta → Project Lens → Gap Report → if `--feed-acquire`, the next Acquire run is seeded by the gap report. A two-pass cycle (initial Acquire, draft, gap-driven Acquire, redraft) is the expected steady-state.

### 11.3 Out of scope

- Drafting chapter prose. Owned by `book-compose`.
- Style linting. Owned by `russellian-style`, called by `book-compose`.
- Persona review. Owned by `book-review`.
- Post-build mechanical QA. Owned by `book-qa`.
- Thesis tree maintenance. Owned by `book-thesis`.

The metabook is the *world model* upstream of these. It does not draft and does not lint prose; it provides the structured ground truth those skills draw on.

## 12. Defaults

| Knob | Default | Where |
|---|---|---|
| Citation traversal depth | 2 | `syntopical/config.yaml` |
| Triage `T_high` | 0.75 | `syntopical/config.yaml` |
| Triage `T_low` | 0.55 | `syntopical/config.yaml` |
| `max_auto_per_run` | 25 | `syntopical/config.yaml` |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` | pinned in metabook venv |
| Citation source priority | OpenAlex first, Semantic Scholar fallback | hardcoded in adapter |
| Wire format with booklogic | JSON (`--io json`) | metabook adapter |
| Scrapling rate limit | per-host `download_delay >= 1s` | scrapling-fetch session |
| Cache TTL | 7 days | scrapling-fetch session |

All defaults are tunable in `syntopical/config.yaml` without code changes. The embedding model is pinned in the venv to satisfy reproducibility (NFR-3); changing it requires a workspace migration and a fresh ranking pass.

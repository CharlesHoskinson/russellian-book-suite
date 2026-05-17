# russellian-book-suite

You give the suite a folder of sources and a chapter contract. Between input and output it fact-checks every claim against those sources, drafts the chapter, lints the prose under Bertrand Russell's analytic discipline, dispatches a multi-persona editorial panel, and refuses to ship until every gate passes. The output is a non-fiction book in Markdown, HTML, and PDF that did not roll off an AI prose mill.

```text
"A book by Bertrand Russell may be hard to follow, but it cannot be misunderstood." — A. J. Ayer
```

The suite enforces a weaker version of the same standard: every sentence atomic, every claim sourced, every paragraph earning its place.

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

Hosted AI prose tools leave a recognisable signature that any trained reader identifies within the first paragraph. Sentences average eighteen words [Hugging Face Prose Survey, 2024]. Paragraphs cluster in threes. The first adjective is "comprehensive" or "robust," and em-dashes carry connective work that a colon or period should do instead. A domain editor at a serious publisher, opening a manuscript at page one, sees the pattern before the second heading and stops trusting the facts that follow it.

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

<details>
<summary><strong>scrapling-fetch</strong> — sole network boundary of the suite</summary>

**What it does.** Every outbound HTTP call in the suite passes through this skill. It wraps Scrapling 0.4.8 — a Python scraping library — and exposes four source-specific adapters: `arxiv` parses abstract pages, `openalex` queries the OpenAlex JSON API, `semantic_scholar` falls back to HTML when the API is unavailable, and `doi` resolves redirect chains to canonical URLs. On top of those adapters sits a streaming `download_pdf` function that checks content-type before writing to disk and verifies the completed file's sha256 against the value returned in the response header. Three fetch modes ship: `plain` for standard sessions, `stealth` for StealthySession (fingerprint-randomised), and `dynamic` for DynamicSession (Playwright-backed). Session construction wires per-host rate limits and politeness defaults; nothing scatters them across caller code. The skill does not fetch data for callers outside the suite; the import-linter contract in CI enforces this as a hard rule.

**Inputs / outputs.**

The skill takes a URL or arXiv ID, a fetch mode, and optional per-call rate-limit overrides. It returns either a `PaperRecord` dataclass, a PDF written to a caller-specified path, or a typed exception from the hierarchy `FetchFailed | RateLimitExceeded | BlockedRequest | NotAPdf | OfflineMiss | ArxivIdNotFound`. Responses land in an on-disk cache keyed by URL; the cache directory is configurable. Setting `SCRAPLING_OFFLINE=1` forces cache-only mode: the skill opens no network socket.

**When to invoke.** Use this skill whenever the acquisition pipeline needs a URL fetched and the caller is not `scrapling-fetch` itself — arXiv abstract pages, arXiv PDFs by ID, OpenAlex metadata or reference lookups, and DOI resolution to final landing URLs all route through here.

**When NOT to invoke.** This skill is dedicated infrastructure, not a generic scraper; callers outside the book suite should not route through it. For local files or workspace directories, use `pathlib` directly. With `SCRAPLING_OFFLINE=1` active and the resource absent from cache, the skill raises `OfflineMiss`; seed the cache first or clear the env var before calling.

**Trigger phrases.** "fetch a URL", "get this paper's metadata", "download this PDF", "what does this paper cite", "what cites this paper", "scrape this URL", "traverse a citation graph".

**Example walkthrough.**

```bash
# From a skill that has sibling_skills installed in its venv:
from sibling_skills import load_skill_api
sf = load_skill_api("scrapling-fetch", expected_major=0)
record = sf.fetch_arxiv("2310.04673")
print(record.title)
# → "Lossless LLM Compression via Quantization-Aware Pruning"
```

`fetch_arxiv` dispatches to the `arxiv` adapter, which parses the abstract page at `arxiv.org/abs/2310.04673`, returns a `PaperRecord` with `title`, `authors`, `abstract`, and `year` populated, and writes the raw HTML to the on-disk cache. The skill downloads no PDF unless the caller also calls `download_pdf`. Rate limiting fires automatically; a second call to the same URL within the TTL window returns from cache without opening a socket.

**Where to dive deeper.**
- `skills/scrapling-fetch/SKILL.md`
- `skills/scrapling-fetch/tests/unit/` — fixture-driven adapter tests covering all four adapters, the download path, and the exception hierarchy.

</details>
<details>
<summary><strong>syntopical-metabook</strong> — world model above the canonical book workspace</summary>

**What it does.** The metabook sits one layer above the claim ledger without touching it. It acquires papers through citation-graph traversal, ranks and triages candidates against the chapter contract, and downloads those that pass both an embedding-similarity threshold and a booklogic reachability veto. From the acquired corpus it builds a syntopical layer: a topic map that groups concepts by thesis-tree node, disputed-question tables produced by booklogic's symbolic rewrite rules, and canonical-concept reconciliation files that track how different sources name the same idea. Per-chapter lenses slice that world model to exactly what the drafter needs before writing a single sentence. Gap reports close the cycle by scoring per-thesis-node coverage and appending uncovered nodes to `acquisition/pending-seeds.txt`, seeding the next Acquire run automatically. Four sub-workflows — **Acquire**, **Synthesize**, **Project Lens**, **Gap Report** — execute in that order; Acquire can run alone on a new seed set without triggering the others.

The skill never touches the network directly. `scrapling-fetch` handles every HTTP call; the metabook reaches it through `sibling_skills.load_skill_api`. EDN symbolic reasoning stays on the ClojureScript side; the metabook calls booklogic through `scripts/booklogic_adapter.py` over a JSON subprocess wire. With `SYNTOPICAL_NO_BOOKLOGIC=1` active, the Synthesize workflow skips the veto step and falls back to `book-knowledge.detect_conflicts` for disputed questions, plus surface-form overlap for concept reconciliation; each affected artefact carries a `Legacy mode — booklogic disabled` banner.

**Inputs / outputs.**

The metabook reads `raw/`, `wiki/`, `claims/`, `graph/`, and `chapters/<id>/contract.yaml` — all read-only; it writes exclusively to `syntopical/`. A pytest plugin intercepts `open()` calls from metabook scripts and fails any test where a write targets the canonical subtrees. The acquisition audit trail lives in `syntopical/acquisition/manifest.jsonl`, which is append-only and records every run, every candidate, and every outcome. Two env vars: `SYNTOPICAL_NO_BOOKLOGIC=1` for legacy heuristics, `BOOKLOGIC_BIN` to override the binary path.

**When to invoke.** The natural-language triggers are phrases like "acquire papers for chapter X" (Acquire sub-workflow), "synthesize the metabook" (Synthesize, producing topic-map, disputed-question tables, and concept files), "project a lens for chapter Y" (writes `syntopical/lenses/ch-Y.md`), and "show coverage gaps in chapter Z" (Gap Report). Invoke it before drafting any chapter whose lens file does not yet exist.

**When NOT to invoke.** When `book-compose` needs to draft and the lens already exists, open `syntopical/lenses/` directly — the metabook is not a gatekeeper for the drafting step. PDF ingestion into the canonical workspace belongs to `book-knowledge`. Symbolic rewrite queries against the EDN atomspace go through booklogic's CLI; the metabook adapter is a convenience wrapper, not a general-purpose symbolic shell.

**Trigger phrases.** "acquire papers for chapter X", "synthesize the metabook", "project a lens for chapter Y", "show coverage gaps in chapter Z", "self-curating world model", "citation-graph traversal".

**Example walkthrough.**

```bash
# User intent: "set up the world model for chapter 3 and project a lens"
# Assumes contract.yaml exists at chapters/ch-03/contract.yaml

from sibling_skills import load_skill_api
sm = load_skill_api("syntopical-metabook", expected_major=0)
workspace = "/path/to/my-book"

sm.acquire(workspace, chapter_id="ch-03")
# → syntopical/acquisition/manifest.jsonl updated; PDFs in syntopical/acquisition/incoming/

sm.synthesize(workspace)
# → syntopical/topic-map.md, disputed-questions/*.md, concepts/*.md

sm.project_lens(workspace, chapter_id="ch-03")
# → syntopical/lenses/ch-03.md
```

`book-compose` reads `syntopical/lenses/ch-03.md` before drafting. The lens is a tag-filtered slice of the topic map carrying a YAML frontmatter block with the coverage score. If the score is below the contract threshold, Gap Report will have already written the uncovered nodes to `pending-seeds.txt`; the next Acquire run picks them up automatically.

**Where to dive deeper.**
- `skills/syntopical-metabook/SKILL.md`
- `docs/superpowers/specs/2026-05-16-syntopical-metabook-design.md` and `2026-05-16-syntopical-metabook-requirements.md`
- `skills/syntopical-metabook/tests/integration/` — integration tests covering the four sub-workflows end-to-end.

</details>
<details>
<summary><strong>sibling_skills</strong> — shared cross-skill loader package</summary>

**What it does.** `sibling_skills` is a Python package, not a Claude Code skill. It does one thing: load another skill's `skill_api.py` module by name and validate the major version before any skill code executes. The package is under twenty lines of meaningful logic — `loader.py` plus an `__init__.py` re-export — yet it is the only sanctioned import path between skills in the suite. CI enforces this: a PR that imports a sibling skill root directly fails the import-linter gate before tests run. The consequence of that discipline is that a skill's internal refactor cannot silently break a caller; the version check catches the mismatch at load time, not at the call site.

Each skill declares `API_VERSION: tuple[int, int]` in its `skill_api.py`. When the major component mismatches the caller's `expected_major` argument, the loader raises `IncompatibleSkillApiVersion` before returning the module. This loader enforces the cross-skill ABI contract (REQ-ABI-1 through REQ-ABI-5, specified in `openspec/changes/add-syntopical-metabook/specs/skill-abi/spec.md`); nothing else does. Skills root defaults to `~/.claude/skills/`; set `SIBLING_SKILLS_ROOT` to override, which is what the test suite does to point at fixture skill trees.

**Inputs / outputs.**

The package takes a skill name string and an optional `expected_major` integer. It returns the imported `skill_api` module ready to call, or raises one of two exceptions: `IncompatibleSkillApiVersion` on major-version mismatch or absent `API_VERSION`, and `FileNotFoundError` when no `skill_api.py` exists at the resolved path.

**When to invoke.** Any skill in the suite that needs to call a function from another skill's public surface should use this loader — including new skills calling `scrapling-fetch`, `book-knowledge`, or `book-thesis`, and any caller that needs to gate on a specific major version of a dependency skill.

**When NOT to invoke.** Utilities within the same skill's `scripts/` directory take a relative import, not this loader. The `booklogic` interface goes through `scripts/booklogic_adapter.py` over a subprocess wire, bypassing `sibling_skills` entirely. General Python module loading outside the suite's skill boundary has nothing to do with this package.

**Trigger phrases.** Not a routable Claude Code skill — no trigger phrases. Import it directly in Python: `from sibling_skills import load_skill_api`.

**Example walkthrough.**

```python
from sibling_skills import load_skill_api, IncompatibleSkillApiVersion

bk = load_skill_api("book-knowledge", expected_major=0)
claims = bk.query_claims({"state": "verified"}, workspace_root)
```

`book-compose` calls this when it needs `book-knowledge.query_claims`. The loader walks `~/.claude/skills/book-knowledge/skill_api.py`, imports it, reads `API_VERSION`, and confirms the major is `0`. If `book-knowledge` later ships `API_VERSION = (1, 0)` — a breaking change — the same call raises `IncompatibleSkillApiVersion("Skill 'book-knowledge' API_VERSION is (1, 0); expected major 0")` before any skill code runs. The caller then either adapts to the new surface or pins `expected_major=0` and waits for a compatibility shim.

**Where to dive deeper.**
- `sibling_skills/loader.py` — the whole package is small enough to read in two minutes.
- `sibling_skills/tests/test_loader.py` — unit tests for version-mismatch paths and env-var override.
- `openspec/changes/add-syntopical-metabook/specs/skill-abi/spec.md` — the ABI contract (REQ-ABI-1..5) this loader enforces.

</details>
<details>
<summary><strong>booklogic</strong> — CLJS-on-Node reasoning CLI: interface contract for the metabook</summary>

**What it does.** `booklogic` is not a Claude Code skill in this repository. It is an external ClojureScript-on-Node CLI authored in parallel, discoverable on PATH after its documented install step. The metabook calls it over stdin/stdout on a JSON wire; it never imports it. Given a corpus of verified claims or concept atoms, `booklogic` applies its local EDN ruleset to detect disputed questions, reconcile concept clusters, test candidate reachability against a thesis tree, and report its own version. The Python side consumes JSON only. EDN is the canonical on-disk form; the JSON wire format is a deterministic, bijective projection, and `scripts/booklogic_adapter.py` never sees raw EDN. Requirement IF-BL-15 is the round-trip guarantee: `edn → json → edn` is the identity function for every atom shape in the protocol. The four subcommands partition the reasoning surface: `disputed-questions` finds claim conflicts, `reconcile-concepts` clusters alternates under a canonical slug, `reachable-from-thesis` tests whether a candidate paragraph has any rewrite path to any thesis node, and `version` emits a provenance atom for CI sanity checks. Each output atom carries `:ruleset-checksum` — the sha256 of all `rules/*.edn` files in lexicographic order — so consumers can detect silent ruleset drift.

**Inputs / outputs.** The wire is JSON. Stdin carries the JSON-projected EDN input atom; pass `--io json` explicitly. Stdout returns the output atom plus three provenance keys on every non-error response: `:booklogic-version`, `:ruleset-checksum`, and `:produced-at`. Stderr receives an `:error` atom whose `:code` determines the exit code — 0 success, 1 schema violation, 2 rule failure, 3 internal, 4 timeout, 5 api-version mismatch. Set `BOOKLOGIC_BIN` to override the executable path.

**When to invoke.** Use `booklogic` when the metabook needs disputed-question detection (`disputed-questions`), concept reconciliation across sources (`reconcile-concepts`), thesis-reachability vetting for a candidate paragraph (`reachable-from-thesis`), or a wire-format version atom for CI health-check (`version`).

**When NOT to invoke.** Skip `booklogic` for Python-side claim ingestion or ledger writes — that is `book-knowledge`. Skip it for sentence-grain prose checks — that is `russellian-style`. Skip it for any task that requires network I/O: `booklogic` makes zero network calls by contract; all evaluation runs locally against `rules/*.edn`.

**Trigger phrases.** `booklogic`, `disputed questions`, `reachable from thesis`.

**Example walkthrough.** The stub ships before the real CLI exists. Set `BOOKLOGIC_BIN="python booklogic_stub.py"` in the test environment and run:

```bash
BOOKLOGIC_BIN="python skills/syntopical-metabook/tests/fixtures/booklogic_stub.py" \
  python -c "
import sys; sys.path.insert(0, 'skills/syntopical-metabook/scripts')
import booklogic_adapter as bl
v = bl.version()
print(v)
"
# BooklogicVersion(booklogic_version='0.0.0-stub', api_version=(0, 1), ruleset_checksum='stub-no-rules')
```

The stub returns `"0.0.0-stub"` and the adapter strips the JSON quote layer, handing back a typed Python dataclass. To swap to the real CLI: `unset BOOKLOGIC_BIN`. A conformance suite at `tests/conformance/booklogic/` runs golden JSON I/O pairs against the stub on every commit and nightly against the real binary once it ships.

**Where to dive deeper.**
- `openspec/changes/add-syntopical-metabook/specs/booklogic/spec.md` — the 15-requirement interface contract.
- `skills/syntopical-metabook/scripts/booklogic_adapter.py` — consumer-side adapter.
- `skills/syntopical-metabook/tests/conformance/booklogic/` — golden I/O suite.
- `skills/syntopical-metabook/tests/fixtures/booklogic_stub.py` — dev stub.

</details>

### Tier 2 — Drafting pipeline

<details>
<summary><strong>book-knowledge</strong> — epistemic compiler: claim ingestion, provenance, RDF graph</summary>

**What it does.** The claim ledger starts here. `book-knowledge` reads local PDF and Markdown sources, extracts claims with PROV-O provenance, projects them into an RDF dataset, validates the graph with SHACL, and runs competency queries that confirm the knowledge base answers the questions the book contract requires. The ledger appends; nothing deletes. A claim enters `claims/ledger.jsonl` once, then its state advances through `proposed → verified → disputed → superseded` and stops there. Belief propagation runs a Bayesian damping pass over the provenance DAG so a single source cannot double-count by appearing twice in the witness chain. The metabook reads this ledger as ground truth; no other skill writes to it. Three services sit below the public API: `verify_claim.py` promotes a proposed claim to verified by checking the locator text against the raw source; `detect_conflicts.py` runs antonym-pair contradiction detection across the ledger; `project_graph.py` and `validate_shacl.py` together write and check the TriG dataset that downstream skills treat as authoritative. Every SPARQL competency query ships in `assets/` alongside the SHACL shapes, so the entire gate configuration travels with the skill.

**Inputs / outputs.** Four public functions cross the skill boundary (IF-BK-1..4): `ingest_pdf(path, workspace)` adds a source and returns an `IngestResult`; `query_claims(filter, workspace)` returns filtered `ClaimRecord` objects from the ledger; `is_source_ingested(sha256, workspace)` checks deduplication by content hash; `list_concepts(workspace)` returns every `ConceptRef` from `wiki/concepts/`. The skill owns `raw/`, `wiki/`, `claims/`, and `graph/` exclusively — no sibling writes there.

**When to invoke.** `book-knowledge` handles source ingestion, claim queries, RDF graph revalidation, and the Bayesian belief pass. Invoke it at each of those four checkpoints.

**When NOT to invoke.** Skip `book-knowledge` for chapter drafting — that is `book-compose`. Skip it for sentence-grain voice checks — that is `russellian-style`. Skip it for casual document Q&A that needs no persistent claim record; reach the source directly.

**Trigger phrases.** `ingest this paper`, `extract claims`, `validate claims`, `audit the knowledge graph`.

**Example walkthrough.** Ingest a PDF, count the claims it produces, and run a competency query:

```python
from pathlib import Path
from skill_api import ingest_pdf, query_claims, ClaimFilter

ws = Path("my-book-workspace")
result = ingest_pdf(Path("sources/nakamoto2008.pdf"), ws)
print(result.status, result.claims_extracted)
# ingested  47

verified = query_claims(ClaimFilter(state="verified"), ws)
print(len(verified), "verified claims in ledger")
# 312 verified claims in ledger
```

`ingest_pdf` computes a sha256 before writing anything; a second call with the same file returns `already_present` without touching the ledger. The release gate blocks on SHACL conformance and zero `unsupported_claims` before any chapter ships.

**Where to dive deeper.**
- `skills/book-knowledge/SKILL.md` — component inventory, workspace layout, release-gate criteria.
- `skills/book-knowledge/skill_api.py` — IF-BK-1..4 public surface.
- `skills/book-knowledge/references/` — ingest, wiki, claims, graph audit, and provenance playbooks.
- `skills/book-knowledge/tests/` — pytest suite covering every script.

</details>
<details>
<summary><strong>book-thesis</strong> — argument spine: thesis tree, entailment loop, Datalog consistency</summary>

**What it does.** Every paragraph in a manuscript must earn its place. `book-thesis` owns the intent substrate — the thesis tree, paragraph back-pointers to thesis nodes, a per-paragraph entailment loop, and a Datalog consistency pass that derives transitive contradictions across chapter-level claim triples. It sits as Layer 2–4 above `book-knowledge`'s Layer 1: Layer 2 holds the YAML/RDF thesis spine; Layer 3 dispatches an LLM critic per paragraph that returns `entailed | weakly-entailed | unrelated | contradicts`; Layer 4 runs Datalog rules against the full claim set to surface contradictions that span chapter boundaries. Four defect classes flow from here into `book-qa`: D9 orphan-paragraph, D10 transitive-contradiction, D11 failed-entailment, D12 unadvanced sub-argument. `book-thesis` does not ingest claims or draft prose; those belong elsewhere.

**Inputs / outputs.** One public function (IF-BT-1): `read_thesis_tree(chapter_id, workspace) → ThesisTree`. It reads `chapters/<chapter_id>/thesis-tree.yaml` and returns a `ThesisTree` dataclass holding a list of `ThesisNode` objects, each carrying `node_id`, `statement`, `tags`, `required_evidence_kind`, and `parent_id`. The function raises `ThesisNotDefined` when no tree file exists for the requested chapter. Each chapter owns its own `thesis-tree.yaml`; the tree is the interface between intent and evidence.

**When to invoke.** `book-thesis` owns argument structure, not facts. Invoke it to compile a new thesis spec into RDF triples, lint paragraph back-pointers against the tree, run the Datalog consistency pass after a ledger update, generate exemplar packs for the drafter, or prepare entailment payloads for an LLM critic.

**When NOT to invoke.** Skip `book-thesis` for claim ingestion or ledger writes — that is `book-knowledge`. Skip it for sentence-grain linting (hedges, passive voice) — that is `russellian-style`. Skip it for chapter orchestration — that is `book-compose`. And skip it for qualitative editorial review by personas — that is `book-review`.

**Trigger phrases.** `thesis tree`, `entailment loop`, `orphan paragraph`, `transitive contradiction`.

**Example walkthrough.** Write a minimal thesis tree for chapter `ch-01` with two nodes, then run the entailment pass:

```yaml
# chapters/ch-01/thesis-tree.yaml
chapter_id: ch-01
nodes:
  - node_id: root
    statement: "Bitcoin's fixed supply creates disinflationary pressure over long horizons."
    tags: [monetary-policy]
    required_evidence_kind: empirical
    parent_id: null
  - node_id: supply-cap
    statement: "The 21M cap is enforced by consensus rules, not policy."
    tags: [protocol]
    required_evidence_kind: formal
    parent_id: root
```

```bash
python scripts/compile_thesis.py my-workspace ch-01
python scripts/lint_supports.py my-workspace v0.1
```

`compile_thesis.py` writes RDF triples into the book-knowledge graph; `lint_supports.py` flags any paragraph whose `supports:` field names a node that doesn't exist or whose chain doesn't reach `:Thesis`. A detected D11 failure — an LLM critic returning `contradicts` — blocks release through the soft-gate path in `book-qa`.

**Where to dive deeper.**
- `skills/book-thesis/SKILL.md` — architecture diagram, layer inventory, usage commands.
- `skills/book-thesis/skill_api.py` — IF-BT-1 public surface.
- `skills/book-thesis/tests/` — fixture cases for compile, lint, Datalog, and entailment dispatch.
- `skills/book-qa/` — D9–D12 defect definitions and gate configuration.

</details>
<details>
<summary><strong>book-compose</strong> — chapter orchestrator: contract in, gated release out</summary>

**What it does.** A chapter contract enters; a gated release bundle exits. `book-compose` drives nine pipeline stages: it loads `chapters/contracts/<chapter_id>.yaml`, runs a pre-flight SHACL check, slices verified claims from the ledger, produces a section outline for user approval, drafts each section by loading a `russellian-style` system prompt, applies the `humanizer` sibling for a final AI-pattern pass, dispatches the seven-persona editorial panel, assembles a chapter bundle, and — on explicit request — builds the book-level release: `manuscript.md`, a React/Tailwind HTML browser, and a Playwright PDF. No stage reaches backwards; stage N reads only what stage N-1 wrote.

**Inputs / outputs.** The skill reads `chapters/contracts/<chapter_id>.yaml` for the chapter contract, `syntopical/lenses/<chapter_id>.md` for the world-model slice, and `claims/ledger.jsonl` for the verified claim set. It writes drafts and review artefacts under `chapters/drafts/<chapter_id>/`, release bundles under `chapters/releases/<chapter_id>-<version>/`, and book-level releases under `book/releases/<version>/`. The public API function `read_lens(chapter_id, workspace)` — defined in `skill_api.py` as interface contract IF-BC-1 — reads and validates the lens file, enforcing the section order `## Topics` → `## Disputed Questions` → `## Concept Reconciliation` → `## Coverage`; any deviation raises `LensContractViolation`.

**When to invoke.** Use when the user says "draft chapter ch-NN", "build release bundle for ch-NN", or "build the book release". These cover the three distinct pipeline entry points: chapter drafting (stages 1–7), chapter bundle assembly (stage 8), and full book release (stage 9).

**When NOT to invoke.** Skip `book-compose` for source ingestion or claim extraction — that is `book-knowledge`. Skip it for sentence-grain prose rewrites on text that isn't inside the chapter pipeline — use `russellian-style` directly.

**Trigger phrases.** The frontmatter lists: `"draft chapter X"`, `"compile chapter from contract"`, `"build release bundle for chapter X"`, `"render chapter to PDF"`, `"build the book release"`, `"publish the book"`.

**Example walkthrough.** The user says "draft chapter ch-01". `book-compose` loads `chapters/contracts/ch-01.yaml`, verifies claims against the SHACL shapes, queries the ledger for the ch-01 claim slice, and presents a section outline. On approval it drafts each section: loads the `technical-exposition` system prompt via `system_prompt_loader.load("technical-exposition")`, generates a first-pass draft, calls `russellian-style` for voice discipline, calls `humanizer` for AI-pattern removal. Section drafting complete, `review-conductor` dispatches the seven-persona panel and aggregates findings into `verdict.json`. If `verdict.verdict != "soft-gate-fail"`, the bundle lands at `chapters/drafts/ch-01/draft.md`. Any gating persona — Gottlieb, Domain Expert, Copyeditor, or AI-Slop Detector — can raise a critical finding that sends the chapter back to drafting.

**Where to dive deeper.**
- `skills/book-compose/SKILL.md`
- `skills/book-compose/skill_api.py` — IF-BC-1 (`read_lens`)
- `skills/book-compose/tests/`

</details>
<details>
<summary><strong>russellian-style</strong> — generation contract first, checker second</summary>

**What it does.** The skill is a generation contract first, a checker second. The contract runs before prose exists: three mode-keyed system prompts live at `assets/system-prompts/technical-exposition.md`, `assets/system-prompts/narrative-editorial.md`, and `assets/system-prompts/polemic.md`. `system_prompt_loader.load(mode)` reads the matching file and returns it as the LLM system message, conditioning the writer to the Russellian structural mandates before drafting begins. Those mandates hold four requirements: vary sentence length deliberately, with at least one sentence under ten words and at least one exceeding twenty-five per screen; favour compound-complex sentences with short declarative beats; open paragraphs with the conclusion the paragraph will earn; end paragraphs by changing argumentative pressure, not by restating what the paragraph just said. The checker side — twelve linter modules emitting seventeen rule names — audits prose already in existence. Six modules emit gating rules: `lint_hedges.py` covering `no-hedging`, `lint_passive_voice.py` covering `active-voice`, `lint_signal_density.py` covering `signal-density`, `lint_parallel_structure.py` covering `parallel-structure`, `lint_listicle_abstract.py` covering `listicle-abstract` and `listicle-anaphora`, and `lint_sentence_rhythm.py` covering `rhythm-uniform-length` and `rhythm-repeated-opening`. Six modules emit advisory rules: `lint_ai_staccato.py` covering `staccato-paragraph-run` and three variant patterns, `lint_ai_vocabulary.py` covering `ai-vocabulary`, `lint_burstiness.py` covering `burstiness`, `lint_concrete_instance_density.py` covering `concrete-instance-density`, `lint_epistemic_precision.py` covering `epistemic-precision`, and `lint_paragraph_motion.py` covering `paragraph-motion`. The `humanizer` sibling skill extends the checker with a 24-pattern Wikipedia catalog of AI writing tells when installed.

**Inputs / outputs.** On the generation side, the skill loads one of three system-prompt Markdown files from `assets/system-prompts/` and returns its text as a string for the caller to pass to the LLM. On the linting side, it accepts a text fragment and a list of rule names, writes the text to a temporary Markdown file, runs the requested linters, and returns a list of `LintIssue` dataclasses — one per violation — carrying linter name, line, column, and a human-readable message. The output artefact for a full chapter pass is `style-pass-report.md`, which records per-rule findings, a `vitality_metrics` block, and corpus anchors when vitality linters fire.

**When to invoke.** Use when the user says "apply Russell style", "run the linters on chapter 3", or "Russell pass on draft.md". Also use when `book-compose` loads the system prompt at drafting time and calls `lint_fragment` after each section.

**When NOT to invoke.** Skip `russellian-style` for marketing copy, fiction, launch announcements, or any genre where accuracy is not the primary contract. Skip it for source ingestion, claim ledger writes, or chapter orchestration — those belong to other skills.

**Trigger phrases.** The frontmatter lists: `"apply Russell style"`, `"rewrite in Russellian style"`, `"tighten this prose"`, `"remove hedging"`, `"atomize this paragraph"`, `"Russell pass on this draft"`.

**Example walkthrough.** Load the generation contract, draft a paragraph, lint it, fix it, re-lint.

```python
from skills.russellian_style.scripts.system_prompt_loader import load
from skills.russellian_style.skill_api import lint_fragment, LintIssue

prompt = load("technical-exposition")   # returns the system-prompt string
draft = "Hedges weaken a sentence in ways that passive prose also does."
issues: list[LintIssue] = lint_fragment(draft, linters=["no-hedging", "active-voice"])
# issues[0] => LintIssue(linter="active-voice", line=1, col=1, message=...)
fixed = "Hedges and passive constructions both erode signal density."
assert lint_fragment(fixed, linters=["no-hedging", "active-voice"]) == []
```

The first draft triggers `active-voice` on the passive construction; the rewrite commits to a direct claim and clears both rules. The same cycle — run, read, rewrite, re-run — applies to all six gating rules until zero violations remain.

**Where to dive deeper.**
- `skills/russellian-style/SKILL.md`
- `skills/russellian-style/assets/system-prompts/` — three mode-keyed generation contracts
- `skills/russellian-style/assets/russell-corpus/` — 50-paragraph Russell corpus index
- `skills/russellian-style/tests/`

</details>
<details>
<summary><strong>book-review</strong> — seven editorial personas, dispatched in parallel, severity-gated</summary>

**What it does.** A chapter draft that clears style linting still fails if a real editor would stop trusting it. `book-review` closes that gap: seven editorial personas read the draft in parallel, each from a distinct critical lens, and return severity-tagged findings that either block release or surface as advisory. The gate is binary — `persona_critical_count == 0` to ship — but the evidence is qualitative: each persona's full Markdown report lives under `chapters/drafts/<chapter_id>/reviews/`, and the conductor's aggregation produces `persona-review.md` with a verdict table, substring-deduplicated findings, and final counts by severity.

**Inputs / outputs.** The skill reads a chapter draft from `chapters/drafts/<chapter_id>/draft.md` and the chapter contract from `chapters/contracts/<chapter_id>.yaml`. It constructs one dispatch packet per persona, issues parallel Task subagent calls, and writes individual reports to `chapters/drafts/<chapter_id>/reviews/<persona>.md`. The aggregation script merges those into `chapters/drafts/<chapter_id>/persona-review.md` and writes `verdict.json` with the `persona_critical_count` field that `book-compose` reads at stage 7.

**When to invoke.** Use when the user says "review chapter X with personas", "Gottlieb pass on this chapter", or "is this chapter ready for review". Single-persona dispatch is a valid entry point for targeted feedback.

**When NOT to invoke.** Skip `book-review` for source ingestion, prose-grain linting, or chapter drafting — each belongs to a different skill. Skip it for qualitative review of prose that lives outside the book pipeline.

**Trigger phrases.** The frontmatter lists: `"review chapter X with personas"`, `"Gottlieb pass on this chapter"`, `"run the editorial reviews"`, `"what would Gottlieb say about this draft"`, `"soft-gate this chapter"`.

**Example walkthrough.** The user says "Gottlieb pass on chapter ch-03". `book-review` loads `chapters/drafts/ch-03/draft.md`, constructs a Gottlieb dispatch packet (persona role description, severity rubric, draft text, contract metadata), issues a single Task subagent call, and writes findings to `chapters/drafts/ch-03/reviews/gottlieb.md`. The report tags each finding by severity: `critical` blocks release, while `important` and `minor` are advisory. If Gottlieb marks any finding `critical` — cadence collapse, AI-sloppy pattern density above threshold, or a structural defect the rubric defines as blocking — `persona_critical_count` increments and the chapter's release gate fails. The writer reads `gottlieb.md`, revises through `book-compose`, and re-runs the pass.

**Where to dive deeper.**
- `skills/book-review/SKILL.md`
- `skills/book-review/personas/` — one Markdown role file per persona
- `skills/book-review/tests/`

</details>
<details>
<summary><strong>review-conductor</strong> — multi-persona panel orchestrator: YAML config in, verdict out</summary>

**What it does.** `book-review` dispatches one persona at a time; `review-conductor` dispatches them all at once. The conductor loads a panel YAML (`panels/<panel-id>.yaml`), constructs one dispatch packet per persona via `dispatch_panel.py`, fires every packet in parallel through the caller-provided dispatcher, and aggregates the results through per-persona severity gates. Two artefacts exit every run: `panel-review.md`, the human-readable aggregate with substring-deduplicated findings, and `verdict.json`, the machine-readable record with per-persona critical counts and a top-level `decision` field — either `ship` or `redraft`. If `verdict.json.decision == "redraft"`, `book-compose` returns the chapter to its drafting stage.

**Inputs / outputs.** The conductor reads a panel YAML from `panels/`, a chapter draft from `chapters/drafts/<chapter_id>/draft.md`, and Outcomes exemplars from `book-review/references/outcomes/` to inject as few-shot context into each persona packet. It calls `book-review`'s `dispatch_review` primitive for each persona, then writes `chapters/drafts/<chapter_id>/panel-review.md` and `chapters/drafts/<chapter_id>/verdict.json`. The verdict carries `per_persona_counts`, `decision`, and `soft_gate_triggered`.

**When to invoke.** Use when the user says "run the panel", "review chapter with the conductor", or "soft-gate this chapter via review-conductor". The conductor is the right entry point whenever the full panel — not a single persona — needs to run.

**When NOT to invoke.** Skip `review-conductor` for a single-persona targeted pass — invoke `book-review` directly. Skip it for source ingestion, prose linting, or chapter drafting.

**Trigger phrases.** The frontmatter lists: `"run the panel"`, `"review chapter with the conductor"`, `"run the seven-persona panel"`, `"soft-gate this chapter via review-conductor"`.

**Example walkthrough.** A panel YAML declares five personas: Gottlieb and Domain Expert are `gating`; Lay Reader, Enjoyment Reader, and First-Time Visitor are `advisory`. The conductor fires all five in parallel.

```bash
python -c "
from review_conductor.conductor import run_panel
from pathlib import Path
verdict = run_panel(
    workspace=Path('workspaces/bermuda'),
    chapter_id='ch-02',
    panel_path=Path('panels/five-persona.yaml'),
    dispatcher=None,
)
print(verdict['decision'], verdict['soft_gate_triggered'])
"
```

Expected output: `redraft True`. Gottlieb found one `critical` AI-sloppy pattern; `soft_gate_rule: any_critical_from_gating` fires. `verdict.json` records `per_persona_counts.gottlieb.critical = 1`; `panel-review.md` surfaces the finding with a deduplicated excerpt. The three advisory personas logged findings that appear in the report but did not trigger the gate.

**Where to dive deeper.**
- `skills/review-conductor/SKILL.md`
- `skills/review-conductor/tests/` — 29 tests: schema validation, panel loading, dispatch construction, aggregation

</details>
<details>
<summary><strong>book-qa</strong> — post-build defect gate: D1-D13, C1-C15, Sentinel-Healer loop</summary>

**What it does.** Every artefact that `book-compose.build_book` produces enters this gate before it ships. The gate runs four stages. `lint_artifact.py` applies deterministic mechanical rules: eight D-class rules covering orphan citation tokens, raw Markdown bleed inside HTML, broken cross-references, heading hierarchy violations, count-contract failures, paragraph-length variance, CSS reset clobber, and asset 404s. `dispatch_chapter_qa.py` fires a swarm of fresh-context agents — ten per chapter — each checking one chapter against all fifteen C-class editorial dimensions, returning JSON tickets only. The sentinel script aggregates D and C tickets into a single defect ledger, classifying each as critical, important, or minor. `healer.py` opens an isolated-context agent per defect class, proposes a minimal patch, and hands it back to the sentinel for verification; the sentinel confirms the original failing check now passes before writing the change. Three iterations is the maximum.

**Inputs / outputs.** The skill reads a built artefact (the release directory that `build_book` writes), `checklists/house-style.yaml`, and an optional `qa-waivers.yaml` at the workspace root. Book-thesis contributes D9-D12 inputs: `qa/supports-defects.json` (D9, D12), `qa/datalog-defects.json` (D10), and `qa/entailment-results.json` (D11). With `enable_verification: true` set in `qa-config.yaml`, the gate reads `qa/verification-defects.json` for D13. Outputs are `qa/lint-findings.json` (D-class), `qa/swarm-findings.json` (C-class), `claims/proposed-transitions.jsonl`, and a `qa/ledger-writeback-<version>.md` summary for `book-knowledge`.

**When to invoke.** Use after `book-compose.build_book` completes and before the release bundle ships. The `--qa` flag on `book-compose` skips this gate during iteration; remove the flag for release builds.

**When NOT to invoke.** Skip `book-qa` for anything before `build_book` has produced an artefact — source ingestion, chapter drafting, and prose linting all run earlier in the pipeline. Skip it for qualitative persona judgement; that is `book-review`.

**Trigger phrases.** The frontmatter lists `"run book-qa"` and `"gate this release"`. Invocation is automatic from `build_book`; direct invocation is for re-running a failed gate without rebuilding.

**Example walkthrough.** The Bermuda manuscript v0.4 enters the gate.

```bash
python scripts/lint_artifact.py workspaces/bermuda v0.4
python scripts/dispatch_chapter_qa.py workspaces/bermuda v0.4
python scripts/sentinel.py workspaces/bermuda
python scripts/healer.py workspaces/bermuda --max-iterations 3
```

Two defects surface: D6 (paragraph-length variance at 1.31, outside the [0.4, 1.2] band in chapter 3) and C7 (scene anchoring absent in chapter 5's opening section). For each, the healer opens a fresh-context agent: D6 splits the overlong paragraph at a natural clause boundary; C7 inserts a two-sentence locating phrase. Sentinel re-runs both checks, confirms zero violations, and writes the patched artefact. Release exits clean.

**Where to dive deeper.**
- `skills/book-qa/SKILL.md`
- `skills/book-qa/references/` — defect taxonomy detail and waiver format
- `skills/book-qa/tests/` — `test_lint_artifact.py`, `test_sentinel_writeback.py`, `test_propose_writeback.py`, `test_transition_rules.py`

</details>

### Tier 3 — Optional verification

<details>
<summary><strong>neurosym-forge</strong> — Tier 3 scaffolder: ClojureScript + Rust neurosymbolic verifier projects</summary>

**What it does.** `neurosym-forge` is a scaffolder, not a verifier. It produces ClojureScript + Rust project skeletons under MeTTa-style atomspace conventions, then provides helpers for extending those skeletons — adding sorts, rewrite rules, and grounded atoms — without touching the host skill or the book pipeline directly. The scaffolded project does the actual verification: `shadow-cljs` and `cargo` run the ClojureScript and Rust layers; the skill only authors the inputs those tools consume. Three linters ship with the scaffold: `lint_atomspace.py` checks that every atom carries a `:sort` annotation with no unbound variables; `lint_rewrite_coverage.py` checks that every rewrite rule has a fixture test; `render_call_graph.py` draws the Claude/CLJS/Rust phase boundary as an ASCII diagram. The skill encodes MeTTa idioms — `=`, `:`, `!`, `match`, `superpose`, and grounded-atom wiring — as authoring conventions documented in `references/metta-idioms.md`.

**Inputs / outputs.** `scaffold_project.py` takes a workspace name and an optional `--book-knowledge-bridge` flag; with the flag set, it accepts `claims/ledger.jsonl` from `book-knowledge` as Phase-1 input and seeds the atomspace from the claim ledger. Without it, the scaffold is a blank slate. `add_sort.py`, `add_rewrite_rule.py`, and `add_grounded_atom.py` each extend an existing scaffold in-place. The verifier emits `qa/verification-defects.json`. When the workspace sets `enable_verification: true` in `qa-config.yaml`, `book-qa` reads that file and raises D13 (claim-set-unsatisfiable) on any unsatisfied constraint.

**When to invoke.** Use when a workspace needs logical verification beyond what prose linters catch — Z3 constraints on date arithmetic, e-graph rewriting for algebraic claims, or Datalog consistency over cross-chapter assertions. Off by default; explicit opt-in per workspace.

**When NOT to invoke.** Skip `neurosym-forge` for prose reviews, claim ingestion, or chapter drafting. Skip it for any workspace where the prose linters and persona reviews are sufficient — most manuscripts do not need this tier.

**Trigger phrases.** The frontmatter lists: `"scaffold a neurosymbolic project"`, `"verify these claims with Z3"`, `"add a rewrite rule"`, `"ground this predicate in Rust"`, `"extend the atomspace IR"`.

**Example walkthrough.** Scaffold a verifier for the Bermuda workspace, add a `Date` sort and a date-ordering rule, then run.

```bash
python -m scripts.scaffold_project --workspace workspaces/bermuda --out verifiers/bermuda
python -m scripts.add_sort --project verifiers/bermuda --sort Date --doc "calendar date"
python -m scripts.add_rewrite_rule \
  --project verifiers/bermuda \
  --rule "(= (date-before? (Date ?d1) (Date ?d2)) (< ?d1 ?d2))"
```

Override `verifiers/bermuda/src/axioms.rs` with the Z3 date-arithmetic constraints, then run the scaffolded project:

```bash
cd verifiers/bermuda && npm run build && node dist/verify.js
```

`qa/verification-defects.json` exits with zero entries; `book-qa` reads it and D13 stays silent. A contradictory date claim would produce one D13 entry and block the release gate.

**Where to dive deeper.**
- `skills/neurosym-forge/SKILL.md`
- `skills/neurosym-forge/references/` — MeTTa idioms, atomspace EDN IR, grounded-atom wiring
- `docs/concepts/neurosym-forge.md` — scope, layers, and integration boundary
- `docs/operations/neurosym-forge-runbook.md` — operator workflow for the verifier side-channel
- `verifiers/bermuda/` — reference implementation

</details>

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

Two audiences use this suite differently. Authors care about workspace initialisation, source ingestion, and the chapter pipeline. Engineers care about venv setup, test invocation, and the architectural sections that explain why the pieces fit as they do.

### Authors

Install the skills first. There is no install script; the canonical method copies each skill directory into Claude Code's skill root and builds a venv in place.

1. **Clone the repo and check out `main`.**

```bash
git clone https://github.com/CharlesHoskinson/russellian-book-suite.git
cd russellian-book-suite
```

2. **Install the skills into Claude Code.** Copy one skill at a time or run the batch loop for all seven core skills. `neurosym-forge` is optional; omit it unless you need the verifier track.

```bash
# single skill
cp -r skills/book-qa ~/.claude/skills/book-qa
cd ~/.claude/skills/book-qa
python -m venv .venv
.venv/Scripts/python -m pip install -e ".[dev]"

# all seven core skills (bash)
for skill in russellian-style book-knowledge book-compose book-review review-conductor book-qa book-thesis; do
  cp -r skills/$skill ~/.claude/skills/$skill
done

# PowerShell equivalent
foreach ($skill in 'russellian-style','book-knowledge','book-compose','book-review','review-conductor','book-qa','book-thesis') {
  Copy-Item -Recurse "skills\$skill" "$env:USERPROFILE\.claude\skills\$skill"
}
```

   After installing `russellian-style` and `book-compose`, download the spaCy model once — the linters won't run without it.

```bash
.venv/Scripts/python -m spacy download en_core_web_sm
```

   Skills are now discoverable in a Claude Code session by slash name: `/book-knowledge`, `/book-compose`, and so on.

3. **Initialise a book workspace with `book-knowledge`.** Run from the `book-knowledge` skill directory.

```bash
.venv/Scripts/python -m scripts.workspace init /path/to/my-book
```

4. **Drop source PDFs into `<workspace>/raw/`.** Ingest each source and project the claim graph.

```bash
.venv/Scripts/python -m scripts.ingest_pdf source.pdf /path/to/my-book
.venv/Scripts/python -m scripts.verify_claim /path/to/my-book
.venv/Scripts/python -m scripts.project_graph /path/to/my-book
.venv/Scripts/python -m scripts.validate_shacl /path/to/my-book
```

5. **Write a chapter contract at `<workspace>/chapters/contracts/<id>.yaml`.** The contract names the topic, the claims that must appear, the constraints that must not be violated, and the evidence thresholds. A minimal example:

```yaml
chapter_id: ch-01
title: "The reinsurance engine"
prose_mode: technical-exposition
must_include_claims: [claim-001, claim-003]
must_not_do:
  - "Do not assert GDP figures without a source token"
evidence_required: 2
acceptance_threshold: 0.80
```

   `prose_mode` accepts `technical-exposition`, `narrative-editorial`, or `polemic`; it defaults to `technical-exposition`. `book-compose` loads the matching system prompt from `russellian-style/assets/system-prompts/` and passes it to the LLM as the system message.

6. **Run the drafting pipeline end-to-end through `book-compose`.** In a Claude Code session:

   `"draft chapter ch-01"`

   The orchestrator runs stages 1–7 and writes `chapters/drafts/ch-01/draft.md`. When all chapters pass their review gate, build the release:

   `"build the book release v1.0"`

7. **Open the release bundle under `<workspace>/book/releases/`.** The bundle contains `manuscript.md`, `manuscript.html` (React/Tailwind browser), `manuscript.pdf` (Playwright render), and `claims-bibliography.jsonl`.

### Engineers

The suite has no monorepo venv. Each skill owns its own venv; `sibling_skills` is a shared dependency installed into whichever venv needs it.

1. **Clone the repo.**

```bash
git clone https://github.com/CharlesHoskinson/russellian-book-suite.git
cd russellian-book-suite
```

2. **Set up the venv for the skill you need.** Each skill lives at `skills/<name>/`. Build its venv, install the skill in editable mode, then install `sibling_skills` into the same venv.

```bash
cd skills/book-knowledge
python -m venv .venv
.venv/Scripts/python.exe -m pip install -e ".[test]"
.venv/Scripts/python.exe -m pip install -e ../../sibling_skills
```

3. **Run the skill's test suite.**

```bash
.venv/Scripts/python.exe -m pytest tests/ -q
```

4. **Read [The pipeline](#the-pipeline) and [The three tiers](#the-three-tiers) for architecture.** Those two sections explain the ownership boundaries and data-flow contracts that the tests enforce.

5. **Read [Contributing](#contributing) before opening a PR.** The lint gate is mandatory; a PR that introduces gating violations will not be merged regardless of test status.

## End-to-end: the Bermuda manual

The Bermuda workspace predates Tier 1. The metabook tier (Tier 1) adds an upstream acquisition stage — `scrapling-fetch` harvesting sources, `syntopical-metabook` building the world-model layer — which the Bermuda workspace did not exercise. What follows is a Tier 2 + Tier 3 end-to-end: ledger synthesis, chapter drafting, QA gate, and release. A separate follow-up example will demonstrate the acquisition stage once a workspace exists that runs `scrapling-fetch` and `syntopical-metabook` from a clean start.

This pipeline produced a ten-chapter, ~28,000-word non-fiction book on contemporary Bermuda. The workspace at `examples/bermuda-manual/` is the proof.

What "proof" means here requires a qualification. `tools/synthesize_bermuda_ledger.py` built the Bermuda ledger from a thesis YAML, not from an ingested PDF corpus. The thesis describes the argument structure; the tool produced a matching claim ledger, which the rest of the pipeline then drafted, reviewed, and shipped end-to-end. This validates the drafting → review → release chain on a real-shaped workload. `book-knowledge`'s own test suite exercises the PDF-ingest path, but no full Bermuda-scale build has yet run from PDF sources. A future release will rebuild the workspace from primary sources — Bermuda Government statistics, Department of Tourism reports, Association of Bermuda Insurers and Reinsurers (ABIR) data.

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
│       ├── manuscript.md              # 10 chapters, ~28,000 words
│       ├── manuscript.html            # React/Tailwind browser
│       ├── manuscript.pdf             # Playwright render (cover/TOC only in v6.0.0; full-body PDF render is a known limitation)
│       ├── claims-bibliography.jsonl  # one record per claim cited in the release
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

`shacl_conforms: true` confirms the projected RDF graph validates against `shapes.ttl`. `competency_clean: true` means all eight competency queries return zero rows — no orphan wiki pages, no unsupported claims, no transitive contradictions, no posterior-floor violations, no open rebuttals against load-bearing claims. The distinction matters: a graph that passes structure checks can still fail a competency query if the manuscript cites a claim without provenance support. Both gates must pass.

## Local-only constraint

No paid APIs. No telemetry. The suite routes every outbound HTTP call through `scrapling-fetch`: it is the single network boundary. Only `scrapling-fetch` imports `requests`, `httpx`, `urllib3`, `aiohttp`, or `playwright`; no other skill does. The `ci/.import-linter` contract enforces the rule; a PR that imports any of those libraries from a skill other than `scrapling-fetch` fails CI before tests run. Everything else in the pipeline runs local.

The booklogic CLI runs locally, against EDN rules on disk. There is no remote service. The metabook talks to it over stdin/stdout on a JSON wire.

The full dependency stack:

- **Python**: pdfplumber (PDF ingest), markdown-it-py (Markdown ingest), rdflib (graph), pyshacl (SHACL validation), jsonschema (claim validation), spaCy (dependency parsing for Russellian linters), pypdf (PDF post-processing), matplotlib (figures), geopandas (maps), great_tables and plottable (tables), css-inline (HTML rendering), pyDatalog (the consistency pass in book-thesis).
- **Node**: `@mermaid-js/mermaid-cli` for Mermaid diagrams, called from Playwright's bundled Chromium.
- **Playwright**: HTML → PDF rendering with Chromium.

Image sources for visuals come from OpenStreetMap (under the Open Database Licence), Wikimedia Commons (Creative Commons licences), and programmatic charts generated from the claim ledger. No image fetch happens at runtime; assets ship with the workspace.

LLM calls happen at three points in the pipeline: section drafting (`book-compose` calls a sibling skill or external agent for the first-pass prose), per-paragraph entailment (`book-thesis` Layer 3), and the per-chapter editorial swarm (`book-qa` Stage 2). Every call uses a callable parameter (`llm_call=`); tests pass fake LLM functions. No live network call runs in any test.

## Repository layout

One skill per directory under `skills/`; each is self-contained with its own `SKILL.md`, `scripts/`, `tests/`, `.venv/` (gitignored), and `pyproject.toml`. Cross-cutting infrastructure — shared Python loader, CI contracts, documentation tooling — lives at the repo root or in top-level sibling directories, not inside any individual skill.

```
russellian-book-suite/
├── README.md
├── LICENSE
├── ci/
│   ├── .import-linter
│   ├── lint_no_shadow_writes.py
│   └── test_*.py
├── docs/
│   ├── concepts/
│   ├── operations/
│   └── qa/                       # NEW (Stage 5 of README refactor)
├── examples/
│   └── bermuda-manual/
├── openspec/
│   └── changes/
│       └── archive/<date>-add-syntopical-metabook/
├── sibling_skills/               # NEW — shared loader package
├── skills/
│   ├── book-compose/
│   ├── book-knowledge/
│   ├── book-qa/
│   ├── book-review/
│   ├── book-thesis/
│   ├── neurosym-forge/
│   ├── review-conductor/
│   ├── russellian-style/
│   ├── scrapling-fetch/          # NEW — Tier 1
│   └── syntopical-metabook/      # NEW — Tier 1
├── tools/
│   └── lint_readme.py            # NEW — README lint helper
└── verifiers/
    └── bermuda/
```

Read-only boundaries between skills are strict. The metabook accesses scrapling-fetch through `sibling_skills.load_skill_api`, not by direct import; it reads, never writes, the fetch skill's surface. `book-compose` reads only the chapter-lens files that the metabook deposits under `syntopical/lenses/`; the metabook's internals are opaque to it. The workspace directories `raw/`, `claims/`, `wiki/`, and `graph/` are open to every skill for reading, but `book-knowledge` alone writes them.

## Deep QA: how this README was made

Russellian-style's `technical-exposition` system prompt governed every word in this README. Every prose-writing subagent in the refactor loaded the prompt via `system_prompt_loader.load("technical-exposition")` and embedded it as the writer's voice contract before drafting a single sentence. The lint pass confirmed the result; the QA report at `docs/qa/README-QA-2026-05-17.md` carries the per-linter counts.

Twelve linter modules emit seventeen rule names. Six modules gate (eight rule names): `no-hedging`, `active-voice`, `signal-density`, `parallel-structure`, `listicle-abstract`, `listicle-anaphora`, `rhythm-uniform-length`, `rhythm-repeated-opening`. Six modules advise (nine rule names): AI staccato, AI vocabulary, burstiness, concrete-instance-density, epistemic-precision, paragraph-motion. Final gating violations on the assembled README: zero. Advisory findings: 72, each documented in the QA report with the author's disposition. The dominant source of advisory noise was `epistemic-precision` — 70 of the 72 findings — firing on technically-precise sentences that name file paths, version numbers, and numeric thresholds.

This section is the proof. The suite that drafted every other section drafted this one too. The Russell discipline sat in the generation contract, not bolted on after the fact. A reader who doubts the suite's voice can run `python tools/lint_readme.py README.md` locally; the result is reproducible.

## Documentation

The repo's prose documentation lives in three places. Conceptual docs at `docs/concepts/` cover each skill's design reasoning in one file per topic. Operational runbooks at `docs/operations/` cover deploying, running, and recovering pipeline components. QA reports from the README pass live at `docs/qa/`. Find each skill's `SKILL.md` and its `references/` linked from that skill's mini-tutorial in [The skills](#the-skills).

- `docs/concepts/neurosym-forge.md` — neurosymbolic verifier scaffolder: scope, layers, and integration boundary
- `docs/operations/2026-05-12-bundle-c-runbook.md` — Phase-4 operator runbook for Bundle C end-to-end
- `docs/operations/codex-review-protocol.md` — autonomous whole-repo review protocol for Codex-style agents
- `docs/operations/neurosym-forge-runbook.md` — operator workflow for the verifier side-channel
- `docs/qa/` — README QA reports (generated at Stage 5 of the README refactor)

## Contributing

PR reviews use three severity buckets: **P0** (blocker — broken invariant, build failure, security issue), **P1** (must fix before merge — broken doc refs, contract-runtime mismatches, tautological test gates), **P2** (post-merge polish — comment clarity, test strengthening with no current bug). Every finding cites `file:line`. The reviewer writes the verdict to `openspec/changes/<change>/PR-<N>-REVIEW.md`; PR-33-REVIEW.md under `changes/codex-phase-1/` and PR-47-REVIEW.md under `changes/add-syntopical-metabook/` are the standing examples. The verdict line is one of: `approve`, `approve with follow-ups`, `request changes`, `block`.

Every cross-cutting change lives under `openspec/changes/<change-name>/` with four files: `proposal.md`, `design.md`, `tasks.md`, and one `specs/<domain>/spec.md` per affected domain. When the change merges, `openspec archive <change>` folds the delta specs into `openspec/specs/` and moves the change folder to `openspec/changes/archive/<date>-<change>/`. The `changes/add-syntopical-metabook/` folder illustrates a complete lifecycle from proposal through archive.

Each skill ships its own venv at `skills/<name>/.venv/` and its own pytest suite at `skills/<name>/tests/`. Run `pytest tests/ -q` from the skill directory. Tests carrying the `live` marker hit real upstreams — OpenAlex, Scrapling targets, booklogic binary — and run nightly. Unit tests use a fake `llm_call=` callable and touch no network. Any PR that lets a live-only failure reach the standard suite gets a P1.

Six checks gate every PR: `cljs-bermuda-test` and `cljs-integration` compile and run the ClojureScript booklogic layer; `lint-workflow-yaml` runs actionlint on the workflow file; `smoke (Bermuda end-to-end)` runs the thesis-to-graph pipeline end-to-end; `test book-qa py3.12+py3.13` and `test book-thesis py3.12+py3.13` cover both supported Python versions. The `ci/.import-linter` contract and `ci/lint_no_shadow_writes.py` plugin both execute inside those test suites, not as separate jobs.

Project conventions accumulate in per-session memory files at `~/.claude/projects/.../memory/feedback_*.md`; `feedback_pr_review_style.md` is the primary source this section abstracts. Each skill owns its version in `pyproject.toml`; the suite as a whole declares none. The `API_VERSION` field in each `skill_api.py` governs compatibility; `sibling_skills.load_skill_api(name, expected_major)` raises `IncompatibleSkillApiVersion` on a major mismatch before any skill code executes.

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

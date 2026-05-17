# Syntopical Metabook — Added Requirements

## ADDED Requirements

### Requirement: Citation Graph Acquisition
The syntopical-metabook skill SHALL produce a deduplicated candidate pool of
PaperRef records by traversing the citation graph (via scrapling-fetch
openalex adapter preferred, semantic_scholar adapter fallback) to a configured
depth D (default 2) when the user or a sibling skill invokes Acquire with one
or more seeds.

#### Scenario: Single-seed depth-1 traversal
- GIVEN seed `arxiv:2310.04673` and D=1
- WHEN Acquire runs
- THEN the candidate pool contains every direct reference and citation of that paper

#### Scenario: Duplicate deduplication across seeds
- GIVEN duplicate PaperRef records discovered across multiple seeds
- WHEN Acquire runs
- THEN duplicates are merged by first non-null key in order arxivId, doi, ss_id, openalex_id

---

### Requirement: Candidate Embedding Scoring
When a candidate pool is produced, the syntopical-metabook skill SHALL score
each candidate against the target chapter contract using cosine similarity
between sentence-transformer embeddings of the candidate's title plus abstract
and the chapter's title plus summary plus concatenated thesis-tree statements.

#### Scenario: Relative ordering preserved by topical relevance
- GIVEN candidate A with high topical overlap and candidate B with low topical overlap against a fixed chapter
- WHEN scoring runs
- THEN score(A) > score(B)

#### Scenario: Deterministic scoring across runs
- GIVEN identical candidate pool and chapter contract inputs
- WHEN scoring runs on two separate occasions
- THEN resulting scores are bit-identical

---

### Requirement: Triage Partitioning
When scoring of a candidate pool completes, the syntopical-metabook skill SHALL
partition candidates into auto-approve, manual-review, and reject buckets by
configured score thresholds, and SHALL write the result to
`syntopical/acquisition/triage-<run_id>.md`.

#### Scenario: Candidate scores above the high threshold
- GIVEN T_high = 0.75 and a candidate with score 0.82
- WHEN triage runs
- THEN the candidate is listed under the auto-approve bucket of the triage file

#### Scenario: Candidate scores between thresholds
- GIVEN T_high = 0.75, T_low = 0.55, and a candidate with score 0.62
- WHEN triage runs
- THEN the candidate is listed under the manual-review bucket of the triage file

#### Scenario: Candidate scores below the low threshold
- GIVEN T_low = 0.55 and a candidate with score 0.41
- WHEN triage runs
- THEN the candidate is listed under the reject bucket of the triage file

---

### Requirement: Conditional Download with Dedup Guard
When triage completes, the syntopical-metabook skill SHALL download every
auto-approve candidate (capped at max_auto_per_run) via the scrapling-fetch
download_pdf interface into `syntopical/acquisition/incoming/`, unless a
candidate's resolved sha256 matches an already-ingested source, in which case
the skill SHALL mark the candidate `already-have` in the triage file and skip
download.

#### Scenario: Novel candidate is downloaded
- GIVEN an auto-approve candidate whose sha256 is not present in the ingested-source ledger
- WHEN the download step runs
- THEN the PDF is fetched into `syntopical/acquisition/incoming/`

#### Scenario: Already-ingested candidate is skipped
- GIVEN an auto-approve candidate whose resolved sha256 matches an ingested source
- WHEN the download step runs
- THEN the candidate is marked `already-have` in the triage file and no network download occurs

---

### Requirement: Post-Download Ingest Handoff
When a download succeeds, the syntopical-metabook skill SHALL call
`book-knowledge.ingest_pdf` to ingest the file into the canonical workspace
and, on status `ingested` or `already_present`, SHALL delete the staged copy
from `incoming/`.

#### Scenario: Successful ingest cleans up staging
- GIVEN a PDF downloaded to `syntopical/acquisition/incoming/`
- WHEN ingest returns status `ingested`
- THEN the staged copy is deleted from `incoming/`

#### Scenario: Already-present ingest cleans up staging
- GIVEN a PDF downloaded to `syntopical/acquisition/incoming/`
- WHEN ingest returns status `already_present`
- THEN the staged copy is deleted from `incoming/`

---

### Requirement: Failure Isolation in Acquire
The syntopical-metabook skill SHALL append a failure record to
`syntopical/acquisition/manifest.jsonl` and continue with the next candidate
if a download or ingest step raises an exception.

#### Scenario: Network error on one candidate does not halt the run
- GIVEN a candidate pool of N candidates and one candidate that raises a download exception
- WHEN the download phase runs
- THEN a failure record for that candidate is appended to `manifest.jsonl` and the remaining N-1 candidates are processed

---

### Requirement: Acquire Run Manifest
The syntopical-metabook skill SHALL append one JSON line per Acquire run to
`syntopical/acquisition/manifest.jsonl` with fields: run_id, started_at,
finished_at, seeds, depth, candidates_n, auto_approved, manual_review,
rejected_n, downloaded, and failures.

#### Scenario: Manifest line written after a complete run
- GIVEN an Acquire run that processes three seeds, approves two candidates, and downloads one
- WHEN the run finishes
- THEN `manifest.jsonl` contains one new line whose `run_id` field matches the run and whose `downloaded` array lists the ingested file with its sha256

---

### Requirement: HALT File Abort
The syntopical-metabook skill SHALL exit Acquire on entry with exit code 2 and
emit no network calls if the file `syntopical/acquisition/HALT` exists at the
workspace root.

#### Scenario: HALT file prevents acquisition
- GIVEN `syntopical/acquisition/HALT` is present in the workspace
- WHEN Acquire is invoked
- THEN the skill exits with code 2 and no outbound requests are made

---

### Requirement: Feed-Acquire from Gap Seeds
Where `--feed-acquire` is enabled, the syntopical-metabook skill SHALL treat
uncovered thesis-node statements from the most recent gap report as additional
seeds on the next Acquire run.

#### Scenario: Uncovered nodes become seeds when feed-acquire is set
- GIVEN `--feed-acquire` is enabled and the most recent gap report lists two uncovered thesis nodes
- WHEN the next Acquire run starts
- THEN those two node statements are present in the seed list alongside any user-supplied seeds

---

### Requirement: Booklogic Reachability Veto
The syntopical-metabook skill SHALL invoke
`booklogic_adapter.reachable_from_thesis` against the target chapter's thesis
tree when triage marks a candidate as auto-approve, and SHALL demote the
candidate to manual-review with a `booklogic-veto` annotation if the returned
ReachabilityVerdict has `reachable` equal to false.

#### Scenario: High-scoring candidate vetoed by booklogic
- GIVEN a candidate with embedding score 0.82 (above T_high) that has no rewrite path to any thesis node
- WHEN triage runs
- THEN the candidate appears under manual-review with a `booklogic-veto` annotation and the rule-trace

#### Scenario: High-scoring candidate passes booklogic check
- GIVEN a candidate with embedding score 0.82 and a ReachabilityVerdict with reachable true
- WHEN triage runs
- THEN the candidate remains in auto-approve

---

### Requirement: Booklogic Veto Bypass via Env Var
Where `SYNTOPICAL_NO_BOOKLOGIC=1` is set, the syntopical-metabook skill SHALL
skip the booklogic veto, retain the embedding-only triage outcome, and SHALL
append a warning record of kind `booklogic-veto-skipped` to
`syntopical/acquisition/manifest.jsonl`.

#### Scenario: Veto bypassed and warning recorded
- GIVEN `SYNTOPICAL_NO_BOOKLOGIC=1` is set and an auto-approve candidate exists
- WHEN triage runs
- THEN no booklogic subprocess is invoked, the candidate keeps its triage bucket, and a `booklogic-veto-skipped` record appears in `manifest.jsonl`

---

### Requirement: Topic Map Generation
When Synthesize runs, the syntopical-metabook skill SHALL rewrite
`syntopical/topic-map.md` listing every concept slug from the book-knowledge
concept list, grouped by thesis-tree top-level node, with one row per concept
of shape: slug, sources list, n_verified_claims.

#### Scenario: Topic map reflects workspace concept count
- GIVEN a workspace with C concepts distributed across T thesis branches
- WHEN Synthesize runs
- THEN the file contains exactly C concept rows distributed across at most T sections

---

### Requirement: Booklogic-Driven Disputed Questions
When Synthesize runs, the syntopical-metabook skill SHALL invoke
`booklogic_adapter.disputed_questions` with verified claims obtained from
book-knowledge, group the returned DisputedQuestion records by topic, and
write each group to `syntopical/disputed-questions/<topic-slug>.md` as a
Markdown table with columns: Question, Position, Source, Claim-ID,
Rewrite-witness, Evidence locator.

#### Scenario: Disputed-question file written per topic
- GIVEN four verified claims tagged `finality` that booklogic resolves into one disputed question with four positions
- WHEN Synthesize runs
- THEN `syntopical/disputed-questions/finality.md` exists with one question header and four position rows, every Claim-ID cell links into the claim ledger, and every Rewrite-witness cell names a rule ID

#### Scenario: Stale files removed when booklogic returns empty
- GIVEN booklogic returns an empty disputed-questions list
- WHEN Synthesize runs
- THEN every existing file under `syntopical/disputed-questions/` is deleted so the directory reflects current state

---

### Requirement: Concept Reconciliation Pages
When Synthesize runs, the syntopical-metabook skill SHALL invoke
`booklogic_adapter.reconcile_concepts` with concepts obtained from
book-knowledge and, for each returned CanonicalConcept, SHALL write
`syntopical/concepts/<canonical_slug>.md` naming the canonical slug,
alternates, source-by-source surface-form usage, and the rewrite-witness
rule IDs.

#### Scenario: Unified concept page written
- GIVEN concepts `nakamoto-consensus` (surface `longest-chain rule`) and `longest-chain` (surface `Bitcoin consensus`) that booklogic unifies under canonical slug `nakamoto-consensus`
- WHEN Synthesize runs
- THEN `syntopical/concepts/nakamoto-consensus.md` exists, references both source pages, and names the rewrite witnesses

---

### Requirement: Synthesize Idempotence
The Synthesize sub-workflow SHALL be idempotent with respect to the claim
ledger, concept set, and booklogic ruleset checksum: re-running with no
upstream changes SHALL produce zero file diffs under `syntopical/`.

#### Scenario: Double run with frozen inputs produces no diff
- GIVEN the claim ledger, concept set, and booklogic ruleset checksum are unchanged between two runs
- WHEN Synthesize runs twice in succession
- THEN a diff of `syntopical/` between the two runs is empty

---

### Requirement: Citation-Backed Prose
The syntopical-metabook skill SHALL ensure every prose paragraph written under
`syntopical/` carries at least one citation pointing at a book-knowledge claim
ID, a wiki page slug, or a booklogic rule ID. Free-floating claims are
prohibited.

#### Scenario: Citation linter rejects uncited paragraphs
- GIVEN a prose paragraph written under `syntopical/` with no citation marker
- WHEN the citation-coverage linter runs
- THEN the linter reports a violation for that paragraph

---

### Requirement: Legacy Mode Fallback for Synthesize
Where `SYNTOPICAL_NO_BOOKLOGIC=1` is set, the syntopical-metabook skill SHALL
substitute legacy heuristics for booklogic — using
`book-knowledge.detect_conflicts` for disputed questions and
surface-form-overlap clustering for concept reconciliation — and SHALL prepend
a `> Legacy mode — booklogic disabled` banner to every affected artifact.

#### Scenario: Legacy banner appears when booklogic disabled
- GIVEN `SYNTOPICAL_NO_BOOKLOGIC=1` is set and Synthesize runs
- WHEN a disputed-questions file is written
- THEN the file begins with `> Legacy mode — booklogic disabled`

---

### Requirement: Per-Chapter Lens Projection
The syntopical-metabook skill SHALL write `syntopical/lenses/<C>.md` when the
user or a sibling skill requests a lens for chapter C, containing the subset
of topic-map rows, disputed-question entries, and concept-reconciliation notes
whose tags intersect the union of C's tags and the chapter's thesis-tree tags,
plus a coverage summary block.

#### Scenario: Lens file scoped to chapter tags
- GIVEN chapter C with tags {finality, liveness} and a topic map containing entries tagged {finality} and {safety}
- WHEN the lens is projected
- THEN `syntopical/lenses/C.md` contains the {finality} entry and omits the {safety} entry

---

### Requirement: Lens Section Order Contract
The lens file SHALL use the exact section order: Topics, Disputed Questions,
Concept Reconciliation, Coverage, with no other top-level sections,
so that book-compose can parse it deterministically.

#### Scenario: Lens sections appear in mandated order
- GIVEN a lens file written by the syntopical-metabook skill
- WHEN the section headings are extracted
- THEN they appear in the order Topics, Disputed Questions, Concept Reconciliation, Coverage and no other level-2 headings are present

---

### Requirement: Lens YAML Frontmatter
The lens file SHALL include a YAML frontmatter block with keys: chapter_id,
generated_at, source_run_id, n_topics, n_disputed, n_concepts, coverage_score,
for traceability.

#### Scenario: Frontmatter present and complete
- GIVEN a lens file written for chapter `ch-03`
- WHEN the YAML frontmatter is parsed
- THEN all seven required keys are present and chapter_id equals `ch-03`

---

### Requirement: Coverage Gap Report
The syntopical-metabook skill SHALL compute, for every thesis node, a coverage
score equal to min(1.0, n_verified_supporting_claims / required_evidence_count)
when Gap Report runs against a chapter contract, and SHALL write
`syntopical/reports/gaps-<C>-<timestamp>.md` listing every node with coverage
score below 1.0, sorted ascending.

#### Scenario: Partially-covered node appears in gap report
- GIVEN a thesis node requiring three supporting verified claims with only one present
- WHEN Gap Report runs
- THEN that node appears in the gap report with coverage_score = 0.33

---

### Requirement: Gap Seeds Written for Feed-Acquire
Where `--feed-acquire` is enabled, the syntopical-metabook skill SHALL append
every uncovered node statement to
`syntopical/acquisition/pending-seeds.txt`, consumed by the next Acquire run.

#### Scenario: Uncovered nodes appended to pending seeds
- GIVEN `--feed-acquire` is enabled and Gap Report identifies two nodes with coverage_score < 1.0
- WHEN Gap Report finishes
- THEN both node statements are appended to `syntopical/acquisition/pending-seeds.txt`

---

### Requirement: Zero Direct Network Calls
The syntopical-metabook skill SHALL make zero direct network calls. All
outbound traffic SHALL be routed through scrapling-fetch.

#### Scenario: No banned network imports in syntopical-metabook
- GIVEN the syntopical-metabook skill codebase
- WHEN the CI import linter runs
- THEN no import of requests, httpx, urllib3, aiohttp, or playwright is found

---

### Requirement: Offline-Only Sub-Workflows
The Synthesize, Project Lens, and Gap Report sub-workflows SHALL make zero
network calls under any conditions.

#### Scenario: Synthesize runs without network access
- GIVEN network access is blocked at the OS level
- WHEN Synthesize runs
- THEN the run completes without error

---

### Requirement: Pinned Sentence-Transformer Model
The syntopical-metabook skill SHALL pin the sentence-transformer model name
and weights in its venv so that ranking is reproducible across runs and
machines.

#### Scenario: Scoring is reproducible on a different machine
- GIVEN the same venv lockfile is used on two different machines
- WHEN scoring runs with identical inputs on both machines
- THEN the resulting scores are bit-identical

---

### Requirement: No Direct Canonical Writes
The test suite SHALL fail if the syntopical-metabook skill writes to `raw/`,
`claims/`, `wiki/`, or `graph/` directly. Canonical ingest is
book-knowledge's sole privilege.

#### Scenario: Direct write to canonical directory causes test failure
- GIVEN the syntopical-metabook skill attempts to write a file into `claims/`
- WHEN the test suite runs
- THEN the direct-write guard test fails

---

### Requirement: Non-Interactive Invocation
Every Acquire, Synthesize, Project Lens, and Gap Report invocation SHALL
complete without interactive prompts. The audit manifest is the user's
after-the-fact review surface.

#### Scenario: Acquire runs unattended
- GIVEN an Acquire invocation with no controlling terminal
- WHEN the run executes
- THEN it completes without blocking on any prompt

---

### Requirement: Generation Provenance Footer
Every artifact written by syntopical-metabook SHALL carry a generation
provenance footer with keys: generated_by, generated_at, source_run_id,
skill_api_versions, so a reader can reconstruct the producing pipeline.

#### Scenario: Provenance footer present in lens file
- GIVEN a lens file written by the syntopical-metabook skill
- WHEN the file is read
- THEN a provenance footer block is present containing generated_by, generated_at, source_run_id, and skill_api_versions

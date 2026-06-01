# Russellian Book Suite V3 Skill Migration Plan Design

Date: 2026-06-01. Status: proposed companion to V3 architecture.

Related spec:

- `docs/superpowers/specs/2026-06-01-rbs-v3-architecture-design.md`

## 1. Goal

Update the skill-by-skill migration plan so every legacy skill ports into the
V3 architecture cleanly. The plan preserves accepted behavioral contracts and
golden fixtures, but it does not preserve v1's Python module layout, path
coupling, direct file writes, in-process LLM calls, or per-skill runtime
boundaries.

The skills are being rewritten. They may change shape when the change:

- preserves the accepted external behavior;
- removes a v1 migration scar;
- makes the service fit the V3 query/command split;
- pushes orchestration into `rbs-pipeline-svc`;
- pushes durable outputs into `rbs-artifact-svc`;
- pushes network into `rbs-fetch-svc`;
- pushes model-backed operations into `rbs-agent-svc`;
- makes heavy dependencies explicit, typed unsupported, or ADR-blocked.

## 2. Universal Migration Gate

Before implementation starts for a service, its migration package must include:

```text
1. service contract catalog entry
2. proto operation inventory
3. query/command classification
4. allowed caller matrix
5. rbs-core type list
6. service-local SQLx state list
7. artifact kind registry entries
8. capability manifest operations
9. workflow template stages for commands
10. agent/fetch/artifact boundary declarations
11. heavy dependency disposition
12. golden fixture list
13. conformance expected verdict
```

The `rbs-conformance` layer fails a service migration when any item is missing,
contradictory, or hidden behind prose only.

## 3. Migration Readiness States

```text
InventoryReady
  requirements extracted from dossier and v1 source where needed

ContractReady
  service catalog, proto inventory, artifact kinds, core types, manifests ready

ConformanceReady
  rbs-conformance reports PASS or explicit BLOCKED for known ADRs

ImplementationReady
  service can be implemented without open architecture questions

GoldenReady
  v2/v3 output matches accepted v1 fixtures or accepted deviations

RetirementReady
  Python skill can be removed from production workflow
```

Rules:

- `ImplementationReady` requires `ConformanceReady`.
- `RetirementReady` requires `GoldenReady`.
- `BLOCKED` decisions are allowed only before implementation planning.
- `WARN` is allowed for experimental capabilities, not for core replacement.

## 4. Platform Foundation Changes

V3 adds these foundation tasks before domain service ports:

| Foundation item | Purpose |
|---|---|
| `contracts/services/*.yaml` | RPC inventory, operation class, allowed callers. |
| `contracts/artifacts/*.yaml` | Artifact kinds, schemas, provenance, owner, version policy. |
| `contracts/workflows/*.yaml` | Pipeline DAG templates and command-stage edges. |
| `contracts/heavy-deps/*.yaml` | Heavy dependency dispositions and ADR blockers. |
| `rbs-conformance` | CI/CLI compliance checks over contracts, protos, manifests, schemas, dossiers, fixtures. |
| `rbs-agent-svc` V3 packet kinds | Adds embeddings/ranking and deterministic stubs. |
| `rbs-core` domain type catalog | Promotes shared semantic types before services fork their own strings. |

## 5. Service Migration Plans

### 5.1 `scrapling-fetch` -> `rbs-fetch-svc`

**V3 role:** platform infrastructure and sole outbound network boundary.

**Architectural changes from v1:**

- replace Scrapling/trafilatura with Rust-native plain fetch and extraction;
- keep `Stealth` and `Dynamic` in API but return typed unsupported until browser
  ADR is accepted;
- represent adapters as first-class operations.

**Required operations:**

```text
FetchPage        command
DownloadPdf      command
Extract          command
FetchArxiv       command
FetchOpenalex    command
FetchDoi         command
FetchSemanticScholar command
Ready            query
```

**Artifacts:** fetched page, fetched PDF, extracted markdown, paragraph list,
source manifest, fetch audit.

**QA checks:** fetch boundary, adapter fixture coverage, cache/offline behavior,
PDF streaming cleanup, robots/rate-limit policy, no network crates outside
`rbs-fetch-svc`.

**Readiness:** `ImplementationReady` for Plain mode; `BLOCKED` only for
Stealth/Dynamic native browser parity.

### 5.2 `book-qa` -> `rbs-qa-svc`

**V3 role:** final book/workflow quality gate, not architecture conformance QA.

**Architectural changes from v1:**

- split deterministic lint, swarm, sentinel, healer, and writeback proposal;
- make writeback a proposal artifact, not a direct knowledge mutation;
- route healer and C-class editorial sweep through `rbs-agent-svc`;
- track healer iterations in SQLx, not `healer-state.json`.

**Required operations:**

```text
LintArtifact       command
RunSwarm           command
Sentinel           command
Heal               command
ProposeWriteback   command
GetWaiverPolicy    query
```

**Artifacts:** `qa_defects`, `qa_sentinel`, `qa_healer_report`,
`qa_writeback_proposal`.

**Workflow rules:** `ApplyWriteback` is a knowledge command stage invoked by
pipeline after QA emits a proposal.

**QA checks:** D1-D13/C1-C15 enum coverage, hard-vs-advisory gate semantics,
healer iteration cap, waiver behavior decision, artifact schema parity, golden
per defect class.

**Readiness:** `ContractReady` after waiver semantics are decided; otherwise
`BLOCKED` only for waiver-specific behavior, not for D1-D8 lint.

### 5.3 `book-review` + `review-conductor` -> `rbs-review-svc`

**V3 role:** persona and panel review service.

**Architectural changes from v1:**

- merge review and conductor into one service;
- store persona prompt versions as artifacts or versioned config;
- route persona execution through `rbs-agent-svc`;
- keep aggregation deterministic and fail-closed.

**Required operations:**

```text
RunPanel           command
RunPersona         command
AggregateVerdict   command
GetPanelConfig     query
ListPersonas       query
```

**Artifacts:** persona review, panel review, verdict JSON, panel config.

**QA checks:** persona ID stability, prompt versioning, severity parse parity,
deterministic stub outputs, fail-closed parse failures, artifact schema parity.

**Readiness:** `ImplementationReady` after prompt versioning mechanism is
chosen.

### 5.4 `russellian-style` -> `rbs-style-svc`

**V3 role:** deterministic style and refusal-scope service.

**Architectural changes from v1:**

- port pure regex/statistical linters first;
- classify spaCy-dependent linters as native parser, degraded rule, or typed
  unsupported;
- expose rule registry as query API;
- keep style reports as artifact outputs.

**Required operations:**

```text
LintArtifact     command
GetRules         query
ScoreDelta       command
CheckRefusal     query
```

**Artifacts:** style pass report, delta report.

**QA checks:** rule registry parity, sentence segmentation golden tests,
spaCy-dependent rule disposition, advisory-vs-gating rule schema, artifact
schema parity.

**Readiness:** pure linters can be `ImplementationReady`; spaCy-dependent rules
remain `BLOCKED` until ADR or degraded contract is accepted.

### 5.5 `book-knowledge` -> `rbs-knowledge-svc`

**V3 role:** canonical source, claim, graph/read-model, and writeback service.

**Architectural changes from v1:**

- remote acquisition calls `rbs-fetch-svc`;
- append-only claim ledger is SQLx-owned with byte-compatible exports;
- graph/RDF/SHACL behavior is either Rust-native, typed validation, or ADR
  blocked;
- all downstream consumers use query APIs or artifact refs.

**Required operations:**

```text
IngestSource       command
QueryClaims        query
GetClaim           query
TransitionClaim    command
ListConflicts      query
PropagateBeliefs   command
ApplyWriteback     command
ValidateGraph      command
GetGraphReport     query
```

**Artifacts:** source manifest, raw source, claim ledger snapshot, conflict
report, belief report, TriG snapshot, SHACL report.

**QA checks:** FSM transition legality, append-only ledger export parity,
remote acquisition through fetch, no cross-service SQL, RDF/SHACL decision,
graph report schema.

**Readiness:** core ledger/query path can proceed; graph validation remains
`BLOCKED` until RDF/SHACL ADR.

### 5.6 `book-thesis` -> `rbs-thesis-svc`

**V3 role:** thesis tree, supports, contradiction, entailment packet, and D9-D12
defect service.

**Architectural changes from v1:**

- read knowledge through allowed query APIs;
- compile thesis artifacts through artifact service;
- run entailment execution through `rbs-agent-svc`;
- keep thesis packet building/parsing deterministic in service;
- replace Datalog with accepted Rust rules/graph strategy or block affected
  operation.

**Required operations:**

```text
CompileThesis             command
CheckSupports             command
RunContradictionPass      command
BuildEntailmentPackets    command
ParseEntailmentResults    command
GetThesisStructure        query
```

**Artifacts:** thesis tree, thesis triples, supports defects, datalog defects,
entailment packets, entailment parsed results, D9-D12 defect files.

**QA checks:** D9-D12 schema parity, entailment packet schema, agent packet
schema, Datalog/RDF disposition, QA compatibility with defect artifacts.

**Readiness:** supports and packet parsing can proceed; contradiction pass is
`BLOCKED` until Datalog/RDF ADR.

### 5.7 `syntopical-metabook` -> `rbs-syntopical-svc`

**V3 role:** syntopical knowledge-curation service.

**Architectural changes from v1:**

- acquisition uses `rbs-fetch-svc`;
- reads knowledge/thesis through query APIs;
- ranking uses `rbs-agent-svc` embeddings/ranking or typed unsupported;
- booklogic runs behind a service-owned trait or adapter sidecar only after ADR;
- dormant v0.3 code ports only when live call site plus golden fixture exists.

**Required operations:**

```text
RunAcquire            command
RunSynthesize         command
ProjectLens           command
ReadLens              query
BuildCoverageReport   command
RunGovernance         command
GetTopicMap           query
```

**Artifacts:** acquisition manifest, triage, topic map, disputed questions,
concept reconciliation, lens, gap report, governance positions, rule reports.

**QA checks:** lens four-section contract, school/lens constants, embedding
score golden fixture, booklogic trait decision, no direct network, dormant code
exclusion.

**Readiness:** lens/project/gap pure paths can proceed; ranking and booklogic
operations are `BLOCKED` until ADR or typed unsupported decision.

### 5.8 `paragraph-weaver` -> `rbs-weaver-svc`

**V3 role:** deterministic paragraph threading service.

**Architectural changes from v1:**

- preserve immutable paragraph body, seam-only edits, bridge validation, and
  deterministic ordering;
- thesis/style dependencies become query or workflow stages, not hidden imports;
- optional bridge suggestion or critique uses `rbs-agent-svc` and is not part of
  deterministic baseline.

**Required operations:**

```text
Weave        command
GetReport    query
ValidateBridge query
ValidateSeamEdit query
```

**Artifacts:** weave goal, woven output, provenance render, clean render,
weave report.

**QA checks:** immutable-body encoding, exact ordering fixtures, feasibility
refusal, cycle detection, bridge/seam rejection, provenance/clean render parity.

**Readiness:** earliest low-risk deterministic port after core contracts.

### 5.9 `book-compose` -> `rbs-compose-svc`

**V3 role:** workflow compiler and release assembler.

**Architectural changes from v1:**

- compose no longer owns sibling orchestration internals;
- it emits workflow templates for pipeline execution;
- review, QA, style, thesis, knowledge, syntopical, and agent commands execute
  as pipeline stages;
- `ReadLens` moves to `rbs-syntopical-svc`; compose consumes the lens query;
- PDF/EPUB rendering is typed unsupported or sidecar-backed until ADR.

**Required operations:**

```text
DraftChapter          command
BuildReleaseBundle    command
BuildBook             command
ValidateContract      command
GetReleaseManifest    query
```

**Workflow stages:** contract, preflight, claim slice, outline, approval block,
draft, style, review, persona soft gate, QA, chapter bundle, book release.

**Artifacts:** chapter contract, draft, evidence summary, claim slice, release
manifest, release bundle, manuscript, book manifest, bibliography, render
outputs.

**QA checks:** human `Blocked` continuation, persona soft-gate semantics,
orphan citation strip, release manifest parity, render capability disposition,
lens contract compatibility.

**Readiness:** late port after dependency services expose stable contracts.

### 5.10 `neurosym-forge` -> `rbs-forge-svc`

**V3 role:** verifier scaffold, verifier execution, induction, and optional D13
provider.

**Architectural changes from v1:**

- expose verifier APIs over Tonic;
- keep subprocesses behind `VerifierClient` and explicit `subprocess.run`
  permission profiles;
- route LLM lifts and optional semantic similarity through `rbs-agent-svc`;
- choose z3 and CLJS/booklogic strategy through ADR before native port;
- D13 is a typed artifact consumed by QA, not a direct file read.

**Required operations:**

```text
ScaffoldVerifier     command
RunVerifier          command
InduceTheory         command
AddConstraint        command
ExplainDefect        query
RenderVerifier       command
Similar              command
```

**Artifacts:** scaffold tree, EDN atomspace, axioms source, KG source, verifier
verdict, D13 defect artifact, induction candidates, provenance render.

**QA checks:** EDN roundtrip, scaffold layout parity, z3 disposition,
CLJS/booklogic disposition, subprocess permission profile, D13 schema, golden
SAT/UNSAT fixtures.

**Readiness:** last domain port; only EDN/codegen layers should start before z3
and CLJS/booklogic decisions.

## 6. Skill Dossier Update Rule

Each migration dossier should gain a V3 addendum with this structure:

```text
## 8. V3 compatibility addendum

- Operation catalog:
- Query/command classification:
- Allowed callers:
- Artifact kinds:
- rbs-core shared types:
- Service-local SQLx state:
- Capability manifest operations:
- Workflow template stages:
- Agent/fetch/artifact boundaries:
- Heavy dependency disposition:
- Conformance checks:
- Golden fixture gate:
- Blocked decisions:
```

The addendum is the bridge between the wiki dossier and the repo-side
`contracts/` files. `rbs-conformance` should fail if a dossier lists a required
operation that has no catalog/proto/manifest representation.

## 7. Revised Retirement Rule

A Python skill can be retired only when:

```text
1. all required V3 catalog entries exist;
2. all required proto operations exist;
3. all required capability manifests validate;
4. all durable artifacts have schema and owner;
5. all heavy dependency decisions are resolved or typed unsupported;
6. policy checks pass for network, agent, artifact, DB, and subprocess use;
7. trace/context checks pass;
8. golden fixtures pass for preserved behavior;
9. accepted deviations are documented in the dossier addendum;
10. rbs-conformance reports PASS for the service retirement gate.
```

## 8. Migration Review Checklist

```text
[ ] The skill has no path/import coupling in the target.
[ ] The skill has no direct workspace writes in the target.
[ ] The skill has no direct provider calls in the target.
[ ] The skill has no direct network calls unless it is rbs-fetch-svc.
[ ] Commands are pipeline stages when cross-domain or long-running.
[ ] Queries are explicitly allowlisted.
[ ] Artifacts round-trip through rbs-artifact-svc.
[ ] Heavy dependencies are native, delegated, sidecar-backed, unsupported, or blocked.
[ ] Golden fixtures pin preserved behavior.
[ ] Dormant v1 behavior is excluded unless live and fixture-backed.
[ ] rbs-conformance can prove the above.
```

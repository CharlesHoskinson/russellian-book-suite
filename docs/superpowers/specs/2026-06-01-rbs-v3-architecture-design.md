# Russellian Book Suite V3 Architecture Design

Date: 2026-06-01. Status: proposed V3 architecture after V2 audit.

## 1. Goal

V3 resolves the V2 architecture audit findings without abandoning the accepted
Rust microservice direction. The target remains an API-first Rust MSA using
Tokio, Axum, Tonic, Serde/prost, SQLx, tracing, and OpenTelemetry.

The core V3 change is a stricter contract model and a more precise service-call
rule:

- `rbs-pipeline-svc` owns commands, long-running workflows, retries,
  cancellation, human gates, and cross-domain mutations.
- Domain services may make explicitly whitelisted read/query Tonic calls to
  other domain services.
- Domain services may not write another service's state, read another
  service's SQL, or import another service's internals.
- Every operation is represented in `rbs-proto` and in the capability/control
  plane.
- A new architecture QA layer continuously checks that specs, protos,
  capability manifests, artifact schemas, workflows, migration dossiers, tests,
  and policy rules stay consistent.

V3 is a compatibility architecture for the rewrite, not a product feature
expansion.

## 2. Problems V3 Fixes

The V2 audit found these gaps:

1. Required service RPCs from the dossiers were not fully represented in the
   architecture contract examples.
2. The ASCII protocol forbade direct domain-to-domain calls, while the dossiers
   required normal read/query dependencies such as thesis reading knowledge or
   compose reading syntopical lenses.
3. `rbs-agent-svc` covered LLM/subagent/reviewer/healer/entailment calls, but
   not embeddings and ranking.
4. `rbs-core` had only neutral starter types, not the service-domain type
   catalog required by the migration dossiers.
5. Artifact kinds, schemas, provenance, and versioning were not cataloged per
   service output.
6. Heavy dependency decisions remained open without a uniform way to block,
   defer, or type-unsupported affected operations.
7. Nothing enforced that future architecture docs, proto files, manifests,
   migration plans, and golden fixtures stayed in sync.

## 3. V3 Layer Model

```text
+--------------------------------------------------------------------+
| L6  Architecture QA / Conformance                                  |
|     contract catalog, policy gates, dossier coverage, golden gates  |
+--------------------------------------------------------------------+
| L5  Operator API                                                    |
|     rbs-gateway, Axum REST, OpenAPI, typed error envelope           |
+--------------------------------------------------------------------+
| L4  Workflow commands                                                |
|     rbs-pipeline-svc, DAGs, jobs, retries, cancellation, gates       |
+--------------------------------------------------------------------+
| L3  Domain services                                                  |
|     query APIs allowed by contract; commands go through pipeline     |
+--------------------------------------------------------------------+
| L2  Platform services                                                |
|     workspace, artifact, capability registry, fetch, agent           |
+--------------------------------------------------------------------+
| L1  Shared contracts and policy                                      |
|     rbs-core, rbs-proto, rbs-policy, rbs-telemetry, rbs-config       |
+--------------------------------------------------------------------+
| L0  Runtime and persistence                                          |
|     Tokio, SQLx, service DBs, blob store, OpenTelemetry collector    |
+--------------------------------------------------------------------+
```

L6 is new. It is not book-domain QA. It is architecture conformance QA for the
rewrite itself.

## 4. Query / Command Rule

V3 replaces the V2 "domain services do not call each other directly" rule with a
query/command split.

### 4.1 Query Calls

A domain service may call another domain service directly over Tonic only when
all of the following are true:

- the callee RPC is declared as `operation_class = query`;
- the RPC is side-effect free except for logs, traces, metrics, and read audit;
- the caller/callee edge is listed in the service contract catalog;
- the request uses `RequestContext`;
- the response returns typed values or `ArtifactRef`, never private SQL rows or
  raw filesystem paths;
- the call appears in the caller's capability manifest permissions.

Examples:

```text
rbs-thesis-svc       -> KnowledgeService.QueryClaims
rbs-syntopical-svc   -> KnowledgeService.QueryClaims
rbs-syntopical-svc   -> ThesisService.GetThesisStructure
rbs-compose-svc      -> SyntopicalService.ReadLens
rbs-compose-svc      -> KnowledgeService.GetGraphReport
rbs-weaver-svc       -> ThesisService.GetThesisStructure
```

### 4.2 Command Calls

Cross-domain commands are not direct calls. They are pipeline stages.

An RPC is a command when it mutates durable state, writes canonical artifacts,
launches long-running work, invokes non-deterministic model work, needs retry or
cancellation, can block on operator approval, or changes another service's
state.

Examples:

```text
QA writeback proposal    -> pipeline stage -> KnowledgeService.ApplyWriteback
Compose review stage     -> pipeline stage -> ReviewService.RunPanel
Compose QA stage         -> pipeline stage -> QaService.Sentinel
Thesis entailment run    -> pipeline stage -> AgentService.RunPacket
Forge verifier run       -> pipeline stage -> ForgeService.RunVerifier
```

### 4.3 Forbidden Calls

These remain forbidden:

- cross-service SQL;
- cross-service filesystem reads or writes;
- direct provider calls outside `rbs-agent-svc`;
- direct network calls outside `rbs-fetch-svc`;
- direct durable artifact writes outside `rbs-artifact-svc`;
- imports from another service crate's private modules;
- hot-loaded arbitrary code inside gateway or pipeline.

## 5. Architecture QA Layer

The architecture QA layer is a compliance system that prevents drift between
the design, the proto contracts, capability manifests, artifact schemas, and
skill migration plan.

It is implemented as a small set of platform artifacts:

```text
crates/
  rbs-conformance/          # CI/CLI conformance checks
  rbs-contract-catalog/     # typed readers for service/catalog YAML
contracts/
  services/*.yaml           # service operations, query/command class, callers
  artifacts/*.yaml          # artifact kinds, schemas, owners, provenance
  workflows/*.yaml          # pipeline workflow templates and stage edges
  heavy-deps/*.yaml         # heavy dependency decisions and blockers
capabilities/
  *.yaml                    # operation manifests used by registry
schemas/
  artifacts/*.schema.json
  capabilities/*.schema.json
  contracts/*.schema.json
```

`rbs-conformance` is a CI-first crate and CLI. A later read-only
`rbs-conformance-svc` may expose results through the gateway, but runtime
service is not required for milestone 1.

### 5.1 Conformance Inputs

The QA layer reads:

- `docs/superpowers/specs/*v3*.md`;
- `contracts/services/*.yaml`;
- `contracts/artifacts/*.yaml`;
- `contracts/workflows/*.yaml`;
- `contracts/heavy-deps/*.yaml`;
- `proto/rbs/v1/*.proto`;
- `capabilities/*.yaml`;
- `schemas/**/*.schema.json`;
- `tests/golden/**`;
- migration dossiers in the wiki;
- architecture decision log pending/accepted decisions.

### 5.2 Conformance Checks

Required checks:

| Check | Purpose |
|---|---|
| `rpc_inventory` | Every dossier RPC exists in the service contract catalog and `rbs-proto`. |
| `query_command_matrix` | Every service-to-service edge is allowed, classified, and non-contradictory. |
| `capability_manifest_match` | Every service operation has a matching capability operation or explicit exemption. |
| `artifact_kind_registry` | Every durable output has owner, kind, schema, content type, provenance, and version policy. |
| `core_type_catalog` | Every semantic ID/enum/value object required by a dossier is assigned to `rbs-core` or service-local types. |
| `agent_boundary` | Every model-backed operation routes through `rbs-agent-svc` or is typed unsupported. |
| `fetch_boundary` | Every network operation routes through `rbs-fetch-svc`. |
| `db_boundary` | No contract or migration implies cross-service SQL. |
| `workflow_command_gate` | Cross-domain commands are pipeline stages, not direct domain calls. |
| `heavy_dep_decision` | Operations depending on unresolved heavy deps are blocked or typed unsupported. |
| `golden_fixture_gate` | No skill can retire until required golden fixtures are registered. |
| `trace_context_gate` | Every RPC and job stage carries `RequestContext` and emits trace attributes. |
| `dossier_coverage` | Every requirement ID from migration dossiers maps to a proto, type, artifact, workflow, test, or explicit unsupported decision. |

### 5.3 Conformance Verdicts

The QA layer uses four verdicts:

```text
PASS      contract is complete and enforceable
WARN      allowed but needs attention before stable/core maturity
FAIL      contradicts architecture or misses required contract
BLOCKED   depends on an unresolved architecture decision
```

`FAIL` blocks merge. `BLOCKED` blocks implementation plans for the affected
service operation. `WARN` is allowed for draft/experimental capability maturity
but not for stable/core.

### 5.4 Compliance Gates

Milestone 1 CI includes:

```text
cargo test -p rbs-conformance
rbs-conformance check rpc-inventory
rbs-conformance check query-command-matrix
rbs-conformance check capability-manifest-match
rbs-conformance check artifact-kind-registry
rbs-conformance check heavy-dep-decision
rbs-conformance check dossier-coverage
rbs-conformance check trace-context
```

No domain service may move from design to implementation until its
`dossier_coverage` check is `PASS` or explicitly `BLOCKED` by an accepted ADR.

## 6. Service Contract Catalog

V3 adds a service contract catalog as the source of truth between dossiers and
proto.

Example:

```yaml
service: rbs-qa-svc
proto_service: QaService
operations:
  - name: LintArtifact
    class: command
    owner: rbs-qa-svc
    request: LintRequest
    response: LintResponse
    input_artifacts: [chapter_draft, thesis_defects, forge_d13_defects]
    output_artifacts: [qa_defects]
    allowed_callers: [rbs-pipeline-svc]
  - name: GetWaiverPolicy
    class: query
    owner: rbs-qa-svc
    request: GetWaiverPolicyRequest
    response: GetWaiverPolicyResponse
    allowed_callers: [rbs-gateway, rbs-pipeline-svc]
```

Rules:

- Every proto RPC has one catalog entry.
- Every catalog operation has one proto RPC.
- Every operation has `class = query | command`.
- Every command has workflow/pipeline behavior unless explicitly local to the
  service.
- Every query has an allowlist of caller services.

## 7. Artifact Kind Registry

Artifacts are no longer free-form strings. Every durable artifact kind has a
registry record.

Example:

```yaml
kind: qa_defects
version: 1
owner_service: rbs-qa-svc
content_type: application/json
schema_ref: schema:artifacts.qa_defects.v1
provenance:
  required_input_refs: true
  required_trace_id: true
  required_producer_version: true
version_policy: append_only
golden_fixtures:
  - tests/golden/rbs-qa-svc/qa_defects/
```

Rules:

- service responses return `ArtifactRef`, not paths;
- artifact writes go only through `rbs-artifact-svc`;
- output artifact kinds must match the service catalog and capability manifest;
- schema changes require version bump and golden fixture review.

## 8. Agent Boundary V3

`rbs-agent-svc` becomes the only model-backed operation boundary.

It owns:

- LLM generation;
- subagent dispatch;
- persona review execution;
- healer packets;
- entailment execution;
- embeddings;
- ranking;
- structured parsing;
- deterministic provider stubs;
- transcript artifacts and redaction metadata.

Agent operation classes:

```text
agent.generate
agent.review_persona
agent.heal_ticket
agent.entailment
agent.embed
agent.rank
agent.parse_structured
```

This resolves the syntopical embedding/ranking gap and the forge optional
semantic index gap.

## 9. Heavy Dependency Decision Layer

Every heavy dependency used by a migrated skill must have one decision record in
`contracts/heavy-deps/*.yaml`.

Allowed dispositions:

```text
native_rust
model_backed_agent_operation
service_owned_trait
adapter_sidecar
typed_unsupported
blocked_pending_adr
```

Current required decisions:

| Dependency | Affected services | Required disposition |
|---|---|---|
| Scrapling/trafilatura | fetch | native Rust plain mode; stealth/dynamic typed unsupported until browser ADR |
| spaCy | style, review, compose | native parser or typed degraded style rules |
| sentence-transformers/torch | syntopical, forge optional | agent embed/rank or typed unsupported |
| rdflib/pyshacl/SPARQL | knowledge, thesis, compose | Rust RDF stack, typed validation, or blocked pending ADR |
| pyDatalog | thesis | Rust rules engine or typed graph pass |
| Playwright/Pandoc | compose | render sidecar, native renderer, or typed unsupported |
| z3 | forge | Rust z3 crate or solver trait/subprocess profile |
| shadow-cljs/nbb/booklogic | syntopical, forge | service-owned trait or adapter sidecar, blocked until ADR |

## 10. Skill Migration Compatibility Rule

Because the skills are being rewritten, they may change to fit the architecture
when the change removes v1 scars and preserves the accepted behavioral contract.

Allowed changes:

- replace path/file coupling with ArtifactRef and typed query contracts;
- move orchestration from a skill into pipeline workflow templates;
- move non-deterministic work into `rbs-agent-svc`;
- move network acquisition into `rbs-fetch-svc`;
- move durable writes into `rbs-artifact-svc`;
- split an overloaded v1 function into query and command operations;
- drop dormant v1 code without live call sites and without golden fixtures;
- represent unresolved heavy behavior as typed unsupported.

Not allowed:

- silently drop golden behavior;
- flatten hard gates into advisory warnings;
- hide unresolved dependencies as implementation details;
- recreate sibling imports through service crate dependencies;
- bypass artifact/fetch/agent boundaries for convenience.

## 11. Revised Migration Order

### 11.1 Platform and Contract Foundation

1. V3 architecture spec and ADR updates.
2. `contracts/services` service operation catalog.
3. `contracts/artifacts` artifact kind registry.
4. `contracts/workflows` workflow template catalog.
5. `contracts/heavy-deps` decision catalog.
6. `rbs-core` starter type catalog.
7. `rbs-proto` service skeletons generated or checked against the catalog.
8. `rbs-conformance` crate and CI gates.
9. `rbs-telemetry`, `rbs-config`, `rbs-policy`.
10. `rbs-capability-sdk` and capability manifest schemas.

### 11.2 Platform Services

1. `rbs-gateway`
2. `rbs-workspace-svc`
3. `rbs-artifact-svc`
4. `rbs-capability-registry-svc`
5. `rbs-pipeline-svc`
6. `rbs-fetch-svc`
7. `rbs-agent-svc`

### 11.3 Domain Services

The domain order remains close to V2, but each service must pass its
conformance readiness gate before implementation starts.

1. `rbs-qa-svc`
2. `rbs-review-svc`
3. `rbs-style-svc`
4. `rbs-knowledge-svc`
5. `rbs-thesis-svc`
6. `rbs-syntopical-svc`
7. `rbs-weaver-svc`
8. `rbs-compose-svc`
9. `rbs-forge-svc`

## 12. V3 Review Checklist

```text
[ ] Every dossier RPC appears in service catalog and proto.
[ ] Every operation is query or command.
[ ] Every query caller is allowlisted.
[ ] Every cross-domain command is a pipeline workflow stage.
[ ] Every operation has a capability manifest entry or exemption.
[ ] Every durable output has an artifact kind registry entry.
[ ] Every artifact kind has schema, owner, provenance, and version policy.
[ ] Every model-backed operation routes through rbs-agent-svc.
[ ] Every network operation routes through rbs-fetch-svc.
[ ] Every heavy dependency has an accepted disposition.
[ ] Every service migration has golden fixtures registered.
[ ] Every pending ADR blocks affected implementation plans.
[ ] `rbs-conformance` enforces these rules in CI.
```

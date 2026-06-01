# Russellian Book Suite v2 - ASCII Microservices Protocol

Date: 2026-06-01. Status: companion protocol for the v2 Rust microservices architecture.

Source spec: `docs/superpowers/specs/2026-05-31-rust-axum-v2-architecture-design.md`

This document is the operational protocol for the v2 architecture. It uses plain ASCII diagrams so the service boundaries, request paths, data ownership rules, and test obligations remain readable in terminals, logs, reviews, and generated documentation.

## 1. Protocol Goals

The protocol defines:

- which service may call which service
- which service owns which data
- which messages cross REST and gRPC boundaries
- which artifacts are returned by handle instead of path
- which failures are typed and how they move back to the caller
- which traces, jobs, and audit records must exist for every workflow
- which tests prove a service can replace its Python v1 skill

The protocol does not define implementation internals. A service can change its module layout, repository code, SQL shape, cache strategy, or internal algorithms as long as this external protocol remains compatible.

## 2. Global Topology

All operator traffic enters through `rbs-gateway`. All internal traffic uses Tonic/gRPC. Domain services do not call each other directly unless a later protocol revision explicitly permits it. Workflow composition belongs to `rbs-pipeline-svc`. Capability discovery, version resolution, permission declarations, and external skill endpoint resolution belong to `rbs-capability-registry-svc`.

```text
                                     PUBLIC REST
                                  JSON / Serde DTOs

        +------------------+       +------------------+
        | Operator / CLI   | ----> | rbs-gateway      |
        | Tests / UI       |       | Axum REST        |
        +------------------+       +--------+---------+
                                             |
                                             | Tonic / protobuf
                                             v
        +--------------------+     +--------------------+     +--------------------+
        | rbs-workspace-svc  | <-- | rbs-pipeline-svc   | --> | rbs-capability    |
        +--------------------+     +----------+---------+     | -registry-svc     |
                                               |              +----------+---------+
                    +--------------------------+--------------------------+
                    |                          |                          |
                    v                          v                          v
        +--------------------+     +--------------------+     +--------------------+
        | rbs-artifact-svc   |     | rbs-fetch-svc      |     | rbs-agent-svc      |
        +----------+---------+     +----------+---------+     +----------+---------+
                   |                          |                          |
                   v                          v                          v
        +--------------------+     +--------------------+     +--------------------+
        | Blob store         |     | Internet           |     | LLM / agents       |
        | + index DB         |     | outbound only      |     | external only      |
        +--------------------+     +--------------------+     +--------------------+

        +--------------------------------------------------------------+
        | Domain services orchestrated by rbs-pipeline-svc             |
        |                                                              |
        | rbs-knowledge-svc     rbs-thesis-svc      rbs-syntopical-svc |
        | rbs-style-svc         rbs-review-svc      rbs-qa-svc         |
        | rbs-compose-svc       rbs-forge-svc       rbs-weaver-svc     |
        +--------------------------------------------------------------+

        +--------------------------------------------------------------+
        | External skill services                                      |
        | CapabilityExecutor + manifest + scoped permissions           |
        +--------------------------------------------------------------+
```

## 3. Layer Protocol

The architecture is layered by protocol, not by source folders.

```text
+-----------------------------------------------------------------------+
| L5  Operator contracts                                                |
|     REST endpoints, OpenAPI snapshots, stable error envelope          |
+-----------------------------------------------------------------------+
| L4  Workflow orchestration                                             |
|     Jobs, DAG stages, capability stages, retries, cancellation, events |
+-----------------------------------------------------------------------+
| L3  Domain services                                                    |
|     Knowledge, thesis, syntopical, style, review, QA, compose, etc.    |
+-----------------------------------------------------------------------+
| L2  Core infrastructure services                                       |
|     Workspace, artifact, capability registry, fetch, agent             |
+-----------------------------------------------------------------------+
| L1  Shared platform                                                    |
|     rbs-core, rbs-proto, rbs-config, rbs-telemetry, rbs-policy         |
+-----------------------------------------------------------------------+
| L0  Runtime and persistence                                            |
|     Tokio, SQLx, service DBs, blob store, OpenTelemetry collector      |
+-----------------------------------------------------------------------+
```

Layer rules:

- L5 may call L4 and selected L2 services through Tonic clients.
- L4 may call L2 and L3 services through Tonic clients.
- L4 resolves generic capability stages through `rbs-capability-registry-svc`.
- L3 services may call L2 services through Tonic clients.
- L3 services must not call each other directly in milestone 1.
- L2 services must not call L3 services.
- L1 crates must not depend on service crates.
- L0 is accessed only through the owning service or shared platform crate.

## 4. Service Naming Protocol

Service names are stable API names. Crate names, binary names, proto package names, database schema names, and deployment names should be mechanically related.

```text
Logical service               Crate / binary                Proto service               DB/schema
--------------------------    --------------------------    -----------------------     ----------------
rbs-gateway                   rbs-gateway                   none for server API         none or gateway_db
rbs-workspace-svc             rbs-workspace-svc             WorkspaceService           workspace_db
rbs-artifact-svc              rbs-artifact-svc              ArtifactService            artifact_db
rbs-capability-registry-svc   rbs-capability-registry-svc   CapabilityRegistryService  cap_registry_db
rbs-pipeline-svc              rbs-pipeline-svc              PipelineService            pipeline_db
rbs-fetch-svc                 rbs-fetch-svc                 FetchService               fetch_db
rbs-agent-svc                 rbs-agent-svc                 AgentService               agent_db
rbs-knowledge-svc             rbs-knowledge-svc             KnowledgeService           knowledge_db
rbs-thesis-svc                rbs-thesis-svc                ThesisService              thesis_db
rbs-syntopical-svc            rbs-syntopical-svc            SyntopicalService          syntopical_db
rbs-style-svc                 rbs-style-svc                 StyleService               style_db
rbs-review-svc                rbs-review-svc                ReviewService              review_db
rbs-qa-svc                    rbs-qa-svc                    QaService                  qa_db
rbs-compose-svc               rbs-compose-svc               ComposeService             compose_db
rbs-forge-svc                 rbs-forge-svc                 ForgeService               forge_db
rbs-weaver-svc                rbs-weaver-svc                WeaverService              weaver_db
external skill svc            external deployable           CapabilityExecutor         owned by skill
```

Protocol rule: a service name ending in `-svc` means it is independently deployable and reachable by gRPC. The gateway is independently deployable but does not expose a gRPC server in milestone 1.

## 5. Allowed Call Matrix

Legend:

```text
Y  = allowed in milestone 1
N  = forbidden
C  = conditionally allowed by capability manifest permissions
P  = allowed only through rbs-pipeline-svc orchestration
I  = internal implementation detail, not a network call
```

```text
Caller \ Callee       gateway work artifact registry pipeline fetch agent domain external
-------------------   ------- ---- -------- -------- -------- ----- ----- ------ --------
operator/client       Y       N    N        N        N        N     N     N      N
rbs-gateway           I       Y    Y        Y        Y        N     N     N      N
rbs-workspace-svc     N       I    N        N        N        N     N     N      N
rbs-artifact-svc      N       N    I        N        N        N     N     N      N
rbs-cap-registry-svc  N       N    N        I        N        N     N     N      C
rbs-pipeline-svc      N       Y    Y        Y        I        Y     Y     Y      C
rbs-fetch-svc         N       N    Y        N        N        I     N     N      N
rbs-agent-svc         N       N    Y        N        N        N     I     N      N
domain service        N       Y    Y        N        N        N     Y     I      N
external skill svc    N       C    C        N        N        C     C     N      I
```

Domain-to-domain calls are `P`: they are represented as pipeline stages, not direct service calls. Example: compose needs QA; compose submits or participates in a pipeline that invokes QA, then consumes QA artifacts by ID.

External skill calls are `C`: they are allowed only when declared in the capability manifest, approved by registry policy, and scoped in the execution request.

## 6. Shared Request Context Protocol

Every REST request entering the gateway creates or validates a request context. Every gRPC request carries the same context.

```text
+--------------------+
| RequestContext     |
+--------------------+
| trace_id           | required, globally unique per operator request
| request_id         | required, unique per gateway request
| workspace_id       | required when request touches workspace state
| actor              | required, operator or service identity
| caller_service     | required on gRPC requests
| idempotency_key    | required on mutating REST requests when retryable
| deadline_ms        | required for gRPC calls
| auth_scope         | required after auth is enabled
| redaction_profile  | required for logs and traces
+--------------------+
```

Propagation path:

```text
REST header/body
      |
      v
rbs-gateway validates or creates RequestContext
      |
      v
Tonic metadata: trace_id, request_id, actor, caller_service, deadline_ms
      |
      v
service logs, spans, DB rows, artifacts, and job events carry trace_id
```

Required headers for REST clients:

```text
X-Request-Id: optional; gateway creates one if absent
X-Idempotency-Key: required for retryable mutating requests
Authorization: required when gateway auth is enabled
```

Required Tonic metadata:

```text
x-rbs-trace-id
x-rbs-request-id
x-rbs-caller-service
x-rbs-actor
x-rbs-deadline-ms
```

## 7. Public REST Protocol

REST exists for operators and future clients. It must be stable, ergonomic, and traceable. It must not expose internal service topology details that would prevent service refactoring.

```text
Client
  |
  | HTTP JSON
  v
rbs-gateway
  |
  | validate DTO
  | authenticate actor
  | create RequestContext
  | call gRPC service
  v
backend service
  |
  | protobuf response or typed service error
  v
rbs-gateway
  |
  | map to REST response envelope
  v
Client
```

REST response shape:

```text
Success:
{
  "data": { ... },
  "trace_id": "trc_...",
  "request_id": "req_..."
}

Failure:
{
  "error": {
    "code": "namespace.reason",
    "message": "human-readable summary",
    "details": { },
    "trace_id": "trc_..."
  }
}
```

REST route classes:

```text
/health, /ready, /version, /capabilities
/capabilities/*
/workspaces/*
/jobs/*
/artifacts/*
/fetch/*
/chapters/*
/claims/*
/syntopical/*
```

Protocol rule: REST never returns raw service database IDs unless they are stable public IDs defined in `rbs-core`.

## 8. gRPC Protocol

Every gRPC service follows the same shape:

```text
service <Name>Service
  rpc Health(HealthRequest) returns HealthResponse
  rpc Ready(ReadyRequest) returns ReadyResponse
  rpc <Capability>(<Capability>Request) returns <Capability>Response
```

Capability extension services add:

```text
service CapabilityRegistryService
  rpc RegisterCapability(RegisterCapabilityRequest) returns RegisterCapabilityResponse
  rpc ValidateManifest(ValidateManifestRequest) returns ValidateManifestResponse
  rpc ListCapabilities(ListCapabilitiesRequest) returns ListCapabilitiesResponse
  rpc ResolveCapability(ResolveCapabilityRequest) returns ResolveCapabilityResponse
  rpc EnableCapability(EnableCapabilityRequest) returns EnableCapabilityResponse
  rpc DisableCapability(DisableCapabilityRequest) returns DisableCapabilityResponse

service CapabilityExecutor
  rpc Describe(DescribeRequest) returns DescribeResponse
  rpc Validate(ValidateCapabilityRequest) returns ValidateCapabilityResponse
  rpc DryRun(DryRunCapabilityRequest) returns DryRunCapabilityResponse
  rpc Execute(ExecuteCapabilityRequest) returns ExecuteCapabilityResponse
  rpc Health(HealthRequest) returns HealthResponse
  rpc Ready(ReadyRequest) returns ReadyResponse
```

Every mutating request contains:

```text
context              RequestContext
idempotency_key      string
workspace_id         WorkspaceId, when workspace-scoped
input_artifacts      repeated ArtifactRef, when reading artifacts
expected_versions    repeated VersionGuard, when stale writes matter
```

Every durable output response contains:

```text
context              ResponseContext
result               typed result enum or message
output_artifacts     repeated ArtifactRef
warnings             repeated DomainWarning
```

The `ResponseContext` contains:

```text
trace_id
request_id
service_name
service_version
duration_ms
```

Protocol rule: gRPC responses return `ArtifactRef`, not absolute filesystem paths. Direct file paths are implementation details of `rbs-artifact-svc`.

## 9. Job Protocol

Long-running operations are jobs. The gateway should not hold request threads open for domain work, fetches, LLM calls, or composition.

```text
POST /jobs or workflow route
      |
      v
rbs-gateway
      |
      v
PipelineService.SubmitJob
      |
      v
+------------------+
| pipeline_db      |
| job row          |
| event stream     |
| stage records    |
+------------------+
      |
      v
Pipeline workers invoke services through Tonic
```

Job state machine:

```text
          +---------+
          | Queued  |
          +----+----+
               |
               v
          +---------+       dependency/policy wait       +---------+
          | Running | ------------------------------->   | Blocked |
          +----+----+                                    +----+----+
               |                                              |
      +--------+---------+----------------+                    |
      |                  |                |                    |
      v                  v                v                    |
 +---------+        +---------+      +-----------+             |
 | Success |        | Failed  |      | Cancelled |             |
 +---------+        +---------+      +-----------+             |
      ^                                                     retry/unblock
      |                                                        |
      +--------------------------------------------------------+
```

Job event protocol:

```text
event_id
job_id
stage_id
trace_id
timestamp
severity
event_type
message
artifact_refs[]
service_name
retry_count
```

Minimum event types:

```text
job.accepted
job.started
stage.started
stage.blocked
stage.retrying
stage.succeeded
stage.failed
job.succeeded
job.failed
job.cancelled
artifact.created
policy.denied
```

## 10. Artifact Protocol

Artifacts are the durable exchange format between services. Service responses reference artifacts by ID. Artifact bytes and artifact paths are hidden behind `rbs-artifact-svc`.

```text
producer service
      |
      | ArtifactService.WriteArtifact
      v
+---------------------+       +------------------+
| rbs-artifact-svc    | ----> | artifact_db      |
| validates owner     |       | index/provenance |
| writes atomically   |       +------------------+
| computes sha256     |
+----------+----------+
           |
           v
    +-------------+
    | blob store  |
    +-------------+
```

Artifact reference:

```text
+-------------------+
| ArtifactRef       |
+-------------------+
| artifact_id       |
| workspace_id      |
| artifact_kind     |
| content_type      |
| sha256            |
| version           |
| created_by        |
| created_at        |
+-------------------+
```

Artifact lifecycle:

```text
Proposed -> Validated -> Written -> Indexed -> Referenced -> Archived
     |          |            |          |            |
     |          |            |          |            +-- not deleted by default
     |          |            |          +--------------- queryable metadata
     |          |            +-------------------------- atomic blob write
     |          +--------------------------------------- schema/content checks
     +-------------------------------------------------- service intent
```

Protocol rules:

- Only `rbs-artifact-svc` writes blob bytes.
- Services may hold temporary files only inside their private runtime temp directory.
- Workspace-visible outputs must be written through `ArtifactService`.
- Artifact writes include producer service, trace ID, and source artifact refs.
- Artifact updates are append-only versions unless a service-specific protocol says otherwise.
- Consumers validate artifact kind and content type before reading.

## 11. Persistence Ownership Protocol

Each service owns its database or schema. Cross-service SQL is forbidden. A service can expose read models through gRPC, but other services cannot read its tables.

```text
+-------------------+      owns      +-------------------+
| rbs-workspace-svc | -------------> | workspace_db      |
+-------------------+                +-------------------+

+-------------------+      owns      +-------------------+
| rbs-artifact-svc  | -------------> | artifact_db       |
+-------------------+                +-------------------+

+-----------------------+  owns      +--------------------------+
| rbs-cap-registry-svc  | ---------> | capability_registry_db   |
+-----------------------+            +--------------------------+

+-------------------+      owns      +-------------------+
| rbs-pipeline-svc  | -------------> | pipeline_db       |
+-------------------+                +-------------------+

+-------------------+      owns      +-------------------+
| rbs-fetch-svc     | -------------> | fetch_db          |
+-------------------+                +-------------------+

+-------------------+      owns      +-------------------+
| domain service    | -------------> | domain_db         |
+-------------------+                +-------------------+
```

Migration protocol:

```text
migrations/
  rbs-workspace-svc/
  rbs-artifact-svc/
  rbs-capability-registry-svc/
  rbs-pipeline-svc/
  rbs-fetch-svc/
  rbs-agent-svc/
  rbs-knowledge-svc/
  ...
```

CI must fail when:

- a service imports another service's migration files
- a service opens another service's database URL
- a test relies on cross-service table reads
- a protobuf response exposes private SQL row shape
- a capability manifest grants access to another service's private tables

### 11.1 Capability Extension Protocol

New skills are registered through manifests and executed through service boundaries. The registry controls discovery and scheduling metadata; it does not execute skills.

```text
capability manifest
      |
      | RegisterCapability / ValidateManifest
      v
rbs-capability-registry-svc
      |
      | ResolveCapability
      v
rbs-pipeline-svc
      |
      | CapabilityExecutor.Execute
      v
external or core skill service
      |
      +--> rbs-artifact-svc for durable outputs
      +--> rbs-fetch-svc only when manifest permits fetch.request
      +--> rbs-agent-svc only when manifest permits agent.run
```

Manifest contract:

```text
capability.id
capability.version
capability.runtime
operation.id
operation.kind
input_artifacts[]
output_artifacts[]
params_schema_ref
result_schema_ref
permissions[]
policy
tests
```

Capability states:

```text
draft -> registered -> test_pending -> enabled -> deprecated -> disabled
             |              |
             v              v
          rejected       quarantined
```

Runtime types:

```text
core_service
external_tonic
adapter_sidecar
wasm_sandbox
```

Milestone 1 implements `core_service` and `external_tonic`. `adapter_sidecar` is represented but disabled by default. `wasm_sandbox` is deferred.

## 12. Fetch Protocol

`rbs-fetch-svc` is the only outbound network service. This rule preserves the current `scrapling-fetch` boundary while moving it into native Rust architecture.

```text
caller
  |
  | FetchService.FetchPage / DownloadPdf / ResolvePaper
  v
rbs-fetch-svc
  |
  +--> check mode
  +--> check allow policy
  +--> check cache
  +--> check robots
  +--> check rate limit
  +--> perform outbound request, if allowed
  +--> normalize/extract
  +--> write artifact through rbs-artifact-svc
  +--> return ArtifactRef + fetch audit summary
```

Fetch mode protocol:

```text
Mode       Milestone 1 behavior
--------   ------------------------------------------------------------
Plain      implemented natively in Rust
Stealth    returns fetch.unsupported_mode with mode=Stealth
Dynamic    returns fetch.unsupported_mode with mode=Dynamic
```

Fetch adapters:

```text
arXiv ID        -> metadata lookup -> PDF/page artifacts
OpenAlex ID     -> metadata lookup -> source manifest artifact
SemanticScholar -> metadata lookup -> source manifest artifact
DOI             -> resolver lookup -> canonical URL -> fetch path
URL page        -> HTTP GET -> HTML -> Markdown -> paragraph artifacts
PDF URL         -> streamed download -> sha256 -> PDF artifact
```

Fetch audit record:

```text
trace_id
workspace_id
requested_url
canonical_url
adapter
mode
cache_status
robots_status
rate_limit_status
http_status
content_type
byte_count
sha256
artifact_refs[]
```

Protocol rule: no other crate may depend on outbound HTTP client or browser automation crates unless it is part of `rbs-fetch-svc`.

## 13. Agent Protocol

`rbs-agent-svc` owns non-deterministic external reasoning calls: LLM, subagent, reviewer, entailment, and healer dispatch.

```text
domain service
  |
  | AgentService.RunPacket
  v
rbs-agent-svc
  |
  +--> validate packet schema
  +--> apply redaction profile
  +--> choose provider adapter
  +--> execute or use deterministic test stub
  +--> parse structured response
  +--> write transcript artifact
  +--> return parsed result + ArtifactRef
```

Agent packet protocol:

```text
packet_id
trace_id
workspace_id
purpose
schema_version
input_artifact_refs[]
prompt_template_id
redaction_profile
expected_response_schema
timeout_ms
```

Protocol rules:

- Domain services build packets; they do not call providers directly.
- Test mode uses deterministic stubs.
- Raw provider transcripts are artifacts with redaction metadata.
- Failed parse returns typed `agent.parse_failed`, not an unstructured string.

## 14. Domain Service Protocol

Every domain service follows the same boundary shape:

```text
Input:
  RequestContext
  WorkspaceId
  ArtifactRef[]
  service-specific options

Process:
  validate inputs
  load artifacts through rbs-artifact-svc
  call rbs-agent-svc only if non-deterministic reasoning is required
  write outputs through rbs-artifact-svc
  return typed result and ArtifactRef[]

Output:
  typed verdict/report
  warnings[]
  ArtifactRef[]
  trace_id
```

Skill-to-service mapping:

```text
v1 skill / concern        v2 service             Primary outputs
----------------------    -------------------    -----------------------------
book-knowledge            rbs-knowledge-svc      manifests, claims, wiki, graph
book-thesis               rbs-thesis-svc         thesis tree, support links
syntopical-metabook       rbs-syntopical-svc     topic maps, lenses, gaps
russellian-style          rbs-style-svc          style reports
book-review               rbs-review-svc         persona reviews, panel verdict
review-conductor          rbs-review-svc         panel orchestration config
book-qa                   rbs-qa-svc             D/C defects, QA verdicts
book-compose              rbs-compose-svc        drafts, release bundles
neurosym-forge            rbs-forge-svc          verifier scaffolds/reports
paragraph-weaver          rbs-weaver-svc         paragraph threads/bridges
scrapling-fetch           rbs-fetch-svc          fetched source artifacts
```

## 15. Syntopical Metabook Protocol

`rbs-syntopical-svc` is the knowledge-curation layer above book knowledge. It must preserve the current rule that syntopical outputs live under syntopical ownership and that acquisition goes through fetch.

```text
Pipeline stage: syntopical.acquire
      |
      v
rbs-syntopical-svc
      |
      +--> read current knowledge artifacts
      +--> compute acquisition targets
      +--> call rbs-fetch-svc for external sources
      +--> call rbs-artifact-svc to read/write artifacts
      +--> emit acquisition manifest

Pipeline stage: syntopical.synthesize
      |
      v
rbs-syntopical-svc
      |
      +--> read claim/topic/source artifacts
      +--> build disputed questions
      +--> reconcile concepts
      +--> produce lenses and gap reports
      +--> write syntopical artifacts
```

Syntopical service outputs:

```text
syntopical_acquisition_manifest
topic_map
disputed_question_map
concept_reconciliation_report
lens_catalog
gap_report
governance_report
```

Protocol rules:

- Syntopical acquisition never performs direct HTTP.
- Syntopical outputs must cite input artifact refs.
- Syntopical reports must distinguish source fact, inference, dispute, and gap.
- Syntopical writes are append-only artifact versions unless a governance action supersedes them.

## 16. QA and Review Protocol

QA and review are separate services. Review handles persona and panel judgment. QA handles deterministic and semi-deterministic quality gates.

```text
chapter artifact
      |
      +--> rbs-review-svc
      |       |
      |       +--> optional rbs-agent-svc calls
      |       +--> panel verdict artifact
      |
      +--> rbs-qa-svc
              |
              +--> deterministic lint
              +--> sentinel checks
              +--> optional healer packet through rbs-agent-svc
              +--> QA defect artifact
```

Verdict protocol:

```text
pass
advisory_fail
hard_gate_fail
blocked
```

Protocol rules:

- A hard gate fail must be machine-readable.
- A waiver must reference the exact defect ID and artifact version.
- Healer proposals are proposed transitions, not direct writes to canonical artifacts.
- Review parse failures fail closed.

## 17. Compose Protocol

Composition is late-stage orchestration. It should consume stable artifacts and service verdicts rather than reaching into service internals.

```text
Compose request
      |
      v
rbs-pipeline-svc
      |
      +--> rbs-workspace-svc: load chapter contract
      +--> rbs-artifact-svc: load source artifacts
      +--> rbs-compose-svc: draft/render
      +--> rbs-review-svc: review stage, if requested
      +--> rbs-qa-svc: QA stage, if requested
      +--> rbs-artifact-svc: release bundle
```

Compose outputs:

```text
chapter_draft
chapter_contract_report
release_manifest
release_bundle
```

Protocol rule: compose consumes review and QA outputs by artifact ref. It does not import review or QA code.

## 18. Error Protocol

All services return typed errors. The gateway maps them to the public REST envelope.

```text
Service error namespace examples:

policy.path_traversal
policy.network_denied
workspace.not_found
artifact.not_found
artifact.version_conflict
pipeline.job_not_found
pipeline.job_cancelled
capability.unknown
capability.disabled
capability.permission_denied
capability.schema_invalid
fetch.unsupported_mode
fetch.rate_limited
fetch.robots_denied
fetch.not_pdf
agent.provider_unavailable
agent.parse_failed
qa.hard_gate_failed
review.parse_failed
```

Status mapping:

```text
Service category              REST status
--------------------------    -----------
malformed request             400
auth failure                  401
policy violation              403
unknown resource              404
state/version conflict        409
domain validation failure     422
internal failure              500
dependency unavailable        503
unsupported capability        503
```

Failure propagation:

```text
domain service error
      |
      v
Tonic status + structured detail
      |
      v
rbs-pipeline-svc records job event
      |
      v
rbs-gateway maps to REST envelope
      |
      v
client receives error code + trace_id
```

Protocol rules:

- Errors must include trace ID.
- Internal error messages must be redacted before returning to REST clients.
- Policy violations are not retries.
- Dependency unavailable may be retried by pipeline policy.
- Domain hard gates are successful service executions with failing verdicts, not infrastructure crashes.

## 19. Observability Protocol

Every service emits traces, structured logs, and metrics. Trace propagation is part of the contract.

```text
REST request span
      |
      v
gateway handler span
      |
      v
gRPC client span
      |
      v
service handler span
      |
      v
job stage span
      |
      v
artifact/fetch/agent child spans
```

Required span attributes:

```text
rbs.trace_id
rbs.request_id
rbs.workspace_id
rbs.job_id
rbs.stage_id
rbs.service
rbs.operation
rbs.artifact_id
rbs.error_code
rbs.capability_id
rbs.operation_id
rbs.capability_version
rbs.capability_runtime
```

Required metrics:

```text
http_requests_total
http_request_duration_ms
grpc_requests_total
grpc_request_duration_ms
jobs_queued
jobs_running
jobs_failed_total
artifact_write_bytes
fetch_requests_total
fetch_cache_hits_total
agent_calls_total
policy_denials_total
capability_executions_total
capability_failures_total
```

Protocol rule: no workflow is accepted as production-ready until a trace can be followed from REST entry to final artifact or error.

## 20. Security and Policy Protocol

Security is enforced at the gateway, service boundary, and artifact/write policy layers.

```text
external caller
      |
      v
rbs-gateway
  - auth
  - request validation
  - rate limit
  - trace creation
      |
      v
internal service mesh / local compose network
  - service identity
  - deadline propagation
  - no public service ports by default
      |
      v
owning service
  - policy checks
  - DB ownership
  - artifact ownership
```

Policy rules:

- Only `rbs-gateway` exposes public REST.
- Backend gRPC ports are not public by default.
- Services reject requests missing caller identity.
- Services reject workspace paths that escape owned roots.
- Services reject writes to artifacts they do not own.
- Capability manifests are denied if they request undeclared, forbidden, or boundary-breaking permissions.
- Only `rbs-fetch-svc` performs outbound HTTP/browser automation.
- Only `rbs-agent-svc` performs LLM/provider calls.
- Secrets are supplied through `rbs-config`; they are never stored in artifacts or traces.

## 21. Startup Protocol

Local MSA startup under Docker Compose:

```text
1. start databases / blob store / OpenTelemetry collector
2. run migrations per service
3. start rbs-workspace-svc
4. start rbs-artifact-svc
5. start rbs-capability-registry-svc
6. load enabled capability manifests
7. start rbs-fetch-svc
8. start rbs-agent-svc
9. start domain services and external skill services
10. start rbs-pipeline-svc
11. start rbs-gateway
12. run readiness probes
```

Readiness protocol:

```text
rbs-gateway /ready
      |
      +--> WorkspaceService.Ready
      +--> ArtifactService.Ready
      +--> CapabilityRegistryService.Ready
      +--> PipelineService.Ready
      +--> FetchService.Ready
      +--> AgentService.Ready
      +--> selected domain Ready checks
```

Shutdown protocol:

```text
SIGTERM
  |
  +--> stop accepting new REST/gRPC requests
  +--> mark in-flight jobs as draining
  +--> finish or checkpoint active stages
  +--> flush traces/logs
  +--> close DB pools
  +--> exit
```

## 22. Testing Protocol

Tests prove the protocol, not just implementation details.

```text
+--------------------------+------------------------------------------+
| Test class               | What it proves                           |
+--------------------------+------------------------------------------+
| unit                     | local invariants and pure logic          |
| property                 | IDs, paths, artifact refs, DAG rules     |
| protobuf contract        | gRPC compatibility                       |
| capability manifest      | skill registration and permissions       |
| executor contract        | generic skill execution compatibility    |
| OpenAPI snapshot         | public REST compatibility                |
| Tonic service            | service handler behavior                 |
| Axum handler             | gateway routing and mapping              |
| component                | service + owned DB + artifact mocks      |
| Docker Compose           | cross-service wiring                     |
| end-to-end               | operator workflow through gateway        |
| golden compatibility     | v2 output matches accepted v1 fixtures   |
| policy                   | forbidden imports, network, DB access    |
| observability            | trace propagation                        |
| performance              | latency/throughput smoke and benchmarks  |
+--------------------------+------------------------------------------+
```

Required CI gates:

```text
cargo fmt --check
cargo clippy --workspace --all-targets -- -D warnings
cargo test --workspace
protobuf generation check
protobuf compatibility check
capability manifest validation
capability permission lint
CapabilityExecutor contract test
OpenAPI snapshot check
SQLx migration check
golden fixture check
dependency policy check
trace propagation smoke check
Docker Compose integration smoke check
```

Golden replacement rule:

```text
Python v1 skill can be retired only when:
  1. v2 service exposes equivalent accepted protocol surface
  2. v2 service passes protocol contract tests
  3. v2 service passes golden fixture compatibility tests
  4. v2 service passes policy and observability gates
  5. migration notes document changed behavior, if any
```

## 23. Milestone 1 Vertical Slice Protocol

Milestone 1 should build a real path through the distributed stack, not isolated crates.

```text
Operator
  |
  | POST /workspaces
  v
rbs-gateway
  |
  v
rbs-workspace-svc
  |
  v
workspace_db

Operator
  |
  | POST /fetch/pages
  v
rbs-gateway
  |
  v
rbs-pipeline-svc
  |
  v
rbs-fetch-svc
  |
  v
rbs-artifact-svc
  |
  v
artifact_db + blob store

Operator
  |
  | POST /chapters/:id/qa
  v
rbs-gateway
  |
  v
rbs-pipeline-svc
  |
  v
rbs-qa-svc
  |
  v
rbs-artifact-svc
```

Milestone 1 minimum services:

```text
rbs-core
rbs-proto
rbs-config
rbs-telemetry
rbs-policy
rbs-capability-sdk
rbs-gateway
rbs-workspace-svc
rbs-artifact-svc
rbs-capability-registry-svc
rbs-pipeline-svc
rbs-fetch-svc
rbs-qa-svc
```

Milestone 1 success criteria:

```text
1. create workspace through REST
2. list registered capabilities through REST
3. resolve enabled QA capability through registry
4. submit fetch job through REST
5. fetch Plain mode from local mock server
6. write fetched artifact through artifact service
7. submit QA job over fetched or fixture artifact
8. execute QA through a capability stage
9. write QA report artifact
10. stream job events
11. inspect trace from gateway to registry to service to artifact write
12. pass contract, policy, manifest, executor, and golden smoke tests
```

## 24. Evolution Protocol

The protocol can evolve, but only through versioned changes.

Change classes:

```text
Patch:
  adds optional field
  adds new error code
  adds new endpoint that does not change existing behavior

Minor:
  adds required capability behind new version
  adds new service
  adds new job stage type

Major:
  removes field
  changes field semantics
  changes service ownership
  changes artifact lifecycle
  breaks golden compatibility
```

Compatibility rules:

- Additive protobuf changes are preferred.
- Breaking protobuf changes require versioned package or service.
- REST breaking changes require OpenAPI version update.
- Artifact schema changes require migration and golden fixture update.
- Service ownership changes require a protocol update and ADR.

## 25. Review Checklist

Before implementation planning, verify:

```text
[ ] Every service has one owner and one protocol role.
[ ] Gateway contains no domain logic.
[ ] Pipeline owns orchestration.
[ ] Capability registry owns capability metadata, not execution.
[ ] Domain services do not call each other directly.
[ ] Artifact outputs are handles, not paths.
[ ] Only fetch service has outbound network capability.
[ ] Only agent service has provider/LLM capability.
[ ] Every request carries trace context.
[ ] Every long operation is job-based.
[ ] Every service owns its persistence.
[ ] Every Python skill maps to a Rust service or merged service.
[ ] Every replacement has a golden compatibility rule.
[ ] Arbitrary future skills have manifest, permission, schema, registry, and executor paths.
```

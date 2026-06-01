# Skill Capability Protocol Design

Date: 2026-06-01. Status: accepted extension-plane design, promoted into the core v2 architecture and ASCII protocol.

Related documents:

- `docs/superpowers/specs/2026-05-31-rust-axum-v2-architecture-design.md`
- `docs/superpowers/specs/2026-06-01-rust-microservices-ascii-protocol.md`

## 1. Goal

Add an extension plane that lets Russellian Book Suite v2 register, discover, authorize, schedule, test, and retire arbitrary future skills without changing the gateway or hard-coding every workflow into `rbs-pipeline-svc`.

The protocol must preserve the core v2 boundaries:

- `rbs-gateway` remains the public REST boundary.
- `rbs-pipeline-svc` remains the workflow orchestrator.
- `rbs-artifact-svc` remains the durable artifact boundary.
- `rbs-fetch-svc` remains the only outbound network boundary.
- `rbs-agent-svc` remains the only LLM/provider boundary.
- Services communicate through Tonic/gRPC.
- Durable data is owned by one service; cross-service SQL remains forbidden.

## 2. Non-goals

- Do not hot-load arbitrary code into `rbs-gateway` or `rbs-pipeline-svc`.
- Do not let a skill bypass `rbs-artifact-svc` for durable outputs.
- Do not let a skill perform direct HTTP, browser automation, or LLM calls unless the protocol routes them through `rbs-fetch-svc` or `rbs-agent-svc`.
- Do not make arbitrary skills trusted by default.
- Do not require every experimental skill to become a first-class core service before it can be tested.
- Do not design a public marketplace in milestone 1. The protocol should not prevent one later, but it is not required now.

## 3. Design Choice

Three extension strategies were considered.

```text
+---------------------------+--------------------+--------------------------+
| Strategy                  | Flexibility        | Risk                     |
+---------------------------+--------------------+--------------------------+
| Core-only Rust services   | medium             | low runtime risk, slow   |
| Host-loaded plugins       | high               | high safety/debug risk   |
| Manifest + external svc   | high               | moderate ops complexity  |
+---------------------------+--------------------+--------------------------+
```

Recommended: manifest plus external service registration.

New skills run as separate services or adapters. They publish a signed or locally trusted manifest, expose a generic Tonic executor protocol, and are scheduled by `rbs-pipeline-svc` after `rbs-capability-registry-svc` validates their manifest and policy. Core suite services can also publish capability manifests, so the same scheduling model works for built-in and future skills.

## 4. Capability Plane Topology

```text
                         REST
                   +-------------+
Operator / CLI --->| rbs-gateway |
                   +------+------+
                          |
                          | Tonic
                          v
                   +-------------+
                   | rbs-pipeline|
                   | -svc        |
                   +------+------+             +--------------------+
                          |                    | rbs-capability     |
                          | ResolveCapability | -registry-svc      |
                          +------------------->| manifests, policy, |
                          |                    | versions, health   |
                          |                    +---------+----------+
                          |                              |
                          | ExecuteCapability            | Describe/Health
                          v                              v
             +------------------------+        +------------------------+
             | first-class suite svc  |        | external skill svc     |
             | or generic executor    |        | / adapter sidecar      |
             +-----------+------------+        +-----------+------------+
                         |                                 |
                         +--------------+------------------+
                                        |
                                        v
                              +------------------+
                              | rbs-artifact-svc |
                              +------------------+
```

## 5. New Platform Service

### `rbs-capability-registry-svc`

Purpose: authoritative registry for capabilities, operations, versions, permissions, schemas, endpoints, test obligations, health state, and deprecation status.

Responsibilities:

- validate capability manifests
- store enabled/disabled/deprecated state
- resolve capability IDs and operation IDs to callable endpoints
- expose capability discovery to the gateway
- provide scheduling metadata to the pipeline
- enforce capability compatibility policy
- record health/readiness for external skill services
- reject capabilities that request forbidden permissions

Non-responsibilities:

- does not execute skills
- does not store skill artifacts
- does not own domain-specific skill data
- does not call LLM providers or outbound network

## 6. Capability Identity

Capability IDs are stable, namespaced, and semver-versioned.

```text
capability_id:  rbs.qa.lint
operation_id:   rbs.qa.lint.artifact
version:        2.0.0
provider:       rbs-core-suite
runtime:        core_service | external_tonic | adapter_sidecar
```

ID rules:

- IDs are lowercase dotted names.
- `rbs.*` is reserved for suite-owned capabilities.
- Third-party or local experimental skills use `local.*`, `lab.*`, or an organization namespace.
- Operation IDs are more specific than capability IDs.
- A capability may expose multiple operations.
- Semver applies to operation contracts, not just service binaries.

## 7. Capability Manifest

Every skill publishes a manifest. The manifest is the skill's contract with the platform.

```yaml
manifest_version: 1
capability:
  id: rbs.qa
  name: Book QA
  version: 2.0.0
  provider: rbs-core-suite
  maturity: core
  runtime: core_service
  endpoint:
    service_name: rbs-qa-svc
    protocol: tonic
    address_ref: service:rbs-qa-svc

operations:
  - id: rbs.qa.lint_artifact
    name: Lint artifact
    kind: job_stage
    deterministic: true
    idempotent: true
    input_artifacts:
      - kind: chapter_draft
        required: true
    output_artifacts:
      - kind: qa_report
        required: true
    params_schema_ref: schema:rbs.qa.lint_params.v1
    result_schema_ref: schema:rbs.qa.lint_result.v1
    timeout_ms: 120000
    retry:
      max_attempts: 1
    permissions:
      - artifact.read:chapter_draft
      - artifact.write:qa_report
      - agent.run:healer_packet
    policy:
      requires_workspace: true
      allow_live_network: false
      allow_direct_provider_calls: false

tests:
  contract_fixtures:
    - tests/fixtures/capabilities/rbs.qa/lint_artifact.json
  golden_fixtures:
    - tests/golden/rbs.qa/lint_artifact/
```

Manifest sections:

```text
capability     identity, owner, runtime, maturity, endpoint
operations     callable units scheduled by the pipeline
schemas        request, params, result, artifact, and error schemas
permissions    declared access needs
policy         enforcement hints and hard requirements
resources      timeout, memory, CPU, concurrency, retries
observability  expected spans, metrics, redaction profile
tests          contract, golden, policy, and integration fixtures
deprecation    replacement capability and removal schedule
```

## 8. Runtime Types

```text
+------------------+----------------------------------------------------+
| Runtime type     | Use                                                |
+------------------+----------------------------------------------------+
| core_service     | built-in suite services such as QA, review, fetch  |
| external_tonic   | independently deployed Rust or non-Rust service    |
| adapter_sidecar  | migration or experimental wrapper around old code  |
| wasm_sandbox     | deferred option for pure deterministic transforms  |
+------------------+----------------------------------------------------+
```

Milestone 1 implements `core_service` and `external_tonic`. `adapter_sidecar` may be represented in the manifest model but should remain disabled by default. `wasm_sandbox` is explicitly deferred.

## 9. Generic Executor Protocol

Arbitrary external skills implement a generic Tonic service. Core services may expose specialized APIs and also register generic capability operations.

```text
service CapabilityExecutor {
  rpc Describe(DescribeRequest) returns DescribeResponse;
  rpc Validate(ValidateCapabilityRequest) returns ValidateCapabilityResponse;
  rpc DryRun(DryRunCapabilityRequest) returns DryRunCapabilityResponse;
  rpc Execute(ExecuteCapabilityRequest) returns ExecuteCapabilityResponse;
  rpc Health(HealthRequest) returns HealthResponse;
  rpc Ready(ReadyRequest) returns ReadyResponse;
}
```

Execution request:

```text
ExecuteCapabilityRequest
  context: RequestContext
  capability_id: string
  operation_id: string
  version_constraint: string
  workspace_id: WorkspaceId
  input_artifacts: ArtifactRef[]
  params_json: JsonValue
  idempotency_key: string
  deadline_ms: u64
```

Execution response:

```text
ExecuteCapabilityResponse
  context: ResponseContext
  verdict: CapabilityVerdict
  output_artifacts: ArtifactRef[]
  warnings: DomainWarning[]
  metrics: CapabilityMetric[]
  result_json: JsonValue
```

Verdicts:

```text
success
advisory_fail
hard_gate_fail
blocked
unsupported
invalid_input
```

## 10. Scheduling Protocol

The pipeline schedules capabilities by manifest, not by hard-coded service calls.

```text
JobSpec
  |
  +--> stage: capability
          capability_id: rbs.qa
          operation_id: rbs.qa.lint_artifact
          version: ">=2.0,<3.0"
          input_artifacts: [...]
          params: {...}
```

Execution flow:

```text
rbs-pipeline-svc
      |
      | ResolveCapability(capability_id, operation_id, version)
      v
rbs-capability-registry-svc
      |
      | endpoint + permissions + schemas + runtime type
      v
rbs-pipeline-svc
      |
      | validate input refs and permission envelope
      v
capability executor service
      |
      | read/write through rbs-artifact-svc
      v
artifact refs returned to pipeline
```

Pipeline rules:

- unknown capability fails before execution
- disabled capability fails before execution
- deprecated capability emits warning or fails depending on policy
- manifest permissions are checked before execution
- operation schemas are validated before execution
- output artifact kinds must match manifest declarations
- every capability stage emits job events and traces

## 11. Permission Protocol

Capabilities must declare all required permissions. Undeclared access is denied.

```text
artifact.read:<kind>
artifact.write:<kind>
workspace.read
workspace.write:<scope>
fetch.request:<adapter_or_mode>
agent.run:<packet_kind>
secret.read:<secret_name>
subprocess.run:<profile>
network.none
```

Hard rules:

- `network.direct` is forbidden in ordinary capabilities.
- External source acquisition goes through `rbs-fetch-svc`.
- LLM/provider calls go through `rbs-agent-svc`.
- Artifact writes go through `rbs-artifact-svc`.
- Database access is only to the service's own DB/schema.
- A capability cannot expand its permissions at runtime.
- Permission changes are semver-significant.

## 12. Registration Protocol

Registration is explicit. A service is not callable merely because it is reachable on the network.

```text
1. capability package/service publishes manifest
2. admin or deployment submits manifest to registry
3. registry validates schema and IDs
4. registry checks permissions against policy
5. registry checks endpoint health/readiness
6. registry records capability as registered but disabled
7. contract tests and policy tests run
8. operator enables capability
9. pipeline may schedule capability stages
```

Registration states:

```text
draft -> registered -> test_pending -> enabled -> deprecated -> disabled -> removed
             |              |
             v              v
          rejected       quarantined
```

## 13. Discovery Protocol

Gateway discovery reads from the registry.

REST:

```text
GET /capabilities
GET /capabilities/:capability_id
GET /capabilities/:capability_id/operations
POST /capabilities/register        admin only
POST /capabilities/:id/enable      admin only
POST /capabilities/:id/disable     admin only
```

Tonic registry service:

```text
RegisterCapability
ValidateManifest
ListCapabilities
GetCapability
ResolveCapability
EnableCapability
DisableCapability
DeprecateCapability
CheckCapabilityHealth
```

## 14. Schema Protocol

The platform needs both JSON schemas and protobuf contracts.

Use protobuf for:

- registry service APIs
- executor service APIs
- pipeline scheduling APIs
- stable typed IDs and artifact refs

Use JSON Schema for:

- capability params
- generic result payloads
- artifact content contracts
- fixtures readable by operators and tests

Rule: the generic executor carries `params_json` and `result_json`, but the manifest must identify schemas for both. Core suite services may expose strongly typed protobuf APIs in addition to the generic executor.

## 15. Artifact Kind Protocol

Capabilities declare the artifact kinds they consume and produce.

```text
artifact_kind:
  id: qa_report
  version: 1
  content_type: application/json
  schema_ref: schema:rbs.qa.report.v1
  owner_capability: rbs.qa
```

Artifact rules:

- new artifact kinds require registry validation
- artifact kinds are versioned
- output artifact kinds must be declared in the operation manifest
- artifact schema changes require golden fixture updates
- a capability may read generic kinds and write only declared owned kinds unless granted exception

## 16. Maturity Levels

```text
experimental  callable only with explicit flag; no retirement of v1 code
beta          can run in normal workflows, but not as sole gate
stable        can be used as a normal workflow dependency
core          suite-owned, supported by standard CI and migration policy
deprecated    still callable, emits warnings, replacement declared
disabled      not callable
```

Graduation gates:

```text
experimental -> beta:
  manifest validates
  executor contract tests pass
  policy tests pass

beta -> stable:
  golden fixtures pass
  trace propagation test passes
  failure-mode tests pass
  artifact schemas versioned

stable -> core:
  accepted by architecture decision
  owned by suite maintainers
  included in normal CI
  documented migration/compatibility rules
```

## 17. Security Model

The extension plane is a zero-trust boundary.

```text
untrusted skill package
      |
      v
manifest validation
      |
      v
permission policy check
      |
      v
contract tests
      |
      v
disabled registration
      |
      v
operator enablement
      |
      v
pipeline execution with scoped credentials
```

Required controls:

- backend services are not public by default
- capability endpoints require service identity
- manifest registration requires admin authority
- skill credentials are scoped to declared permissions
- secrets are referenced by name, not embedded in manifests
- skill logs/traces use the platform redaction profile
- failed or misbehaving capabilities can be quarantined

## 18. Observability Protocol

Capability execution must look like native workflow execution.

Required span attributes:

```text
rbs.capability_id
rbs.operation_id
rbs.capability_version
rbs.capability_runtime
rbs.capability_maturity
rbs.job_id
rbs.stage_id
rbs.workspace_id
rbs.error_code
```

Required job events:

```text
capability.resolved
capability.permission_checked
capability.started
capability.artifact_read
capability.artifact_written
capability.succeeded
capability.failed
capability.quarantined
```

## 19. Testing Protocol

Every capability must bring tests with it.

Required test classes:

```text
manifest schema test
permission policy test
executor contract test
input schema validation test
output schema validation test
artifact kind compatibility test
golden fixture test
trace propagation test
failure-mode test
registration lifecycle test
```

Core CI gates added by this protocol:

```text
cargo test -p rbs-capability-registry-svc
protobuf compatibility check for capability registry/executor APIs
manifest validation over capabilities/**/*.yaml
permission lint over capability manifests
golden fixture smoke for enabled stable/core capabilities
unknown capability scheduling test
disabled capability scheduling test
trace propagation over generic capability execution
```

## 20. Repository Layout Additions

```text
russellian-book-suite/
  crates/
    rbs-capability-registry-svc/
    rbs-capability-sdk/
  proto/
    rbs/v1/capability_registry.proto
    rbs/v1/capability_executor.proto
  capabilities/
    rbs.qa.yaml
    rbs.review.yaml
    rbs.syntopical.yaml
    local.example.yaml
  schemas/
    capabilities/
      rbs.qa.lint_params.v1.schema.json
      rbs.qa.lint_result.v1.schema.json
  migrations/
    rbs-capability-registry-svc/
  tests/
    fixtures/
      capabilities/
    golden/
      capabilities/
```

## 21. Migration Impact

Current first-class services become registered capabilities:

```text
rbs-fetch-svc       -> rbs.fetch.*
rbs-qa-svc          -> rbs.qa.*
rbs-review-svc      -> rbs.review.*
rbs-style-svc       -> rbs.style.*
rbs-knowledge-svc   -> rbs.knowledge.*
rbs-thesis-svc      -> rbs.thesis.*
rbs-syntopical-svc  -> rbs.syntopical.*
rbs-compose-svc     -> rbs.compose.*
rbs-forge-svc       -> rbs.forge.*
rbs-weaver-svc      -> rbs.weaver.*
```

The pipeline can still have optimized built-in stage handlers for core services, but it should resolve stage metadata through the registry. This keeps one control plane for core and arbitrary skills.

## 22. Milestone Plan

### Milestone A: Static registry

- Add manifest schema.
- Add local manifest files for core services.
- Add registry service with list/get/resolve operations.
- Add gateway `/capabilities` backed by registry.
- Add policy tests for forbidden permissions.

### Milestone B: Generic executor

- Add `CapabilityExecutor` protobuf.
- Add Rust SDK helpers for external skills.
- Add pipeline generic capability stage.
- Add in-process test executor.
- Add unknown/disabled capability tests.

### Milestone C: External skill service

- Add one example external skill service.
- Register it through manifest.
- Execute it through pipeline.
- Prove artifact read/write through `rbs-artifact-svc`.
- Prove trace propagation.

### Milestone D: Graduation workflow

- Add maturity transitions.
- Add golden fixture enforcement.
- Add quarantine/disable flow.
- Add deprecation and replacement metadata.

## 23. Architecture Changes Required

The current v2 architecture has been updated to add:

- `rbs-capability-registry-svc` as a platform service.
- `rbs-capability-sdk` as an optional helper crate.
- `CapabilityRegistryService` and `CapabilityExecutor` protobuf APIs.
- `capabilities/` and `schemas/capabilities/` repository roots.
- `rbs-pipeline-svc` support for generic capability stages.
- gateway capability-management REST endpoints.
- CI gates for manifests, permissions, and generic executor contracts.

## 24. Review Checklist

```text
[ ] New skills can be added without modifying gateway route code.
[ ] New skills can be scheduled without hard-coding pipeline branches.
[ ] New skills cannot bypass artifact/fetch/agent boundaries.
[ ] Capability permissions are declared and enforceable.
[ ] Capability params/results are schema-validated.
[ ] Unknown, disabled, deprecated, and unsupported capabilities have typed failures.
[ ] Core services and arbitrary services share one discovery model.
[ ] The design supports external Rust services first.
[ ] Legacy sidecars are possible but disabled by default.
[ ] A future marketplace is not required but not blocked.
```

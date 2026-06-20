# Capability: homoiconic-kg delta

## ADD Requirements

### Requirement: REQ-KG-047 - Design-intelligence entities declared (Ubiquitous)

The framework SHALL declare design-intelligence graph entities for requirements,
design decisions, tests, CI workflows, CI jobs, operator commands, and
traceability links in the unified EDN schema.

Rationale: code and claims are already graph-shaped, but agents need design
intent, test coverage, and CI gates in the same query surface to improve the
repo safely.

#### Scenario: schema declares the design-intelligence entity set

- **WHEN** `kg-schema.edn` is parsed
- **THEN** it declares `design-requirement`, `design-decision`, `test-case`,
  `ci-workflow`, `ci-job`, `operator-command`, and `traceability-link`
- **AND** each entity has a stable identity attribute and source provenance

### Requirement: REQ-KG-048 - OpenSpec and design docs project into the graph (Event-driven)

When the design-intelligence projection step runs, the framework SHALL project
OpenSpec requirements, scenarios, design decisions, risks, non-goals,
alternatives, and operator commands into the unified graph with source file and
line provenance.

Rationale: an agent cannot use a design claim safely unless it can trace the
claim back to authored text.

#### Scenario: authored design records become graph rows

- **WHEN** the projection runs on a fixture containing an OpenSpec requirement,
  a design decision, a risk, a non-goal, and a documented command
- **THEN** each authored record appears as a graph row with source path and line
- **AND** the source files are byte-identical before and after projection

### Requirement: REQ-KG-049 - Traceability links are evidence-first (Ubiquitous)

The framework SHALL store traceability links with kind, confidence, witness,
provenance, and promoted status, and SHALL treat only deterministic or reviewed
links as canonical.

Rationale: unreviewed model-inferred links can manufacture false design
relationships; preserving them as evidence keeps them inspectable without making
them authoritative.

#### Scenario: weak link remains evidence-only

- **WHEN** a requirement and a code node have only a lexical or semantic match
- **THEN** the graph stores a `traceability-link` with `promoted=false`
- **AND** canonical queries exclude it unless they explicitly ask for evidence

### Requirement: REQ-KG-050 - Tests and CI project into the graph (Event-driven)

When the test-and-CI projection step runs, the framework SHALL project test
cases, workflows, jobs, matrix selectors, required checks, and documented command
invocations into the unified graph.

Rationale: design utility depends on knowing not only what code exists, but what
tests and CI gates protect it.

#### Scenario: CI required gate is queryable

- **WHEN** the projection runs on a fixture workflow with a required aggregator
  job
- **THEN** the workflow, job, and required-gate status are graph rows
- **AND** the command or matrix selector that causes the job to run is queryable

### Requirement: REQ-KG-051 - Design analysis queries exist (Ubiquitous)

The framework SHALL provide named graph queries for impact, rationale,
coverage-gaps, stale-docs, untested-god-nodes, claim-grounding, and CI gates.

Rationale: named queries make the graph operational for agents; otherwise the
graph remains an internal data structure.

#### Scenario: coverage query names unsupported requirements

- **WHEN** `coverage-gaps` runs on a graph containing a requirement with no
  promoted implementation, test, or CI link
- **THEN** the query returns that requirement with its source path and line

### Requirement: REQ-KG-052 - Agent answers cite graph provenance (Ubiquitous)

The design-intelligence query surface SHALL return source-backed paths through
the graph, including node ids, edge kinds, source files, and line numbers for
every answer row.

Rationale: graph answers are useful to agents only when they are auditable.

#### Scenario: impact query returns evidence paths

- **WHEN** an agent asks for the impact of a code symbol
- **THEN** the result includes affected requirements, tests, CI jobs, claims, and
  design decisions
- **AND** each row includes the source path and line for the graph evidence

### Requirement: REQ-KG-053 - Design projection is deterministic and read-only (Ubiquitous)

The design-intelligence projection SHALL be a deterministic, read-only function
of a git snapshot and graphify snapshot.

Rationale: design audit outputs and golden tests are meaningful only when the
same inputs produce the same rows without mutating source artifacts.

#### Scenario: repeated projection matches byte-for-byte

- **WHEN** the projection runs twice on the same fixture snapshot
- **THEN** the canonically ordered projected rows are byte-identical
- **AND** all input files are byte-identical before and after projection

### Requirement: REQ-KG-054 - Graphify community coverage is reported (Event-driven)

When a design-intelligence audit runs, the framework SHALL map graphify
communities to requirements, tests, CI jobs, claims, design decisions, and open
risks, and SHALL flag high-centrality communities with missing coverage.

Rationale: graphify communities are the practical unit for whole-repo design
review; every high-centrality community needs explicit coverage.

#### Scenario: uncovered high-centrality community is flagged

- **WHEN** a high-centrality graphify community has code nodes but no promoted
  requirement, test, CI, claim, or design-decision links
- **THEN** the coverage report flags the community as uncovered

### Requirement: REQ-KG-055 - Ambiguous design links are not promoted (Unwanted)

If a traceability candidate is ambiguous, then the framework SHALL store all
candidates as evidence and SHALL NOT promote any candidate without deterministic
disambiguation or review.

Rationale: a false canonical link can send an agent to change the wrong
abstraction or claim unsupported coverage.

#### Scenario: multiple symbol matches stay unpromoted

- **WHEN** a requirement mentions a symbol name that resolves to multiple
  graphify code nodes
- **THEN** each candidate is stored as evidence-only
- **AND** no candidate appears in canonical traceability queries

### Requirement: REQ-KG-056 - Design graph snapshot is reproducible (Ubiquitous)

The framework SHALL document the commands, graphify version, source commit, and
projection inputs used to build a design-intelligence graph snapshot.

Rationale: a graph used by agents to improve design must be reproducible, or its
findings cannot be reviewed later.

#### Scenario: snapshot metadata identifies its inputs

- **WHEN** the design-intelligence audit artifact is generated
- **THEN** it records the git commit, graphify version, projection commands,
  graph node/edge counts, and generated report paths

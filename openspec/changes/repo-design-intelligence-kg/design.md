# Design: repo-design-intelligence-kg

## Goal

Build a unified graph that helps agents study and improve the repository design.
The graph must connect code, claims, requirements, design decisions, tests, CI
gates, and operator workflows with file and line provenance.

The graph should answer design questions, not merely retrieve nearby text.

## Existing assets

- `graphify-out/graph.json` gives the source code topology.
- `skills/book-knowledge/scripts/project_graphify.py` projects graphify nodes and
  edges into `code-node` and `code-edge`.
- `skills/book-knowledge/scripts/code_claim_autolink.py` materializes
  deterministic code-to-claim links and link evidence.
- `skills/book-knowledge/assets/kg-schema.edn` is the unified schema contract.
- `openspec/specs/homoiconic-kg/spec.md` already defines the EDN-front,
  Cozo-back substrate and conformance harness.
- `docs/superpowers/specs/2026-06-16-comprehensive-audit-design.md` already
  uses graphify communities as audit coverage anchors.

## Ontology additions

Add these entity families to `kg-schema.edn` in the implementation phase:

- `design-requirement`: one EARS requirement from OpenSpec, with source path,
  line, capability, requirement id, status, and text.
- `design-decision`: one explicit decision, rationale, alternative, non-goal,
  risk, or switch trigger from specs, plans, README, or runbooks.
- `test-case`: one pytest, Rust, cljs, or shell-check test case with file, line,
  framework, and name.
- `ci-workflow` and `ci-job`: one GitHub Actions workflow/job, including whether
  it is required or advisory and what paths or matrix rows select it.
- `operator-command`: one documented command from runbooks or Make/Nix entry
  points.
- `traceability-link`: a typed edge connecting any two graph nodes with kind,
  confidence, witness, provenance, and promoted flag.

The `traceability-link` relation is evidence-first. A weak candidate is stored,
but not treated as canonical until deterministic evidence or review promotes it.

## Link kinds

Canonical link kinds:

- `requirement-implemented-by`: requirement to code node.
- `requirement-covered-by`: requirement to test case.
- `requirement-gated-by`: requirement to CI job.
- `decision-constrains`: design decision to code node, workflow, or requirement.
- `claim-supported-by-code`: claim to code node through existing
  code-claim-link semantics.
- `test-exercises-code`: test case to code node.
- `workflow-runs-test`: CI job to test case or command.
- `command-touches-artifact`: operator command to path or graph entity.

Evidence-only link kinds:

- `mentions-symbol`
- `mentions-path`
- `mentions-requirement`
- `similar-to`
- `possible-stale-doc`
- `possible-coverage-gap`

## Extraction passes

### P1: OpenSpec extractor

Read `openspec/specs/**/spec.md` and `openspec/changes/**/specs/**/spec.md`.
Emit `design-requirement` rows with stable IDs. Detect EARS headings, scenarios,
and cited test names.

### P2: Design-doc extractor

Read README, AGENTS, CLAUDE, docs/specs, docs/operations, docs/superpowers, and
change `proposal.md`/`design.md`/`tasks.md`. Emit design decisions, risks,
non-goals, alternatives, commands, and ownership rules. Keep every node tied to a
source file and line.

### P3: Test and CI extractor

Read tests, Makefile, Nix files, `.github/workflows/*.yml`,
`.github/ci/skills-matrix.json`, and `ci/compute_matrix.py`. Emit test cases,
workflows, jobs, and selection rules.

### P4: Traceability linker

Link requirements to code/tests/CI by deterministic evidence first:

- exact REQ ID mention
- exact file path mention
- exact symbol mention resolved by graphify
- test name cited in a requirement scenario
- CI job command invokes a known test path or Make/Nix target

Store weaker lexical/semantic matches as `traceability-link` rows with
`promoted=false`.

### P5: Query pack

Add a small script surface that runs named graph queries through `cozo_store`:

- `impact <symbol-or-path>`
- `why <symbol-or-requirement>`
- `coverage-gaps`
- `stale-docs`
- `untested-god-nodes`
- `claim-grounding <symbol-or-claim>`
- `ci-gates <capability-or-path>`

Every query result must include source file and line evidence.

### P6: Design audit report

Generate `docs/audits/<date>-design-intelligence-kg/` with:

- `README.md`: graph snapshot, top risks, go/no-go.
- `coverage-map.md`: graphify communities mapped to requirements, tests, CI,
  claims, and docs.
- `findings.md`: source-backed design issues.
- `queries.md`: query pack outputs that support the findings.

## Quality gates

- Extractors are read-only and deterministic over a git snapshot.
- Generated rows use canonical ordering before golden comparison.
- Weak inferred links never become canonical automatically.
- Every graph answer cites file and line provenance.
- Stale-doc and coverage-gap findings require a graph path plus a source anchor.
- The conformance harness must fail loudly on backend divergence.

## Agent workflow

Agents should use the graph as a planning and review tool:

1. Ask `impact` before changing a file or symbol.
2. Ask `why` before refactoring a high-centrality abstraction.
3. Ask `coverage-gaps` before claiming a subsystem is tested.
4. Ask `ci-gates` before changing workflow selection or matrix logic.
5. Record new design decisions in OpenSpec so the next extraction pass sees them.

The graph is advisory until its conformance tests pass. It should improve agent
orientation, not replace code review or tests.

# Capability delta: induction-grammar — change: tier6-induction-grammar

This change introduces a new capability `induction-grammar`,
the framework's BookLogic grammar enforcer + LLM proposer
interface. The enforcer gates every LLM-generated candidate
constraint AGAINST `booklogic-schema.edn` BEFORE any Z3 or
Cozo invocation. Rejected proposals never reach a solver.

## ADD

### REQ-INDUCE-040 — Ubiquitous

The framework SHALL ship
`skills/neurosym-forge/scripts/_induction_grammar.cljs`
exposing `grammar-conforming?(edn-form, schema) -> bool`
that returns `true` iff the form is a valid BookLogic
`defconstraint` AST referencing only predicates declared in
`schema`. The accepted grammar SHALL be encoded as a
top-level `^:const` BNF block in the same file.

**Rationale:** The LLM must never invent the language. A
mechanical grammar gate, sourced from one place in the code,
is the single source of truth for what shape a candidate may
take.
**Tested by:** `tests/test_induction_grammar.py::test_valid_defconstraint_passes` and `::test_bnf_block_is_top_level_const` (added in V1.2, V1.3).

### REQ-INDUCE-041 — Optional feature

WHERE the LLM proposer is invoked, it SHALL receive
(a) the schema's predicates with sorts and return types,
(b) a focused atom cluster from Phase Q `SemanticIndex`,
(c) the BookLogic grammar BNF as a system-prompt section.
The proposer SHALL produce a single EDN form per call.

**Rationale:** The prompt scaffold is the LLM's contract.
Embedding the BNF in the system prompt narrows the candidate
distribution before any output token is emitted; the focused
cluster keeps the prompt under the context budget.
**Tested by:** `tests/test_induction_grammar.py::test_proposer_prompt_embeds_schema_and_bnf` (added in V3.2).

### REQ-INDUCE-042 — Unwanted behaviour

IF the LLM proposer returns a non-EDN string, an EDN form
whose head is not `defconstraint`, an EDN form referencing
predicates outside the schema, an arg whose sort does not
match the predicate's declared signature, or an operator
outside the BNF, THEN the grammar enforcer SHALL reject the
form with a structured error tagged
`:grammar-fail/non-edn`, `:grammar-fail/wrong-head`,
`:grammar-fail/unknown-predicate`,
`:grammar-fail/wrong-sort`, or `:grammar-fail/illegal-op`
respectively. NO Z3 or Cozo invocation SHALL be made on a
rejected form.

**Rationale:** Five disjoint failure categories, named at
the point of rejection, let the orchestrator's failure log
distinguish "the LLM hallucinated a predicate" from "the LLM
emitted prose instead of EDN". Burning a solver call on a
rejected form is wasted budget AND obscures the failure
mode.
**Tested by:** `tests/test_induction_grammar.py::test_each_failure_category_rejects_and_tags` (added in V2.2).

### REQ-INDUCE-043 — Ubiquitous

The LLM proposer SHALL reuse
`skills/neurosym-forge/scripts/_llm_lift.py`'s
`LLMLiftProvider` abstraction; backend selection SHALL be
controlled by `NEUROSYM_LLM_PROVIDER` env var with values
`stub` | `openai` | `anthropic` | `local`. The Stub
provider SHALL read deterministic candidates from
`tests/fixtures/llm-responses/constraint-*.edn`.

**Rationale:** Phase P already shipped a provider
abstraction with key handling, header scrubbing, and a stub
responder. Reusing it keeps the security surface centralised
and lets the test suite run offline by default.
**Tested by:** `tests/test_induction_grammar.py::test_stub_provider_produces_deterministic_candidate` (added in V3.3).

### REQ-INDUCE-044 — Optional feature

WHERE `NEUROSYM_INDUCTION_DRY_RUN=1` is set, the proposer
SHALL print candidates to stdout in ordered EDN form AFTER
grammar validation but BEFORE solver dispatch; NO Cozo or
Z3 call SHALL be made.

**Rationale:** A debugging affordance for iterating on the
schema-to-prompt transformation, capturing regression
fixtures, and validating prompt-template changes without
paying solver cost.
**Tested by:** `tests/test_induction_grammar.py::test_dry_run_prints_candidates_and_skips_solvers` (added in V4.1).

### REQ-INDUCE-045 — Ubiquitous

A test suite SHALL exercise: (a) a valid `defconstraint`
form passes the grammar; (b) a form with an invalid head
fails; (c) a form citing an unknown predicate fails; (d) a
form with an out-of-schema arg sort fails; (e) the Stub
provider produces a deterministic candidate identical
across runs.

**Rationale:** Five orthogonal tests cover the five failure
categories plus the stub-determinism property. Without this
suite the grammar enforcer is unverifiable; the failure
categories degrade silently as the BNF evolves.
**Tested by:** `tests/test_induction_grammar.py::{test_valid_defconstraint_passes,test_each_failure_category_rejects_and_tags,test_stub_provider_produces_deterministic_candidate}` (added in V1.3, V2.2, V3.3).

### REQ-INDUCE-046 — Unwanted behaviour

IF the grammar BNF reference in
`_induction_grammar.cljs` drifts from the operator dispatch
list in `codegen_axioms.py` (e.g., codegen adds `(mod a b)`
without a matching BNF entry), THEN the drift lint
`tests/test_induction_grammar_drift.py` SHALL fail at
`make lint` with a structured message naming the missing
operator.

**Rationale:** Two sources of truth for the operator set
guarantees they drift; a lint catches the drift before the
inducer silently rejects candidates the codegen would
accept. Mirrors the SUPPORT_MATRIX drift lint from Tier 5.
**Tested by:** `tests/test_induction_grammar_drift.py::test_lint_fails_when_codegen_adds_op_without_bnf_entry` (added in V4.2, V4.3).

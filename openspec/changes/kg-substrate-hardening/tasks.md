# Tasks

- [x] Define committed substrate conformance fixtures over authored EDN queries and frozen relation rows. (REQ-KG-041, REQ-KG-042)
- [x] Add a pure-Python reference evaluator for the declared `defquery-basic-v1` subset. (REQ-KG-042, REQ-KG-043)
- [x] Add the conformance harness that loads fixtures through `CozoStore.load` and runs EDN through `CozoStore.query_edn`. (REQ-KG-041, REQ-KG-043)
- [x] Canonicalize result rows as backend-order-independent multisets. (REQ-KG-044)
- [x] Fail loudly on divergence with fixture name plus `cozo_only` and `reference_only` rows. (REQ-KG-046)
- [x] Document the backend switch-trigger list. (REQ-KG-045)
- [x] Cover every requirement with exact-name tests in `tests/test_substrate_conformance.py`. (REQ-KG-041, REQ-KG-042, REQ-KG-043, REQ-KG-044, REQ-KG-045, REQ-KG-046)

# KG Contradiction Workbench Tasks

- [x] Document normalized helper provenance, subject/predicate keys, unit registry, symbolic rules, and NLI seam behavior. (REQ-KG-021..027)
- [x] Declare the four helper relations in `kg-schema.edn`. (REQ-KG-021)
- [x] Add the deterministic normalized-fact parser and project helper rows from the existing ledger. (REQ-KG-021, REQ-KG-025)
- [x] Add EDN-authored workbench rule declarations and compile them to CozoScript through `booklogic_kg`. (REQ-KG-022, REQ-KG-023, REQ-KG-025)
- [x] Implement quantity clash, interval inconsistency, and supersession checks. (REQ-KG-022, REQ-KG-023, REQ-KG-024)
- [x] Implement injected NLI residue routing and seam-down unresolved behavior. (REQ-KG-026, REQ-KG-027)
- [x] Cover every S4 requirement and canonical correctness case with `tests/test_contradiction_workbench.py`. (REQ-KG-021..027)

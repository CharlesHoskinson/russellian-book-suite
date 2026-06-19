# KG Contradiction Workbench Tasks

- [x] Document normalized helper provenance, subject/predicate keys, unit registry, symbolic rules, and NLI seam behavior. (REQ-KG-012..018)
- [x] Declare the four helper relations in `kg-schema.edn`. (REQ-KG-012)
- [x] Add the deterministic normalized-fact parser and project helper rows from the existing ledger. (REQ-KG-012, REQ-KG-016)
- [x] Add EDN-authored workbench rule declarations and compile them to CozoScript through `booklogic_kg`. (REQ-KG-013, REQ-KG-014, REQ-KG-016)
- [x] Implement quantity clash, interval inconsistency, and supersession checks. (REQ-KG-013, REQ-KG-014, REQ-KG-015)
- [x] Implement injected NLI residue routing and seam-down unresolved behavior. (REQ-KG-017, REQ-KG-018)
- [x] Cover every S4 requirement and canonical correctness case with `tests/test_contradiction_workbench.py`. (REQ-KG-012..018)

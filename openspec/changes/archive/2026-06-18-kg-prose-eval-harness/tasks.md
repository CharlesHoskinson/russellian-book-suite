# KG Prose Eval Harness Tasks

- [x] Define the frozen corpus layout and side-product interchange schema. (REQ-EVAL-001, REQ-EVAL-003)
- [x] Add a committed frozen benchmark task with snapshot, chapter contract, side products, and gold. (REQ-EVAL-001, REQ-EVAL-004)
- [x] Implement attribution and factuality metrics over landed S1/S2 artifacts. (REQ-EVAL-002)
- [x] Return honest `unscored` results for reasoning, contradiction, rigor, and fusion until their producing artifacts and gold exist. (REQ-EVAL-002, REQ-EVAL-006)
- [x] Wire S1 claim-first bundle versus flat-claim-list comparative reporting. (REQ-EVAL-005)
- [x] Add the run harness, side-product emission, input immutability check, and determinism guard. (REQ-EVAL-001, REQ-EVAL-003, REQ-EVAL-007)
- [x] Add metric goldens and result-set equality checks. (REQ-EVAL-004)
- [x] Cover every requirement with the named pytest tests and run the full book-knowledge suite. (REQ-EVAL-001..007)

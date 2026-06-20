# Engine doctrine

- Non-determinism is confined to artifact *production*. The gate is a pure
  function of frozen, content-hashed artifacts (`engine.gate.score_gate`).
- One hard ordering constraint: acyclic precedence. Slot order and edge-loading
  are soft penalties in the target's `order_objective`.
- Cycles are reported, never fatal: demote the weakest edge in a reported SCC.
- Bridges use a closed vocabulary (`assets/connectives.json`) and may name only
  entities present in their two flanking paragraphs.
- Seam edits must preserve a paragraph's load-bearing tokens.
- Feasibility connectivity is judged by *shared entities* between paragraphs. The
  entity proxy keeps possessives intact ("snail's" is not "snail"), so a
  connected argument shares bare nouns across paragraphs.
- Deferred to v1.5: NLI bridge soft-check, seam-level entity-grid coherence,
  calibrated coherence/goal-attainment thresholds, NER replacing the keyword proxy.

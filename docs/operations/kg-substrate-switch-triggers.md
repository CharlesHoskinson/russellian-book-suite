# KG Substrate Switch Triggers

Cozo remains the sole production store behind `cozo_store`. The reference
backend exists only for authoring-time conformance checks over a declared query
subset. A backend swap is reconsidered only when one of these triggers is true:

1. Python or platform support breaks for the embedded Cozo dependency.
2. An unpatchable correctness or security issue appears in the production store.
3. The reference backend reproduces the rule surface acceptably across the frozen
   conformance fixtures.
4. The embedded / Python-primary / offline constraints are relaxed for the suite.

Meeting a trigger does not perform a migration. It opens an explicit design
decision and keeps REQ-KG-002 and REQ-KG-002b in force until that decision lands.

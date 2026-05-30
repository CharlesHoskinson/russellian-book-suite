# Authoring a new target

Implement `targets.base.Target` and `register()` an instance:

- `plan_template(goal) -> [Slot]` — ordered slots; mark required ones.
- `role_vocabulary() -> tuple[str, ...]` — the role tags BIND may assign.
- `order_objective(seq, graph, goal) -> float` — SOFT penalties only (lower is
  better); never encode hard constraints here (precedence is the engine's job).
- `gate_hook(artifacts) -> GateResult` — deep targets delegate to
  `engine.gate.score_gate`; shallow stubs return a not-yet-deep warning.
- `prose_policy` — `"russellian-style"` only if the genre is non-persuasive;
  otherwise `"none"`.

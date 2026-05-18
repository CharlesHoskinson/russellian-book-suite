# Design: tier1-solver-timeout

## Z3 API surface

`z3-rs 0.20` exposes `Solver::set_params(&Params)` (instance-level) and
the global `set_global_param("timeout", "30000")` (process-level). We
use the instance form to scope per-`check_all` call and avoid leaking
state across multiple solver lifetimes if the framework ever moves to
multi-solver verification (Tier 4).

```rust
use z3::Params;

let solver = Solver::new();
let mut params = Params::new();
params.set_u32("timeout", timeout_ms);
solver.set_params(&params);
```

The Z3 `timeout` parameter is per-call wall-clock; on expiry Z3
returns `Z3_L_UNDEF` which `z3-rs` surfaces as `SatResult::Unknown`.
`solver.get_reason_unknown()` returns the string `"timeout"` on
expiry (vs. `"theory-incompleteness"` for genuine incompleteness).

## Env-var override

```rust
let timeout_ms: u32 = std::env::var("VERIFIER_SOLVER_TIMEOUT_MS")
    .ok()
    .and_then(|s| s.parse().ok())
    .unwrap_or(30_000);
```

A CI matrix that wants to budget a slow domain at 5 minutes sets
`VERIFIER_SOLVER_TIMEOUT_MS=300000`. A fast smoke run sets 5_000.

## `:unknown` propagation

The existing `match solver.check()` arm already handles
`SatResult::Unknown` correctly — it constructs a `Verdict { status:
"unknown", explanation: ..., .. }`. The downstream Verdict EDN format
already includes `:status :unknown` as a distinct value alongside
`:sat` and `:unsat`. No Rust-side wiring change is needed beyond the
timeout itself.

What IS missing: the pytest smoke harnesses (`tests/test_smoke.py` in
each verifier) currently accept `(":sat", "sat")` OR `(":unsat", "unsat")`
in `assert status in ...`. A `:unknown` verdict slips through neither
arm and pytest raises a less-clear AssertionError. The fix is to add
explicit `:unknown` handling: a `:unknown` verdict on a fixture that
should be `:sat` or `:unsat` is a TEST FAILURE with a distinct error
message indicating solver gave up rather than the underlying constraint
being violated.

## Scaffold template

The scaffold's `cljs-orchestrator/src/main/__project__/smt.rs.tmpl`
inherits the same env-var + default + Params dance, so every new
verifier gets the timeout by construction.

## Why 30 seconds default?

The bermuda smoke runs in ~3 s on cold cargo build, well under 30 s.
The osmotic smoke (one QF_NRA constraint, 4 reals) runs in ~5 ms.
30 s is comfortably above any realistic Tier-1-scale instance while
being short enough that a CI hang surfaces within a single retry
budget instead of multi-hour stalls.

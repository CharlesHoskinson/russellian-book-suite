# Grounded atoms

A grounded atom is a host-language value or function exposed to the CLJS atomspace through napi-rs.

## Adding one

```bash
.venv/Scripts/python.exe -m scripts.add_grounded_atom \
  --project ../../verifiers/osmotic-pressure \
  --slug osmotic_pressure \
  --name :my-fn \
  --lib custom \
  --fn my_fn \
  --sort '{"kind":"fn","args":[":atom"],"ret":":verdict"}' \
  --doc "custom solver hook"
```

The helper:

1. Validates the sort.
2. Appends a record to `rules/grounded.edn`.
3. Writes a `#[napi]` stub to `rust-verifier/src/<lib>.rs` with `todo!()`.
4. Wires `mod <lib>;` into `rust-verifier/src/lib.rs` if absent.
5. Appends a CLJS bridge thin-shim to `cljs-orchestrator/src/main/<slug>/bridge.cljs`.
6. Refreshes the checksum.

## Then

Edit the Rust file to replace `todo!()` with the real backend call. Run `npm run build:rust` to compile. The CLJS side picks up the new function the next time the orchestrator loads.

## Sort discipline

Every grounded atom is typed. The argument shape is currently always `String` over the napi boundary (EDN-as-text); the Rust function is responsible for parsing. For payloads over ~5 MB switch to `Buffer + msgpack` — out of scope for v0.1.

## Supported libraries

- `z3` — SMT/FOL satisfiability
- `egg` — e-graph equality saturation
- `cozo` — embedded Datalog
- `tectonic` — LaTeX rendering
- `custom` — anything else

Adding a new library is just a new module file in `rust-verifier/src/` and a `mod` declaration.

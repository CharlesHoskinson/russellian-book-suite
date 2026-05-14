# Worked example: osmotic pressure

End-to-end demonstration based on `clojure.md` § 7.

## Scaffold

```bash
cd skills/neurosym-forge
.venv/Scripts/python.exe -m scripts.scaffold_project \
  --name "Osmotic Pressure Verifier" --slug osmotic_pressure \
  --out ../../verifiers/osmotic-pressure
```

## Add domain sorts

```bash
.venv/Scripts/python.exe -m scripts.add_sort \
  --project ../../verifiers/osmotic-pressure --sort ":molarity"
```

## Add the van 't Hoff law

```bash
.venv/Scripts/python.exe -m scripts.add_rewrite_rule \
  --project ../../verifiers/osmotic-pressure \
  --rule-file vant-hoff.edn
```

`vant-hoff.edn`:

```json
{"id": "R042",
 "lhs": {"kind": "expression", "sort": ":real",
         "head": {"kind": "symbol", "name": ":osmotic-pressure",
                  "sort": {"kind": "fn", "args": [":solution"], "ret": ":real"}},
         "args": [{"kind": "variable", "name": "?s", "sort": ":solution"}]},
 "rhs": {"kind": "expression", "sort": ":real",
         "head": {"kind": "symbol", "name": ":*",
                  "sort": {"kind": "fn", "args": [":real", ":real", ":real", ":real"], "ret": ":real"}},
         "args": [{"kind": "expression", "sort": ":real",
                   "head": {"kind": "symbol", "name": ":vant-hoff-i",
                            "sort": {"kind": "fn", "args": [":solution"], "ret": ":real"}},
                   "args": [{"kind": "variable", "name": "?s", "sort": ":solution"}]},
                  {"kind": "expression", "sort": ":real",
                   "head": {"kind": "symbol", "name": ":molarity",
                            "sort": {"kind": "fn", "args": [":solution"], "ret": ":real"}},
                   "args": [{"kind": "variable", "name": "?s", "sort": ":solution"}]},
                  {"kind": "grounded", "sort": ":real",
                   "name": ":R-gas-constant",
                   "grounded": {"lib": "custom", "fn": "r_constant", "napi": false}},
                  {"kind": "expression", "sort": ":real",
                   "head": {"kind": "symbol", "name": ":temperature",
                            "sort": {"kind": "fn", "args": [":solution"], "ret": ":real"}},
                   "args": [{"kind": "variable", "name": "?s", "sort": ":solution"}]}]},
 "doc": "van 't Hoff: pi = i * M * R * T",
 "tags": ["algebraic", "domain-chemistry"]}
```

## Build and verify

```bash
cd ../../verifiers/osmotic-pressure
npm install
npm run build
# Then run Phase 1 by hand: Claude reads doc.pdf and emits work/claims.edn
node cljs-orchestrator/dist/main.js verify work/claims.edn work/verdict.edn
```

The full pipeline (paper text → PDF report) tracks `clojure.md` § 7 step-for-step.

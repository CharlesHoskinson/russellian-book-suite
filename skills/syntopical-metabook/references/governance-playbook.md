# Governance playbook

The governance layer turns symbolic verdicts into literature-positioned
scholarship. Walk this once per book workspace.

## 1. Curate schools

Create `<workspace>/syntopical/schools/<slug>.edn` for each school of
thought your work engages with. Example for a consensus paper:

```clojure
{:version 1
 :school :praos
 :name "Praos school"
 :charter "Adaptively-secure Ouroboros family. τ ≤ 1 leader-per-slot."
 :members ["praos2017" "genesis2018" "ouroboros2017"]
 :canonical-asserts [":tau-leq-one"]
 :canonical-rejects [":tau-multi-leader"]}
```

`members` are `doc_id`s your book-knowledge ledger already knows about.
`canonical-asserts` / `canonical-rejects` are rule-id keywords; matching
them declares the school's position editorially, overriding atom-inferred
stance.

## 2. Build the positions ledger

```bash
forge govern build /c/epochpoet
```

This writes `<workspace>/syntopical/positions.edn` — one row per
`(rule, school)` pair.

## 3. Render per-rule reports

```bash
forge govern report /c/epochpoet
```

This writes `<workspace>/syntopical/rules/<rule-id>.md`. Read these to
decide whether to accept each induced rule.

## 4. Iterate

Edit schools, re-run `build`. The positions ledger is idempotent;
running twice produces byte-identical output.

## See also

- `docs/superpowers/specs/2026-05-20-syntopical-metabook-v0.2-design.md`
- `docs/superpowers/plans/2026-05-20-syntopical-metabook-v0.2.md`

# Governance playbook

The governance layer turns symbolic verdicts into literature-positioned
scholarship. Walk this once per book workspace.

## 1. Curate schools

Create `<workspace>/syntopical/schools/<slug>.edn` for each school of
thought your work engages with:

```clojure
{:version 1
 :school :school-a
 :name "School A"
 :charter "One-paragraph statement of what this school holds."
 :members ["doc-a1" "doc-a2"]
 :canonical-asserts [":some-rule-id"]
 :canonical-rejects [":another-rule-id"]}
```

`members` are `doc_id`s your book-knowledge ledger already knows about.
`canonical-asserts` / `canonical-rejects` are rule-id keywords; matching
them declares the school's position editorially, overriding atom-inferred
stance. Name your own work's school in `governance-config.edn`
(`:self-school`, default `:my-own-work`) so the adversarial review can find
positions you take against a cited school.

## 2. Build the positions ledger

```bash
forge govern build <workspace>
```

Writes `<workspace>/syntopical/positions.edn` — one row per `(rule, school)`
pair, covering both induced rules and `defconstraint` rules.

## 3. Render the reports

```bash
forge govern report      <workspace>   # syntopical/rules/<rule>.md
forge govern map         <workspace>   # syntopical/figures/consensus-map.{tex,svg}
forge govern review      <workspace>   # syntopical/adversarial-review.md
forge govern quarantine  <workspace>   # rules that failed forge induce --governance-gate
```

Renderers refuse to run on a `positions.edn` older than its source ledgers;
re-run `forge govern build` first.

## 4. Iterate

Edit schools, re-run `build`. The positions ledger is idempotent; running
twice produces byte-identical output.

## See also

- `references/acquire-playbook.md`, `synthesize-playbook.md`, `lens-and-gap-playbook.md`
- `docs/superpowers/specs/2026-05-31-syntopical-metabook-v0.3-generalization-design.md`

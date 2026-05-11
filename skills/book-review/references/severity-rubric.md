# Severity rubric

The pipeline treats severity as a soft gate. There is exactly one rule that
spans all five personas and the chapter contract:

> A finding is `critical` if and only if the persona believes, given its
> lens, that the chapter must not ship in its current form.

Everything else follows from that rule.

## The three levels

- **Critical** — blocks chapter release. The chapter contract's
  `persona_critical_count == 0` acceptance test fails when any persona
  returns at least one critical finding. Critical is reserved for what the
  persona's own definition lists as critical patterns. Personas should
  prefer `important` if uncertain.
- **Important** — should be fixed before publication, but does not block.
  Important findings are surfaced in the aggregated report and counted, but
  the chapter contract gate ignores them. The author addresses them at
  their discretion.
- **Minor** — advisory polish. Word choice, comma preferences, mild
  awkwardness. Minor findings are listed but not summarized — the count
  goes in the per-persona table and that is the end of it.

## Per-persona criticals are persona-specific

Each persona's definition file lists the patterns *that persona* treats as
critical. The aggregator does not second-guess these lists. Examples:

- **Gottlieb** — listicle abstracts ("rests on six premises"), anaphoric
  enumerations, three or more consecutive sentences sharing structure,
  AI-sloppy patterns of the kind catalogued in `russellian-style`.
- **Lay Reader** — undefined jargon at first use; a paragraph the lay reader
  cannot parse on first reading; a missing transition that breaks the
  argument.
- **Domain Expert** — a claim that is technically wrong; a citation that
  does not support its claim; a missing caveat where one is required.
- **Copyeditor** — a fact contradicted by another chapter; a notation that
  conflicts with the project's notation list; a broken cross-reference.
- **Enjoyment Reader** — a passage the reader put the draft down at; a
  chapter that fails to deliver on its opening promise.

## Aggregator behavior

`aggregate_reviews.py` reads each persona's review report, extracts findings
with their severity, and produces `persona-review.md`. Two specifics matter
for severity counting:

1. **Substring deduplication.** If two personas raise findings with
   substantially overlapping text — say, both Gottlieb and Lay Reader
   complain about the same listicle abstract — the aggregator counts the
   pair once for the gate, but lists both verbatim under their persona
   sections. Deduplication uses a substring-overlap heuristic; tune the
   threshold in `aggregate_reviews.py` if it produces false negatives.
2. **Severity is taken at face value.** The aggregator does not promote or
   demote severities. If Gottlieb says critical and the Copyeditor says
   minor about the same line, both labels are preserved and the gate sees
   one critical.

## Gate enforcement

The chapter contract has an acceptance test:

```yaml
acceptance:
  persona_critical_count: 0
```

`chapter_contract_check` reads `persona-review.md`, sums per-persona
critical counts, and fails the chapter's release gate if the sum is greater
than zero. Important and minor counts are reported but never gate.

The gate is *soft*: failing the gate prevents the chapter from being marked
release-ready, but does not delete or modify the draft. The author revises
and re-runs the review pass.

## Escalation order

When multiple personas return critical findings, address them in dispatch
order. By convention the dispatch order is:

1. Robert Gottlieb
2. Domain Expert
3. Lay Reader
4. Copyeditor
5. Enjoyment Reader

Gottlieb goes first because his lens — cadence, atomicity, the absence of
AI-sloppy patterns — is the most common bottleneck in machine-assisted
drafts. Fixing a Gottlieb critical (e.g., killing a listicle abstract) often
incidentally clears Lay Reader and Enjoyment Reader criticals on the same
passage. Domain Expert goes second because factual errors must be fixed
before further stylistic work; otherwise the author re-edits prose around
a claim that will later be removed. Copyeditor goes near the end because
mechanics depend on the final wording. Enjoyment Reader is last for the
same reason: engagement is downstream of correctness and clarity.

## When to override severity

The author does not override severity. The persona owns the rubric. If a
persona's rubric is wrong — it is gating on something the author considers
non-blocking — edit the persona file's Severity rubric section, rerun the
review, and accept the new judgments. Do not patch the aggregator to
selectively ignore a persona's criticals. That is how soft gates rot.

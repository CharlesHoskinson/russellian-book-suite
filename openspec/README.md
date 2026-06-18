# OpenSpec — russellian-book-suite

This tree holds the spec-driven development surface for the repo, following the
[OpenSpec convention](https://github.com/Fission-AI/OpenSpec).

## Layout

- `specs/<capability>/spec.md` — steady-state truth for each capability. Written in
  [EARS](https://en.wikipedia.org/wiki/Easy_Approach_to_Requirements_Syntax)
  (Easy Approach to Requirements Syntax). Updated by merging spec deltas from
  archived changes.
- `changes/<change-name>/` — in-flight or recently-merged changes. Each contains:
  - `proposal.md` — why + what
  - `design.md` — technical approach
  - `tasks.md` — implementation checklist; each task line cites the REQ IDs it satisfies
  - `specs/<capability>/spec.md` — delta against the steady-state spec (ADD / MODIFY / REMOVE)
- `changes/archive/YYYY-MM-DD-<change-name>/` — archived changes.

## REQ ID convention

`REQ-<CAPABILITY-SLUG>-<NNN>` where NNN is zero-padded. Numbers are stable across
PRs; renumbering is forbidden.

Capability slugs and their full capability names:

| Slug | Capability |
|---|---|
| `EDN` | edn-boundary |
| `TRACE` | ingest-trace |
| `DSL` | booklogic-dsl |
| `BERMUDA-RULES` | bermuda-rules |
| `CLJS-ORCH` | cljs-orchestrator |
| `QA-PIPE` | qa-defect-pipeline |
| `VERIFIER-BUILD` | verifier-build |
| `OSMOTIC` | osmotic-pressure-verifier |
| `VOICE` | russellian-voice |
| `DELTA` | russell-delta |
| `VOICE-EVAL` | voice-eval |
| `READING` | reading-council |
| `KG` | homoiconic-kg |
| `EVAL` | kg-prose-eval |
| `CHAP` | chapter-retrieval |
| `ATTR` | attributed-generation |
| `ARG` | argumentation |
| `PROOF` | proof-obligations |

## EARS patterns

| Pattern | Form |
|---|---|
| Ubiquitous | `The <system> shall <requirement>` |
| Event-driven | `When <trigger>, the <system> shall <requirement>` |
| State-driven | `While <state>, the <system> shall <requirement>` |
| Optional feature | `Where <feature>, the <system> shall <requirement>` |
| Unwanted behaviour | `If <condition>, then the <system> shall <requirement>` |

Each REQ in `specs/*/spec.md` carries the pattern label in its heading
(e.g. `### REQ-EDN-001 — Ubiquitous`).

## Workflow

This repo adopts the OpenSpec directory + spec-delta convention manually via `git`
and `gh`. The canonical OpenSpec slash-command interface (`/opsx:propose`,
`/opsx:apply`, `/opsx:archive`) is a Node-based CLI; adopting it is a follow-up
post-v0.4.0 (deferred; tracked as Open Question 6 in the roadmap design doc).
The manual cycle is identical to the CLI's:

1. **Propose.** Create `changes/<change>/proposal.md` (and optionally `design.md`,
   `tasks.md`, `specs/` deltas). Open a draft PR.
2. **Refine.** Iterate until requirements are crisp and spec deltas are agreed.
3. **Execute.** Implement against `tasks.md`. Tests cite REQ IDs in their
   docstring or test name. Each commit references one or more tasks.
4. **Merge.** Squash-merge to `main`. The GitHub Milestone for the change
   auto-closes if the PR is tagged.
5. **Archive.** Move `changes/<change>/` to `changes/archive/YYYY-MM-DD-<change>/`.
   Merge the spec deltas into `specs/<capability>/spec.md`. Publish a GitHub
   Release if the change is a milestone.

## See also

- `docs/specs/2026-05-17-ears-openspec-roadmap-design.md` — the design for this layer.
- `AGENTS.md` § OpenSpec workflow — agent-facing instructions.

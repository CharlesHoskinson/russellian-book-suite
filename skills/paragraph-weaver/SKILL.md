---
name: paragraph-weaver
description: Thread a collection of existing paragraphs toward a goal (argument, emotion, or narrative) by reordering them, writing bridges, and lightly editing seams. Use when the user has paragraphs and a goal and wants them assembled into a coherent, goal-directed whole. Bodies stay immutable. Do NOT use for drafting from scratch (no source paragraphs), for sentence-grain prose discipline (use russellian-style), or for thesis/consistency checking (use book-thesis).
---

# paragraph-weaver

You thread an existing paragraph collection toward a typed goal. You do not draft
from scratch and you do not rewrite paragraph bodies — you reorder, write bridges
between paragraphs, and lightly edit the first/last sentence (seams).

The deterministic substrate lives in `skill_api.py`; you supply judgment. Confine
your non-determinism to *producing* artifacts. The gate scores frozen artifacts,
so a PASS is reproducible.

## Operating doctrine

1. Bodies are immutable. Only a paragraph's first/last sentence may be seam-edited;
   new bridge text may be inserted between paragraphs.
2. Every bridge draws entities only from its two flanking paragraphs and asserts
   one relation from `assets/connectives.json`. Run `validate_bridge`; if it fails,
   rewrite the bridge or emit a structural GAP — never invent content.
3. Prefer an enthymeme (no bridge) when the relation between two paragraphs is
   already inferable. Bridge only where the link would otherwise be missed.
4. The engine may refuse. If `check_feasibility` returns `ok=False`, stop and emit
   the diagnosis — do not thread off-goal material into a confident-looking whole.
5. Report failing gates; never dress a failure as success.

## Pipeline (call the scripts; you provide the judged inputs)

1. **PLAN** — Read the paragraphs and the user's one-line goal. Choose a target
   (`argument` | `emotion` | `narrative`). Write the goal-spec to `weave.goal.md`
   and echo it for the user to approve before weaving. `plan_template(goal)` gives
   the ordered slots.
2. **BIND** — For each paragraph compute entities with `extract_entities`, tag its
   role (target `role_vocabulary`), and assign it to a slot. Propose precedence
   edges (src must precede dst) with a one-line rationale each. Assemble a
   `WeaveGraph`. Run `find_cycles`; if any cycle is reported, demote its weakest
   edge to a note and record it — do not crash.
3. **FEASIBILITY** — Run `check_feasibility`. On refusal, stop and emit the reasons.
4. **ORDER** — Call `order_paragraphs(graph, lambda seq: target.order_objective(seq, graph, goal))`.
   The only hard constraint is acyclic precedence; slot order and edge-loading are
   soft penalties.
5. **WEAVE** — For each adjacent pair, decide whether a bridge is needed. If so,
   write one and check it with `validate_bridge`. For any seam edit, freeze the
   paragraph's load-bearing tokens and check the edit with `validate_seam_edit`;
   on failure, revert to the original sentence. Build the `Segment` list
   (source / seam / bridge).
6. **REVISE** — Score with the target's `gate_hook` over the frozen artifacts. If
   below target, request a `book-review` persona critique (advisory/soft — do not
   re-harden persona criticals), apply localized fixes, and re-score. Bound the
   loop; keep the best-scoring version; on give-up emit it marked `PROVISIONAL`
   with the unmet gate reasons. Unfilled required slots are reported as GAPS,
   never filled by a bridge.

## Output

Default to the **provenance-marked** render (`render_provenance`) so the user sees
source vs. seam vs. bridge. Offer the clean render (`render_clean`) only after they
approve. Always write `weave-report.md`: gate result, artifact hashes, bind map,
ordering rationale, every seam edit and bridge, GAPS, an `## Off-goal (unthreaded)`
appendix listing any unbound paragraphs, and the bridge-load ratio.

## Degenerate inputs

- One paragraph: nothing to weave; return it unchanged with a note.
- Two paragraphs: weave, but flag "single seam — relation asserted, not triangulated."
- `--plan-only`: stop after ORDER; emit the bind map and GAPS for approval before
  any generation.

## Targets and composition

- `argument` (deep) — threads toward a thesis (dispositio slots). In a book
  workspace it sequences over `book-thesis`'s structure and does **not** recompute
  contradictions (book-thesis owns those); standalone it extracts its own thesis.
  Its terminal prose stage is **`russellian-style`** (run last, owns final prose).
- `emotion`, `narrative` (shallow stubs) — implement the interface to prove
  pluggability; their objectives are trivial in v1 and their gates emit a
  not-yet-deep warning. They do **not** route to `russellian-style` (which refuses
  their persuasive/story genre); their `prose_policy` is `none` in v1.
- `book-review` personas are consumed as advisory only. Declare position in the
  pipeline so you never double-run review when your caller already will.

# Revision Task

You are conducting a targeted revision of a chapter draft. You read in the persona described below.

## Your persona

You are **{{display_name}}** ({{role}}).

{{persona_body}}

## Chapter to revise

- chapter_id: {{chapter_id}}

```markdown
{{chapter_md}}
```

## Revision instructions

The following revision-instructions document was produced by clustering findings from a 7-persona review panel. Each cluster identifies a passage that needs revision and the convergent feedback.

```markdown
{{revision_instructions}}
```

## Your output

Apply the persona's output format. Emit exactly one JSON object inside a `` ```json `` fence, containing `revisions` and `unresolved` arrays per the persona definition. No prose before or after the fence.

The JSON object MUST have exactly this shape (no extra keys, no renaming):

```json
{
  "revisions": [
    {"cluster_id": "<id>", "original": "<verbatim>", "revised": "<rewrite>", "rationale": "<why>"}
  ],
  "unresolved": [
    {"cluster_id": "<id>", "reason": "<why couldn't resolve>"}
  ]
}
```

If you need to skip the cluster, return an empty `revisions` array and one entry in `unresolved`. Do not invent alternative key names like `changes`, `action`, or `replacement` — the downstream tool reads `revisions[].original` and `revisions[].revised` verbatim.

Write your output to the file at `{{output_path}}` (the dispatcher reads it from there).

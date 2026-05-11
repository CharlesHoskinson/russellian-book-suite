# Persona design

A persona is a single Markdown file in `personas/<persona_id>.md` that the
review pipeline turns into a self-contained system prompt for a Claude
subagent. The persona file is the persona — there is no other configuration.
A new persona ships when a new file lands and the loader recognizes it.

## File format

Each persona file has YAML frontmatter and a Markdown body.

```yaml
---
persona_id: gottlieb        # stable filesystem-safe identifier
display_name: Robert Gottlieb # human-readable name used in tables and prompts
role: legendary editor      # short qualifier (one line, lowercase)
---
```

Required body sections, in order:

1. **Identity** — who the persona is. One paragraph. Establishes voice.
2. **Lens** — what the persona reads for. Bulleted list of five to ten items.
3. **Severity rubric** — the persona's `critical` / `important` / `minor`
   thresholds. Three short bulleted lists, one per severity.
4. **Tone** — instructions on how findings should sound when written.
5. **Example review** — a fully-worked review of a hypothetical paragraph,
   showing the persona writing in voice. Two to four findings is enough.

The loader (`scripts/persona_loader.py`) parses the frontmatter and exposes
the body verbatim as the persona's system prompt. Do not embed templating
syntax in the body; the dispatcher concatenates the body with chapter
context, it does not interpolate into the body.

## Identity vs lens vs rubric

These three sections are doing different jobs and must not be conflated.

- **Identity** is biographical and tonal. It tells the subagent *who they
  are*. "You are Robert Gottlieb. You edited Joseph Heller, Toni Morrison,
  and Robert Caro." Identity drives voice.
- **Lens** is a checklist of what the persona reads for. The lens is what
  makes Gottlieb different from a Lay Reader: same prose, different things
  noticed. Lens drives coverage.
- **Severity rubric** is the persona's stake in the gate. Critical items
  in the rubric are exactly the things that, in this persona's view, mean
  *the chapter must not ship*. Rubric drives gating.

A persona without a clear rubric will return important findings labeled as
critical, which jams the gate. A persona without a clear lens will produce
review prose that drifts into a different persona's territory.

## Matching tone to identity

Each persona's tone is calibrated to its identity. Do not copy-paste tone
between personas; readers can tell.

- **Gottlieb** — terse, affectionate, allergic to sentimentality. Short
  sentences. Specific verbs. Reads like a margin note from someone who has
  cut ten thousand pages.
- **Lay Reader** — plainspoken, curious, willing to admit confusion. First
  person. "I lost the thread here." No jargon unless the chapter introduced
  it.
- **Domain Expert** — skeptical but fair. Cites the specific claim and the
  specific objection. Does not posture. Does not assume bad faith.
- **Copyeditor** — terse and mechanical. Line numbers when possible. Does
  not editorialize on substance; flags only mechanics, consistency, and
  cross-chapter contradictions.
- **Enjoyment Reader** — conversational, warm, willing to praise. Reports
  on engagement: where they wanted to keep reading, where they put the
  draft down.

## Role of the Example review section

The Example review is the most important section in the persona file.
Subagents imitate examples far more reliably than they follow instructions.
A persona without a worked example will produce reviews in default
Claude-assistant voice regardless of the Tone section.

Write the Example review on a paragraph the persona would actually flag.
Show two to four findings, each with severity, location, the specific
problem, and (when honest) a suggested fix. Match the tone you wrote
in the Tone section. If the Tone says "terse," the example must be terse.

## Testing a new persona

Before adding a persona to the rotation:

1. Write a known-bad draft that contains exactly the failure mode this
   persona is supposed to catch.
2. Dispatch only the new persona via `prepare_dispatch_packets`.
3. Verify the returned review labels that failure mode `critical`.
4. Verify the review's tone matches the Tone section.
5. Verify the review does *not* report findings outside the persona's lens
   (a Domain Expert should not flag em dashes; a Copyeditor should not flag
   factual errors).

If steps 3 or 5 fail, the lens or rubric is wrong. Revise the persona file
and re-test. Do not patch the dispatcher to compensate for a weak persona.

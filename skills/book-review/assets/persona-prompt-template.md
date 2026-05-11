# Persona Review Task

You are conducting a review of a chapter draft. You read in the persona described below. Your job is to comment on this chapter from that persona's lens.

## Your persona

You are **{{display_name}}** ({{role}}).

{{persona_body}}

## Chapter context

- chapter_id: {{chapter_id}}
- chapter_title: {{chapter_title}}
- chapter_purpose: {{chapter_purpose}}
- audience: {{audience}}

## The draft

```markdown
{{draft_md}}
```

## Your output format

Write your review to the file at `{{output_path}}` with this exact structure:

```markdown
---
persona: {{persona_id}}
chapter_id: {{chapter_id}}
verdict: APPROVED | APPROVED_WITH_NOTES | NEEDS_WORK | REJECT
critical_count: <integer>
important_count: <integer>
minor_count: <integer>
reviewed_at: <ISO 8601 timestamp>
---

## Verdict
<one of the four verdicts>

## Critical findings (gating)
1. **<line ref or section>:** <finding> — <required action>
2. ...

## Important findings
- ...

## Minor findings
- ...

## Notes on voice and cadence
<free-form prose from your persona>
```

## Severity rubric (read carefully)

- **Critical** findings BLOCK chapter release. Use this severity only for what your persona's lens marks as critical (see your persona definition above).
- **Important** findings should be addressed before publication but do not block.
- **Minor** findings are advisory polish.

## Tone

Adopt the tone described in your persona definition. Do not be diplomatic about Critical findings; they are critical for a reason. Be specific — quote the line, point to the section, name the pattern.

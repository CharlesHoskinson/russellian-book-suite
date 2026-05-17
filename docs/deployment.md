# Skill deployment

Canonical: `<repo>/skills/<name>/`. Runtime: `~/.claude/skills/<name>/`. Linked via Windows directory junctions:

```powershell
New-Item -ItemType Junction `
  -Path "$HOME\.claude\skills\<name>" `
  -Target "<repo>\skills\<name>"
```

Junctions share inodes — editing at either path edits both. Junctions are created lazily once the source directory exists. Existing suite skills (pre-dating this change) are independent copies and are out of scope to junction here.

For `sibling_skills` (a Python package, not a Claude skill) the junction goes to `~/.claude/skills/sibling_skills/` only because the `load_skill_api` loader walks that root by default. Override via `SIBLING_SKILLS_ROOT` env var.

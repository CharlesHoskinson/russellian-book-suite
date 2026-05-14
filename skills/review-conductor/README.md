# review-conductor

Panel orchestration over `book-review`. Reads a YAML panel config, runs the configured personas through `book-review`'s dispatch primitives, applies a per-persona severity gate, and emits a verdict.

See `SKILL.md` for the full description.

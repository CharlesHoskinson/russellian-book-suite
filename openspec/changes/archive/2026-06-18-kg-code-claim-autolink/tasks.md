# Tasks: kg-code-claim-autolink

- [x] Add `link-evidence`, `code-claim-link.kind`, and `code-node.source-file` to `kg-schema.edn`. (REQ-KG-035, REQ-KG-036)
- [x] Project graphify `source_file` into `code-node.source-file`. (REQ-KG-036)
- [x] Implement exact normalized source-file matching for module-like code nodes. (REQ-KG-036, REQ-KG-038)
- [x] Implement conservative symbol mention extraction and exact symbol resolution. (REQ-KG-037, REQ-KG-040)
- [x] Require a `contains`/`uses` trail before exact-symbol canonical promotion. (REQ-KG-037, REQ-KG-038)
- [x] Store evidence for canonical, weak, and ambiguous candidates. (REQ-KG-035, REQ-KG-038, REQ-KG-040)
- [x] Add canonical sorting and a frozen golden for deterministic output. (REQ-KG-039)
- [x] Add tests covering every S6 requirement and correctness case. (REQ-KG-035, REQ-KG-036, REQ-KG-037, REQ-KG-038, REQ-KG-039, REQ-KG-040)

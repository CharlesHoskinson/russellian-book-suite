# Worked Example

End-to-end walkthrough on a seeded book-knowledge workspace at `C:\path\to\book`. The workspace has been ingested, validated, and contains a chapter contract for `ch-03`. The walkthrough exercises every script the skill ships.

## Scenario

The chapter contract `chapters/contracts/ch-03.yaml` declares a synthesis chapter on coroutine state machines. The workspace ledger has accumulated 27 verified claims; the SPARQL query for `ch-03` returns 12 of them. Pandoc is on `PATH`. The user wants the chapter built at version `0.1.0` in Markdown and PDF.

## Step-by-step

### 1. Load the contract

```python
from pathlib import Path
from scripts.chapter_contract import load_contract

contract = load_contract(Path("chapters/contracts/ch-03.yaml"))
# returns: {
#   "chapter_id": "ch-03",
#   "title": "Coroutine State Machines for UDT Workflows",
#   "purpose": "...",
#   "audience": "researcher",
#   "chapter_type": "synthesis",
#   "must_include": [...],
#   "evidence_requirements": {
#     "minimum_verified_claims": 10,
#     "max_unresolved_conflicts": 0,
#     "evidence_density_target": 7
#   },
#   "acceptance_tests": [
#     "shacl_conforms == true",
#     "unsupported_claim_count == 0",
#     "hedge_count == 0",
#     "passive_voice_ratio < 0.05"
#   ],
#   "output_formats": ["markdown", "pdf"]
# }
```

### 2. Run pre-flight

```python
from scripts.preflight import preflight

result = preflight(Path(r"C:\path\to\book"))
# PreflightResult(passes=True, shacl_conforms=True,
#                 unsupported_claims=0, contradictions=0,
#                 report_path=...graph/reports/preflight-20260509T...Z.md,
#                 issues=[])
```

The pre-flight gate returns `passes=True`. The pipeline advances. If it had returned `passes=False`, drafting would halt; the script would write `chapters/drafts/ch-03/blocked.md` listing the issues and the user would be expected to triage them in the workspace before re-invoking the skill.

### 3. Query verified claims

```python
from scripts.query_chapter_evidence import query_chapter_evidence

evidence = query_chapter_evidence(Path(r"C:\path\to\book"), "ch-03")
# {"chapter_id": "ch-03",
#  "claims": ["c-0001", "c-0007", "c-0011", "c-0012", "c-0014",
#             "c-0017", "c-0019", "c-0020", "c-0023", "c-0024",
#             "c-0025", "c-0026"]}
```

Twelve claims. The contract requires a minimum of ten. The chapter is feasible.

### 4. Generate the outline

Claude reads the contract and the claim list, opens each claim's canonical text from the workspace ledger, and writes the outline to `chapters/drafts/ch-03/outline.md`:

```markdown
# ch-03 Outline

## Section 1. Why coroutines

Depends on: (axiom: chapter purpose)
Establishes: coroutine vs continuation distinction
Cited claims: c-0001, c-0007
Forecast density: 7.2

## Section 2. The state-machine compilation

Depends on: section 1
Establishes: compilation correctness lemma
Cited claims: c-0011, c-0012, c-0014, c-0017
Forecast density: 8.1

## Section 3. Circuit-width measurements

Depends on: sections 1, 2
Establishes: 23% width reduction in benchmark suite
Cited claims: c-0019, c-0020, c-0023
Forecast density: 6.4

## Section 4. Limits and counterexamples

Depends on: sections 1, 2, 3
Establishes: when continuations remain preferable
Cited claims: c-0024, c-0025, c-0026
Forecast density: 7.0

## Must-include coverage

- comparison table: section 3
- circuit-width measurements: section 3
- coroutine vs continuation: section 1
```

### 5. User approves

The skill pauses. The user reads the outline, confirms the must-include coverage, and replies `approve`. Drafting begins.

### 6. Draft and style each section

For section 1:

```python
# Draft to disk
section_path = Path(r"C:\path\to\book\chapters\drafts\ch-03\section-1.md")
section_path.write_text(initial_draft, encoding="utf-8")
```

Then invoke russellian-style via the Skill tool with the absolute path. The skill returns the rewritten prose plus a per-section report. The rewritten prose replaces the file contents; the report is appended to `chapters/drafts/ch-03/style-pass-report.md` with header `## section-1`.

Repeat for sections 2 through 4. After all sections are styled, concatenate them:

```python
from pathlib import Path

draft_dir = Path(r"C:\path\to\book\chapters\drafts\ch-03")
sections = sorted(draft_dir.glob("section-*.md"))
draft_md = draft_dir / "draft.md"
draft_md.write_text("\n\n".join(p.read_text(encoding="utf-8") for p in sections),
                    encoding="utf-8")
```

### 7. Verify against the contract

```python
from scripts.chapter_contract_check import check_draft

check = check_draft(draft_md, contract)
# ContractCheckResult(passes=True,
#                     metrics={'hedge_count': 0,
#                              'passive_voice_ratio': 0.018,
#                              'modifier_budget_violations': 0,
#                              'parallel_structure_violations': 1,
#                              'sentence_count': 412},
#                     failed_tests=[])
```

`passes=True`. The chapter is releasable.

### 8. Build the release bundle

```python
from scripts.build_release_bundle import build_release_bundle

bundle = build_release_bundle(
    Path(r"C:\path\to\book"),
    "ch-03",
    "0.1.0",
    ["markdown", "pdf"],
)
# returns: WindowsPath('C:/path/to/book/chapters/releases/ch-03-0.1.0')
```

The bundle directory contains `draft.md`, `draft.pdf`, `evidence-summary.md`, `claims-slice.jsonl`, and `manifest.yaml`. The chapter is shippable.

## Equivalent CLI invocations

The scripts ship as importable modules. For direct invocation from PowerShell, use the `-c` form to import and call the public functions:

```powershell
cd C:\Users\charl\.claude\skills\book-compose

.venv\Scripts\python.exe -c "from pathlib import Path; from scripts.preflight import preflight; r = preflight(Path(r'C:\path\to\book')); print('passes:', r.passes, 'issues:', r.issues)"

.venv\Scripts\python.exe -c "from pathlib import Path; from scripts.query_chapter_evidence import query_chapter_evidence; print(query_chapter_evidence(Path(r'C:\path\to\book'), 'ch-03'))"

.venv\Scripts\python.exe -c "from pathlib import Path; from scripts.build_release_bundle import build_release_bundle; print(build_release_bundle(Path(r'C:\path\to\book'), 'ch-03', '0.1.0', ['markdown', 'pdf']))"
```

When the scripts gain `if __name__ == '__main__'` entry points in a future revision, the equivalent module form will be:

```powershell
.venv\Scripts\python.exe -m scripts.preflight C:\path\to\book
.venv\Scripts\python.exe -m scripts.query_chapter_evidence C:\path\to\book ch-03
.venv\Scripts\python.exe -m scripts.build_release_bundle C:\path\to\book ch-03 0.1.0
```

Both forms call the same underlying function. The `-c` form is preferred today because it makes the function name and arguments explicit and works against the public API without requiring an argparse layer.

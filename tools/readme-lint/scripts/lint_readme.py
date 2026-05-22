"""Per-section Russell-style lint runner for the top-level README.md.

Parses the README at H2 boundaries, reads the `<!-- voice: <mode> -->` declaration
required at the top of each section, and runs the russellian-style 17-rule registry
against each section's body. Sections that violate gating rules > 2 cause the runner
to exit 1.

The cross-tool sys.modules namespace eviction is the same workaround used in
tools/russellian-style-audit/scripts/lint_samples.py - when calling skill_api.lint_fragment
from inside another tool's `scripts` package, the runner must temporarily evict that
package so russellian-style's internal `importlib.import_module("scripts.lint_X")` calls
resolve to russellian-style's scripts/* and not the caller's.
"""

from __future__ import annotations

import argparse
import contextlib
import importlib.util
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_REPO_ROOT = _HERE.parent.parent.parent
_RUSSELLIAN_STYLE_ROOT = _REPO_ROOT / "skills" / "russellian-style"


ALL_17_RULES = [
    "no-hedging", "active-voice", "signal-density", "parallel-structure",
    "listicle-abstract", "listicle-anaphora",
    "rhythm-uniform-length", "rhythm-repeated-opening",
    "burstiness", "ai-vocabulary",
    "staccato-paragraph-run", "negation-affirmation-template",
    "this-is-conclusion-overuse", "abstract-subject-run",
    "concrete-instance-density", "epistemic-precision", "paragraph-motion",
]
GATING_RULES = {
    "no-hedging", "active-voice", "signal-density", "parallel-structure",
    "listicle-abstract", "listicle-anaphora",
    "rhythm-uniform-length", "rhythm-repeated-opening",
    "burstiness", "ai-vocabulary",
}
VALID_MODES = {"technical-exposition", "narrative-editorial", "polemic", "mixed"}


@dataclass
class Section:
    heading: str
    voice: str
    ignore: set[str]
    body: str


@dataclass
class SectionLintResult:
    section: Section
    issues: list  # list[LintIssue]
    gating_count: int
    advisory_count: int
    passes: bool = field(init=False)

    def __post_init__(self):
        self.passes = self.gating_count <= 2


@contextlib.contextmanager
def _evict_caller_scripts_namespace():
    """Same workaround as russellian-style-audit/scripts/lint_samples.py."""
    saved = {k: v for k, v in sys.modules.items() if k == "scripts" or k.startswith("scripts.")}
    for k in list(saved):
        del sys.modules[k]
    try:
        yield
    finally:
        for k, v in saved.items():
            sys.modules[k] = v


def _load_russellian_skill_api():
    """Load russellian-style's skill_api in a clean sys.modules state."""
    with _evict_caller_scripts_namespace():
        if str(_RUSSELLIAN_STYLE_ROOT) not in sys.path:
            sys.path.insert(0, str(_RUSSELLIAN_STYLE_ROOT))
        spec = importlib.util.spec_from_file_location(
            "russellian_style_skill_api",
            _RUSSELLIAN_STYLE_ROOT / "skill_api.py",
        )
        module = importlib.util.module_from_spec(spec)
        sys.modules["russellian_style_skill_api"] = module
        spec.loader.exec_module(module)
        return module


_skill_api = _load_russellian_skill_api()
_lint_fragment_raw = _skill_api.lint_fragment


def _lint_fragment(text: str, linters=None):
    with _evict_caller_scripts_namespace():
        return _lint_fragment_raw(text, linters=linters)


_VOICE_RE = re.compile(r"<!--\s*voice:\s*(\S+)\s*-->")
_IGNORE_RE = re.compile(r"<!--\s*lint-disable:\s*([^|]+?)\s+reason=([^>]+?)\s*-->")


def parse_readme(text: str) -> list[Section]:
    """Split README text at H2 boundaries. Each section must declare a voice mode."""
    sections: list[Section] = []
    current_heading: str | None = None
    current_voice: str | None = None
    current_ignore: set[str] = set()
    current_body_lines: list[str] = []

    def flush():
        nonlocal current_heading, current_voice, current_ignore, current_body_lines
        if current_heading is not None:
            if current_voice is None:
                raise ValueError(f"Section without voice declaration: {current_heading!r}")
            sections.append(Section(
                heading=current_heading,
                voice=current_voice,
                ignore=current_ignore,
                body="\n".join(current_body_lines).strip() + "\n",
            ))
        current_heading = None
        current_voice = None
        current_ignore = set()
        current_body_lines = []

    for line in text.splitlines():
        if line.startswith("## "):
            flush()
            current_heading = line[3:].strip()
            continue
        if current_heading is None:
            continue
        voice_match = _VOICE_RE.search(line)
        if voice_match and current_voice is None:
            current_voice = voice_match.group(1)
            if current_voice not in VALID_MODES:
                raise ValueError(f"Invalid voice mode {current_voice!r} in section {current_heading!r}")
            continue
        ignore_match = _IGNORE_RE.search(line)
        if ignore_match:
            rules = [r.strip() for r in ignore_match.group(1).split(",") if r.strip()]
            current_ignore.update(rules)
            continue
        current_body_lines.append(line)
    flush()
    return sections


def parse_single_section(text: str, section_substring: str) -> Section:
    """Parse just one section by H2-heading substring match. Returns the matched section.

    Used by the CLI's --section flag so an incremental rewrite can lint a single section
    without requiring every other section to have a voice declaration yet.

    Raises:
        LookupError: no H2 heading contained the substring (case-insensitive).
        ValueError: the matched section is missing a voice declaration.
    """
    needle = section_substring.lower()
    lines = text.splitlines()
    target_start = None
    target_heading = None
    for i, line in enumerate(lines):
        if line.startswith("## ") and needle in line[3:].lower():
            target_start = i
            target_heading = line[3:].strip()
            break
    if target_start is None:
        raise LookupError(f"No H2 heading matched substring {section_substring!r}")
    # Find the next H2 (or EOF)
    target_end = len(lines)
    for j in range(target_start + 1, len(lines)):
        if lines[j].startswith("## "):
            target_end = j
            break
    single_section_text = "\n".join(lines[target_start:target_end]) + "\n"
    sections = parse_readme(single_section_text)
    if not sections:
        raise ValueError(f"Section {target_heading!r} parsed but produced no body")
    return sections[0]


def lint_section(section: Section) -> SectionLintResult:
    """Run lint_fragment with all 17 rules; filter out ignored rules; classify."""
    issues = _lint_fragment(section.body, linters=ALL_17_RULES)
    issues = [i for i in issues if i.linter not in section.ignore]
    gating_count = sum(1 for i in issues if i.linter in GATING_RULES)
    advisory_count = len(issues) - gating_count
    return SectionLintResult(
        section=section,
        issues=issues,
        gating_count=gating_count,
        advisory_count=advisory_count,
    )


def run_full_lint(readme_path: Path) -> tuple[list[SectionLintResult], int]:
    """Lint every section of README.md. Returns (results, exit_code)."""
    text = readme_path.read_text(encoding="utf-8")
    sections = parse_readme(text)
    results = [lint_section(s) for s in sections]
    exit_code = 0 if all(r.passes for r in results) else 1
    return results, exit_code


def _print_results(results: list[SectionLintResult]) -> None:
    for r in results:
        flag = "PASS" if r.passes else "FAIL"
        print(f"[{flag}] section={r.section.heading} (mode={r.section.voice}): gating={r.gating_count}, advisory={r.advisory_count}")
        if not r.passes:
            for issue in r.issues:
                if issue.linter in GATING_RULES:
                    print(f"  - [{issue.linter}] L{issue.line}: {issue.message[:80]}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--readme", type=Path, default=_REPO_ROOT / "README.md",
                        help="Path to README.md (default: repo root)")
    parser.add_argument("--section", type=str, default=None,
                        help="Limit to a single section by heading (case-insensitive substring). When supplied, only that section is parsed; missing voice declarations in other sections are ignored.")
    args = parser.parse_args()
    if args.section:
        text = args.readme.read_text(encoding="utf-8")
        try:
            section = parse_single_section(text, args.section)
        except LookupError as exc:
            print(f"ERROR: {exc}")
            return 2
        except ValueError as exc:
            print(f"ERROR: {exc}")
            return 2
        result = lint_section(section)
        _print_results([result])
        return 0 if result.passes else 1
    results, exit_code = run_full_lint(args.readme)
    _print_results(results)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())

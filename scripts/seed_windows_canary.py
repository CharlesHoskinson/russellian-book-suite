"""One-time sweep: add `pytestmark = pytest.mark.windows_canary` at the
top of every test file that exercises platform-sensitive behaviour.

Detection heuristic (any one match → tag):
  - Source contains: subprocess. / tempfile. / shutil. / Path(...).write_text
    / Path(...).write_bytes / .symlink_to / os.symlink / os.rename / os.replace
    / socket.
  - Filename matches: test_*cli*.py / test_*scaffold*.py / test_*ingest*.py
    / test_*workspace*.py

Usage:
    python scripts/seed_windows_canary.py             # dry-run, prints list
    python scripts/seed_windows_canary.py --apply     # writes tags into files
    python scripts/seed_windows_canary.py --skill book-knowledge --apply
                                                      # limit to one skill

Idempotent: a file already carrying `pytestmark = pytest.mark.windows_canary`
is skipped. Re-running --apply is a no-op.
"""
from __future__ import annotations
import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / "skills"
DEFAULT_SKILLS = [
    "book-qa", "book-thesis", "book-knowledge", "book-review",
    "book-compose", "russellian-style", "review-conductor", "neurosym-forge",
]

# Per-line substring triggers. Order doesn't matter; any one hit tags the file.
_CONTENT_TRIGGERS = (
    "subprocess.",
    "tempfile.",
    "shutil.",
    ".write_text(",
    ".write_bytes(",
    ".symlink_to(",
    "os.symlink",
    "os.rename(",
    "os.replace(",
    "socket.",
)

# Filename glob backstops (case-insensitive substring match on stem).
_FILENAME_GLOBS = ("cli", "scaffold", "ingest", "workspace")

_PYTESTMARK_LINE = "pytestmark = pytest.mark.windows_canary\n"
_PYTEST_IMPORT_RE = re.compile(r"^import\s+pytest\b|^from\s+pytest\s+import", re.MULTILINE)
_ALREADY_TAGGED_RE = re.compile(r"^pytestmark\s*=\s*pytest\.mark\.windows_canary", re.MULTILINE)


def _matches_filename(stem: str) -> bool:
    s = stem.lower()
    if not s.startswith("test_"):
        return False
    return any(g in s for g in _FILENAME_GLOBS)


def _matches_content(text: str) -> bool:
    return any(t in text for t in _CONTENT_TRIGGERS)


def _file_should_be_tagged(path: Path) -> tuple[bool, str]:
    """Return (should_tag, reason). Reason is empty when not tagged."""
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return False, ""
    if _ALREADY_TAGGED_RE.search(text):
        return False, "already-tagged"
    reasons: list[str] = []
    for trigger in _CONTENT_TRIGGERS:
        if trigger in text:
            reasons.append(f"content:{trigger}")
            break
    if _matches_filename(path.stem):
        reasons.append(f"filename:{path.stem}")
    if reasons:
        return True, ",".join(reasons)
    return False, ""


def _insert_pytestmark(text: str) -> str:
    """Insert pytestmark line and a `import pytest` if absent.

    Placement: after the module docstring (if any) and any `from __future__`
    imports. Before all other imports and code.
    """
    lines = text.splitlines(keepends=True)
    insert_idx = 0

    # Skip leading shebang
    if lines and lines[0].startswith("#!"):
        insert_idx = 1

    # Skip module docstring
    i = insert_idx
    while i < len(lines) and lines[i].strip() == "":
        i += 1
    if i < len(lines) and lines[i].lstrip().startswith(('"""', "'''")):
        quote = lines[i].lstrip()[:3]
        if lines[i].count(quote) >= 2:
            insert_idx = i + 1
        else:
            j = i + 1
            while j < len(lines) and quote not in lines[j]:
                j += 1
            insert_idx = j + 1 if j < len(lines) else i + 1

    # Skip `from __future__` block
    while insert_idx < len(lines) and lines[insert_idx].startswith("from __future__"):
        insert_idx += 1

    # Skip a single blank line after __future__
    if insert_idx < len(lines) and lines[insert_idx].strip() == "":
        insert_idx += 1

    needs_pytest_import = not _PYTEST_IMPORT_RE.search(text)
    new_lines = lines[:insert_idx]
    if needs_pytest_import:
        new_lines.append("import pytest\n")
    new_lines.append("\n")
    new_lines.append(_PYTESTMARK_LINE)
    new_lines.append("\n")
    new_lines.extend(lines[insert_idx:])
    return "".join(new_lines)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(
        prog="seed_windows_canary",
        description="Sweep skill tests/ dirs and tag platform-sensitive tests.",
    )
    ap.add_argument("--apply", action="store_true",
                    help="Write changes; default is dry-run.")
    ap.add_argument("--skill", action="append",
                    help="Limit to named skill; repeatable. Default: all 8 matrix skills.")
    args = ap.parse_args(argv)

    skills = args.skill or DEFAULT_SKILLS
    total_seen = 0
    total_tag = 0
    for skill in skills:
        tests_dir = SKILLS_DIR / skill / "tests"
        if not tests_dir.is_dir():
            print(f"[skip] {skill}: no tests/ directory", file=sys.stderr)
            continue
        for path in sorted(tests_dir.rglob("test_*.py")):
            total_seen += 1
            tag, reason = _file_should_be_tagged(path)
            if not tag:
                continue
            total_tag += 1
            rel = path.relative_to(REPO_ROOT)
            print(f"[tag] {rel}    ({reason})")
            if args.apply:
                path.write_text(_insert_pytestmark(path.read_text(encoding="utf-8")),
                                encoding="utf-8")
    print(
        f"\nseen={total_seen} tag={total_tag} mode={'APPLY' if args.apply else 'DRY-RUN'}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

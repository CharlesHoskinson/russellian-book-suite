"""Phase A.3 tests: REQ-INGEST-044, REQ-INGEST-045 — Makefile structure assertions."""
from pathlib import Path

MAKEFILE = Path(__file__).resolve().parents[1] / "Makefile"


def test_extract_target_exists():
    """REQ-INGEST-044: Makefile defines an `extract` target."""
    text = MAKEFILE.read_text(encoding="utf-8")
    assert "\nextract:" in text, "no `extract:` target found in Makefile"


def test_ci_depends_on_extract():
    """REQ-INGEST-045: `ci:` target's dependency list includes `extract`."""
    text = MAKEFILE.read_text(encoding="utf-8")
    for line in text.splitlines():
        if line.startswith("ci:"):
            deps = line.split(":", 1)[1].split()
            assert "extract" in deps, f"`ci:` does not depend on `extract`; deps={deps!r}"
            return
    raise AssertionError("no `ci:` target line found in Makefile")

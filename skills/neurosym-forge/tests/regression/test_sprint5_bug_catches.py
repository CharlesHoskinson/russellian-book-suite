"""Seven regression tests, one per sprint-5 bug (§ 2 of the design spec).

Each test re-introduces the bug and asserts the appropriate gate catches
it. If a future template change accidentally re-introduces a bug, these
tests fail — preventing the silent regression that caused the sprint-5
thrash.
"""
from __future__ import annotations

import shutil
import subprocess
import sys

import pytest

from .conftest import REPO_ROOT, SKILL_ROOT, run_make_ci

# Skip on non-Linux + when nbb isn't on PATH (means we're not in the nix
# develop shell). The canonical gate is the new ci.yml from PR-2, which
# runs every job through `nix develop -c`.
pytestmark = pytest.mark.skipif(
    shutil.which("cargo") is None
    or shutil.which("nbb") is None
    or sys.platform != "linux",
    reason="sprint-5 regressions require the nix develop shell (cargo + nbb + jdk)",
)


# ----- Bug #1: stale `napi build` in package.json -----

def test_bug1_napi_build_invocation_fails(fresh_bake) -> None:
    project = fresh_bake("bug1")
    pkg = project / "package.json"
    text = pkg.read_text(encoding="utf-8")
    bad = '"build:rust": "cd rust-verifier && napi build --platform --release ../cljs-orchestrator/native"'
    # Replace whatever build:rust currently is with the buggy napi form.
    import re
    new_text = re.sub(r'"build:rust":\s*"[^"]*"', bad, text)
    assert new_text != text, "couldn't find build:rust to mutate"
    pkg.write_text(new_text, encoding="utf-8")
    result = run_make_ci(project)
    assert result.returncode != 0
    assert "napi" in result.stderr.lower() or "package.json not found" in result.stderr


# ----- Bug #2: CLJS namespace dash/underscore mismatch -----

def test_bug2_underscore_ns_fails(fresh_bake) -> None:
    project = fresh_bake("bug2_test")
    core = project / "cljs-orchestrator" / "src" / "main" / "bug2_test" / "core.cljs"
    text = core.read_text(encoding="utf-8")
    # Re-introduce: change `(ns bug2-test.core)` to `(ns bug2_test.core)`.
    new_text = text.replace("(ns bug2-test.", "(ns bug2_test.")
    assert new_text != text, "couldn't find dashed ns to revert"
    core.write_text(new_text, encoding="utf-8")
    result = run_make_ci(project)
    assert result.returncode != 0
    assert "expected namespace" in result.stderr.lower() or "namespace" in result.stderr.lower()


# ----- Bug #3: CI workflow hardcoded underscore module name -----
# (This bug lives in .github/workflows/ci.yml, not in the template.)
# We assert that the *active* ci.yml uses the dashed form.

def test_bug3_ci_uses_dashed_module_name() -> None:
    ci = REPO_ROOT / ".github" / "workflows" / "ci.yml"
    text = ci.read_text(encoding="utf-8")
    # The original bug: `nbb -m osmotic_pressure.booklogic .`
    # Correct form: `nbb -m osmotic-pressure.booklogic .`
    bad = "osmotic_pressure.booklogic"
    assert bad not in text, (
        f"ci.yml references {bad!r} — sprint-5 bug #3 has regressed. "
        f"All nbb module names must be dashed."
    )


# ----- Bug #4: scaffold test asserted old underscore namespace -----
# (Lives in skills/neurosym-forge/tests/test_scaffold_project.py.)

def test_bug4_scaffold_test_uses_dashed_assertion() -> None:
    test = SKILL_ROOT / "tests" / "test_scaffold_project.py"
    text = test.read_text(encoding="utf-8")
    # If the assertion was reverted to underscore, this string appears.
    assert '"(ns osmotic_pressure.core"' not in text, (
        "test_scaffold_project.py asserts underscore namespace — "
        "sprint-5 bug #4 has regressed."
    )


# ----- Bug #5: shadow-cljs `../native/X.node` compile-time resolution -----

def test_bug5_compile_time_require_fails(fresh_bake) -> None:
    project = fresh_bake("bug5")
    bridge = project / "cljs-orchestrator" / "src" / "main" / "bug5" / "bridge.cljs"
    text = bridge.read_text(encoding="utf-8")
    # Re-introduce: replace js/require with the compile-time form
    bad = text.replace(
        "(def ^:private native (js/require",
        "; mutated\n;(def ^:private native (js/require",
    )
    # Also restore the broken `:require` form
    bad = bad.replace(
        "(:require [cljs.reader :as edn])",
        '(:require ["../native/bug5-verifier.node" :as native]\n'
        "            [cljs.reader :as edn])",
    )
    assert bad != text, "couldn't mutate bridge.cljs"
    bridge.write_text(bad, encoding="utf-8")
    result = run_make_ci(project)
    assert result.returncode != 0
    assert "not available" in result.stderr or "require" in result.stderr.lower()


# ----- Bug #6: CLJS `slurp` undeclared -----

def test_bug6_slurp_undeclared(fresh_bake) -> None:
    project = fresh_bake("bug6")
    phases = project / "cljs-orchestrator" / "src" / "main" / "bug6" / "phases.cljs"
    text = phases.read_text(encoding="utf-8")
    # Re-introduce: replace readFileSync with slurp; drop fs require
    bad = text.replace(
        "(.toString (.readFileSync fs report-path))",
        "(slurp report-path)",
    ).replace(
        '            ["fs" :as fs]))',
        "))",
    )
    assert bad != text, "couldn't mutate phases.cljs"
    phases.write_text(bad, encoding="utf-8")
    result = run_make_ci(project)
    assert result.returncode != 0
    assert "slurp" in result.stderr.lower() or "undeclared" in result.stderr.lower()


# ----- Bug #7: silent regex break in lifts.edn -----

def test_bug7_regex_break_caught_by_extract_gate(fresh_bake) -> None:
    """REQ-INGEST-048: A regex break in a baked project's lifts.edn
    causes `make ci` to fail at the new extract gate (OPAQUE-fraction
    threshold), BEFORE reaching the smoke step.

    The spec wording targets JS-style `(?<v>)` named groups specifically,
    but `ingest_ledger.py` has a `_to_python_regex` converter that
    silently rewrites JS-form to Python-form — masking that exact bug at
    the ingest layer. We mutate the regex's literal prefix instead to a
    non-matching token, which is the same class of silent failure (the
    sprint-5 root cause was a regex that compiled fine but didn't match
    the fixture).

    Removing the silent converter is tracked separately (general-purpose
    framework hardening, Tier 2+).
    """
    project = fresh_bake("bug7")
    lifts = project / "rules" / "booklogic" / "lifts.edn"
    text = lifts.read_text(encoding="utf-8")
    # Mutate `count\\s*(?P<v>...)` → `zzzNEVERMATCH\\s*(?P<v>...)` — the
    # regex still compiles but never matches the smoke-fixture claims.
    bad = text.replace("count\\s*(?P<v>", "zzzNEVERMATCH\\s*(?P<v>")
    assert bad != text, "couldn't find `count\\s*(?P<v>` to mutate in lifts.edn"
    lifts.write_text(bad, encoding="utf-8")

    # The baked project also needs a fixture for the extract target to
    # run — drop a one-line known-good claim. (The smoke-rules fixture
    # doesn't ship one because the bake's primary purpose is the cljs
    # compile / cargo build chain.)
    fixtures_dir = project / "fixtures"
    fixtures_dir.mkdir(parents=True, exist_ok=True)
    (fixtures_dir / "claims_clean.jsonl").write_text(
        '{"claim_id":"smk-001","status":"verified","canonical_text":"count 7","claim_type":"fact"}\n',
        encoding="utf-8",
    )

    result = run_make_ci(project)
    assert result.returncode != 0, (
        f"expected `make ci` to fail at extract gate; stdout: {result.stdout!r}\n"
        f"stderr: {result.stderr!r}"
    )
    # The error message from extract_preview includes "exceeds threshold"
    combined = (result.stdout + result.stderr).lower()
    assert "exceeds threshold" in combined or "opaque" in combined, (
        f"extract-gate failure mode not surfaced; combined output:\n{combined}"
    )

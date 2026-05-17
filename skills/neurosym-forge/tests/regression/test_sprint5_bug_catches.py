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
from pathlib import Path

import pytest

from .conftest import REPO_ROOT, SKILL_ROOT, run_make_ci

# Skip on non-Linux: cargo .so chain only exercises on Linux.
pytestmark = pytest.mark.skipif(
    shutil.which("cargo") is None
    or subprocess.run(["uname"], capture_output=True).stdout.strip() != b"Linux",
    reason="sprint-5 regressions require Linux toolchain",
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


# ----- Bug #7: JS-style (?<name>) named group -----

def test_bug7_js_named_group_caught_by_regex_check(fresh_bake) -> None:
    project = fresh_bake("bug7")
    lifts = project / "rules" / "booklogic" / "lifts.edn"
    text = lifts.read_text(encoding="utf-8")
    # Mutate (?P<v> back to (?<v>
    bad = text.replace("(?P<v>", "(?<v>")
    assert bad != text, "couldn't find (?P<v> to mutate"
    lifts.write_text(bad, encoding="utf-8")
    # Direct script check (faster than full make ci):
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "regex-compile-check.py"),
         str(lifts)],
        capture_output=True, text=True,
    )
    assert result.returncode != 0
    assert "?<" in result.stderr or "(?P<" in result.stderr

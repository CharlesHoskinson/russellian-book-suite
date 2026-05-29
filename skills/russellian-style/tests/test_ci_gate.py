"""Regression tests for the conftest spaCy-model gate.

In CI the linter suite must actually run; a missing en_core_web_sm model must
hard-error rather than silently drop the linter tests from collection.
"""
import importlib.util
from pathlib import Path

CONFTEST = Path(__file__).resolve().parent / "conftest.py"


def _load_conftest_module():
    spec = importlib.util.spec_from_file_location("_rs_conftest_under_test", CONFTEST)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_is_ci_detects_github_actions_env():
    mod = _load_conftest_module()
    assert mod._is_ci({"CI": "true"}) is True
    assert mod._is_ci({"CI": "1"}) is True
    assert mod._is_ci({"CI": "TRUE"}) is True


def test_is_ci_false_when_unset_or_local():
    mod = _load_conftest_module()
    assert mod._is_ci({}) is False
    assert mod._is_ci({"CI": ""}) is False
    assert mod._is_ci({"CI": "false"}) is False

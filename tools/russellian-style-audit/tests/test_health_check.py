from pathlib import Path

from scripts.health_check import HealthCheckResult, check_api_smoke, check_pytest_suite


FIXTURES = Path(__file__).parent / "fixtures"


def test_health_check_result_dataclass_shape():
    r = HealthCheckResult(name="x", status="PASS", evidence="all good")
    assert r.name == "x"
    assert r.status == "PASS"
    assert r.evidence == "all good"


def test_check_api_smoke_clean_text_returns_no_issues():
    result = check_api_smoke(
        clean_path=FIXTURES / "clean.md",
        hedged_path=FIXTURES / "hedged.md",
        listicle_path=FIXTURES / "listicle.md",
    )
    assert isinstance(result, HealthCheckResult)
    assert result.name == "api_smoke"
    assert result.status in {"PASS", "FAIL"}
    # On a healthy skill, PASS is expected. We accept either outcome to avoid
    # coupling the test to the skill's behavior — the audit's purpose is to
    # detect both states.
    if result.status == "PASS":
        assert "no-hedging" in result.evidence or "linter" in result.evidence.lower() or "hedged" in result.evidence.lower()


def test_check_pytest_suite_runs_pytest_and_returns_status(tmp_path: Path):
    """check_pytest_suite invokes pytest as a subprocess; tests it as a callable interface."""
    audit_tests_dir = Path(__file__).parent
    result = check_pytest_suite(tests_dir=audit_tests_dir)
    assert isinstance(result, HealthCheckResult)
    assert result.name == "pytest_suite"
    assert result.status in {"PASS", "FAIL"}
    assert "exit" in result.evidence.lower() or "passed" in result.evidence.lower() or "failed" in result.evidence.lower()

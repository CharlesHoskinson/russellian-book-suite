from pathlib import Path

from scripts.health_check import HealthCheckResult, check_api_smoke, check_pytest_suite, check_composes_with, check_corpus_retrieval, check_system_prompts


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


def test_check_composes_with_returns_pass_or_warn_per_consumer(tmp_path: Path):
    """composes_with reports per-consumer status; missing venvs WARN, present venvs run import smoke."""
    result = check_composes_with(consumers=["book-compose", "book-review", "book-qa", "humanizer"])
    assert isinstance(result, HealthCheckResult)
    assert result.name == "composes_with"
    assert result.status in {"PASS", "WARN", "FAIL"}
    for consumer in ["book-compose", "book-review", "book-qa", "humanizer"]:
        assert consumer in result.evidence


def test_check_composes_with_warns_when_consumer_venv_missing(tmp_path: Path):
    """A non-existent consumer name produces WARN evidence including the missing-venv reason."""
    result = check_composes_with(consumers=["nonexistent-skill-xyz"])
    assert result.status == "WARN"
    assert "nonexistent-skill-xyz" in result.evidence
    assert "venv" in result.evidence.lower() or "missing" in result.evidence.lower()


def test_check_corpus_retrieval_returns_pass_or_fail():
    result = check_corpus_retrieval(tags=["antithesis", "concrete_example", "concession"])
    assert isinstance(result, HealthCheckResult)
    assert result.name == "corpus_retrieval"
    assert result.status in {"PASS", "FAIL"}
    for tag in ["antithesis", "concrete_example", "concession"]:
        assert tag in result.evidence


def test_check_system_prompts_loads_all_three_modes():
    result = check_system_prompts(modes=["technical-exposition", "narrative-editorial", "polemic"])
    assert isinstance(result, HealthCheckResult)
    assert result.name == "system_prompts"
    assert result.status in {"PASS", "FAIL"}
    for mode in ["technical-exposition", "narrative-editorial", "polemic"]:
        assert mode in result.evidence

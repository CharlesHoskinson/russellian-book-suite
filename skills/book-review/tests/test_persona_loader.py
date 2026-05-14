from pathlib import Path
import pytest
from scripts.persona_loader import load_persona, list_personas, load_all, Persona


def _write_persona(dir: Path, persona_id: str, name: str, role: str, body: str = "Body."):
    dir.mkdir(parents=True, exist_ok=True)
    (dir / f"{persona_id}.md").write_text(
        f"---\npersona_id: {persona_id}\ndisplay_name: {name}\nrole: {role}\n---\n\n{body}\n",
        encoding="utf-8",
    )


def test_load_persona_returns_record(tmp_path, monkeypatch):
    _write_persona(tmp_path, "test-persona", "Test Persona", "tester")
    monkeypatch.setattr("scripts.persona_loader.PERSONAS_DIR", tmp_path)
    p = load_persona("test-persona")
    assert isinstance(p, Persona)
    assert p.persona_id == "test-persona"
    assert p.display_name == "Test Persona"
    assert p.role == "tester"
    assert "Body." in p.body_md


def test_list_personas_returns_ids(tmp_path, monkeypatch):
    _write_persona(tmp_path, "alpha", "Alpha", "a")
    _write_persona(tmp_path, "beta", "Beta", "b")
    monkeypatch.setattr("scripts.persona_loader.PERSONAS_DIR", tmp_path)
    ids = list_personas()
    assert sorted(ids) == ["alpha", "beta"]


def test_load_all_returns_persona_records(tmp_path, monkeypatch):
    _write_persona(tmp_path, "alpha", "Alpha", "a")
    _write_persona(tmp_path, "beta", "Beta", "b")
    monkeypatch.setattr("scripts.persona_loader.PERSONAS_DIR", tmp_path)
    records = load_all()
    assert len(records) == 2
    assert all(isinstance(r, Persona) for r in records)


def test_load_persona_missing_raises(tmp_path, monkeypatch):
    monkeypatch.setattr("scripts.persona_loader.PERSONAS_DIR", tmp_path)
    with pytest.raises(FileNotFoundError):
        load_persona("nonexistent")


def test_load_persona_missing_required_field_raises(tmp_path, monkeypatch):
    (tmp_path / "bad.md").write_text("---\nrole: tester\n---\nBody.\n", encoding="utf-8")
    monkeypatch.setattr("scripts.persona_loader.PERSONAS_DIR", tmp_path)
    with pytest.raises(ValueError):
        load_persona("bad")


def test_real_personas_load():
    # Don't monkeypatch; use the real personas/ directory
    from scripts.persona_loader import load_all
    real = load_all()
    ids = [p.persona_id for p in real]
    assert sorted(ids) == sorted([
        "ai-slop-detector", "copyeditor", "domain-expert",
        "enjoyment-reader", "first-time-visitor",
        "gottlieb", "lay-reader",
    ])


def test_ai_slop_detector_persona_loads():
    """Ai-slop-detector persona is shipped in personas/."""
    from scripts.persona_loader import load_persona
    p = load_persona("ai-slop-detector")
    assert p.persona_id == "ai-slop-detector"
    assert p.display_name == "AI-Slop Detector"
    assert "humanizer" in p.body_md.lower()
    assert "Wikipedia" in p.body_md
    assert "## Severity rubric" in p.body_md
    assert "Critical" in p.body_md
    assert "Important" in p.body_md
    assert "Minor" in p.body_md


def test_first_time_visitor_persona_loads():
    """First-time-visitor persona is shipped in personas/."""
    from scripts.persona_loader import load_persona
    p = load_persona("first-time-visitor")
    assert p.persona_id == "first-time-visitor"
    assert p.display_name == "First-Time Visitor"
    assert "30 second" in p.body_md.lower() or "thirty second" in p.body_md.lower()
    assert "## Severity rubric" in p.body_md
    assert "timeline" in p.body_md.lower()

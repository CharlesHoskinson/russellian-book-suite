"""Schema validation tests for panel-config.schema.json + verdict.schema.json + load_panel."""
import pytest

pytestmark = pytest.mark.windows_canary

import json
from pathlib import Path

import jsonschema
import pytest
import yaml

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "assets" / "panel-config.schema.json"
VERDICT_SCHEMA_PATH = Path(__file__).resolve().parent.parent / "assets" / "verdict.schema.json"


def _schema():
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _verdict_schema():
    return json.loads(VERDICT_SCHEMA_PATH.read_text(encoding="utf-8"))


def _valid_panel():
    return {
        "panel_id": "chapter-default",
        "artifact_scope": "chapter",
        "description": "test panel",
        "personas": [
            {"id": "gottlieb", "severity_gate": "gating"},
            {"id": "lay-reader", "severity_gate": "advisory"},
        ],
        "verdict": {
            "hard_gate": False,
            "soft_gate_rule": "any_critical_from_gating",
        },
        "outcomes": {
            "exemplar_paths": [],
            "per_persona_exemplars": 1,
        },
        "output": {
            "panel_report_path": "chapters/drafts/{chapter_id}/panel-review.md",
            "verdict_path": "chapters/drafts/{chapter_id}/verdict.json",
        },
    }


def _valid_verdict():
    return {
        "panel_id": "chapter-default",
        "artifact": {"type": "chapter", "id": "ch-01"},
        "verdict": "pass",
        "gating_criticals": 0,
        "advisory_criticals": 2,
        "per_persona": {
            "gottlieb": {"critical": 0, "important": 1, "minor": 3},
        },
        "report_path": "chapters/drafts/ch-01/panel-review.md",
        "timestamp": "2026-05-13T03:00:00Z",
    }


def _write_panel(tmp_path: Path, panel_dict: dict, name: str = "test-panel.yaml") -> Path:
    p = tmp_path / name
    p.write_text(yaml.safe_dump(panel_dict), encoding="utf-8")
    return p


# ---------- panel-config schema ----------


def test_valid_panel_validates():
    jsonschema.validate(instance=_valid_panel(), schema=_schema())


def test_missing_panel_id_fails():
    panel = _valid_panel()
    del panel["panel_id"]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=panel, schema=_schema())


def test_unknown_severity_gate_fails():
    panel = _valid_panel()
    panel["personas"][0]["severity_gate"] = "bogus"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=panel, schema=_schema())


def test_unknown_artifact_scope_fails():
    panel = _valid_panel()
    panel["artifact_scope"] = "bogus"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=panel, schema=_schema())


def test_unknown_field_fails():
    panel = _valid_panel()
    panel["unexpected_field"] = "value"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=panel, schema=_schema())


# ---------- verdict schema ----------


def test_valid_verdict_validates():
    jsonschema.validate(instance=_valid_verdict(), schema=_verdict_schema())


def test_verdict_unknown_value_fails():
    verdict = _valid_verdict()
    verdict["verdict"] = "bogus"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=verdict, schema=_verdict_schema())


# ---------- load_panel ----------


def test_load_panel_returns_dataclass(tmp_path):
    from scripts.load_panel import load_panel
    path = _write_panel(tmp_path, _valid_panel())
    panel = load_panel(path)
    assert panel.panel_id == "chapter-default"
    assert panel.artifact_scope == "chapter"
    assert [p.id for p in panel.personas] == ["gottlieb", "lay-reader"]
    assert panel.personas[0].severity_gate == "gating"


def test_load_panel_missing_required_raises(tmp_path):
    from scripts.load_panel import load_panel
    bad = _valid_panel()
    del bad["panel_id"]
    path = _write_panel(tmp_path, bad)
    with pytest.raises(jsonschema.ValidationError):
        load_panel(path)


def test_load_panel_unknown_field_raises(tmp_path):
    from scripts.load_panel import load_panel
    bad = _valid_panel()
    bad["bogus"] = "value"
    path = _write_panel(tmp_path, bad)
    with pytest.raises(jsonschema.ValidationError):
        load_panel(path)


def test_chapter_default_panel_loads():
    """The shipped panels/chapter-default.yaml validates and yields a 7-persona panel."""
    from scripts.load_panel import load_panel
    path = Path(__file__).resolve().parent.parent / "panels" / "chapter-default.yaml"
    panel = load_panel(path)
    assert panel.panel_id == "chapter-default"
    assert panel.artifact_scope == "chapter"
    ids = [p.id for p in panel.personas]
    assert sorted(ids) == sorted([
        "ai-slop-detector", "copyeditor", "domain-expert",
        "enjoyment-reader", "first-time-visitor",
        "gottlieb", "lay-reader",
    ])
    gating = {p.id for p in panel.personas if p.severity_gate == "gating"}
    assert gating == {"gottlieb", "domain-expert", "copyeditor", "ai-slop-detector"}

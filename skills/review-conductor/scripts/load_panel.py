"""Load and validate panel-config YAML against panel-config.schema.json."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import jsonschema
import yaml

ASSETS = Path(__file__).resolve().parent.parent / "assets"
PANEL_SCHEMA = json.loads((ASSETS / "panel-config.schema.json").read_text(encoding="utf-8"))


@dataclass(frozen=True)
class PersonaConfig:
    id: str
    severity_gate: str  # "gating" | "advisory"
    delegates_to: Optional[str] = None


@dataclass(frozen=True)
class VerdictConfig:
    hard_gate: bool
    soft_gate_rule: str


@dataclass(frozen=True)
class OutcomesConfig:
    exemplar_paths: list[str]
    per_persona_exemplars: int


@dataclass(frozen=True)
class OutputConfig:
    panel_report_path: str
    verdict_path: str


@dataclass(frozen=True)
class Panel:
    panel_id: str
    artifact_scope: str
    description: str
    personas: list[PersonaConfig]
    verdict: VerdictConfig
    outcomes: OutcomesConfig
    output: OutputConfig


def load_panel(path: Path) -> Panel:
    path = Path(path).resolve()
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    jsonschema.validate(instance=raw, schema=PANEL_SCHEMA)
    outcomes_raw = raw.get("outcomes") or {"exemplar_paths": [], "per_persona_exemplars": 0}
    # Resolve relative exemplar paths against the panel YAML's directory so
    # the chapter-default panel's `../book-review/references/outcomes/...`
    # works regardless of the caller's CWD.
    panel_dir = path.parent
    raw_paths = outcomes_raw.get("exemplar_paths", [])
    resolved_paths: list[str] = []
    for p in raw_paths:
        candidate = Path(p)
        if not candidate.is_absolute():
            candidate = (panel_dir / candidate).resolve()
        resolved_paths.append(str(candidate))
    return Panel(
        panel_id=raw["panel_id"],
        artifact_scope=raw["artifact_scope"],
        description=raw.get("description", ""),
        personas=[
            PersonaConfig(
                id=p["id"],
                severity_gate=p["severity_gate"],
                delegates_to=p.get("delegates_to"),
            )
            for p in raw["personas"]
        ],
        verdict=VerdictConfig(
            hard_gate=raw["verdict"]["hard_gate"],
            soft_gate_rule=raw["verdict"]["soft_gate_rule"],
        ),
        outcomes=OutcomesConfig(
            exemplar_paths=resolved_paths,
            per_persona_exemplars=outcomes_raw.get("per_persona_exemplars", 0),
        ),
        output=OutputConfig(
            panel_report_path=raw["output"]["panel_report_path"],
            verdict_path=raw["output"]["verdict_path"],
        ),
    )

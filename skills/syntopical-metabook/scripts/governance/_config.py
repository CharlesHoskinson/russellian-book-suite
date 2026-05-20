"""governance-config.edn loader; auto-creates with defaults on first run."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from ._schools import _read_edn_map


DEFAULTS = {
    "self_school": "my-own-work",
    "supports_min_docs": 2,
    "contradicts_min_docs": 1,
}


@dataclass(frozen=True)
class GovernanceConfig:
    self_school: str
    supports_min_docs: int
    contradicts_min_docs: int


_DEFAULT_EDN = (
    "{:version 1\n"
    " :self-school :my-own-work\n"
    " :supports-min-docs 2\n"
    " :contradicts-min-docs 1}\n"
)


def load_or_create_config(path: Path) -> GovernanceConfig:
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_DEFAULT_EDN, encoding="utf-8")
        return GovernanceConfig(**DEFAULTS)
    data = _read_edn_map(path.read_text(encoding="utf-8"))
    self_school = data.get("self-school", DEFAULTS["self_school"])
    if isinstance(self_school, str) and self_school.startswith(":"):
        self_school = self_school[1:]
    return GovernanceConfig(
        self_school=str(self_school),
        supports_min_docs=int(data.get("supports-min-docs",
                                       DEFAULTS["supports_min_docs"])),
        contradicts_min_docs=int(data.get("contradicts-min-docs",
                                          DEFAULTS["contradicts_min_docs"])),
    )

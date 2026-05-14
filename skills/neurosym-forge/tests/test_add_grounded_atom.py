# skills/neurosym-forge/tests/test_add_grounded_atom.py
from __future__ import annotations

from pathlib import Path

import pytest

from scripts._io import read_edn_as_json, write_json_as_edn
from scripts.add_grounded_atom import add_grounded_atom


def _seed(tmp_path: Path) -> Path:
    (tmp_path / "rules").mkdir()
    (tmp_path / "rust-verifier" / "src").mkdir(parents=True)
    (tmp_path / "cljs-orchestrator" / "src" / "main" / "demo").mkdir(parents=True)
    write_json_as_edn(tmp_path / "rules" / "seed.edn",
                      {"version": 1, "sorts": [":real", ":verdict", ":atom"],
                       "rules": [], "atoms": []})
    write_json_as_edn(tmp_path / "rules" / "grounded.edn", {"version": 1, "grounded": []})
    write_json_as_edn(tmp_path / "rules" / ".checksums.edn", {"checksums": {}})
    (tmp_path / "rust-verifier" / "src" / "custom.rs").write_text(
        "// custom grounded atoms\n", encoding="utf-8")
    (tmp_path / "rust-verifier" / "src" / "lib.rs").write_text(
        "#![deny(clippy::all)]\nuse napi_derive::napi;\n\nmod ir;\nmod custom;\n",
        encoding="utf-8")
    (tmp_path / "cljs-orchestrator" / "src" / "main" / "demo" / "bridge.cljs").write_text(
        "(ns demo.bridge)\n", encoding="utf-8")
    return tmp_path


def test_appends_grounded_record(tmp_path: Path) -> None:
    project = _seed(tmp_path)
    add_grounded_atom(
        project, project_slug="demo",
        name=":my-fn", lib="custom", fn="my_fn",
        sort={"kind": "fn", "args": [":atom"], "ret": ":verdict"},
        doc="custom solver hook",
    )
    grounded = read_edn_as_json(project / "rules" / "grounded.edn")["grounded"]
    assert any(g["name"] == ":my-fn" for g in grounded)


def test_appends_rust_stub(tmp_path: Path) -> None:
    project = _seed(tmp_path)
    add_grounded_atom(
        project, project_slug="demo",
        name=":my-fn", lib="custom", fn="my_fn",
        sort={"kind": "fn", "args": [":atom"], "ret": ":verdict"},
    )
    rs = (project / "rust-verifier" / "src" / "custom.rs").read_text()
    assert "pub fn my_fn" in rs
    assert "todo!()" in rs


def test_appends_cljs_bridge_stub(tmp_path: Path) -> None:
    project = _seed(tmp_path)
    add_grounded_atom(
        project, project_slug="demo",
        name=":my-fn", lib="custom", fn="my_fn",
        sort={"kind": "fn", "args": [":atom"], "ret": ":verdict"},
    )
    bridge = (project / "cljs-orchestrator" / "src" / "main" / "demo" / "bridge.cljs").read_text()
    assert "myFn" in bridge


def test_rejects_duplicate(tmp_path: Path) -> None:
    project = _seed(tmp_path)
    add_grounded_atom(project, project_slug="demo",
                      name=":my-fn", lib="custom", fn="my_fn",
                      sort={"kind": "fn", "args": [":atom"], "ret": ":verdict"})
    with pytest.raises(ValueError, match="duplicate"):
        add_grounded_atom(project, project_slug="demo",
                          name=":my-fn", lib="custom", fn="my_fn",
                          sort={"kind": "fn", "args": [":atom"], "ret": ":verdict"})

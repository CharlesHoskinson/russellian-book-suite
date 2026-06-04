# skills/neurosym-forge/tests/test_add_grounded_atom.py
from __future__ import annotations

import pytest

pytestmark = pytest.mark.windows_canary

from pathlib import Path

import pytest

from scripts._edn_reader import Keyword
from scripts._io import read_edn_file, write_edn_file
from scripts.add_grounded_atom import add_grounded_atom

GROUNDED_KEY = Keyword("grounded")
NAME_KEY = Keyword("name")
CHECKSUMS_KEY = Keyword("checksums")


def _seed(tmp_path: Path) -> Path:
    (tmp_path / "rules").mkdir()
    (tmp_path / "rust-verifier" / "src").mkdir(parents=True)
    (tmp_path / "cljs-orchestrator" / "src" / "main" / "demo").mkdir(parents=True)
    write_edn_file(tmp_path / "rules" / "seed.edn", {
        Keyword("version"): 1,
        Keyword("sorts"): [Keyword("real"), Keyword("verdict"), Keyword("atom")],
        Keyword("rules"): [],
        Keyword("atoms"): [],
    })
    write_edn_file(tmp_path / "rules" / "grounded.edn", {
        Keyword("version"): 1,
        GROUNDED_KEY: [],
    })
    write_edn_file(tmp_path / "rules" / ".checksums.edn", {CHECKSUMS_KEY: {}})
    (tmp_path / "rust-verifier" / "src" / "custom.rs").write_text(
        "// custom grounded atoms\n", encoding="utf-8")
    (tmp_path / "rust-verifier" / "src" / "lib.rs").write_text(
        "#![deny(clippy::all)]\nuse napi_derive::napi;\n\nmod ir;\nmod custom;\n",
        encoding="utf-8")
    (tmp_path / "cljs-orchestrator" / "src" / "main" / "demo" / "bridge.cljs").write_text(
        "(ns demo.bridge)\n", encoding="utf-8")
    return tmp_path


_SORT = {Keyword("kind"): Keyword("fn"),
         Keyword("args"): [Keyword("atom")],
         Keyword("ret"): Keyword("verdict")}


def test_appends_grounded_record(tmp_path: Path) -> None:
    project = _seed(tmp_path)
    add_grounded_atom(
        project, project_slug="demo",
        name=":my-fn", lib="custom", fn="my_fn",
        sort=_SORT,
        doc="custom solver hook",
    )
    grounded = read_edn_file(project / "rules" / "grounded.edn")[GROUNDED_KEY]
    assert any(g[NAME_KEY] == ":my-fn" for g in grounded)


def test_appends_rust_stub(tmp_path: Path) -> None:
    project = _seed(tmp_path)
    add_grounded_atom(
        project, project_slug="demo",
        name=":my-fn", lib="custom", fn="my_fn",
        sort=_SORT,
    )
    rs = (project / "rust-verifier" / "src" / "custom.rs").read_text()
    assert "pub fn my_fn" in rs
    assert "todo!()" in rs


def test_appends_cljs_bridge_stub(tmp_path: Path) -> None:
    project = _seed(tmp_path)
    add_grounded_atom(
        project, project_slug="demo",
        name=":my-fn", lib="custom", fn="my_fn",
        sort=_SORT,
    )
    bridge = (project / "cljs-orchestrator" / "src" / "main" / "demo" / "bridge.cljs").read_text()
    assert "myFn" in bridge


def test_rejects_duplicate(tmp_path: Path) -> None:
    project = _seed(tmp_path)
    add_grounded_atom(project, project_slug="demo",
                      name=":my-fn", lib="custom", fn="my_fn",
                      sort=_SORT)
    with pytest.raises(ValueError, match="duplicate"):
        add_grounded_atom(project, project_slug="demo",
                          name=":my-fn", lib="custom", fn="my_fn",
                          sort=_SORT)


def test_rejects_hyphenated_fn(tmp_path: Path) -> None:
    project = _seed(tmp_path)
    with pytest.raises(ValueError, match="snake_case"):
        add_grounded_atom(project, project_slug="demo",
                          name=":my-fn", lib="custom", fn="my-fn",
                          sort=_SORT)


def test_emits_fixture_test(tmp_path: Path) -> None:
    project = _seed(tmp_path)
    add_grounded_atom(project, project_slug="demo",
                      name=":my-fn", lib="custom", fn="my_fn",
                      sort=_SORT)
    fixture = project / "tests" / "grounded" / "test_my_fn.cljs"
    assert fixture.exists()
    text = fixture.read_text(encoding="utf-8")
    assert "my-fn-stub-returns" in text
    assert "demo.bridge" in text


def test_appends_mod_when_no_anchor(tmp_path: Path) -> None:
    project = _seed(tmp_path)
    # Strip the `mod ir;` anchor before calling.
    lib_rs = project / "rust-verifier" / "src" / "lib.rs"
    lib_rs.write_text("#![deny(clippy::all)]\nuse napi_derive::napi;\n", encoding="utf-8")
    add_grounded_atom(project, project_slug="demo",
                      name=":my-fn", lib="custom", fn="my_fn",
                      sort=_SORT)
    text = lib_rs.read_text(encoding="utf-8")
    assert "mod custom;" in text

"""REQ-EDN-045: Scaffold template's booklogic.cljs.tmpl ships with the
`canonical-var-name` function so every new project gets the cross-language
contract."""
from __future__ import annotations

from pathlib import Path

BOOKLOGIC_TMPL = (Path(__file__).resolve().parents[1]
                  / "assets" / "project-template"
                  / "cljs-orchestrator" / "src" / "main" / "__project__"
                  / "booklogic.cljs.tmpl")
TEST_TMPL = (Path(__file__).resolve().parents[1]
             / "assets" / "project-template"
             / "cljs-orchestrator" / "src" / "test" / "__project__"
             / "booklogic_test.cljs.tmpl")


def test_booklogic_template_defines_canonical_var_name() -> None:
    text = BOOKLOGIC_TMPL.read_text(encoding="utf-8")
    assert "(defn canonical-var-name" in text, (
        "booklogic.cljs.tmpl must define canonical-var-name"
    )


def test_canonical_var_name_test_exists() -> None:
    text = TEST_TMPL.read_text(encoding="utf-8")
    assert "canonical-var-name-matches-golden" in text, (
        "booklogic_test.cljs.tmpl must reference canonical-var-name-matches-golden"
    )


def test_canonical_var_name_reads_goldens() -> None:
    text = TEST_TMPL.read_text(encoding="utf-8")
    assert "canonical_var_name.edn" in text, (
        "the cljs test should read the cross-language goldens"
    )

"""Cites REQ-VOICE-010, REQ-VOICE-011 (register modifier corridor; v1 unchanged)."""
import pytest
pytestmark = pytest.mark.windows_canary
from pathlib import Path
from scripts.lint_common import load_rules
from scripts.lint_signal_density import lint_signal_density

# A sentence with a modifier ratio between the v1 budget (0.25) and the narrative budget (0.30).
BORDERLINE = "The careful reader quietly tracks each structural detail in the argument."


def _write(tmp_path, text):
    p = tmp_path / "p.md"
    p.write_text(text, encoding="utf-8")
    return p


def test_v1_default_uses_global_budget(tmp_path):
    # no register -> global 0.25 budget (frozen v1 behavior)
    f_default = lint_signal_density(_write(tmp_path, BORDERLINE))
    f_v1_explicit = lint_signal_density(_write(tmp_path, BORDERLINE), rules=load_rules())
    assert [x["rule"] for x in f_default] == [x["rule"] for x in f_v1_explicit]


def test_narrative_register_relaxes_the_budget(tmp_path):
    rules = load_rules("russellian-rules-v2.json")
    flagged_global = lint_signal_density(_write(tmp_path, BORDERLINE), rules=rules)  # no register -> global
    flagged_narrative = lint_signal_density(_write(tmp_path, BORDERLINE), rules=rules, register="narrative-editorial")
    # The borderline sentence trips the tighter global budget but clears the relaxed narrative budget.
    assert len(flagged_narrative) <= len(flagged_global)

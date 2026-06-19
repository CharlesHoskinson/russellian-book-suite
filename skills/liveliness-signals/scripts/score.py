"""Advisory liveliness scoring harness. Never gates (REQ-LIVE-004)."""
from __future__ import annotations
import json
import sys
from pathlib import Path

from scripts.text_util import iter_sentences

# Each signal is (name, callable(sentences, register, profile) -> dict).
# Scorers are appended in later tasks.
SIGNALS: list = []

from scripts import signal_cadence
SIGNALS.append(("cadence", signal_cadence.score))


def _load_profile_safe(profile):
    if profile is not None:
        return profile
    try:
        import skill_api
        return skill_api.load_profile()
    except Exception:
        return None


def score_passage(text: str, register: str = "narrative-editorial", profile=None) -> dict:
    profile = _load_profile_safe(profile)
    sents = iter_sentences(text)
    signals = {}
    for name, fn in SIGNALS:
        try:
            signals[name] = fn(sents, register, profile)
        except Exception as exc:  # advisory: a scorer error must not break the report
            signals[name] = {"signal": name, "score": None, "error": str(exc)}
    return {"register": register, "n_sentences": len(sents), "signals": signals}


def main(argv: list[str]) -> int:
    args = [a for a in argv[1:] if not a.startswith("--")]
    reg = "narrative-editorial"
    for i, a in enumerate(argv):
        if a == "--register" and i + 1 < len(argv):
            reg = argv[i + 1]
    if not args:
        print("usage: score.py [--register REG] <markdown-file>", file=sys.stderr)
        return 2
    text = Path(args[0]).read_text(encoding="utf-8")
    print(json.dumps(score_passage(text, register=reg), indent=2))
    return 0  # advisory: always 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

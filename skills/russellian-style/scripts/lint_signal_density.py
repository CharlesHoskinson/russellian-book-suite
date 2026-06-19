"""Flag sentences whose modifier (adjective+adverb) ratio exceeds budget."""
from __future__ import annotations

import json
import os
import sys
from functools import lru_cache
from pathlib import Path

import spacy

from .lint_common import iter_sentences, load_markdown, load_rules


@lru_cache(maxsize=1)
def _nlp():
    return spacy.load("en_core_web_sm")


def _load_overrides() -> set[str]:
    env_path = os.environ.get("RUSSELLIAN_OVERRIDES")
    if not env_path:
        return set()
    p = Path(env_path)
    if not p.exists():
        return set()
    data = json.loads(p.read_text(encoding="utf-8"))
    return {w.lower() for w in data.get("skip_modifier_words", [])}


def _modifier_ratio(spacy_doc, overrides: set[str]) -> float:
    content = [t for t in spacy_doc if t.is_alpha]
    if not content:
        return 0.0
    modifiers = sum(
        1
        for t in content
        if t.pos_ in ("ADJ", "ADV") and t.lower_ not in overrides
    )
    return modifiers / len(content)


def lint_signal_density(path: Path, rules: dict | None = None, register: str | None = None) -> list[dict]:
    text = load_markdown(path)
    if rules is None:
        rules = load_rules()
    budget = rules["modifier_budget_ratio"]
    by_reg = rules.get("modifier_budget_by_register")
    if register and by_reg and register in by_reg:
        budget = by_reg[register]
    nlp = _nlp()
    overrides = _load_overrides()

    findings: list[dict] = []
    for sentence in iter_sentences(text):
        doc = nlp(sentence.text)
        content = [t for t in doc if t.is_alpha]
        if len(content) < 8:
            continue  # too short to assess
        ratio = _modifier_ratio(doc, overrides)
        if ratio > budget:
            findings.append({
                "rule": "signal-density",
                "sentence": sentence.text,
                "line": sentence.line,
                "col": sentence.col,
                "modifier_ratio": round(ratio, 3),
                "budget": budget,
            })
    return findings


def main(argv: list[str]) -> int:
    args = argv[1:]
    ruleset = "russellian-rules.json"
    register: str | None = None
    rest = []
    i = 0
    while i < len(args):
        if args[i] == "--ruleset" and i + 1 < len(args):
            ruleset = args[i + 1]; i += 2
        elif args[i] == "--register" and i + 1 < len(args):
            register = args[i + 1]; i += 2
        else:
            rest.append(args[i]); i += 1
    if not rest:
        print("usage: lint_signal_density.py [--ruleset NAME] [--register REG] <markdown-file>", file=sys.stderr)
        return 2
    rules = load_rules(ruleset)
    findings = lint_signal_density(Path(rest[0]), rules=rules, register=register)
    print(json.dumps(findings, indent=2))
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

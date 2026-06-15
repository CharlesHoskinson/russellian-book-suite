from pathlib import Path

import yaml

from scripts.clean import parse_vtt, dedupe_rolling, strip_fragments, clean_vtt


def _stock(fixtures_dir: Path) -> list[str]:
    asset = Path(__file__).parents[1] / "assets" / "stock-fragments.yaml"
    return yaml.safe_load(asset.read_text(encoding="utf-8"))["fragments"]


def test_parse_vtt_returns_cues(fixtures_dir: Path):
    cues = parse_vtt((fixtures_dir / "sample.vtt").read_text(encoding="utf-8"))
    assert cues[0][0] == "00:00:01.000"
    assert "Welcome back" in cues[0][1]
    assert len(cues) == 2


def test_dedupe_rolling_collapses_overlap(fixtures_dir: Path):
    cues = parse_vtt((fixtures_dir / "auto_sub.vtt").read_text(encoding="utf-8"))
    text = dedupe_rolling(cues)
    assert text.count("the thing people miss about") == 1
    assert text.count("governance is incentives") == 1
    assert "not slogans" in text


def test_strip_fragments_removes_boilerplate(fixtures_dir: Path):
    out = strip_fragments("Welcome back everybody to another AMA. Real content here.", _stock(fixtures_dir))
    assert "Welcome back" not in out
    assert "Real content here." in out


def test_clean_vtt_human_subs(fixtures_dir: Path):
    passages = clean_vtt(
        (fixtures_dir / "sample.vtt").read_text(encoding="utf-8"),
        stock_fragments=_stock(fixtures_dir),
    )
    joined = " ".join(p["text"] for p in passages)
    assert "Welcome back" not in joined
    assert "governance and why it matters" in joined
    assert passages[0]["t_start"] == "00:00:01.000"

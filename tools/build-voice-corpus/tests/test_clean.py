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
    # Cue 1 is a pure stock fragment -> stripped -> dropped. Cue 2 survives as one passage.
    assert len(passages) == 1
    assert all(p["text"] for p in passages)
    assert passages[0]["t_start"] == "00:00:04.000"
    assert "Welcome back" not in passages[0]["text"]
    assert "governance and why it matters" in passages[0]["text"]


def test_clean_vtt_auto_subs_merges_rolling_window(fixtures_dir: Path):
    passages = clean_vtt(
        (fixtures_dir / "auto_sub.vtt").read_text(encoding="utf-8"),
        stock_fragments=[],
    )
    assert len(passages) == 1
    assert passages[0]["text"] == "the thing people miss about governance is incentives not slogans"
    assert passages[0]["t_start"] == "00:00:01.000"

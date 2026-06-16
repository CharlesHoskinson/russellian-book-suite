import json
from pathlib import Path

from scripts.discover import extract_initial_data, parse_video_entries, hms_to_seconds, discover_channel


def test_extract_initial_data_from_html():
    payload = '{"contents": {"x": 1}}'
    html = f"<html><script>var ytInitialData = {payload};</script></html>"
    data = extract_initial_data(html)
    assert data == {"contents": {"x": 1}}


def test_hms_to_seconds():
    assert hms_to_seconds("20:00") == 1200
    assert hms_to_seconds("1:02:03") == 3723


def test_parse_video_entries(fixtures_dir: Path):
    data = json.loads((fixtures_dir / "channel_initial_data.json").read_text(encoding="utf-8"))
    rows = parse_video_entries(data)
    assert rows[0]["video_id"] == "aaa111"
    assert rows[0]["title"] == "Surprise AMA"
    assert rows[0]["duration_seconds"] == 3723
    assert len(rows) == 2


def test_discover_channel_uses_injected_fetch(fixtures_dir: Path):
    payload = (fixtures_dir / "channel_initial_data.json").read_text(encoding="utf-8")

    def fake_fetch(url: str) -> str:
        return f"<script>var ytInitialData = {payload};</script>"

    rows = discover_channel("https://www.youtube.com/@charleshoskinsoncrypto/videos",
                            fetch=fake_fetch)
    assert {r["video_id"] for r in rows} == {"aaa111", "bbb222"}


def test_extract_initial_data_handles_braces_in_strings():
    # A title containing "};</script>" must NOT truncate the blob.
    payload = '{"title": "weird };</script> title", "n": {"a": 1}}'
    html = f'<script>var ytInitialData = {payload};</script><script>var other = 1;</script>'
    data = extract_initial_data(html)
    assert data["title"] == "weird };</script> title"
    assert data["n"] == {"a": 1}

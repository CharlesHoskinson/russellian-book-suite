from pathlib import Path

from scripts.cli import run
from scripts.corpus_io import read_index
from scripts.manifest import latest_state


def _channel_html(fixtures_dir: Path) -> str:
    payload = (fixtures_dir / "channel_initial_data.json").read_text(encoding="utf-8")
    return f"<script>var ytInitialData = {payload};</script>"


def test_run_end_to_end_offline(tmp_path: Path, fixtures_dir: Path):
    html = _channel_html(fixtures_dir)

    def fetch(url): return html

    def ytdlp_runner(args):
        # write a tiny VTT for whatever video id is in the URL
        vid = args[-1].split("v=")[-1]
        (Path(args[args.index("-o") + 1].replace("%(id)s.%(ext)s", f"{vid}.en.vtt"))).write_text(
            "WEBVTT\n\n00:00:01.000 --> 00:00:03.000\ngovernance is incentives\n", encoding="utf-8")
        return type("R", (), {"returncode": 0})()

    def llm_call(prompt): return '{"rhetorical_move": "states a thesis plainly", "tags": ["candor"]}'

    index_path = tmp_path / "hoskinson-corpus" / "index.json"
    summary = run(
        channel_videos_url="https://www.youtube.com/@charleshoskinsoncrypto/videos",
        workdir=tmp_path, index_path=index_path,
        fetch=fetch, ytdlp_runner=ytdlp_runner, llm_call=llm_call,
        target=2, seed=1,
    )
    idx = read_index(index_path)
    assert idx["paragraph_count"] >= 2
    assert summary["tagged"] == 2


def test_run_is_resumable(tmp_path: Path, fixtures_dir: Path):
    html = _channel_html(fixtures_dir)
    calls = {"ytdlp": 0}

    def fetch(url): return html

    def ytdlp_runner(args):
        calls["ytdlp"] += 1
        vid = args[-1].split("v=")[-1]
        (Path(args[args.index("-o") + 1].replace("%(id)s.%(ext)s", f"{vid}.en.vtt"))).write_text(
            "WEBVTT\n\n00:00:01.000 --> 00:00:03.000\nhello\n", encoding="utf-8")
        return type("R", (), {"returncode": 0})()

    def llm_call(prompt): return '{"rhetorical_move": "m", "tags": ["a"]}'

    index_path = tmp_path / "hoskinson-corpus" / "index.json"
    kw = dict(channel_videos_url="https://x/@c/videos", workdir=tmp_path, index_path=index_path,
              fetch=fetch, ytdlp_runner=ytdlp_runner, llm_call=llm_call, target=2, seed=1)
    run(**kw)
    first = calls["ytdlp"]
    run(**kw)  # second run: everything already tagged
    assert calls["ytdlp"] == first  # no re-fetch
    state = latest_state(tmp_path / "manifest.jsonl")
    assert all(v["stage"] == "tagged" for v in state.values())

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


def test_run_leaves_failed_fetch_retryable(tmp_path: Path, fixtures_dir: Path):
    from scripts.manifest import latest_state
    html = _channel_html(fixtures_dir)

    def fetch(url): return html

    def failing_ytdlp(args):
        return type("R", (), {"returncode": 1})()  # always fails, never writes a VTT

    def llm_call(prompt): return '{"rhetorical_move": "m", "tags": ["a"]}'

    index_path = tmp_path / "hoskinson-corpus" / "index.json"
    run(channel_videos_url="https://x/@c/videos", workdir=tmp_path, index_path=index_path,
        fetch=fetch, ytdlp_runner=failing_ytdlp, llm_call=llm_call, target=2, seed=1)
    state = latest_state(tmp_path / "manifest.jsonl")
    # No video may be left in terminal "skipped" due to a fetch failure; they must remain retryable.
    assert all(v["stage"] != "skipped" for v in state.values())
    assert all(v["stage"] != "tagged" for v in state.values())


def test_run_recovers_from_crash_between_append_and_record(tmp_path: Path, fixtures_dir: Path):
    # Simulate a crash AFTER a video's entries were appended to the index but BEFORE
    # its manifest "tagged" record was written. A rerun must not raise duplicate-id.
    from scripts.corpus_io import init_index, read_index
    from scripts.append_to_index import append_passages
    from scripts.manifest import record

    html = _channel_html(fixtures_dir)

    def fetch(url): return html

    def ytdlp_runner(args):
        vid = args[-1].split("v=")[-1]
        (Path(args[args.index("-o") + 1].replace("%(id)s.%(ext)s", f"{vid}.en.vtt"))).write_text(
            "WEBVTT\n\n00:00:01.000 --> 00:00:03.000\nhello\n", encoding="utf-8")
        return type("R", (), {"returncode": 0})()

    def llm_call(prompt): return '{"rhetorical_move": "m", "tags": ["a"]}'

    index_path = tmp_path / "hoskinson-corpus" / "index.json"
    manifest_path = tmp_path / "manifest.jsonl"

    # Pre-seed the crashed state for video "aaa111": entries in the index, manifest at "cleaned".
    init_index(index_path, version="0.1.0", copyright_policy="own", sources={})
    append_passages(index_path, [{"video_id": "aaa111", "t_start": "00:00:01", "text": "hello",
                                  "rhetorical_move": "m", "tags": ["a"]}])
    for stage in ("discovered", "sampled", "fetched", "cleaned"):
        record(manifest_path, "aaa111", stage)

    # Rerun must complete without raising a duplicate-id ValueError.
    run(channel_videos_url="https://x/@c/videos", workdir=tmp_path, index_path=index_path,
        fetch=fetch, ytdlp_runner=ytdlp_runner, llm_call=llm_call, target=2, seed=1)

    idx = read_index(index_path)
    ids = [e["id"] for e in idx["paragraphs"]]
    # aaa111's pre-seeded entry is present exactly once (not double-appended).
    assert ids.count("hoskinson-aaa111-000") == 1

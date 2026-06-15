from pathlib import Path

from scripts.fetch_captions import build_ytdlp_args, fetch_captions


def test_build_args_human_subs(tmp_path: Path):
    args = build_ytdlp_args("abc123", out_dir=tmp_path, auto=False)
    assert "--write-subs" in args
    assert "--write-auto-subs" not in args
    assert "abc123" in args[-1]


def test_build_args_auto_subs(tmp_path: Path):
    args = build_ytdlp_args("abc123", out_dir=tmp_path, auto=True)
    assert "--write-auto-subs" in args


def test_fetch_prefers_human_then_falls_back(tmp_path: Path):
    calls = []

    def runner(args):
        calls.append(args)
        if "--write-auto-subs" in args:
            (tmp_path / "abc123.en.vtt").write_text("WEBVTT\n", encoding="utf-8")
            return type("R", (), {"returncode": 0})()
        return type("R", (), {"returncode": 0})()

    path = fetch_captions("abc123", out_dir=tmp_path, runner=runner)
    assert path is not None
    assert path.name == "abc123.en.vtt"
    assert len(calls) == 2  # human attempt, then auto


def test_fetch_returns_none_when_no_captions(tmp_path: Path):
    def runner(args):
        return type("R", (), {"returncode": 0})()

    assert fetch_captions("zzz999", out_dir=tmp_path, runner=runner) is None


def test_fetch_nonzero_is_retryable(tmp_path: Path):
    import pytest
    from scripts.fetch_captions import CaptionFetchError

    def runner(args):
        return type("R", (), {"returncode": 1})()  # fails, writes no file

    with pytest.raises(CaptionFetchError):
        fetch_captions("vid_fail", out_dir=tmp_path, runner=runner)


def test_fetch_zero_no_file_is_true_absence(tmp_path: Path):
    def runner(args):
        return type("R", (), {"returncode": 0})()  # succeeds, no captions exist

    assert fetch_captions("vid_none", out_dir=tmp_path, runner=runner) is None

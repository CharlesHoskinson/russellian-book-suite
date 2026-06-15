from scripts.sample import infer_format, length_bucket, stratum_key, sample


def _row(vid, year, dur, title="x"):
    return {"video_id": vid, "title": title, "published": f"{year}-01-01", "duration_seconds": dur}


def test_infer_format_from_title():
    assert infer_format({"title": "Surprise AMA", "duration_seconds": 3600}) == "ama"
    assert infer_format({"title": "Whiteboard: Ouroboros", "duration_seconds": 1200}) == "whiteboard"
    assert infer_format({"title": "Keynote at Summit", "duration_seconds": 2400}) == "keynote"
    assert infer_format({"title": "Quick update", "duration_seconds": 120}) == "short"


def test_length_bucket():
    assert length_bucket(120) == "xs"
    assert length_bucket(1200) == "m"
    assert length_bucket(7200) == "xl"


def test_sample_is_deterministic():
    rows = [_row(f"v{i}", 2020 + (i % 4), 100 + i * 60) for i in range(200)]
    a = sample(rows, target=30, seed=42)
    b = sample(rows, target=30, seed=42)
    assert [r["video_id"] for r in a] == [r["video_id"] for r in b]
    assert len(a) == 30


def test_sample_spans_multiple_strata():
    rows = [_row(f"v{i}", 2020 + (i % 4), 100 + i * 60) for i in range(200)]
    picked = sample(rows, target=40, seed=7)
    strata = {stratum_key(r) for r in picked}
    assert len(strata) >= 4

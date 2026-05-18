from scripts.check_address import check_address


def stub_verifier(chapter: str, rival_text: str) -> dict:
    # Simulate semantic matching: check if both chapter and rival mention consolidation/ferry
    chapter_lower = chapter.lower()
    rival_lower = rival_text.lower()
    if ("consolidated" in chapter_lower or "consolidation" in chapter_lower) and \
       ("consolidated" in rival_lower or "consolidation" in rival_lower):
        return {"addressed": True,
                "supporting_paragraph": "Yet the ferry network has consolidated."}
    return {"addressed": False, "supporting_paragraph": None}


def test_verbatim_path(tmp_path):
    chapter = "Bermuda ferries fact: Ferry consolidation reversed since 2020. More text."
    rival = {"id": "cc-1", "text": "Ferry consolidation reversed since 2020."}
    result = check_address(chapter, rival, verifier=stub_verifier, cache_dir=tmp_path)
    assert result["addressed"] is True
    assert result["mechanism"] == "verbatim"


def test_llm_verifier_path(tmp_path):
    chapter = "Yet the ferry network has consolidated — schedules dropped by half."
    rival = {"id": "cc-1", "text": "Bermuda's ferry network has consolidated rather than expanded."}
    result = check_address(chapter, rival, verifier=stub_verifier, cache_dir=tmp_path)
    assert result["addressed"] is True
    assert result["mechanism"] == "llm"


def test_cache_avoids_verifier_recall(tmp_path):
    chapter = "Yet the ferry network has consolidated — schedules dropped by half."
    rival = {"id": "cc-1", "text": "Bermuda's ferry network has consolidated rather than expanded."}
    calls = {"n": 0}
    def counting(chap, txt):
        calls["n"] += 1
        return stub_verifier(chap, txt)
    check_address(chapter, rival, verifier=counting, cache_dir=tmp_path)
    check_address(chapter, rival, verifier=counting, cache_dir=tmp_path)
    assert calls["n"] == 1

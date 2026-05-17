from scripts.acquire.rank_candidates import rank, Candidate, ScoredCandidate

def test_deterministic_ordering():
    chapter_text = "finality and the longest chain rule in proof-of-stake systems"
    candidates = [
        Candidate(id="c1", title="Longest chain finality",
                  abstract="A paper about finality in proof-of-stake."),
        Candidate(id="c2", title="Cooking recipes",
                  abstract="A book of cooking recipes for autumn."),
    ]
    r1 = rank(chapter_text, candidates)
    r2 = rank(chapter_text, candidates)
    assert [x.id for x in r1] == [x.id for x in r2]
    assert r1[0].id == "c1"
    assert all(0.0 <= s.score <= 1.0 for s in r1)

def test_empty_candidates():
    r = rank("topic", [])
    assert r == []

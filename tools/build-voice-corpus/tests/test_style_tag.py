from pathlib import Path

from scripts.style_tag import build_prompt, parse_tag_response, tag_passage


def _template() -> str:
    return (Path(__file__).parents[1] / "assets" / "extractor-prompt.md").read_text(encoding="utf-8")


def test_build_prompt_injects_passage():
    prompt = build_prompt("the thing people miss is incentives", _template())
    assert "the thing people miss is incentives" in prompt
    assert "{passage}" not in prompt


def test_parse_tag_response_plain_json():
    out = parse_tag_response('{"rhetorical_move": "reframes critique", "tags": ["candor"]}')
    assert out["rhetorical_move"] == "reframes critique"
    assert out["tags"] == ["candor"]


def test_parse_tag_response_with_code_fence():
    raw = '```json\n{"rhetorical_move": "x", "tags": ["y"]}\n```'
    out = parse_tag_response(raw)
    assert out["rhetorical_move"] == "x"


def test_tag_passage_uses_injected_llm():
    def fake_llm(prompt: str) -> str:
        assert "PASSAGE" in prompt
        return '{"rhetorical_move": "reframes critique as a tradeoff", "tags": ["candor", "direct_address"]}'

    out = tag_passage("...", llm_call=fake_llm, template=_template())
    assert out["tags"] == ["candor", "direct_address"]

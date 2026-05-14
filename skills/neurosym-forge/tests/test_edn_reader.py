# skills/neurosym-forge/tests/test_edn_reader.py
from __future__ import annotations

import pytest

from scripts._edn_reader import read_edn, EdnReadError, Keyword


def test_read_int() -> None:
    assert read_edn("42") == 42
    assert read_edn("-17") == -17
    assert read_edn("0") == 0


def test_read_float() -> None:
    assert read_edn("3.14") == 3.14
    assert read_edn("-2.5") == -2.5
    assert read_edn("1.5e3") == 1500.0


def test_read_bool_and_nil() -> None:
    assert read_edn("true") is True
    assert read_edn("false") is False
    assert read_edn("nil") is None


def test_read_string() -> None:
    assert read_edn('"hello"') == "hello"
    assert read_edn('"with \\"quotes\\""') == 'with "quotes"'
    assert read_edn('"line\\nfeed"') == "line\nfeed"
    assert read_edn('"tab\\there"') == "tab\there"
    assert read_edn('"back\\\\slash"') == "back\\slash"


def test_read_keyword() -> None:
    k = read_edn(":foo")
    assert isinstance(k, Keyword)
    assert k.name == "foo"
    assert str(k) == ":foo"


def test_read_namespaced_keyword() -> None:
    k = read_edn(":source/ingested")
    assert isinstance(k, Keyword)
    assert k.namespace == "source"
    assert k.name == "ingested"
    assert str(k) == ":source/ingested"


def test_keyword_equality_and_hashing() -> None:
    assert read_edn(":foo") == Keyword("foo")
    assert read_edn(":foo/bar") == Keyword("bar", namespace="foo")
    assert hash(Keyword("foo")) == hash(Keyword("foo"))
    assert {Keyword("foo"): 1} == {Keyword("foo"): 1}


def test_read_empty_vector() -> None:
    assert read_edn("[]") == []


def test_read_vector() -> None:
    assert read_edn("[1 2 3]") == [1, 2, 3]


def test_read_nested_vector() -> None:
    assert read_edn("[[1 2] [3 4]]") == [[1, 2], [3, 4]]


def test_read_empty_map() -> None:
    assert read_edn("{}") == {}


def test_read_map_with_keyword_keys() -> None:
    result = read_edn('{:kind :symbol :name "foo"}')
    assert result == {Keyword("kind"): Keyword("symbol"), Keyword("name"): "foo"}


def test_read_list() -> None:
    result = read_edn("(:source/ingested {:doc-id \"d1\"})")
    assert isinstance(result, list)
    assert result[0] == Keyword("ingested", namespace="source")
    assert result[1] == {Keyword("doc-id"): "d1"}


def test_read_comma_as_whitespace() -> None:
    assert read_edn("[1, 2, 3]") == [1, 2, 3]


def test_read_line_comment() -> None:
    src = """
    ; this is a comment
    [1 2 3]  ; trailing comment
    """
    assert read_edn(src) == [1, 2, 3]


def test_unsupported_tagged_literal_raises() -> None:
    with pytest.raises(EdnReadError, match="unknown tag"):
        read_edn('#uuid "550e8400-e29b-41d4-a716-446655440000"')


def test_unterminated_string_raises() -> None:
    with pytest.raises(EdnReadError, match="unterminated"):
        read_edn('"oops')


def test_read_edn_all() -> None:
    from scripts._edn_reader import read_edn_all
    src = ":foo :bar :baz"
    out = read_edn_all(src)
    assert out == [Keyword("foo"), Keyword("bar"), Keyword("baz")]

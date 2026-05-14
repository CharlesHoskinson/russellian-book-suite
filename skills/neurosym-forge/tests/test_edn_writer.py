# skills/neurosym-forge/tests/test_edn_writer.py
from __future__ import annotations

import pytest

from scripts._edn_reader import Keyword
from scripts._edn_writer import write_edn, EdnWriteError


def test_write_int() -> None:
    assert write_edn(42) == "42"
    assert write_edn(-17) == "-17"


def test_write_float() -> None:
    assert write_edn(3.14) == "3.14"


def test_write_bool_and_nil() -> None:
    assert write_edn(True) == "true"
    assert write_edn(False) == "false"
    assert write_edn(None) == "nil"


def test_write_string() -> None:
    assert write_edn("hello") == '"hello"'
    assert write_edn('with "quotes"') == '"with \\"quotes\\""'
    assert write_edn("line\nfeed") == '"line\\nfeed"'


def test_write_keyword() -> None:
    assert write_edn(Keyword("foo")) == ":foo"
    assert write_edn(Keyword("bar", namespace="ns")) == ":ns/bar"


def test_write_vector() -> None:
    assert write_edn([1, 2, 3]) == "[1 2 3]"


def test_write_map_with_keyword_keys() -> None:
    out = write_edn({Keyword("kind"): Keyword("symbol"), Keyword("name"): "foo"})
    # Order may vary; assert both pairings are present
    assert ":kind :symbol" in out or ":kind\n :symbol" in out
    assert ':name "foo"' in out or ':name\n "foo"' in out
    assert out.startswith("{") and out.endswith("}")


def test_write_nested() -> None:
    out = write_edn({Keyword("atoms"): [{Keyword("id"): "C001"}]})
    assert out == '{:atoms [{:id "C001"}]}'


def test_write_pretty() -> None:
    out = write_edn({Keyword("a"): 1, Keyword("b"): 2}, pretty=True)
    assert "\n" in out
    assert ":a 1" in out
    assert ":b 2" in out


def test_unsupported_type_raises() -> None:
    class X:
        pass
    with pytest.raises(EdnWriteError, match="cannot serialize"):
        write_edn(X())

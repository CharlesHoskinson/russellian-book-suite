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

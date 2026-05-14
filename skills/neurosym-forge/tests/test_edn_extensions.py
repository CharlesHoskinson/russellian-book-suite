# skills/neurosym-forge/tests/test_edn_extensions.py
from __future__ import annotations

import datetime as dt

import pytest

from scripts._edn_reader import (
    EdnReadError,
    Keyword,
    Symbol,
    read_edn,
    read_edn_all,
)


def test_read_bare_symbol() -> None:
    sym = read_edn("foo")
    assert isinstance(sym, Symbol)
    assert sym.name == "foo"
    assert sym.namespace is None
    assert str(sym) == "foo"


def test_read_namespaced_symbol() -> None:
    sym = read_edn("source/ingested")
    assert isinstance(sym, Symbol)
    assert sym.namespace == "source"
    assert sym.name == "ingested"
    assert str(sym) == "source/ingested"


def test_symbol_equality_and_hash() -> None:
    assert Symbol("foo") == Symbol("foo")
    assert Symbol("bar", namespace="ns") == Symbol("bar", namespace="ns")
    assert hash(Symbol("foo")) == hash(Symbol("foo"))
    assert {Symbol("foo"): 1} == {Symbol("foo"): 1}


def test_symbol_distinct_from_keyword() -> None:
    assert Symbol("foo") != Keyword("foo")
    assert hash(Symbol("foo")) != hash(Keyword("foo"))


def test_true_false_nil_still_literals() -> None:
    # Symbol parsing must not absorb the special literals
    assert read_edn("true") is True
    assert read_edn("false") is False
    assert read_edn("nil") is None


def test_symbol_in_list_head() -> None:
    result = read_edn("(source/ingested {:doc/id \"d1\"})")
    assert isinstance(result, list)
    assert result[0] == Symbol("ingested", namespace="source")
    assert result[1] == {Keyword("id", namespace="doc"): "d1"}


def test_symbol_in_vector() -> None:
    result = read_edn("[foo bar/baz]")
    assert result == [Symbol("foo"), Symbol("baz", namespace="bar")]


def test_read_inst_utc_z() -> None:
    value = read_edn('#inst "2026-05-14T15:30:00Z"')
    assert isinstance(value, dt.datetime)
    assert value.year == 2026 and value.month == 5 and value.day == 14
    assert value.hour == 15 and value.minute == 30
    assert value.tzinfo == dt.timezone.utc


def test_read_inst_with_offset() -> None:
    value = read_edn('#inst "2026-05-14T15:30:00+02:00"')
    assert isinstance(value, dt.datetime)
    assert value.utcoffset() == dt.timedelta(hours=2)


def test_read_inst_with_microseconds() -> None:
    value = read_edn('#inst "2026-05-12T16:13:51.630442Z"')
    assert value.microsecond == 630442


def test_read_inst_inside_collection() -> None:
    result = read_edn('{:ts #inst "2026-05-14T00:00:00Z"}')
    assert isinstance(result[Keyword("ts")], dt.datetime)


def test_unknown_tag_raises() -> None:
    with pytest.raises(EdnReadError, match=r"unknown tag"):
        read_edn('#uuid "550e8400-e29b-41d4-a716-446655440000"')


def test_dangling_hash_raises() -> None:
    with pytest.raises(EdnReadError, match=r"dangling"):
        read_edn("#")


def test_inst_expects_string_payload() -> None:
    with pytest.raises(EdnReadError, match=r"#inst expects a string"):
        read_edn('#inst 42')


def test_inst_invalid_format_raises() -> None:
    with pytest.raises(EdnReadError, match=r"invalid #inst literal"):
        read_edn('#inst "not-a-datetime"')


from scripts._edn_writer import write_edn


def test_write_symbol_bare() -> None:
    assert write_edn(Symbol("foo")) == "foo"


def test_write_symbol_namespaced() -> None:
    assert write_edn(Symbol("ingested", namespace="source")) == "source/ingested"


def test_write_datetime_utc() -> None:
    instant = dt.datetime(2026, 5, 14, 15, 30, tzinfo=dt.timezone.utc)
    assert write_edn(instant) == '#inst "2026-05-14T15:30:00Z"'


def test_write_datetime_offset() -> None:
    tz = dt.timezone(dt.timedelta(hours=2))
    instant = dt.datetime(2026, 5, 14, 15, 30, tzinfo=tz)
    out = write_edn(instant)
    assert out.startswith('#inst "')
    assert "+02:00" in out


def test_round_trip_symbol() -> None:
    from scripts._edn_reader import read_edn as r
    sym = Symbol("ingested", namespace="source")
    assert r(write_edn(sym)) == sym


def test_round_trip_datetime() -> None:
    from scripts._edn_reader import read_edn as r
    instant = dt.datetime(2026, 5, 12, 16, 13, 51, 630442, tzinfo=dt.timezone.utc)
    assert r(write_edn(instant)) == instant


def test_round_trip_event_list() -> None:
    from scripts._edn_reader import read_edn as r
    event = [
        Symbol("ingested", namespace="source"),
        {
            Keyword("id", namespace="doc"): "d1",
            Keyword("ingested-at"): dt.datetime(2026, 5, 14, 0, 0, 0, tzinfo=dt.timezone.utc),
        },
    ]
    s = write_edn(event)
    assert r(s) == event

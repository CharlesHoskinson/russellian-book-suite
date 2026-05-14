# skills/neurosym-forge/tests/test_edn_round_trip.py
from __future__ import annotations

from scripts._edn_reader import Keyword, read_edn
from scripts._edn_writer import write_edn


def _round_trip(value):
    return read_edn(write_edn(value))


def test_round_trip_primitives() -> None:
    for v in [42, -17, 3.14, True, False, None, "hello"]:
        assert _round_trip(v) == v


def test_round_trip_keyword() -> None:
    assert _round_trip(Keyword("foo")) == Keyword("foo")
    assert _round_trip(Keyword("bar", namespace="ns")) == Keyword("bar", namespace="ns")


def test_round_trip_nested_atomspace_record() -> None:
    record = {
        Keyword("kind"): Keyword("expression"),
        Keyword("id"): "C001",
        Keyword("predicate"): Keyword("parishes-count"),
        Keyword("subject"): Keyword("Bermuda"),
        Keyword("value"): 9,
    }
    assert _round_trip(record) == record


def test_round_trip_atomspace_full() -> None:
    space = {
        Keyword("version"): 1,
        Keyword("sorts"): [Keyword("int"), Keyword("real"), Keyword("entity")],
        Keyword("atoms"): [
            {Keyword("kind"): Keyword("expression"),
             Keyword("id"): "C001",
             Keyword("predicate"): Keyword("parishes-count"),
             Keyword("subject"): Keyword("Bermuda"),
             Keyword("value"): 9},
        ],
    }
    assert _round_trip(space) == space


def test_round_trip_string_with_escapes() -> None:
    s = 'line\nfeed and "quotes" plus \\backslash'
    assert _round_trip(s) == s

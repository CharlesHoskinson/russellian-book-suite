# skills/neurosym-forge/scripts/_edn_reader.py
"""Minimal EDN reader.

Supports the subset documented in
docs/specs/2026-05-14-booklogic-v0.4-mission-design.md § "D1 — Real EDN boundary":

    primitives: int, float, str, bool, nil
    keywords:   :foo, :foo/bar
    symbols:    foo, foo/bar
    tagged:     #inst "..."
    collections: {k v ...}, [a b ...], (a b ...)
    comments:   ; to end of line

Does NOT support: sets, custom dispatch, character literals, arbitrary tagged
literals (raises EdnReadError on unknown tags).
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Any


class EdnReadError(ValueError):
    """Raised on malformed EDN or unsupported forms."""


@dataclass(frozen=True)
class Keyword:
    """An EDN keyword. Hashable and equal-by-value.

    Accepts either ``Keyword("name")`` or ``Keyword("ns/name")`` shorthand
    (equivalent to ``Keyword("name", namespace="ns")``).  When the ``name``
    argument contains a ``/`` and no explicit ``namespace`` is supplied the
    string is split automatically, so ``Keyword("doc/id")`` and
    ``Keyword("id", namespace="doc")`` are the same object.
    """

    name: str
    namespace: str | None = None

    def __post_init__(self) -> None:
        # Auto-split "ns/name" shorthand when namespace is not explicitly set.
        if self.namespace is None and "/" in self.name:
            ns, _, name = self.name.partition("/")
            if ns and name and "/" not in name:
                object.__setattr__(self, "namespace", ns)
                object.__setattr__(self, "name", name)

    def __str__(self) -> str:
        if self.namespace:
            return f":{self.namespace}/{self.name}"
        return f":{self.name}"


@dataclass(frozen=True)
class Symbol:
    """An EDN symbol. Hashable and equal-by-value.

    Symbols are bare identifiers (`foo`, `foo/bar`) — distinct from keywords
    (which begin with `:`). The S-expression event heads in the ingestion
    trace use symbols as the leading element of a list.
    """

    name: str
    namespace: str | None = None

    def __str__(self) -> str:
        if self.namespace:
            return f"{self.namespace}/{self.name}"
        return self.name

    def __hash__(self) -> int:
        return hash(("Symbol", self.namespace, self.name))


class EdnList:
    """An EDN list, written as `(a b c ...)`. Distinct from EdnVector.

    REQ-EDN-051: the paren/bracket distinction is preserved through
    read_edn -> write_edn -> read_edn.

    Equality is item-wise and tolerates comparison against a plain Python
    list so that pre-existing callers asserting `read_edn(...) == [...]`
    keep working. To distinguish list vs vector, use ``isinstance``.
    """
    __slots__ = ("items",)
    def __init__(self, items=None):
        self.items = list(items) if items is not None else []
    def __iter__(self): return iter(self.items)
    def __len__(self): return len(self.items)
    def __getitem__(self, i): return self.items[i]
    def __setitem__(self, i, v): self.items[i] = v
    def __delitem__(self, i): del self.items[i]
    def __contains__(self, x): return x in self.items
    def __bool__(self): return bool(self.items)
    def __reversed__(self): return reversed(self.items)
    def append(self, x): self.items.append(x)
    def extend(self, xs): self.items.extend(xs)
    def insert(self, i, x): self.items.insert(i, x)
    def pop(self, *args): return self.items.pop(*args)
    def remove(self, x): self.items.remove(x)
    def clear(self): self.items.clear()
    def index(self, *args, **kw): return self.items.index(*args, **kw)
    def count(self, x): return self.items.count(x)
    def __eq__(self, other):
        if isinstance(other, EdnList):
            return self.items == other.items
        if isinstance(other, list):
            return self.items == other
        return NotImplemented
    def __ne__(self, other):
        eq = self.__eq__(other)
        if eq is NotImplemented:
            return eq
        return not eq
    __hash__ = None  # type: ignore[assignment]
    def __repr__(self): return f"EdnList({self.items!r})"


class EdnVector:
    """An EDN vector, written as `[a b c ...]`. Distinct from EdnList.

    Equality tolerates a plain Python list (same item-wise) for caller
    compatibility; use ``isinstance`` to distinguish from ``EdnList``.
    """
    __slots__ = ("items",)
    def __init__(self, items=None):
        self.items = list(items) if items is not None else []
    def __iter__(self): return iter(self.items)
    def __len__(self): return len(self.items)
    def __getitem__(self, i): return self.items[i]
    def __setitem__(self, i, v): self.items[i] = v
    def __delitem__(self, i): del self.items[i]
    def __contains__(self, x): return x in self.items
    def __bool__(self): return bool(self.items)
    def __reversed__(self): return reversed(self.items)
    def append(self, x): self.items.append(x)
    def extend(self, xs): self.items.extend(xs)
    def insert(self, i, x): self.items.insert(i, x)
    def pop(self, *args): return self.items.pop(*args)
    def remove(self, x): self.items.remove(x)
    def clear(self): self.items.clear()
    def index(self, *args, **kw): return self.items.index(*args, **kw)
    def count(self, x): return self.items.count(x)
    def __eq__(self, other):
        if isinstance(other, EdnVector):
            return self.items == other.items
        if isinstance(other, list):
            return self.items == other
        return NotImplemented
    def __ne__(self, other):
        eq = self.__eq__(other)
        if eq is NotImplemented:
            return eq
        return not eq
    __hash__ = None  # type: ignore[assignment]
    def __repr__(self): return f"EdnVector({self.items!r})"


def _parse_inst(s: str) -> dt.datetime:
    """Parse an ISO-8601 timestamp into a timezone-aware datetime.

    Accepts both 'Z' and '+HH:MM' offsets. Microsecond precision honoured.
    """
    # Python 3.11+ datetime.fromisoformat handles 'Z' natively; for
    # earlier interpreters, normalise 'Z' to '+00:00'.
    normalized = s.replace("Z", "+00:00") if s.endswith("Z") else s
    return dt.datetime.fromisoformat(normalized)


def read_edn(s: str) -> Any:
    """Parse a single EDN form from the given string."""
    parser = _Parser(s)
    parser._skip_ws_and_comments()
    if parser._eof():
        raise EdnReadError("empty input")
    value = parser._parse_form()
    parser._skip_ws_and_comments()
    if not parser._eof():
        raise EdnReadError(f"trailing content at position {parser.pos}")
    return value


def read_edn_all(s: str) -> list[Any]:
    """Parse all top-level EDN forms from the given string. Empty input → []."""
    parser = _Parser(s)
    out: list[Any] = []
    parser._skip_ws_and_comments()
    while not parser._eof():
        out.append(parser._parse_form())
        parser._skip_ws_and_comments()
    return out


class _Parser:
    def __init__(self, source: str) -> None:
        self.src = source
        self.pos = 0

    def _eof(self) -> bool:
        return self.pos >= len(self.src)

    def _peek(self) -> str:
        return self.src[self.pos] if not self._eof() else ""

    def _advance(self) -> str:
        c = self.src[self.pos]
        self.pos += 1
        return c

    def _skip_ws_and_comments(self) -> None:
        while not self._eof():
            c = self._peek()
            if c in " \t\n\r,":
                self.pos += 1
            elif c == ";":
                while not self._eof() and self._peek() != "\n":
                    self.pos += 1
            else:
                return

    def _parse_form(self) -> Any:
        self._skip_ws_and_comments()
        if self._eof():
            raise EdnReadError("unexpected end of input")
        c = self._peek()
        if c == "{":
            return self._parse_map()
        if c == "[":
            return self._parse_vector()
        if c == "(":
            return self._parse_list()
        if c == '"':
            return self._parse_string()
        if c == ":":
            return self._parse_keyword()
        if c == "#":
            self._advance()  # consume '#'
            if self._eof():
                raise EdnReadError("dangling #")
            tag_start = self.pos
            while not self._eof() and self._peek() not in " \t\n\r,()[]{}\";":
                self.pos += 1
            tag = self.src[tag_start:self.pos]
            if not tag:
                raise EdnReadError("dangling # (empty tag)")
            if tag == "inst":
                self._skip_ws_and_comments()
                value = self._parse_form()
                if not isinstance(value, str):
                    raise EdnReadError(
                        f"#inst expects a string payload, got {type(value).__name__}"
                    )
                try:
                    return _parse_inst(value)
                except ValueError as e:
                    raise EdnReadError(f"invalid #inst literal: {e}")
            raise EdnReadError(f"unknown tag #{tag!r}")
        return self._parse_atom()

    def _parse_map(self) -> dict[Any, Any]:
        self._advance()  # consume '{'
        out: dict[Any, Any] = {}
        while True:
            self._skip_ws_and_comments()
            if self._peek() == "}":
                self._advance()
                return out
            key = self._parse_form()
            value = self._parse_form()
            out[key] = value

    def _parse_vector(self) -> "EdnVector":
        items = self._parse_seq("[", "]")
        return EdnVector(items)

    def _parse_list(self) -> "EdnList":
        items = self._parse_seq("(", ")")
        return EdnList(items)

    def _parse_seq(self, open_c: str, close_c: str) -> list[Any]:
        self._advance()  # consume opener
        out: list[Any] = []
        while True:
            self._skip_ws_and_comments()
            if self._peek() == close_c:
                self._advance()
                return out
            out.append(self._parse_form())

    def _parse_string(self) -> str:
        self._advance()  # consume '"'
        out: list[str] = []
        while True:
            if self._eof():
                raise EdnReadError("unterminated string")
            c = self._advance()
            if c == '"':
                return "".join(out)
            if c == "\\":
                esc = self._advance()
                out.append({"n": "\n", "r": "\r", "t": "\t", '"': '"', "\\": "\\"}.get(esc, esc))
            else:
                out.append(c)

    def _parse_keyword(self) -> Keyword:
        self._advance()  # consume ':'
        start = self.pos
        while not self._eof() and self._peek() not in " \t\n\r,()[]{}\";":
            self.pos += 1
        token = self.src[start:self.pos]
        if not token:
            raise EdnReadError(f"empty keyword at position {start}")
        if "/" in token:
            ns, _, name = token.partition("/")
            return Keyword(name=name, namespace=ns)
        return Keyword(name=token)

    def _parse_atom(self) -> Any:
        start = self.pos
        while not self._eof() and self._peek() not in " \t\n\r,()[]{}\";":
            self.pos += 1
        token = self.src[start:self.pos]
        if token == "true":
            return True
        if token == "false":
            return False
        if token == "nil":
            return None
        # number?
        try:
            return int(token)
        except ValueError:
            pass
        try:
            return float(token)
        except ValueError:
            pass
        # Symbol: EDN allows symbols starting with letters, _, and many operator
        # characters (=, +, -, *, /, <, >, !, ?, &, %, ~, ^, .). We accept any
        # non-empty token that isn't a number or boolean as a symbol so that
        # operator heads like `=`, `~=`, `*`, `+`, `-` parse correctly.
        if token and "/" not in token:
            return Symbol(name=token)
        if token and "/" in token:
            ns, _, name = token.partition("/")
            if ns and name and "/" not in name:
                return Symbol(name=name, namespace=ns)
        raise EdnReadError(f"unrecognised atom {token!r} at position {start}")

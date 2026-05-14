# skills/neurosym-forge/scripts/_edn_reader.py
"""Minimal EDN reader.

Supports the subset documented in
docs/specs/2026-05-14-booklogic-v0.4-mission-design.md § "D1 — Real EDN boundary":

    primitives: int, float, str, bool, nil
    keywords:   :foo, :foo/bar
    collections: {k v ...}, [a b ...], (a b ...)
    comments:   ; to end of line

Does NOT support: tagged literals, sets, symbols, custom dispatch, character
literals. The reader raises EdnReadError on unsupported forms.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class EdnReadError(ValueError):
    """Raised on malformed EDN or unsupported forms."""


@dataclass(frozen=True)
class Keyword:
    """An EDN keyword. Hashable and equal-by-value."""

    name: str
    namespace: str | None = None

    def __str__(self) -> str:
        if self.namespace:
            return f":{self.namespace}/{self.name}"
        return f":{self.name}"


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
            raise EdnReadError(
                f"tagged literals, sets, and custom dispatch are not supported "
                f"in PR-1 (position {self.pos})"
            )
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

    def _parse_vector(self) -> list[Any]:
        return self._parse_seq("[", "]")

    def _parse_list(self) -> list[Any]:
        return self._parse_seq("(", ")")

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
        raise EdnReadError(f"unrecognised atom {token!r} at position {start}")

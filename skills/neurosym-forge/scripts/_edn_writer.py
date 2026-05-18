# skills/neurosym-forge/scripts/_edn_writer.py
"""Minimal EDN writer.

Emits EDN syntax for the subset documented in PR-1's plan. Supports the
same types the reader accepts (Keyword, str, int, float, bool, None, list,
dict). Unsupported types raise EdnWriteError.

Two output modes:
    write_edn(obj)              → compact one-line EDN
    write_edn(obj, pretty=True) → multi-line with indentation for maps/vectors

The writer preserves dict insertion order for stability.
"""
from __future__ import annotations

import datetime as dt
from typing import Any

from scripts._edn_reader import Keyword, Symbol


class EdnWriteError(ValueError):
    """Raised when an unsupported type appears in the value."""


_ESC_MAP = {"\n": "\\n", "\r": "\\r", "\t": "\\t", '"': '\\"', "\\": "\\\\"}


def write_edn(value: Any, pretty: bool = False) -> str:
    """Serialize `value` to an EDN string."""
    if pretty:
        return _emit_pretty(value, indent=0)
    return _emit_compact(value)


def _emit_compact(value: Any) -> str:
    if value is None:
        return "nil"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, Keyword):
        return str(value)
    if isinstance(value, Symbol):
        return str(value)
    if isinstance(value, dt.datetime):
        iso = value.isoformat()
        if iso.endswith("+00:00"):
            iso = iso[:-6] + "Z"
        return f'#inst "{iso}"'
    if isinstance(value, str):
        return _emit_string(value)
    if isinstance(value, bool):  # bool is subclass of int — must be after bool branch
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return _emit_float(value)
    if isinstance(value, list):
        return "[" + " ".join(_emit_compact(v) for v in value) + "]"
    if isinstance(value, dict):
        parts = []
        for k, v in value.items():
            parts.append(_emit_compact(k))
            parts.append(_emit_compact(v))
        return "{" + " ".join(parts) + "}"
    raise EdnWriteError(f"cannot serialize {type(value).__name__}: {value!r}")


def _emit_pretty(value: Any, indent: int) -> str:
    if isinstance(value, dict) and value:
        prefix = " " * indent
        lines = ["{"]
        for k, v in value.items():
            kstr = _emit_compact(k)
            vstr = _emit_pretty(v, indent + len(kstr) + 2)
            lines.append(f"{prefix} {kstr} {vstr}")
        lines.append(f"{prefix}}}")
        return "\n".join(lines)
    if isinstance(value, list) and value:
        if all(not isinstance(x, (dict, list)) or not x for x in value):
            return _emit_compact(value)
        prefix = " " * indent
        lines = ["["]
        for v in value:
            lines.append(f"{prefix} {_emit_pretty(v, indent + 1)}")
        lines.append(f"{prefix}]")
        return "\n".join(lines)
    return _emit_compact(value)


def _emit_string(s: str) -> str:
    chunks = ['"']
    for c in s:
        chunks.append(_ESC_MAP.get(c, c))
    chunks.append('"')
    return "".join(chunks)


def _emit_float(f: float) -> str:
    """Emit a float as EDN-readable text WITHOUT scientific notation.

    edn-rs 0.19 does not parse scientific notation; falling back to a
    fixed-point representation is mandatory for the Rust read side to
    parse the value as Edn::Double rather than silently fall through to
    Edn::Str. REQ-EDN-050.
    """
    from math import isfinite, isnan
    if isnan(f) or not isfinite(f):
        raise EdnWriteError(f"cannot emit non-finite float: {f!r}")
    s = f"{f:.17g}"  # shortest round-trippable
    if "e" in s.lower():
        # Fall back to fixed-point. Use a generous 20 fractional digits;
        # strip trailing zeros but keep the decimal point so EDN reads
        # this as a Double rather than an Int.
        s = f"{f:.20f}".rstrip("0").rstrip(".") or "0"
    if "." not in s:
        s += ".0"
    return s

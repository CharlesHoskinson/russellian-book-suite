from __future__ import annotations

from pathlib import Path

import pytest

from scripts._io import read_edn_as_json, write_json_as_edn, file_checksum


def test_round_trip(tmp_path: Path) -> None:
    payload = {"sorts": [":int", ":real"], "rules": [], "atoms": []}
    out = tmp_path / "atomspace.edn"
    write_json_as_edn(out, payload)
    back = read_edn_as_json(out)
    assert back == payload


def test_keywords_render_as_edn(tmp_path: Path) -> None:
    out = tmp_path / "x.edn"
    write_json_as_edn(out, {"k": ":foo"})
    text = out.read_text(encoding="utf-8")
    assert ":foo" in text
    assert '"k"' in text


def test_checksum_stable(tmp_path: Path) -> None:
    f = tmp_path / "x.edn"
    f.write_text("hello", encoding="utf-8")
    a = file_checksum(f)
    b = file_checksum(f)
    assert a == b
    assert len(a) == 64  # sha256 hex


def test_checksum_changes_on_edit(tmp_path: Path) -> None:
    f = tmp_path / "x.edn"
    f.write_text("hello", encoding="utf-8")
    a = file_checksum(f)
    f.write_text("hello!", encoding="utf-8")
    b = file_checksum(f)
    assert a != b

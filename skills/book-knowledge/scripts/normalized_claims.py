"""Deterministic normalized fact projection for contradiction checks."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

TOLERANCE = 1.0e-6


@dataclass(frozen=True)
class UnitSpec:
    dimension: str
    canonical_unit: str
    scale_to_canonical: float


UNIT_REGISTRY: dict[str, UnitSpec] = {
    "m": UnitSpec("length", "m", 1.0),
    "meter": UnitSpec("length", "m", 1.0),
    "meters": UnitSpec("length", "m", 1.0),
    "metre": UnitSpec("length", "m", 1.0),
    "metres": UnitSpec("length", "m", 1.0),
    "cm": UnitSpec("length", "m", 0.01),
    "centimeter": UnitSpec("length", "m", 0.01),
    "centimeters": UnitSpec("length", "m", 0.01),
    "km": UnitSpec("length", "m", 1000.0),
    "kilometer": UnitSpec("length", "m", 1000.0),
    "kilometers": UnitSpec("length", "m", 1000.0),
    "mi": UnitSpec("length", "m", 1609.344),
    "mile": UnitSpec("length", "m", 1609.344),
    "miles": UnitSpec("length", "m", 1609.344),
    "g": UnitSpec("mass", "kg", 0.001),
    "gram": UnitSpec("mass", "kg", 0.001),
    "grams": UnitSpec("mass", "kg", 0.001),
    "kg": UnitSpec("mass", "kg", 1.0),
    "kilogram": UnitSpec("mass", "kg", 1.0),
    "kilograms": UnitSpec("mass", "kg", 1.0),
    "s": UnitSpec("time", "s", 1.0),
    "second": UnitSpec("time", "s", 1.0),
    "seconds": UnitSpec("time", "s", 1.0),
    "min": UnitSpec("time", "s", 60.0),
    "minute": UnitSpec("time", "s", 60.0),
    "minutes": UnitSpec("time", "s", 60.0),
    "h": UnitSpec("time", "s", 3600.0),
    "hour": UnitSpec("time", "s", 3600.0),
    "hours": UnitSpec("time", "s", 3600.0),
}

_UNIT_PATTERN = "|".join(
    sorted((re.escape(unit) for unit in UNIT_REGISTRY), key=len, reverse=True)
)
_QUANTITY_RE = re.compile(
    rf"^\s*(?P<subject>[a-z0-9][a-z0-9 -]*?)\s+"
    rf"(?P<predicate>length|distance|height|depth|mass|weight|duration)\s+"
    rf"(?:is|was|equals|=)\s+"
    rf"(?P<value>[0-9]+(?:\.[0-9]+)?)\s*(?P<unit>{_UNIT_PATTERN})"
    rf"(?:\s+from\s+(?P<start>[0-9]{{4}})\s+to\s+(?P<end>[0-9]{{4}})"
    rf"\s+requires\s+(?P<required>overlap|disjoint))?\s*\.?\s*$",
    re.IGNORECASE,
)
_INTERVAL_RE = re.compile(
    r"^\s*(?P<subject>[a-z0-9][a-z0-9 -]*?)\s+"
    r"(?P<predicate>active|valid|available|occupation|period)\s+"
    r"from\s+(?P<start>[0-9]{4})\s+to\s+(?P<end>[0-9]{4})\s+"
    r"requires\s+(?P<required>overlap|disjoint)\s*\.?\s*$",
    re.IGNORECASE,
)


def _key(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def _object_text(value: float, unit: str) -> str:
    rendered = f"{value:.12g}"
    return f"{rendered} {unit}"


def normalized_rows_for_claim(record: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """Return normalized helper rows for one claim record.

    Only existing claim fields are read. A non-matching text yields empty rows.
    """
    claim_id = str(record.get("claim_id") or record.get("id") or "")
    text = str(record.get("canonical_text") or "")
    rows: dict[str, list[dict[str, Any]]] = {
        "claim-quantity": [],
        "claim-unit": [],
        "claim-time-interval": [],
        "claim-normal-form": [],
    }
    if not claim_id:
        return rows

    quantity_match = _QUANTITY_RE.match(text)
    if quantity_match:
        raw_unit = _key(quantity_match.group("unit"))
        unit_spec = UNIT_REGISTRY[raw_unit]
        raw_value = float(quantity_match.group("value"))
        canonical_value = raw_value * unit_spec.scale_to_canonical
        quantity_id = f"{claim_id}\x1fquantity"
        interval_id = (
            f"{claim_id}\x1ftime"
            if quantity_match.group("start") is not None
            else None
        )
        subject = _key(quantity_match.group("subject"))
        predicate = _key(quantity_match.group("predicate"))
        rows["claim-quantity"].append(
            {
                "id": quantity_id,
                "claim_id": claim_id,
                "value": raw_value,
                "unit": raw_unit,
                "canonical_value": canonical_value,
                "canonical_unit": unit_spec.canonical_unit,
                "dimension": unit_spec.dimension,
            }
        )
        rows["claim-unit"].append(
            {
                "id": f"{claim_id}\x1funit",
                "claim_id": claim_id,
                "unit": raw_unit,
                "canonical_unit": unit_spec.canonical_unit,
                "dimension": unit_spec.dimension,
                "scale_to_canonical": unit_spec.scale_to_canonical,
            }
        )
        if interval_id is not None:
            start = int(quantity_match.group("start"))
            end = int(quantity_match.group("end"))
            if start <= end:
                rows["claim-time-interval"].append(
                    {
                        "id": interval_id,
                        "claim_id": claim_id,
                        "subject": subject,
                        "predicate": predicate,
                        "start": start,
                        "end": end,
                        "required_relation": _key(quantity_match.group("required")),
                    }
                )
        rows["claim-normal-form"].append(
            {
                "id": f"{claim_id}\x1fnormal",
                "claim_id": claim_id,
                "subject": subject,
                "predicate": predicate,
                "object": _object_text(canonical_value, unit_spec.canonical_unit),
                "quantity_id": quantity_id,
                "time_interval_id": interval_id,
            }
        )
        return rows

    interval_match = _INTERVAL_RE.match(text)
    if interval_match:
        start = int(interval_match.group("start"))
        end = int(interval_match.group("end"))
        if start > end:
            return rows
        interval_id = f"{claim_id}\x1ftime"
        subject = _key(interval_match.group("subject"))
        predicate = _key(interval_match.group("predicate"))
        rows["claim-time-interval"].append(
            {
                "id": interval_id,
                "claim_id": claim_id,
                "subject": subject,
                "predicate": predicate,
                "start": start,
                "end": end,
                "required_relation": _key(interval_match.group("required")),
            }
        )
        rows["claim-normal-form"].append(
            {
                "id": f"{claim_id}\x1fnormal",
                "claim_id": claim_id,
                "subject": subject,
                "predicate": predicate,
                "object": f"{start}-{end}",
                "quantity_id": None,
                "time_interval_id": interval_id,
            }
        )
    return rows

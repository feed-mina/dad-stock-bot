from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Iterable, Mapping


SUMMARY_FIELDS = [
    "symbol",
    "name",
    "base_date",
    "market",
    "close",
    "change",
    "change_rate",
    "open",
    "high",
    "low",
    "volume",
    "amount",
    "market_cap",
    "source",
]


def build_summary_row(tick: Mapping[str, Any]) -> dict[str, Any]:
    raw = _parse_raw_json(tick.get("raw_json"))
    return {
        "symbol": str(tick.get("symbol", "")),
        "name": str(raw.get("itmsNm") or ""),
        "base_date": str(raw.get("basDt") or tick.get("event_time") or ""),
        "market": str(raw.get("mrktCtg") or ""),
        "close": _to_int(tick.get("price") or raw.get("clpr")),
        "change": _to_int(raw.get("vs")),
        "change_rate": _to_float(raw.get("fltRt")),
        "open": _to_int(raw.get("mkp")),
        "high": _to_int(raw.get("hipr")),
        "low": _to_int(raw.get("lopr")),
        "volume": _to_int(tick.get("volume") or raw.get("trqu")),
        "amount": _to_int(raw.get("trPrc")),
        "market_cap": _to_int(raw.get("mrktTotAmt")),
        "source": str(tick.get("source", "")),
    }


def build_summary_rows(ticks: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [build_summary_row(tick) for tick in ticks]


def write_summary_csv(rows: Iterable[Mapping[str, Any]], output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=SUMMARY_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return path


def _parse_raw_json(value: Any) -> Mapping[str, Any]:
    if not value:
        return {}
    if isinstance(value, Mapping):
        return value
    try:
        parsed = json.loads(str(value))
    except json.JSONDecodeError:
        return {}
    if isinstance(parsed, Mapping):
        return parsed
    return {}


def _to_int(value: Any) -> int:
    try:
        if value in (None, ""):
            return 0
        return int(float(str(value).replace(",", "")))
    except (TypeError, ValueError):
        return 0


def _to_float(value: Any) -> float | None:
    try:
        if value in (None, ""):
            return None
        return float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return None


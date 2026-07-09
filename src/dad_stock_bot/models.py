from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Mapping, Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _to_int(value: Any, default: int = 0) -> int:
    try:
        if value in (None, ""):
            return default
        return int(float(str(value).replace(",", "")))
    except (TypeError, ValueError):
        return default


def _to_float(value: Any) -> float | None:
    try:
        if value in (None, ""):
            return None
        return float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return None


@dataclass(frozen=True)
class Quote:
    symbol: str
    price: int
    captured_at: str = field(default_factory=utc_now_iso)
    volume: int = 0
    raw: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_kis_rest(cls, output: Mapping[str, Any]) -> "Quote":
        return cls(
            symbol=str(output.get("stck_shrn_iscd") or output.get("mksc_shrn_iscd") or ""),
            price=_to_int(output.get("stck_prpr")),
            volume=_to_int(output.get("acml_vol")),
            raw=dict(output),
        )


@dataclass(frozen=True)
class DailyPrice:
    symbol: str
    base_date: str
    close: int
    open: int = 0
    high: int = 0
    low: int = 0
    volume: int = 0
    amount: int = 0
    name: str = ""
    market: str = ""
    captured_at: str = field(default_factory=utc_now_iso)
    raw: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_public_data(cls, item: Mapping[str, Any]) -> "DailyPrice":
        return cls(
            symbol=str(item.get("srtnCd") or item.get("SRtnCd") or ""),
            base_date=str(item.get("basDt") or ""),
            close=_to_int(item.get("clpr")),
            open=_to_int(item.get("mkp")),
            high=_to_int(item.get("hipr")),
            low=_to_int(item.get("lopr")),
            volume=_to_int(item.get("trqu")),
            amount=_to_int(item.get("trPrc")),
            name=str(item.get("itmsNm") or ""),
            market=str(item.get("mrktCtg") or ""),
            raw=dict(item),
        )


@dataclass(frozen=True)
class RealtimeTrade:
    symbol: str
    trade_time: str
    price: int
    trade_volume: int
    accumulated_volume: int
    change_rate: float | None
    captured_at: str = field(default_factory=utc_now_iso)
    raw: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_kis_fields(cls, fields: Mapping[str, Any]) -> "RealtimeTrade":
        return cls(
            symbol=str(fields.get("MKSC_SHRN_ISCD", "")),
            trade_time=str(fields.get("STCK_CNTG_HOUR", "")),
            price=_to_int(fields.get("STCK_PRPR")),
            trade_volume=_to_int(fields.get("CNTG_VOL")),
            accumulated_volume=_to_int(fields.get("ACML_VOL")),
            change_rate=_to_float(fields.get("PRDY_CTRT")),
            raw=dict(fields),
        )


@dataclass(frozen=True)
class TradeSignal:
    symbol: str
    action: str
    reason: str
    price: int
    generated_at: str = field(default_factory=utc_now_iso)

from __future__ import annotations

import asyncio
import json
from typing import Any, AsyncIterator, Mapping

from .models import RealtimeTrade


REALTIME_TRADE_TR_ID = "H0STCNT0"
REALTIME_TRADE_COLUMNS = [
    "MKSC_SHRN_ISCD",
    "STCK_CNTG_HOUR",
    "STCK_PRPR",
    "PRDY_VRSS_SIGN",
    "PRDY_VRSS",
    "PRDY_CTRT",
    "WGHN_AVRG_STCK_PRC",
    "STCK_OPRC",
    "STCK_HGPR",
    "STCK_LWPR",
    "ASKP1",
    "BIDP1",
    "CNTG_VOL",
    "ACML_VOL",
    "ACML_TR_PBMN",
    "SELN_CNTG_CSNU",
    "SHNU_CNTG_CSNU",
    "NTBY_CNTG_CSNU",
    "CTTR",
    "SELN_CNTG_SMTN",
    "SHNU_CNTG_SMTN",
    "CCLD_DVSN",
    "SHNU_RATE",
    "PRDY_VOL_VRSS_ACML_VOL_RATE",
    "OPRC_HOUR",
    "OPRC_VRSS_PRPR_SIGN",
    "OPRC_VRSS_PRPR",
    "HGPR_HOUR",
    "HGPR_VRSS_PRPR_SIGN",
    "HGPR_VRSS_PRPR",
    "LWPR_HOUR",
    "LWPR_VRSS_PRPR_SIGN",
    "LWPR_VRSS_PRPR",
    "BSOP_DATE",
    "NEW_MKOP_CLS_CODE",
    "TRHT_YN",
    "ASKP_RSQN1",
    "BIDP_RSQN1",
    "TOTAL_ASKP_RSQN",
    "TOTAL_BIDP_RSQN",
    "VOL_TNRT",
    "PRDY_SMNS_HOUR_ACML_VOL",
    "PRDY_SMNS_HOUR_ACML_VOL_RATE",
    "HOUR_CLS_CODE",
    "MRKT_TRTM_CLS_CODE",
    "VI_STND_PRC",
]


def build_subscribe_message(
    approval_key: str,
    symbol: str,
    tr_type: str = "1",
    tr_id: str = REALTIME_TRADE_TR_ID,
    custtype: str = "P",
) -> dict[str, Any]:
    if not approval_key:
        raise ValueError("approval_key is required.")
    if not symbol:
        raise ValueError("symbol is required.")
    return {
        "header": {
            "approval_key": approval_key,
            "custtype": custtype,
            "tr_type": tr_type,
            "content-type": "utf-8",
        },
        "body": {
            "input": {
                "tr_id": tr_id,
                "tr_key": symbol,
            }
        },
    }


def parse_realtime_trade_message(message: str) -> list[RealtimeTrade]:
    if not message or message[0] != "0":
        return []

    parts = message.split("|", 3)
    if len(parts) != 4:
        return []

    _, tr_id, raw_count, payload = parts
    if tr_id != REALTIME_TRADE_TR_ID:
        return []

    try:
        count = int(raw_count)
    except ValueError:
        count = 1

    values = payload.split("^")
    chunk_size = len(REALTIME_TRADE_COLUMNS)
    trades: list[RealtimeTrade] = []

    for index in range(max(count, 1)):
        start = index * chunk_size
        chunk = values[start : start + chunk_size]
        if len(chunk) < chunk_size:
            if index == 0:
                chunk = values[:chunk_size]
            else:
                break
        mapped = dict(zip(REALTIME_TRADE_COLUMNS, chunk))
        trades.append(RealtimeTrade.from_kis_fields(mapped))

    return trades


async def stream_realtime_trades(
    websocket_url: str,
    approval_key: str,
    symbols: tuple[str, ...],
    reconnect_delay_seconds: int = 3,
) -> AsyncIterator[RealtimeTrade]:
    try:
        import websockets
    except ImportError as exc:
        raise RuntimeError(
            "websockets is required for live streaming. Install project dependencies first."
        ) from exc

    while True:
        try:
            async with websockets.connect(websocket_url, ping_interval=None) as websocket:
                for symbol in symbols:
                    message = build_subscribe_message(approval_key, symbol)
                    await websocket.send(json.dumps(message, ensure_ascii=False))

                while True:
                    raw_message = await websocket.recv()
                    if isinstance(raw_message, bytes):
                        raw_message = raw_message.decode("utf-8")
                    if _is_pingpong(raw_message):
                        await websocket.pong(raw_message)
                        continue
                    for trade in parse_realtime_trade_message(str(raw_message)):
                        yield trade
        except asyncio.CancelledError:
            raise
        except Exception:
            await asyncio.sleep(reconnect_delay_seconds)


def _is_pingpong(message: str) -> bool:
    try:
        parsed = json.loads(message)
    except json.JSONDecodeError:
        return False
    if not isinstance(parsed, Mapping):
        return False
    header = parsed.get("header", {})
    return isinstance(header, Mapping) and header.get("tr_id") == "PINGPONG"


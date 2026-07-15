from __future__ import annotations

from contextlib import contextmanager
import csv
from pathlib import Path
import json
import sqlite3
from typing import Iterator, Iterable

from .models import DailyPrice, Quote, RealtimeTrade, TradeSignal


class SQLiteMarketStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def _init_schema(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS ticks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    price INTEGER NOT NULL,
                    volume INTEGER NOT NULL DEFAULT 0,
                    event_time TEXT NOT NULL,
                    source TEXT NOT NULL,
                    raw_json TEXT NOT NULL
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_ticks_symbol_id ON ticks(symbol, id)"
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS signals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    action TEXT NOT NULL,
                    price INTEGER NOT NULL,
                    reason TEXT NOT NULL,
                    generated_at TEXT NOT NULL
                )
                """
            )

    def save_quote(self, quote: Quote) -> None:
        self._insert_tick(
            symbol=quote.symbol,
            price=quote.price,
            volume=quote.volume,
            event_time=quote.captured_at,
            source="rest",
            raw=quote.raw,
        )

    def save_daily_price(self, price: DailyPrice) -> None:
        event_time = price.base_date or price.captured_at
        with self._connect() as connection:
            connection.execute(
                """
                DELETE FROM ticks
                WHERE symbol = ? AND event_time = ? AND source = ?
                """,
                (price.symbol, event_time, "publicdata"),
            )
        self._insert_tick(
            symbol=price.symbol,
            price=price.close,
            volume=price.volume,
            event_time=event_time,
            source="publicdata",
            raw=price.raw,
        )

    def save_trade(self, trade: RealtimeTrade) -> None:
        self._insert_tick(
            symbol=trade.symbol,
            price=trade.price,
            volume=trade.trade_volume,
            event_time=trade.captured_at,
            source="websocket",
            raw=trade.raw,
        )

    def _insert_tick(
        self,
        symbol: str,
        price: int,
        volume: int,
        event_time: str,
        source: str,
        raw: object,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO ticks(symbol, price, volume, event_time, source, raw_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (symbol, price, volume, event_time, source, json.dumps(raw, ensure_ascii=False)),
            )

    def recent_prices(self, symbol: str, limit: int) -> list[int]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT price
                FROM ticks
                WHERE symbol = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (symbol, limit),
            ).fetchall()
        return [int(row["price"]) for row in reversed(rows)]

    def latest_ticks(self, symbol: str | None = None, limit: int = 20) -> list[dict[str, object]]:
        sql = """
            SELECT symbol, price, volume, event_time, source, raw_json
            FROM ticks
        """
        params: list[object] = []
        if symbol:
            sql += " WHERE symbol = ?"
            params.append(symbol)
        sql += " ORDER BY id DESC LIMIT ?"
        params.append(limit)

        with self._connect() as connection:
            rows = connection.execute(sql, params).fetchall()

        result: list[dict[str, object]] = []
        for row in rows:
            result.append(
                {
                    "symbol": row["symbol"],
                    "price": int(row["price"]),
                    "volume": int(row["volume"]),
                    "event_time": row["event_time"],
                    "source": row["source"],
                    "raw_json": row["raw_json"],
                }
            )
        return result

    def export_ticks_csv(
        self,
        output_path: str | Path,
        symbol: str | None = None,
        limit: int = 200,
    ) -> Path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        rows = list(reversed(self.latest_ticks(symbol=symbol, limit=limit)))
        with path.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(
                file,
                fieldnames=["symbol", "price", "volume", "event_time", "source"],
                extrasaction="ignore",
            )
            writer.writeheader()
            writer.writerows(rows)
        return path

    def dedupe_ticks(self, source: str | None = "publicdata") -> int:
        where = "source = ?" if source else "1 = 1"
        params: list[object] = [source] if source else []
        sql = f"""
            DELETE FROM ticks
            WHERE id NOT IN (
                SELECT MAX(id)
                FROM ticks
                WHERE {where}
                GROUP BY symbol, event_time, source
            )
            AND {where}
        """
        with self._connect() as connection:
            cursor = connection.execute(sql, params + params)
            return int(cursor.rowcount)

    def save_signal(self, signal: TradeSignal) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO signals(symbol, action, price, reason, generated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    signal.symbol,
                    signal.action,
                    signal.price,
                    signal.reason,
                    signal.generated_at,
                ),
            )

    def save_signals(self, signals: Iterable[TradeSignal]) -> None:
        for signal in signals:
            self.save_signal(signal)

from __future__ import annotations

import argparse
import asyncio
import json
import logging
from pathlib import Path
from typing import Sequence

from .alerts import TelegramNotifier
from .config import Settings
from .kis import KISClient
from .providers import PublicDataStockPriceProvider
from .realtime import stream_realtime_trades
from .storage import SQLiteMarketStore
from .strategy import MovingAverageBreakoutStrategy


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="dad-stock-bot")
    parser.add_argument("--env-file", default=".env", help="Path to .env file.")
    parser.add_argument("--log-level", default="INFO", help="Python logging level.")

    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("check-config", help="Print non-secret configuration.")

    quote = subparsers.add_parser("quote", help="Fetch one REST quote and store it.")
    quote.add_argument("symbol", nargs="?", help="Stock code. Defaults to first configured symbol.")
    quote.add_argument("--no-save", action="store_true", help="Do not save the quote to SQLite.")

    daily_quote = subparsers.add_parser(
        "daily-quote",
        help="Fetch one delayed daily quote from the public data portal and store it.",
    )
    daily_quote.add_argument(
        "symbol",
        nargs="?",
        help="Stock code. Defaults to first configured symbol.",
    )
    daily_quote.add_argument("--base-date", help="YYYYMMDD trading date. Defaults to latest.")
    daily_quote.add_argument("--no-save", action="store_true", help="Do not save to SQLite.")

    daily_sync = subparsers.add_parser(
        "daily-sync",
        help="Fetch delayed daily quotes for all configured or supplied symbols.",
    )
    daily_sync.add_argument(
        "--symbols",
        help="Comma-separated stock codes. Defaults to DAD_STOCK_SYMBOLS.",
    )
    daily_sync.add_argument("--base-date", help="YYYYMMDD trading date. Defaults to latest.")

    latest = subparsers.add_parser("latest", help="Print recent saved market rows as JSON.")
    latest.add_argument("--symbol", help="Filter by stock code.")
    latest.add_argument("--limit", type=int, default=20)

    export_csv = subparsers.add_parser(
        "export-csv",
        help="Export recent saved market rows to a CSV file.",
    )
    export_csv.add_argument(
        "--output",
        default="data/latest_ticks.csv",
        help="CSV output path.",
    )
    export_csv.add_argument("--symbol", help="Filter by stock code.")
    export_csv.add_argument("--limit", type=int, default=200)

    dedupe = subparsers.add_parser("dedupe", help="Remove duplicate saved market rows.")
    dedupe.add_argument(
        "--all-sources",
        action="store_true",
        help="Dedupe all sources. Defaults to publicdata only.",
    )

    subparsers.add_parser("gui", help="Open the desktop GUI.")

    listen = subparsers.add_parser("listen", help="Listen to KIS websocket realtime trades.")
    listen.add_argument("--short-window", type=int, default=5)
    listen.add_argument("--long-window", type=int, default=20)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    logging.basicConfig(level=getattr(logging, args.log_level.upper(), logging.INFO))

    settings = Settings.from_env_file(args.env_file)

    if args.command == "check-config":
        print(json.dumps(settings.safe_summary(), ensure_ascii=False, indent=2))
        return 0

    if args.command == "quote":
        symbol = args.symbol or settings.symbols[0]
        client = KISClient(settings)
        token = client.issue_access_token()
        quote = client.inquire_price(symbol, token)
        if not args.no_save:
            SQLiteMarketStore(settings.database_path).save_quote(quote)
        print(json.dumps({"symbol": quote.symbol, "price": quote.price}, ensure_ascii=False))
        return 0

    if args.command == "daily-quote":
        symbol = args.symbol or settings.symbols[0]
        provider = PublicDataStockPriceProvider(settings)
        price = provider.get_daily_price(symbol, args.base_date)
        if not args.no_save:
            SQLiteMarketStore(settings.database_path).save_daily_price(price)
        print(
            json.dumps(
                {
                    "symbol": price.symbol,
                    "name": price.name,
                    "base_date": price.base_date,
                    "close": price.close,
                    "open": price.open,
                    "high": price.high,
                    "low": price.low,
                    "volume": price.volume,
                    "market": price.market,
                },
                ensure_ascii=False,
            )
        )
        return 0

    if args.command == "daily-sync":
        provider = PublicDataStockPriceProvider(settings)
        store = SQLiteMarketStore(settings.database_path)
        synced = []
        for symbol in _parse_symbols(args.symbols) or settings.symbols:
            price = provider.get_daily_price(symbol, args.base_date)
            store.save_daily_price(price)
            synced.append(
                {
                    "symbol": price.symbol,
                    "name": price.name,
                    "base_date": price.base_date,
                    "close": price.close,
                    "volume": price.volume,
                    "market": price.market,
                }
            )
        print(json.dumps({"synced": synced}, ensure_ascii=False, indent=2))
        return 0

    if args.command == "latest":
        rows = SQLiteMarketStore(settings.database_path).latest_ticks(
            symbol=args.symbol,
            limit=args.limit,
        )
        print(json.dumps({"rows": rows}, ensure_ascii=False, indent=2))
        return 0

    if args.command == "export-csv":
        path = SQLiteMarketStore(settings.database_path).export_ticks_csv(
            output_path=Path(args.output),
            symbol=args.symbol,
            limit=args.limit,
        )
        print(json.dumps({"output": str(path)}, ensure_ascii=False))
        return 0

    if args.command == "dedupe":
        source = None if args.all_sources else "publicdata"
        deleted = SQLiteMarketStore(settings.database_path).dedupe_ticks(source=source)
        print(json.dumps({"deleted": deleted}, ensure_ascii=False))
        return 0

    if args.command == "gui":
        from .gui import run_gui

        run_gui(settings)
        return 0

    if args.command == "listen":
        asyncio.run(_listen(settings, args.short_window, args.long_window))
        return 0

    parser.error(f"Unknown command: {args.command}")
    return 2


def _parse_symbols(value: str | None) -> tuple[str, ...]:
    if not value:
        return ()
    return tuple(symbol.strip() for symbol in value.split(",") if symbol.strip())


async def _listen(settings: Settings, short_window: int, long_window: int) -> None:
    client = KISClient(settings)
    approval_key = client.issue_approval_key()
    store = SQLiteMarketStore(settings.database_path)
    strategy = MovingAverageBreakoutStrategy(short_window=short_window, long_window=long_window)
    notifier = TelegramNotifier(settings.telegram_bot_token, settings.telegram_chat_id)

    async for trade in stream_realtime_trades(
        settings.websocket_url,
        approval_key,
        settings.symbols,
    ):
        store.save_trade(trade)
        prices = store.recent_prices(trade.symbol, limit=long_window)
        signal = strategy.evaluate(trade.symbol, prices)
        store.save_signal(signal)
        if signal.action != "HOLD":
            notifier.send_signal(signal)
        logging.info("%s %s %s", trade.symbol, trade.price, signal.action)

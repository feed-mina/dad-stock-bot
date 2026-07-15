import tempfile
import unittest
from pathlib import Path

from dad_stock_bot.models import DailyPrice, RealtimeTrade, TradeSignal
from dad_stock_bot.storage import SQLiteMarketStore


class StorageTest(unittest.TestCase):
    def test_save_trade_price_and_signal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = SQLiteMarketStore(Path(tmp) / "ticks.sqlite3")
            store.save_trade(
                RealtimeTrade(
                    symbol="005930",
                    trade_time="093000",
                    price=73000,
                    trade_volume=10,
                    accumulated_volume=100,
                    change_rate=1.2,
                )
            )
            store.save_daily_price(
                DailyPrice(
                    symbol="005930",
                    base_date="20260708",
                    close=73100,
                    volume=20,
                )
            )
            store.save_signal(
                TradeSignal(
                    symbol="005930",
                    action="BUY",
                    price=73000,
                    reason="test",
                )
            )

            self.assertEqual(store.recent_prices("005930", 5), [73000, 73100])
            latest = store.latest_ticks("005930", 2)
            self.assertEqual(latest[0]["price"], 73100)
            self.assertEqual(latest[0]["source"], "publicdata")

            csv_path = store.export_ticks_csv(Path(tmp) / "latest.csv", symbol="005930")
            csv_text = csv_path.read_text(encoding="utf-8")
            self.assertIn("symbol,price,volume,event_time,source", csv_text)
            self.assertIn("005930,73000,10", csv_text)
            self.assertIn("005930,73100,20", csv_text)


if __name__ == "__main__":
    unittest.main()

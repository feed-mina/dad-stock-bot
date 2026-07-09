import tempfile
import unittest
from pathlib import Path

from dad_stock_bot.models import RealtimeTrade, TradeSignal
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
            store.save_signal(
                TradeSignal(
                    symbol="005930",
                    action="BUY",
                    price=73000,
                    reason="test",
                )
            )

            self.assertEqual(store.recent_prices("005930", 5), [73000])


if __name__ == "__main__":
    unittest.main()


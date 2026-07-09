import unittest

from dad_stock_bot.strategy import MovingAverageBreakoutStrategy


class StrategyTest(unittest.TestCase):
    def test_hold_until_enough_prices(self) -> None:
        strategy = MovingAverageBreakoutStrategy(short_window=2, long_window=4)
        signal = strategy.evaluate("005930", [10, 11, 12])

        self.assertEqual(signal.action, "HOLD")

    def test_buy_on_upward_breakout(self) -> None:
        strategy = MovingAverageBreakoutStrategy(short_window=2, long_window=4)
        signal = strategy.evaluate("005930", [10, 10, 12, 15])

        self.assertEqual(signal.action, "BUY")

    def test_sell_on_downward_breakout(self) -> None:
        strategy = MovingAverageBreakoutStrategy(short_window=2, long_window=4)
        signal = strategy.evaluate("005930", [15, 15, 12, 10])

        self.assertEqual(signal.action, "SELL")


if __name__ == "__main__":
    unittest.main()


import unittest

from dad_stock_bot.cli import _parse_symbols


class CliTest(unittest.TestCase):
    def test_parse_symbols(self) -> None:
        self.assertEqual(_parse_symbols(None), ())
        self.assertEqual(_parse_symbols("005930, 000660,,035420"), ("005930", "000660", "035420"))


if __name__ == "__main__":
    unittest.main()

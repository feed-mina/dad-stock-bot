import unittest

from dad_stock_bot.gui import _format_value, _parse_symbols


class GuiHelpersTest(unittest.TestCase):
    def test_parse_symbols(self) -> None:
        self.assertEqual(_parse_symbols("005930, 000660,,035720"), ("005930", "000660", "035720"))

    def test_format_value(self) -> None:
        self.assertEqual(_format_value(263000), "263,000")
        self.assertEqual(_format_value(3.336), "3.34")
        self.assertEqual(_format_value(None), "")


if __name__ == "__main__":
    unittest.main()

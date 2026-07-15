import unittest

from dad_stock_bot.gui import (
    _format_change,
    _format_change_rate,
    _format_value,
    _friendly_error_message,
    _parse_symbols,
    _row_tag,
    _row_values,
)


class GuiHelpersTest(unittest.TestCase):
    def test_parse_symbols(self) -> None:
        self.assertEqual(_parse_symbols("005930, 000660,,035720"), ("005930", "000660", "035720"))

    def test_format_value(self) -> None:
        self.assertEqual(_format_value(263000), "263,000")
        self.assertEqual(_format_value(3.336), "3.34")
        self.assertEqual(_format_value(None), "")

    def test_change_display_helpers(self) -> None:
        self.assertEqual(_format_change(8500), "▲ 8,500")
        self.assertEqual(_format_change(-900), "▼ 900")
        self.assertEqual(_format_change(0), "-")
        self.assertEqual(_format_change_rate(3.336), "▲ 3.34%")
        self.assertEqual(_format_change_rate(-2.59), "▼ 2.59%")

    def test_row_values_and_tags(self) -> None:
        row = {
            "name": "Samsung Electronics",
            "symbol": "005930",
            "close": 263000,
            "change": 8500,
            "change_rate": 3.34,
            "volume": 40086496,
            "amount": 10415841854750,
            "market_cap": 1537571273904000,
            "base_date": "20260714",
        }

        self.assertEqual(_row_tag(row), "up")
        values = _row_values(row)
        self.assertEqual(values[0], "Samsung Electronics")
        self.assertEqual(values[2], "263,000")
        self.assertEqual(values[3], "▲ 8,500")

    def test_friendly_error_message(self) -> None:
        self.assertIn("PUBLIC_DATA_SERVICE_KEY", _friendly_error_message(ValueError("Missing required public data credential: PUBLIC_DATA_SERVICE_KEY")))
        self.assertIn("인증키", _friendly_error_message(RuntimeError("Public data HTTP error 403: Forbidden")))


if __name__ == "__main__":
    unittest.main()

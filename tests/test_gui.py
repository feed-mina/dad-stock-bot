import datetime
import unittest

from dad_stock_bot.gui import (
    _date_digits,
    _format_change,
    _format_change_rate,
    _format_date,
    _format_value,
    _friendly_error_message,
    _latest_per_symbol,
    _parse_date,
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
        self.assertEqual(values[8], "2026-07-14")

    def test_date_helpers(self) -> None:
        self.assertEqual(_format_date("20260714"), "2026-07-14")
        self.assertEqual(_format_date("2026-07-14"), "2026-07-14")
        self.assertEqual(_format_date(""), "")
        self.assertEqual(_format_date("날짜없음"), "날짜없음")
        self.assertEqual(_date_digits("2026-07-14"), "20260714")
        self.assertEqual(_date_digits("bad"), "")
        self.assertEqual(_parse_date("2026-07-14"), datetime.date(2026, 7, 14))
        self.assertIsNone(_parse_date(""))
        self.assertIsNone(_parse_date("2026-13-40"))

    def test_latest_per_symbol_keeps_most_recent_date(self) -> None:
        # Rows deliberately out of date order to prove selection is by base_date.
        rows = [
            {"symbol": "005930", "base_date": "20260713", "close": 260000},
            {"symbol": "005930", "base_date": "20260714", "close": 263000},
            {"symbol": "000660", "base_date": "20260714", "close": 191300},
        ]
        latest = _latest_per_symbol(rows)
        self.assertEqual(len(latest), 2)
        samsung = next(row for row in latest if row["symbol"] == "005930")
        self.assertEqual(samsung["base_date"], "20260714")

    def test_friendly_error_message(self) -> None:
        self.assertIn("PUBLIC_DATA_SERVICE_KEY", _friendly_error_message(ValueError("Missing required public data credential: PUBLIC_DATA_SERVICE_KEY")))
        self.assertIn("인증키", _friendly_error_message(RuntimeError("Public data HTTP error 403: Forbidden")))


if __name__ == "__main__":
    unittest.main()

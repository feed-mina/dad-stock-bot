import tempfile
import unittest
from pathlib import Path

from dad_stock_bot.summary import build_summary_row, write_summary_csv


class SummaryTest(unittest.TestCase):
    def test_build_summary_row_from_public_data_raw_json(self) -> None:
        row = build_summary_row(
            {
                "symbol": "005930",
                "price": 263000,
                "volume": 40086496,
                "event_time": "20260714",
                "source": "publicdata",
                "raw_json": (
                    '{"basDt":"20260714","itmsNm":"Samsung Electronics",'
                    '"mrktCtg":"KOSPI","vs":"8500","fltRt":"3.34",'
                    '"mkp":"255000","hipr":"270000","lopr":"247000",'
                    '"trPrc":"10415841854750","mrktTotAmt":"1537571273904000"}'
                ),
            }
        )

        self.assertEqual(row["name"], "Samsung Electronics")
        self.assertEqual(row["change"], 8500)
        self.assertEqual(row["change_rate"], 3.34)
        self.assertEqual(row["market_cap"], 1537571273904000)

    def test_write_summary_csv(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = write_summary_csv(
                [{"symbol": "005930", "name": "Samsung Electronics", "close": 263000}],
                Path(tmp) / "summary.csv",
            )

            text = path.read_text(encoding="utf-8-sig")
            self.assertIn("symbol,name,base_date", text)
            self.assertIn("005930,Samsung Electronics", text)


if __name__ == "__main__":
    unittest.main()

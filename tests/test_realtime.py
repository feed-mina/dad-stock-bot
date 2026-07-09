import unittest

from dad_stock_bot.realtime import (
    REALTIME_TRADE_COLUMNS,
    build_subscribe_message,
    parse_realtime_trade_message,
)


class RealtimeTest(unittest.TestCase):
    def test_build_subscribe_message(self) -> None:
        message = build_subscribe_message("approval", "005930")

        self.assertEqual(message["header"]["approval_key"], "approval")
        self.assertEqual(message["body"]["input"]["tr_id"], "H0STCNT0")
        self.assertEqual(message["body"]["input"]["tr_key"], "005930")

    def test_parse_realtime_trade_message(self) -> None:
        values = {column: "0" for column in REALTIME_TRADE_COLUMNS}
        values.update(
            {
                "MKSC_SHRN_ISCD": "005930",
                "STCK_CNTG_HOUR": "093000",
                "STCK_PRPR": "73000",
                "CNTG_VOL": "12",
                "ACML_VOL": "1000",
                "PRDY_CTRT": "1.25",
            }
        )
        payload = "^".join(values[column] for column in REALTIME_TRADE_COLUMNS)
        trades = parse_realtime_trade_message(f"0|H0STCNT0|1|{payload}")

        self.assertEqual(len(trades), 1)
        self.assertEqual(trades[0].symbol, "005930")
        self.assertEqual(trades[0].price, 73000)
        self.assertEqual(trades[0].trade_volume, 12)
        self.assertEqual(trades[0].change_rate, 1.25)


if __name__ == "__main__":
    unittest.main()


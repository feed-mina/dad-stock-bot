import unittest

from dad_stock_bot.config import Settings
from dad_stock_bot.providers import (
    PublicDataError,
    PublicDataStockPriceProvider,
    normalize_service_key,
)


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code
        self.text = str(payload)

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, payload):
        self.payload = payload
        self.gets = []

    def get(self, url, **kwargs):
        self.gets.append((url, kwargs))
        return FakeResponse(self.payload)


class PublicDataStockPriceProviderTest(unittest.TestCase):
    def test_get_daily_price(self) -> None:
        payload = {
            "response": {
                "header": {"resultCode": "00", "resultMsg": "NORMAL SERVICE."},
                "body": {
                    "items": {
                        "item": [
                            {
                                "basDt": "20260708",
                                "srtnCd": "005930",
                                "itmsNm": "Samsung Electronics",
                                "mrktCtg": "KOSPI",
                                "clpr": "73000",
                                "mkp": "72000",
                                "hipr": "73500",
                                "lopr": "71500",
                                "trqu": "1000",
                                "trPrc": "73000000",
                            }
                        ]
                    }
                },
            }
        }
        settings = Settings.from_mapping({"PUBLIC_DATA_SERVICE_KEY": "key"})
        session = FakeSession(payload)
        provider = PublicDataStockPriceProvider(settings, session=session)

        price = provider.get_daily_price("005930", "20260708")

        self.assertEqual(price.symbol, "005930")
        self.assertEqual(price.name, "Samsung Electronics")
        self.assertEqual(price.close, 73000)
        self.assertEqual(price.volume, 1000)
        params = session.gets[0][1]["params"]
        self.assertEqual(params["serviceKey"], "key")
        self.assertEqual(params["likeSrtnCd"], "005930")
        self.assertEqual(params["basDt"], "20260708")

    def test_encoding_key_is_decoded_before_request(self) -> None:
        settings = Settings.from_mapping({"PUBLIC_DATA_SERVICE_KEY": "abc%2Bdef%3D"})
        session = FakeSession(
            {
                "response": {
                    "header": {"resultCode": "00"},
                    "body": {"items": {"item": {"srtnCd": "005930", "clpr": "1"}}},
                }
            }
        )
        provider = PublicDataStockPriceProvider(settings, session=session)

        provider.get_daily_price("005930")

        self.assertEqual(session.gets[0][1]["params"]["serviceKey"], "abc+def=")

    def test_normalize_service_key_keeps_decoding_key(self) -> None:
        self.assertEqual(normalize_service_key("abc+def="), "abc+def=")

    def test_missing_public_data_key_raises(self) -> None:
        settings = Settings.from_mapping({})
        provider = PublicDataStockPriceProvider(settings, session=FakeSession({}))

        with self.assertRaises(ValueError):
            provider.get_daily_price("005930")

    def test_error_header_raises(self) -> None:
        settings = Settings.from_mapping({"PUBLIC_DATA_SERVICE_KEY": "key"})
        provider = PublicDataStockPriceProvider(
            settings,
            session=FakeSession(
                {
                    "response": {
                        "header": {"resultCode": "99", "resultMsg": "ERROR"},
                        "body": {},
                    }
                }
            ),
        )

        with self.assertRaises(PublicDataError):
            provider.get_daily_price("005930")


if __name__ == "__main__":
    unittest.main()

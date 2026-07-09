import unittest

from dad_stock_bot.config import Settings
from dad_stock_bot.kis import KISClient


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code
        self.text = str(payload)

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self):
        self.posts = []
        self.gets = []

    def post(self, url, **kwargs):
        self.posts.append((url, kwargs))
        if url.endswith("/oauth2/Approval"):
            return FakeResponse({"approval_key": "approval-123"})
        return FakeResponse({"access_token": "token-123", "rt_cd": "0"})

    def get(self, url, **kwargs):
        self.gets.append((url, kwargs))
        return FakeResponse(
            {
                "rt_cd": "0",
                "output": {
                    "stck_shrn_iscd": "005930",
                    "stck_prpr": "73000",
                    "acml_vol": "1000",
                },
            }
        )


class KISClientTest(unittest.TestCase):
    def test_token_approval_and_quote(self) -> None:
        settings = Settings.from_mapping(
            {
                "KIS_APP_KEY": "app",
                "KIS_APP_SECRET": "secret",
                "KIS_ENV": "demo",
            }
        )
        session = FakeSession()
        client = KISClient(settings, session=session)

        self.assertEqual(client.issue_access_token(), "token-123")
        self.assertEqual(client.issue_approval_key(), "approval-123")
        quote = client.inquire_price("005930", "token-123")

        self.assertEqual(quote.symbol, "005930")
        self.assertEqual(quote.price, 73000)
        self.assertTrue(session.gets[0][1]["headers"]["authorization"].endswith("token-123"))


if __name__ == "__main__":
    unittest.main()


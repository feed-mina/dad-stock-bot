from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .config import Settings
from .models import Quote


TOKEN_PATH = "/oauth2/tokenP"
APPROVAL_PATH = "/oauth2/Approval"
INQUIRE_PRICE_PATH = "/uapi/domestic-stock/v1/quotations/inquire-price"
INQUIRE_PRICE_TR_ID = "FHKST01010100"


class KISError(RuntimeError):
    """Raised when KIS Open API returns an error response."""


@dataclass
class KISClient:
    settings: Settings
    session: Any | None = None
    timeout: int = 10

    def __post_init__(self) -> None:
        if self.session is None:
            try:
                import requests
            except ImportError as exc:
                raise RuntimeError(
                    "requests is required for live KIS API calls. Install project dependencies first."
                ) from exc
            self.session = requests.Session()

    def issue_access_token(self) -> str:
        self.settings.require_api_credentials()
        payload = {
            "grant_type": "client_credentials",
            "appkey": self.settings.app_key,
            "appsecret": self.settings.app_secret,
        }
        response = self.session.post(
            f"{self.settings.rest_base_url}{TOKEN_PATH}",
            headers={
                "Content-Type": "application/json",
                "Accept": "text/plain",
                "charset": "UTF-8",
            },
            json=payload,
            timeout=self.timeout,
        )
        data = self._json_or_raise(response)
        token = data.get("access_token")
        if not token:
            raise KISError("KIS token response did not include access_token.")
        return str(token)

    def issue_approval_key(self) -> str:
        self.settings.require_api_credentials()
        payload = {
            "grant_type": "client_credentials",
            "appkey": self.settings.app_key,
            "secretkey": self.settings.app_secret,
        }
        response = self.session.post(
            f"{self.settings.rest_base_url}{APPROVAL_PATH}",
            headers={"content-type": "application/json"},
            json=payload,
            timeout=self.timeout,
        )
        data = self._json_or_raise(response)
        approval_key = data.get("approval_key")
        if not approval_key:
            raise KISError("KIS approval response did not include approval_key.")
        return str(approval_key)

    def inquire_price(self, symbol: str, access_token: str, market_code: str = "J") -> Quote:
        self.settings.require_api_credentials()
        response = self.session.get(
            f"{self.settings.rest_base_url}{INQUIRE_PRICE_PATH}",
            headers={
                "content-type": "application/json",
                "authorization": f"Bearer {access_token}",
                "appkey": self.settings.app_key,
                "appsecret": self.settings.app_secret,
                "tr_id": INQUIRE_PRICE_TR_ID,
                "custtype": "P",
            },
            params={
                "FID_COND_MRKT_DIV_CODE": market_code,
                "FID_INPUT_ISCD": symbol,
            },
            timeout=self.timeout,
        )
        data = self._json_or_raise(response)
        output = data.get("output")
        if not isinstance(output, Mapping):
            raise KISError("KIS price response did not include output.")
        quote = Quote.from_kis_rest(output)
        if not quote.symbol:
            return Quote(symbol=symbol, price=quote.price, volume=quote.volume, raw=quote.raw)
        return quote

    @staticmethod
    def _json_or_raise(response: Any) -> Mapping[str, Any]:
        status_code = getattr(response, "status_code", 0)
        if status_code >= 400:
            text = getattr(response, "text", "")
            raise KISError(f"KIS HTTP error {status_code}: {text}")
        data = response.json()
        if not isinstance(data, Mapping):
            raise KISError("KIS response was not a JSON object.")
        if data.get("rt_cd") not in (None, "0", 0):
            message = data.get("msg1") or data.get("msg_cd") or "Unknown KIS API error"
            raise KISError(str(message))
        return data


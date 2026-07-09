from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Protocol

from .config import Settings
from .models import DailyPrice


class MarketDataProvider(Protocol):
    def get_daily_price(self, symbol: str, base_date: str | None = None) -> DailyPrice:
        """Fetch delayed or daily market data for a Korean stock symbol."""


class PublicDataError(RuntimeError):
    """Raised when the public data API returns an invalid or failed response."""


@dataclass
class PublicDataStockPriceProvider:
    settings: Settings
    session: Any | None = None
    timeout: int = 10

    def __post_init__(self) -> None:
        if self.session is None:
            try:
                import requests
            except ImportError as exc:
                raise RuntimeError(
                    "requests is required for public data API calls. Install dependencies first."
                ) from exc
            self.session = requests.Session()

    def get_daily_price(self, symbol: str, base_date: str | None = None) -> DailyPrice:
        if not symbol:
            raise ValueError("symbol is required.")
        self.settings.require_public_data_credentials()

        params = {
            "serviceKey": self.settings.public_data_service_key,
            "pageNo": "1",
            "numOfRows": "1",
            "resultType": "json",
            "likeSrtnCd": symbol,
        }
        if base_date:
            params["basDt"] = base_date

        response = self.session.get(
            self.settings.public_data_stock_price_url,
            params=params,
            timeout=self.timeout,
        )
        data = self._json_or_raise(response)
        item = self._first_item(data)
        price = DailyPrice.from_public_data(item)
        if not price.symbol:
            return DailyPrice(
                symbol=symbol,
                base_date=price.base_date,
                close=price.close,
                open=price.open,
                high=price.high,
                low=price.low,
                volume=price.volume,
                amount=price.amount,
                name=price.name,
                market=price.market,
                raw=price.raw,
            )
        return price

    @staticmethod
    def _json_or_raise(response: Any) -> Mapping[str, Any]:
        status_code = getattr(response, "status_code", 0)
        if status_code >= 400:
            raise PublicDataError(
                f"Public data HTTP error {status_code}: {getattr(response, 'text', '')}"
            )
        data = response.json()
        if not isinstance(data, Mapping):
            raise PublicDataError("Public data response was not a JSON object.")
        return data

    @staticmethod
    def _first_item(data: Mapping[str, Any]) -> Mapping[str, Any]:
        response = data.get("response")
        if not isinstance(response, Mapping):
            raise PublicDataError("Public data response did not include response.")

        header = response.get("header", {})
        if isinstance(header, Mapping) and str(header.get("resultCode", "00")) != "00":
            message = header.get("resultMsg") or "Unknown public data API error"
            raise PublicDataError(str(message))

        body = response.get("body", {})
        if not isinstance(body, Mapping):
            raise PublicDataError("Public data response did not include body.")

        items = body.get("items", {})
        if isinstance(items, Mapping):
            item = items.get("item", [])
        else:
            item = items

        if isinstance(item, Mapping):
            return item
        if isinstance(item, list) and item and isinstance(item[0], Mapping):
            return item[0]
        raise PublicDataError("No stock price item found in public data response.")

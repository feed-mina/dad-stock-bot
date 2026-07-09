from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
from typing import Mapping


DEFAULT_REAL_REST_URL = "https://openapi.koreainvestment.com:9443"
DEFAULT_DEMO_REST_URL = "https://openapivts.koreainvestment.com:29443"
DEFAULT_REAL_WS_URL = "ws://ops.koreainvestment.com:21000"
DEFAULT_DEMO_WS_URL = "ws://ops.koreainvestment.com:31000"
DEFAULT_PUBLIC_DATA_STOCK_PRICE_URL = (
    "https://apis.data.go.kr/1160100/service/GetStockSecuritiesInfoService/getStockPriceInfo"
)


def load_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _get(env: Mapping[str, str], key: str, default: str = "") -> str:
    return env.get(key, os.environ.get(key, default)).strip()


def _split_symbols(value: str) -> tuple[str, ...]:
    symbols = tuple(symbol.strip() for symbol in value.split(",") if symbol.strip())
    return symbols or ("005930",)


@dataclass(frozen=True)
class Settings:
    env: str
    app_key: str
    app_secret: str
    account_no: str
    account_product_code: str
    symbols: tuple[str, ...]
    database_path: Path
    rest_base_url: str
    websocket_url: str
    public_data_service_key: str = ""
    public_data_stock_price_url: str = DEFAULT_PUBLIC_DATA_STOCK_PRICE_URL
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    @classmethod
    def from_env_file(cls, path: str | Path = ".env") -> "Settings":
        loaded = load_env_file(Path(path))
        return cls.from_mapping(loaded)

    @classmethod
    def from_mapping(cls, env: Mapping[str, str]) -> "Settings":
        kis_env = _get(env, "KIS_ENV", "demo").lower()
        if kis_env not in {"demo", "real"}:
            raise ValueError("KIS_ENV must be either 'demo' or 'real'.")

        default_rest = DEFAULT_REAL_REST_URL if kis_env == "real" else DEFAULT_DEMO_REST_URL
        default_ws = DEFAULT_REAL_WS_URL if kis_env == "real" else DEFAULT_DEMO_WS_URL

        return cls(
            env=kis_env,
            app_key=_get(env, "KIS_APP_KEY"),
            app_secret=_get(env, "KIS_APP_SECRET"),
            account_no=_get(env, "KIS_ACCOUNT_NO"),
            account_product_code=_get(env, "KIS_ACCOUNT_PRODUCT_CODE"),
            symbols=_split_symbols(_get(env, "DAD_STOCK_SYMBOLS", "005930")),
            database_path=Path(_get(env, "DAD_STOCK_DB_PATH", "data/market_ticks.sqlite3")),
            rest_base_url=_get(env, "KIS_REST_BASE_URL", default_rest).rstrip("/"),
            websocket_url=_get(env, "KIS_WEBSOCKET_URL", default_ws),
            public_data_service_key=_get(env, "PUBLIC_DATA_SERVICE_KEY"),
            public_data_stock_price_url=_get(
                env,
                "PUBLIC_DATA_STOCK_PRICE_URL",
                DEFAULT_PUBLIC_DATA_STOCK_PRICE_URL,
            ),
            telegram_bot_token=_get(env, "TELEGRAM_BOT_TOKEN"),
            telegram_chat_id=_get(env, "TELEGRAM_CHAT_ID"),
        )

    def require_api_credentials(self) -> None:
        missing = [
            name
            for name, value in {
                "KIS_APP_KEY": self.app_key,
                "KIS_APP_SECRET": self.app_secret,
            }.items()
            if not value
        ]
        if missing:
            joined = ", ".join(missing)
            raise ValueError(f"Missing required KIS credentials: {joined}")

    def safe_summary(self) -> dict[str, object]:
        return {
            "env": self.env,
            "symbols": list(self.symbols),
            "database_path": str(self.database_path),
            "rest_base_url": self.rest_base_url,
            "websocket_url": self.websocket_url,
            "has_app_key": bool(self.app_key),
            "has_app_secret": bool(self.app_secret),
            "has_public_data_service_key": bool(self.public_data_service_key),
            "public_data_stock_price_url": self.public_data_stock_price_url,
            "telegram_enabled": bool(self.telegram_bot_token and self.telegram_chat_id),
        }

    def require_public_data_credentials(self) -> None:
        if not self.public_data_service_key:
            raise ValueError("Missing required public data credential: PUBLIC_DATA_SERVICE_KEY")

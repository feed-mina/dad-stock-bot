from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .models import TradeSignal


def format_signal(signal: TradeSignal) -> str:
    return (
        f"[{signal.action}] {signal.symbol} @ {signal.price}\n"
        f"{signal.reason}\n"
        f"{signal.generated_at}"
    )


@dataclass
class TelegramNotifier:
    bot_token: str
    chat_id: str
    session: Any | None = None
    timeout: int = 10

    def __post_init__(self) -> None:
        if self.session is None:
            try:
                import requests
            except ImportError as exc:
                raise RuntimeError(
                    "requests is required for Telegram notifications."
                ) from exc
            self.session = requests.Session()

    @property
    def enabled(self) -> bool:
        return bool(self.bot_token and self.chat_id)

    def send_signal(self, signal: TradeSignal) -> None:
        if not self.enabled:
            return
        response = self.session.post(
            f"https://api.telegram.org/bot{self.bot_token}/sendMessage",
            json={"chat_id": self.chat_id, "text": format_signal(signal)},
            timeout=self.timeout,
        )
        if getattr(response, "status_code", 0) >= 400:
            raise RuntimeError(f"Telegram send failed: {getattr(response, 'text', '')}")


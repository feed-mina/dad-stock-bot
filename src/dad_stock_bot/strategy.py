from __future__ import annotations

from statistics import fmean
from typing import Sequence

from .models import TradeSignal


class MovingAverageBreakoutStrategy:
    def __init__(self, short_window: int = 5, long_window: int = 20) -> None:
        if short_window <= 0 or long_window <= 0:
            raise ValueError("Moving average windows must be positive.")
        if short_window >= long_window:
            raise ValueError("short_window must be smaller than long_window.")
        self.short_window = short_window
        self.long_window = long_window

    def evaluate(self, symbol: str, prices: Sequence[int]) -> TradeSignal:
        if len(prices) < self.long_window:
            return TradeSignal(
                symbol=symbol,
                action="HOLD",
                price=prices[-1] if prices else 0,
                reason=f"Need at least {self.long_window} prices before evaluating.",
            )

        current_price = int(prices[-1])
        short_average = fmean(prices[-self.short_window :])
        long_average = fmean(prices[-self.long_window :])

        if current_price > short_average > long_average:
            return TradeSignal(
                symbol=symbol,
                action="BUY",
                price=current_price,
                reason=(
                    f"Price {current_price} is above short MA {short_average:.2f}, "
                    f"and short MA is above long MA {long_average:.2f}."
                ),
            )
        if current_price < short_average < long_average:
            return TradeSignal(
                symbol=symbol,
                action="SELL",
                price=current_price,
                reason=(
                    f"Price {current_price} is below short MA {short_average:.2f}, "
                    f"and short MA is below long MA {long_average:.2f}."
                ),
            )
        return TradeSignal(
            symbol=symbol,
            action="HOLD",
            price=current_price,
            reason=(
                f"No breakout. short MA {short_average:.2f}, "
                f"long MA {long_average:.2f}."
            ),
        )


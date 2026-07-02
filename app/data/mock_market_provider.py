from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

from app.core.config import load_watchlist_config
from app.schemas.market import DailyBar, MarketSeries, MarketSnapshot


@dataclass(frozen=True)
class MockInstrument:
    symbol: str
    name: str
    market: str


class MockMarketProvider:
    """Deterministic local daily-bar provider for offline MVP development."""

    def __init__(
        self,
        watchlist_path: str | Path = "config/watchlist.yaml",
        seed: int = 20260701,
        end_date: date = date(2026, 6, 30),
        days: int = 95,
    ) -> None:
        self.watchlist_path = Path(watchlist_path)
        self.seed = seed
        self.end_date = end_date
        self.days = days

    def load_instruments(self) -> list[MockInstrument]:
        config = load_watchlist_config(self.watchlist_path)
        instruments: list[MockInstrument] = []
        for stock in config["stocks"]:
            if stock.get("enabled", True) is False:
                continue
            instruments.append(
                MockInstrument(
                    symbol=str(stock.get("symbol") or ""),
                    name=str(stock.get("name") or ""),
                    market=str(stock.get("market") or ""),
                )
            )
        return instruments

    def snapshot(self) -> MarketSnapshot:
        items = [
            MarketSeries(
                name=instrument.name,
                symbol=instrument.symbol,
                market=instrument.market,
                bars=self.daily_bars_for(instrument),
            )
            for instrument in self.load_instruments()
        ]
        return MarketSnapshot(provider="mock", bar_count=self.days, items=items)

    def daily_bars_for(
        self,
        instrument: MockInstrument,
        scenario: str = "normal",
    ) -> list[DailyBar]:
        days = 30 if scenario == "insufficient_history" else self.days
        dates = _trading_days(self.end_date, days)
        rng = random.Random(self.seed + _stable_name_offset(instrument.name))
        prev_close = round(8.0 + rng.random() * 18.0, 2)
        bars: list[DailyBar] = []

        for index, trade_day in enumerate(dates):
            drift = 0.0008 + (index % 9 - 4) * 0.0005
            shock = rng.uniform(-0.018, 0.022)
            open_price = max(1.0, prev_close * (1 + rng.uniform(-0.008, 0.008)))
            close = max(1.0, prev_close * (1 + drift + shock))
            high = max(open_price, close) * (1 + rng.uniform(0.001, 0.018))
            low = min(open_price, close) * (1 - rng.uniform(0.001, 0.018))
            volume = int(900_000 + rng.random() * 500_000 + index * 2_000)
            amount = volume * close
            bars.append(
                DailyBar(
                    trade_date=trade_day.isoformat(),
                    open=round(open_price, 2),
                    high=round(high, 2),
                    low=round(low, 2),
                    close=round(close, 2),
                    volume=volume,
                    amount=round(amount, 2),
                    prev_close=round(prev_close, 2),
                )
            )
            prev_close = close

        if scenario == "zero_volume":
            latest = bars[-1]
            bars[-1] = DailyBar(
                trade_date=latest.trade_date,
                open=latest.open,
                high=latest.high,
                low=latest.low,
                close=latest.close,
                volume=0,
                amount=0,
                prev_close=latest.prev_close,
            )
        elif scenario == "missing_price":
            latest = bars[-1]
            bars[-1] = DailyBar(
                trade_date=latest.trade_date,
                open=latest.open,
                high=latest.high,
                low=latest.low,
                close=None,
                volume=latest.volume,
                amount=latest.amount,
                prev_close=latest.prev_close,
            )

        return bars


def _trading_days(end_date: date, count: int) -> list[date]:
    days: list[date] = []
    cursor = end_date
    while len(days) < count:
        if cursor.weekday() < 5:
            days.append(cursor)
        cursor -= timedelta(days=1)
    return list(reversed(days))


def _stable_name_offset(name: str) -> int:
    return sum((index + 1) * ord(char) for index, char in enumerate(name))

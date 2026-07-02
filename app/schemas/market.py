from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class DailyBar:
    trade_date: str
    open: float | None
    high: float | None
    low: float | None
    close: float | None
    volume: int | None
    amount: float | None
    prev_close: float | None


@dataclass(frozen=True)
class MarketSeries:
    name: str
    symbol: str
    market: str
    bars: list[DailyBar]
    data_status: str = "ok"
    degradation_reasons: list[str] = field(default_factory=list)
    source: str = "provider"
    cache_status: str = "not_applicable"


@dataclass(frozen=True)
class MarketSnapshot:
    provider: str
    bar_count: int
    items: list[MarketSeries]
    data_status: str = "ok"
    degradation_reasons: list[str] = field(default_factory=list)

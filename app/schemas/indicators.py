from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class IndicatorValues:
    ma20: float | None
    ma60: float | None
    momentum_5d_pct: float | None
    momentum_10d_pct: float | None
    momentum_20d_pct: float | None
    max_drawdown_pct: float | None
    atr_pct: float | None
    volume_ratio: float | None


@dataclass(frozen=True)
class IndicatorSnapshot:
    name: str
    symbol: str
    latest_trade_date: str | None
    latest_close: float | None
    indicators: IndicatorValues
    data_status: str
    degradation_reasons: list[str]

from __future__ import annotations

from dataclasses import asdict
from typing import Sequence

from app.data.mock_market_provider import MockInstrument
from app.schemas.indicators import IndicatorSnapshot, IndicatorValues
from app.schemas.market import DailyBar


def moving_average(values: Sequence[float | None], window: int) -> float | None:
    if len(values) < window:
        return None
    window_values = values[-window:]
    if any(value is None for value in window_values):
        return None
    return round(sum(value for value in window_values if value is not None) / window, 4)


def momentum_pct(values: Sequence[float | None], days: int) -> float | None:
    if len(values) <= days:
        return None
    latest = values[-1]
    previous = values[-days - 1]
    if latest is None or previous is None or previous == 0:
        return None
    return round((latest / previous - 1) * 100, 4)


def max_drawdown_pct(values: Sequence[float | None]) -> float | None:
    if not values or any(value is None for value in values):
        return None
    peak = values[0]
    worst = 0.0
    for value in values:
        if value is None:
            return None
        peak = max(peak, value)
        if peak == 0:
            return None
        worst = min(worst, value / peak - 1)
    return round(worst * 100, 4)


def atr_pct(bars: Sequence[DailyBar], window: int = 14) -> float | None:
    if len(bars) < window:
        return None
    latest_close = bars[-1].close
    if latest_close is None or latest_close == 0:
        return None
    true_ranges: list[float] = []
    for bar in bars[-window:]:
        if (
            bar.high is None
            or bar.low is None
            or bar.prev_close is None
            or bar.close is None
        ):
            return None
        true_ranges.append(
            max(
                bar.high - bar.low,
                abs(bar.high - bar.prev_close),
                abs(bar.low - bar.prev_close),
            )
        )
    return round((sum(true_ranges) / len(true_ranges)) / latest_close * 100, 4)


def volume_ratio(bars: Sequence[DailyBar], window: int = 20) -> float | None:
    if len(bars) < window:
        return None
    latest_volume = bars[-1].volume
    if latest_volume is None or latest_volume <= 0:
        return None
    window_values = [bar.volume for bar in bars[-window:]]
    if any(value is None or value <= 0 for value in window_values):
        return None
    average_volume = sum(value for value in window_values if value is not None) / window
    if average_volume == 0:
        return None
    return round(latest_volume / average_volume, 4)


def build_indicator_snapshot(
    instrument: MockInstrument,
    bars: Sequence[DailyBar],
) -> IndicatorSnapshot:
    if not bars:
        return IndicatorSnapshot(
            name=instrument.name,
            symbol=instrument.symbol,
            latest_trade_date=None,
            latest_close=None,
            indicators=_empty_values(),
            data_status="data_insufficient",
            degradation_reasons=["no_bars"],
        )

    latest = bars[-1]
    closes = [bar.close for bar in bars]
    reasons: list[str] = []
    status = "ok"

    if len(bars) < 60:
        status = "data_insufficient"
        reasons.append("requires_at_least_60_bars")
    elif (
        latest.open is None
        or latest.high is None
        or latest.low is None
        or latest.close is None
        or latest.prev_close is None
    ):
        status = "price_missing"
        reasons.append("latest_price_missing")
    elif latest.volume is None or latest.volume <= 0:
        status = "volume_missing"
        reasons.append("latest_volume_missing_or_zero")

    indicators = IndicatorValues(
        ma20=moving_average(closes, 20),
        ma60=moving_average(closes, 60),
        momentum_5d_pct=momentum_pct(closes, 5),
        momentum_10d_pct=momentum_pct(closes, 10),
        momentum_20d_pct=momentum_pct(closes, 20),
        max_drawdown_pct=max_drawdown_pct(closes[-60:]) if len(closes) >= 60 else None,
        atr_pct=atr_pct(bars),
        volume_ratio=volume_ratio(bars) if status != "volume_missing" else None,
    )
    return IndicatorSnapshot(
        name=instrument.name,
        symbol=instrument.symbol,
        latest_trade_date=latest.trade_date,
        latest_close=latest.close,
        indicators=indicators,
        data_status=status,
        degradation_reasons=reasons,
    )


def snapshot_to_dict(snapshot: IndicatorSnapshot) -> dict[str, object]:
    return asdict(snapshot)


def _empty_values() -> IndicatorValues:
    return IndicatorValues(
        ma20=None,
        ma60=None,
        momentum_5d_pct=None,
        momentum_10d_pct=None,
        momentum_20d_pct=None,
        max_drawdown_pct=None,
        atr_pct=None,
        volume_ratio=None,
    )

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

from app.domain.pnl import PnlItem
from app.domain.risk import RiskPosition, RiskSummary
from app.schemas.indicators import IndicatorSnapshot


ALLOWED_WAVE_STATES = {
    "focus_watch": "重点观察",
    "normal_tracking": "正常跟踪",
    "risk_attention": "风险关注",
    "data_insufficient": "数据不足",
    "position_review_candidate": "仓位复核候选",
    "rotation_watch_candidate": "切换观察候选",
    "needs_review": "需要复盘",
}


@dataclass(frozen=True)
class WaveScoreBreakdown:
    trend: Decimal
    momentum: Decimal
    volume: Decimal
    risk: Decimal


@dataclass(frozen=True)
class IndicatorSummary:
    latest_close: float | None
    ma20: float | None
    ma60: float | None
    momentum_5d_pct: float | None
    momentum_10d_pct: float | None
    momentum_20d_pct: float | None
    max_drawdown_pct: float | None
    atr_pct: float | None
    volume_ratio: float | None


@dataclass(frozen=True)
class PositionSummary:
    quantity: Decimal
    current_market_value: Decimal | None
    total_pnl: Decimal
    status: str


@dataclass(frozen=True)
class WaveRiskSummary:
    position_weight_pct: Decimal
    risk_status: str
    reasons: list[str]


@dataclass(frozen=True)
class WaveState:
    state: str
    label_cn: str
    total_score: Decimal
    scores: WaveScoreBreakdown
    reasons: list[str]


@dataclass(frozen=True)
class WaveStateItem:
    name: str
    symbol: str
    latest_trade_date: str | None
    data_status: str
    indicator_summary: IndicatorSummary
    position_summary: PositionSummary
    risk_summary: WaveRiskSummary
    wave_state: WaveState


def build_wave_states(
    indicator_snapshots: list[IndicatorSnapshot],
    risk_summary: RiskSummary,
    pnl_items: list[PnlItem],
) -> list[WaveStateItem]:
    positions = {
        (position.instrument_name, position.instrument_code): position
        for position in risk_summary.positions
    }
    pnl_by_key = {
        (item.instrument_name, item.instrument_code): item
        for item in pnl_items
    }
    return [
        _build_wave_state_item(
            snapshot,
            positions.get((snapshot.name, snapshot.symbol)),
            pnl_by_key.get((snapshot.name, snapshot.symbol)),
        )
        for snapshot in indicator_snapshots
    ]


def _build_wave_state_item(
    snapshot: IndicatorSnapshot,
    risk_position: RiskPosition | None,
    pnl_item: PnlItem | None,
) -> WaveStateItem:
    scores, score_reasons = _score_snapshot(snapshot, risk_position)
    total_score = _total_score(scores)
    state, state_reasons = _state_from_scores(
        snapshot,
        risk_position,
        pnl_item,
        scores,
        total_score,
        score_reasons,
    )
    return WaveStateItem(
        name=snapshot.name,
        symbol=snapshot.symbol,
        latest_trade_date=snapshot.latest_trade_date,
        data_status=snapshot.data_status,
        indicator_summary=_indicator_summary(snapshot),
        position_summary=_position_summary(pnl_item),
        risk_summary=_risk_summary(risk_position),
        wave_state=WaveState(
            state=state,
            label_cn=ALLOWED_WAVE_STATES[state],
            total_score=total_score,
            scores=scores,
            reasons=state_reasons,
        ),
    )


def _score_snapshot(
    snapshot: IndicatorSnapshot,
    risk_position: RiskPosition | None,
) -> tuple[WaveScoreBreakdown, list[str]]:
    if snapshot.data_status != "ok":
        return _zero_scores(), [f"indicator_status:{snapshot.data_status}"]
    values = snapshot.indicators
    if (
        snapshot.latest_close is None
        or values.ma20 is None
        or values.ma60 is None
        or values.momentum_20d_pct is None
    ):
        return _zero_scores(), ["indicator_values_missing"]

    reasons: list[str] = []
    trend = Decimal("35")
    if snapshot.latest_close >= values.ma20 >= values.ma60:
        trend = Decimal("85")
        reasons.append("trend_above_ma20_ma60")
    elif snapshot.latest_close >= values.ma20:
        trend = Decimal("65")
        reasons.append("price_above_ma20")
    elif values.ma20 >= values.ma60:
        trend = Decimal("55")
        reasons.append("ma20_above_ma60")
    else:
        reasons.append("trend_below_ma")

    momentum_inputs = [
        values.momentum_5d_pct,
        values.momentum_10d_pct,
        values.momentum_20d_pct,
    ]
    if all(value is not None and value > 0 for value in momentum_inputs):
        momentum = Decimal("85")
        reasons.append("momentum_positive")
    elif values.momentum_20d_pct > 0:
        momentum = Decimal("65")
        reasons.append("medium_momentum_positive")
    elif values.momentum_20d_pct < -5:
        momentum = Decimal("30")
        reasons.append("medium_momentum_weak")
    else:
        momentum = Decimal("50")

    volume = Decimal("50")
    if values.volume_ratio is not None:
        if values.volume_ratio >= 1.2:
            volume = Decimal("75")
            reasons.append("volume_ratio_elevated")
        elif values.volume_ratio >= 0.8:
            volume = Decimal("60")
        else:
            volume = Decimal("40")
            reasons.append("volume_ratio_low")

    risk = Decimal("80")
    if values.max_drawdown_pct is not None and values.max_drawdown_pct <= -15:
        risk = Decimal("40")
        reasons.append("drawdown_risk_high")
    elif values.max_drawdown_pct is not None and values.max_drawdown_pct <= -10:
        risk = Decimal("60")
        reasons.append("drawdown_risk_medium")
    if values.atr_pct is not None and values.atr_pct >= 8:
        risk = min(risk, Decimal("45"))
        reasons.append("atr_risk_high")
    if risk_position is not None and risk_position.risk_status == "high_concentration":
        risk = min(risk, Decimal("45"))
        reasons.extend(risk_position.reasons)

    return (
        WaveScoreBreakdown(
            trend=trend,
            momentum=momentum,
            volume=volume,
            risk=risk,
        ),
        list(dict.fromkeys(reasons)),
    )


def _state_from_scores(
    snapshot: IndicatorSnapshot,
    risk_position: RiskPosition | None,
    pnl_item: PnlItem | None,
    scores: WaveScoreBreakdown,
    total_score: Decimal,
    reasons: list[str],
) -> tuple[str, list[str]]:
    if snapshot.data_status != "ok":
        return "data_insufficient", list(
            dict.fromkeys([f"indicator_status:{snapshot.data_status}", *reasons])
        )
    if total_score == 0:
        return "data_insufficient", reasons
    if risk_position is not None and risk_position.risk_status == "high_concentration":
        return "position_review_candidate", reasons
    if scores.risk <= Decimal("45"):
        return "risk_attention", reasons
    if (
        pnl_item is not None
        and pnl_item.quantity == 0
        and total_score >= Decimal("70")
    ):
        return "rotation_watch_candidate", reasons
    if total_score >= Decimal("75"):
        return "focus_watch", reasons
    if total_score >= Decimal("60"):
        return "normal_tracking", reasons
    return "needs_review", reasons


def _total_score(scores: WaveScoreBreakdown) -> Decimal:
    return _score(
        scores.trend * Decimal("0.30")
        + scores.momentum * Decimal("0.30")
        + scores.volume * Decimal("0.15")
        + scores.risk * Decimal("0.25")
    )


def _indicator_summary(snapshot: IndicatorSnapshot) -> IndicatorSummary:
    values = snapshot.indicators
    return IndicatorSummary(
        latest_close=snapshot.latest_close,
        ma20=values.ma20,
        ma60=values.ma60,
        momentum_5d_pct=values.momentum_5d_pct,
        momentum_10d_pct=values.momentum_10d_pct,
        momentum_20d_pct=values.momentum_20d_pct,
        max_drawdown_pct=values.max_drawdown_pct,
        atr_pct=values.atr_pct,
        volume_ratio=values.volume_ratio,
    )


def _position_summary(pnl_item: PnlItem | None) -> PositionSummary:
    if pnl_item is None:
        return PositionSummary(
            quantity=Decimal("0"),
            current_market_value=None,
            total_pnl=Decimal("0.00"),
            status="no_position",
        )
    return PositionSummary(
        quantity=pnl_item.quantity,
        current_market_value=pnl_item.current_market_value,
        total_pnl=pnl_item.total_pnl,
        status=pnl_item.status,
    )


def _risk_summary(risk_position: RiskPosition | None) -> WaveRiskSummary:
    if risk_position is None:
        return WaveRiskSummary(
            position_weight_pct=Decimal("0.00"),
            risk_status="no_position",
            reasons=[],
        )
    return WaveRiskSummary(
        position_weight_pct=risk_position.position_weight_pct,
        risk_status=risk_position.risk_status,
        reasons=risk_position.reasons,
    )


def _zero_scores() -> WaveScoreBreakdown:
    return WaveScoreBreakdown(
        trend=Decimal("0"),
        momentum=Decimal("0"),
        volume=Decimal("0"),
        risk=Decimal("0"),
    )


def _score(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

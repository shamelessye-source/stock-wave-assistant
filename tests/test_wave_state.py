from decimal import Decimal

from app.domain.pnl import PnlItem
from app.domain.risk import RiskPosition, RiskSummary
from app.domain.wave_state import build_wave_states
from app.schemas.indicators import IndicatorSnapshot, IndicatorValues


def indicator_snapshot(
    name: str = "Alpha",
    *,
    data_status: str = "ok",
    ma20: float | None = 12.0,
    ma60: float | None = 10.0,
    momentum_5d_pct: float | None = 3.0,
    momentum_10d_pct: float | None = 4.0,
    momentum_20d_pct: float | None = 8.0,
    max_drawdown_pct: float | None = -5.0,
    atr_pct: float | None = 2.5,
    volume_ratio: float | None = 1.4,
) -> IndicatorSnapshot:
    return IndicatorSnapshot(
        name=name,
        symbol="",
        latest_trade_date="2026-06-30",
        latest_close=13.0,
        data_status=data_status,
        degradation_reasons=[] if data_status == "ok" else ["requires_at_least_60_bars"],
        indicators=IndicatorValues(
            ma20=ma20,
            ma60=ma60,
            momentum_5d_pct=momentum_5d_pct,
            momentum_10d_pct=momentum_10d_pct,
            momentum_20d_pct=momentum_20d_pct,
            max_drawdown_pct=max_drawdown_pct,
            atr_pct=atr_pct,
            volume_ratio=volume_ratio,
        ),
    )


def pnl_item(name: str = "Alpha") -> PnlItem:
    return PnlItem(
        instrument_name=name,
        instrument_code="",
        quantity=Decimal("100"),
        average_cost=Decimal("10"),
        cumulative_fee=Decimal("1"),
        realized_pnl=Decimal("0"),
        current_market_value=Decimal("1300"),
        unrealized_pnl=Decimal("300"),
        total_pnl=Decimal("300"),
        status="ok",
        errors=[],
    )


def risk_summary(position: RiskPosition) -> RiskSummary:
    return RiskSummary(
        total_market_value=Decimal("1300"),
        floating_pnl=Decimal("300"),
        realized_pnl=Decimal("0"),
        total_pnl=Decimal("300"),
        max_single_position=position,
        max_single_position_risk_status=position.risk_status,
        direction_concentration=[],
        group_concentration=[],
        positions=[position],
        data_status="capital_base_missing",
        degradation_reasons=["capital_base_missing"],
    )


def risk_position(
    *,
    weight_pct: str = "20",
    risk_status: str = "normal",
) -> RiskPosition:
    return RiskPosition(
        instrument_name="Alpha",
        instrument_code="",
        group="核心观察",
        direction="半导体封测",
        market_value=Decimal("1300"),
        position_weight_pct=Decimal(weight_pct),
        unrealized_pnl=Decimal("300"),
        realized_pnl=Decimal("0"),
        total_pnl=Decimal("300"),
        risk_status=risk_status,
        reasons=[] if risk_status == "normal" else ["single_position_weight_high"],
    )


def test_build_wave_states_marks_strong_explainable_setup_as_focus_watch() -> None:
    position = risk_position(weight_pct="20", risk_status="normal")
    states = build_wave_states(
        indicator_snapshots=[indicator_snapshot()],
        risk_summary=risk_summary(position),
        pnl_items=[pnl_item()],
    )

    state = states[0]
    assert state.wave_state.state == "focus_watch"
    assert state.wave_state.label_cn == "重点观察"
    assert state.wave_state.total_score >= Decimal("75")
    assert "trend_above_ma20_ma60" in state.wave_state.reasons


def test_build_wave_states_uses_position_review_candidate_for_concentration() -> None:
    position = risk_position(weight_pct="75", risk_status="high_concentration")
    states = build_wave_states(
        indicator_snapshots=[indicator_snapshot()],
        risk_summary=risk_summary(position),
        pnl_items=[pnl_item()],
    )

    assert states[0].wave_state.state == "position_review_candidate"
    assert "single_position_weight_high" in states[0].wave_state.reasons


def test_build_wave_states_degrades_when_indicator_data_is_insufficient() -> None:
    position = risk_position(weight_pct="20", risk_status="normal")
    states = build_wave_states(
        indicator_snapshots=[indicator_snapshot(data_status="data_insufficient")],
        risk_summary=risk_summary(position),
        pnl_items=[pnl_item()],
    )

    assert states[0].wave_state.state == "data_insufficient"
    assert states[0].wave_state.total_score == Decimal("0")
    assert "indicator_status:data_insufficient" in states[0].wave_state.reasons

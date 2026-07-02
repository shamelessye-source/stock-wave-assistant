from datetime import datetime
from decimal import Decimal

from app.domain.pnl import PnlItem, PnlSummary
from app.domain.report_builder import build_preclose_report
from app.domain.risk import RiskPosition, RiskSummary
from app.domain.trading_calendar import evaluate_market_session
from app.domain.wave_state import (
    IndicatorSummary,
    PositionSummary,
    WaveRiskSummary,
    WaveScoreBreakdown,
    WaveState,
    WaveStateItem,
)
from app.schemas.indicators import IndicatorSnapshot, IndicatorValues


def test_build_preclose_report_returns_structured_json_contract() -> None:
    report = build_preclose_report(
        indicator_snapshots=[indicator_snapshot("Alpha")],
        risk_summary=risk_summary(data_status="capital_base_missing"),
        wave_states=[
            wave_item("Alpha", "focus_watch", "重点观察", "82.50"),
            wave_item("Beta", "position_review_candidate", "仓位复核候选", "71.25"),
            wave_item("Gamma", "rotation_watch_candidate", "切换观察候选", "73.00"),
        ],
        pnl_summary=PnlSummary(items=[pnl_item("Alpha")]),
        market_session_status=evaluate_market_session(
            datetime.fromisoformat("2026-07-01T14:55:00")
        ),
        generated_at=datetime.fromisoformat("2026-07-01T14:55:00"),
    )

    assert report.report_type == "preclose_1455"
    assert report.as_of_date == "2026-07-01"
    assert report.as_of_time == "14:55:00"
    assert report.market_session_status.status == "preclose"
    assert report.not_advice is True
    assert report.data_status == "capital_base_missing"
    assert report.portfolio_summary.total_market_value == Decimal("1300.00")
    assert report.state_distribution["focus_watch"] == 1
    assert report.attention_items[0].name == "Alpha"
    assert report.position_review_candidates[0].name == "Beta"
    assert report.rotation_watch_candidates[0].name == "Gamma"
    assert "capital_base_missing" in report.data_quality_notes


def test_build_preclose_report_degrades_on_non_trading_day() -> None:
    report = build_preclose_report(
        indicator_snapshots=[],
        risk_summary=risk_summary(data_status="data_insufficient"),
        wave_states=[],
        pnl_summary=PnlSummary(items=[]),
        market_session_status=evaluate_market_session(
            datetime.fromisoformat("2026-07-04T14:55:00")
        ),
        generated_at=datetime.fromisoformat("2026-07-04T14:55:00"),
    )

    assert report.market_session_status.status == "non_trading_day"
    assert report.report_status == "blocked"
    assert report.data_status == "non_trading_day"
    assert "non_trading_day" in report.data_quality_notes


def test_build_preclose_report_keeps_data_insufficient_notes() -> None:
    report = build_preclose_report(
        indicator_snapshots=[
            indicator_snapshot("Alpha", data_status="data_insufficient")
        ],
        risk_summary=risk_summary(data_status="ok"),
        wave_states=[
            wave_item(
                "Alpha",
                "data_insufficient",
                "数据不足",
                "0.00",
                data_status="data_insufficient",
            )
        ],
        pnl_summary=PnlSummary(items=[pnl_item("Alpha")]),
        market_session_status=evaluate_market_session(
            datetime.fromisoformat("2026-07-01T14:55:00")
        ),
        generated_at=datetime.fromisoformat("2026-07-01T14:55:00"),
    )

    assert report.report_status == "partial"
    assert report.data_status == "data_insufficient"
    assert "indicator:Alpha:data_insufficient" in report.data_quality_notes
    assert "wave:Alpha:data_insufficient" in report.data_quality_notes


def indicator_snapshot(name: str, data_status: str = "ok") -> IndicatorSnapshot:
    return IndicatorSnapshot(
        name=name,
        symbol="",
        latest_trade_date="2026-06-30",
        latest_close=13.0,
        data_status=data_status,
        degradation_reasons=[] if data_status == "ok" else ["requires_at_least_60_bars"],
        indicators=IndicatorValues(
            ma20=12.0,
            ma60=10.0,
            momentum_5d_pct=3.0,
            momentum_10d_pct=4.0,
            momentum_20d_pct=8.0,
            max_drawdown_pct=-5.0,
            atr_pct=2.5,
            volume_ratio=1.4,
        ),
    )


def pnl_item(name: str) -> PnlItem:
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


def risk_summary(data_status: str) -> RiskSummary:
    position = RiskPosition(
        instrument_name="Alpha",
        instrument_code="",
        group="核心观察",
        direction="半导体封测",
        market_value=Decimal("1300"),
        position_weight_pct=Decimal("100"),
        unrealized_pnl=Decimal("300"),
        realized_pnl=Decimal("0"),
        total_pnl=Decimal("300"),
        risk_status="high_concentration",
        reasons=["single_position_weight_high"],
    )
    return RiskSummary(
        total_market_value=Decimal("1300"),
        floating_pnl=Decimal("300"),
        realized_pnl=Decimal("0"),
        total_pnl=Decimal("300"),
        max_single_position=position,
        max_single_position_risk_status="high_concentration",
        direction_concentration=[],
        group_concentration=[],
        positions=[position],
        data_status=data_status,
        degradation_reasons=[data_status],
    )


def wave_item(
    name: str,
    state: str,
    label_cn: str,
    score: str,
    data_status: str = "ok",
) -> WaveStateItem:
    return WaveStateItem(
        name=name,
        symbol="",
        latest_trade_date="2026-06-30",
        data_status=data_status,
        indicator_summary=IndicatorSummary(
            latest_close=13.0,
            ma20=12.0,
            ma60=10.0,
            momentum_5d_pct=3.0,
            momentum_10d_pct=4.0,
            momentum_20d_pct=8.0,
            max_drawdown_pct=-5.0,
            atr_pct=2.5,
            volume_ratio=1.4,
        ),
        position_summary=PositionSummary(
            quantity=Decimal("100"),
            current_market_value=Decimal("1300"),
            total_pnl=Decimal("300"),
            status="ok",
        ),
        risk_summary=WaveRiskSummary(
            position_weight_pct=Decimal("10"),
            risk_status="normal",
            reasons=[],
        ),
        wave_state=WaveState(
            state=state,
            label_cn=label_cn,
            total_score=Decimal(score),
            scores=WaveScoreBreakdown(
                trend=Decimal("80"),
                momentum=Decimal("80"),
                volume=Decimal("70"),
                risk=Decimal("70"),
            ),
            reasons=["trend_above_ma20_ma60"],
        ),
    )

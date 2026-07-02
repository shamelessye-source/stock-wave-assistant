from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from app.domain.pnl import PnlSummary
from app.domain.risk import RiskSummary
from app.domain.trading_calendar import MarketSessionStatus
from app.domain.wave_state import WaveStateItem
from app.schemas.indicators import IndicatorSnapshot


@dataclass(frozen=True)
class PortfolioReportSummary:
    total_market_value: Decimal
    floating_pnl: Decimal
    realized_pnl: Decimal
    total_pnl: Decimal
    max_single_position_weight_pct: Decimal
    max_single_position_risk_status: str
    data_status: str


@dataclass(frozen=True)
class ReportListItem:
    name: str
    symbol: str
    state: str
    label_cn: str
    total_score: Decimal
    reasons: list[str]
    data_status: str
    position_weight_pct: Decimal


@dataclass(frozen=True)
class PrecloseReport:
    report_type: str
    report_status: str
    as_of_date: str
    as_of_time: str
    market_session_status: MarketSessionStatus
    not_advice: bool
    data_status: str
    portfolio_summary: PortfolioReportSummary
    risk_flags: list[str]
    watchlist_rankings: list[ReportListItem]
    state_distribution: dict[str, int]
    attention_items: list[ReportListItem]
    rotation_watch_candidates: list[ReportListItem]
    position_review_candidates: list[ReportListItem]
    data_quality_notes: list[str]
    generated_at: str


def build_preclose_report(
    *,
    indicator_snapshots: list[IndicatorSnapshot],
    risk_summary: RiskSummary,
    wave_states: list[WaveStateItem],
    pnl_summary: PnlSummary,
    market_session_status: MarketSessionStatus,
    generated_at: datetime,
) -> PrecloseReport:
    data_quality_notes = _data_quality_notes(
        indicator_snapshots,
        risk_summary,
        wave_states,
        market_session_status,
    )
    data_status = _report_data_status(
        risk_summary,
        wave_states,
        market_session_status,
    )
    report_status = _report_status(data_status, market_session_status)
    rankings = sorted(
        [_report_item(item) for item in wave_states],
        key=lambda item: item.total_score,
        reverse=True,
    )

    return PrecloseReport(
        report_type="preclose_1455",
        report_status=report_status,
        as_of_date=market_session_status.as_of_date,
        as_of_time=market_session_status.as_of_time,
        market_session_status=market_session_status,
        not_advice=True,
        data_status=data_status,
        portfolio_summary=PortfolioReportSummary(
            total_market_value=risk_summary.total_market_value,
            floating_pnl=risk_summary.floating_pnl,
            realized_pnl=risk_summary.realized_pnl,
            total_pnl=risk_summary.total_pnl,
            max_single_position_weight_pct=(
                risk_summary.max_single_position.position_weight_pct
            ),
            max_single_position_risk_status=(
                risk_summary.max_single_position_risk_status
            ),
            data_status=risk_summary.data_status,
        ),
        risk_flags=_risk_flags(risk_summary),
        watchlist_rankings=rankings,
        state_distribution=_state_distribution(wave_states),
        attention_items=[
            item
            for item in rankings
            if item.state in {"focus_watch", "risk_attention", "needs_review"}
        ],
        rotation_watch_candidates=[
            item for item in rankings if item.state == "rotation_watch_candidate"
        ],
        position_review_candidates=[
            item for item in rankings if item.state == "position_review_candidate"
        ],
        data_quality_notes=data_quality_notes,
        generated_at=generated_at.isoformat(),
    )


def _report_item(item: WaveStateItem) -> ReportListItem:
    return ReportListItem(
        name=item.name,
        symbol=item.symbol,
        state=item.wave_state.state,
        label_cn=item.wave_state.label_cn,
        total_score=item.wave_state.total_score,
        reasons=item.wave_state.reasons,
        data_status=item.data_status,
        position_weight_pct=item.risk_summary.position_weight_pct,
    )


def _report_data_status(
    risk_summary: RiskSummary,
    wave_states: list[WaveStateItem],
    market_session_status: MarketSessionStatus,
) -> str:
    if market_session_status.status == "non_trading_day":
        return "non_trading_day"
    if risk_summary.data_status != "ok":
        return risk_summary.data_status
    if any(item.data_status != "ok" for item in wave_states):
        return "data_insufficient"
    return "ok"


def _report_status(
    data_status: str,
    market_session_status: MarketSessionStatus,
) -> str:
    if data_status == "non_trading_day":
        return "blocked"
    if market_session_status.status != "preclose" or data_status != "ok":
        return "partial"
    return "ready"


def _risk_flags(risk_summary: RiskSummary) -> list[str]:
    flags = list(risk_summary.degradation_reasons)
    if risk_summary.max_single_position_risk_status != "normal":
        flags.append(
            "single_position:"
            f"{risk_summary.max_single_position.instrument_name}:"
            f"{risk_summary.max_single_position_risk_status}"
        )
    for item in risk_summary.direction_concentration:
        if item.risk_status != "normal":
            flags.append(f"direction:{item.name}:{item.risk_status}")
    for item in risk_summary.group_concentration:
        if item.risk_status != "normal":
            flags.append(f"group:{item.name}:{item.risk_status}")
    return list(dict.fromkeys(flags))


def _state_distribution(wave_states: list[WaveStateItem]) -> dict[str, int]:
    distribution: dict[str, int] = {}
    for item in wave_states:
        distribution[item.wave_state.state] = (
            distribution.get(item.wave_state.state, 0) + 1
        )
    return distribution


def _data_quality_notes(
    indicator_snapshots: list[IndicatorSnapshot],
    risk_summary: RiskSummary,
    wave_states: list[WaveStateItem],
    market_session_status: MarketSessionStatus,
) -> list[str]:
    notes = list(risk_summary.degradation_reasons)
    if market_session_status.status != "preclose":
        notes.append(market_session_status.status)
    for snapshot in indicator_snapshots:
        if snapshot.data_status != "ok":
            notes.append(f"indicator:{snapshot.name}:{snapshot.data_status}")
            notes.extend(snapshot.degradation_reasons)
    for item in wave_states:
        if item.data_status != "ok":
            notes.append(f"wave:{item.name}:{item.data_status}")
    if not wave_states:
        notes.append("no_wave_states")
    return list(dict.fromkeys(notes))

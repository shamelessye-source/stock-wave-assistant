from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class MarketSessionStatusResponse(BaseModel):
    status: str
    is_trading_day: bool
    is_preclose_time: bool
    session: str
    calendar_mode: str
    as_of_date: str
    as_of_time: str
    report_time: str


class PortfolioReportSummaryResponse(BaseModel):
    total_market_value: str
    floating_pnl: str
    realized_pnl: str
    total_pnl: str
    max_single_position_weight_pct: str
    max_single_position_risk_status: str
    data_status: str


class ReportListItemResponse(BaseModel):
    name: str
    symbol: str
    state: str
    label_cn: str
    total_score: str
    reasons: list[str]
    data_status: str
    position_weight_pct: str


class PrecloseReportResponse(BaseModel):
    report_type: str
    report_status: str
    as_of_date: str
    as_of_time: str
    market_session_status: MarketSessionStatusResponse
    not_advice: bool
    data_status: str
    portfolio_summary: PortfolioReportSummaryResponse
    risk_flags: list[str]
    watchlist_rankings: list[ReportListItemResponse]
    state_distribution: dict[str, int]
    attention_items: list[ReportListItemResponse]
    rotation_watch_candidates: list[ReportListItemResponse]
    position_review_candidates: list[ReportListItemResponse]
    data_quality_notes: list[str]
    generated_at: str


class PrecloseReportRunRequest(BaseModel):
    as_of: str | None = None
    force: bool = False


class PrecloseReportRunResponse(BaseModel):
    status: str
    report_id: str
    report_type: str
    as_of: str
    file_name: str
    relative_path: str
    skipped_reason: str | None = None
    error: str | None = None
    report: dict[str, Any] | None = None

from __future__ import annotations

from pydantic import BaseModel


class RiskPositionResponse(BaseModel):
    instrument_name: str
    instrument_code: str
    group: str
    direction: str
    market_value: str
    position_weight_pct: str
    unrealized_pnl: str
    realized_pnl: str
    total_pnl: str
    risk_status: str
    reasons: list[str]


class ConcentrationItemResponse(BaseModel):
    name: str
    market_value: str
    weight_pct: str
    risk_status: str


class RiskSummaryResponse(BaseModel):
    total_market_value: str
    floating_pnl: str
    realized_pnl: str
    total_pnl: str
    max_single_position: RiskPositionResponse
    max_single_position_risk_status: str
    direction_concentration: list[ConcentrationItemResponse]
    group_concentration: list[ConcentrationItemResponse]
    positions: list[RiskPositionResponse]
    data_status: str
    degradation_reasons: list[str]

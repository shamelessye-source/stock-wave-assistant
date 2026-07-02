from __future__ import annotations

from pydantic import BaseModel


class WaveIndicatorSummaryResponse(BaseModel):
    latest_close: float | None
    ma20: float | None
    ma60: float | None
    momentum_5d_pct: float | None
    momentum_10d_pct: float | None
    momentum_20d_pct: float | None
    max_drawdown_pct: float | None
    atr_pct: float | None
    volume_ratio: float | None


class WavePositionSummaryResponse(BaseModel):
    quantity: str
    current_market_value: str | None
    total_pnl: str
    status: str


class WaveRiskSummaryResponse(BaseModel):
    position_weight_pct: str
    risk_status: str
    reasons: list[str]


class WaveScoreBreakdownResponse(BaseModel):
    trend: str
    momentum: str
    volume: str
    risk: str


class WaveStateDetailResponse(BaseModel):
    state: str
    label_cn: str
    total_score: str
    scores: WaveScoreBreakdownResponse
    reasons: list[str]


class WaveStateItemResponse(BaseModel):
    name: str
    symbol: str
    latest_trade_date: str | None
    data_status: str
    indicator_summary: WaveIndicatorSummaryResponse
    position_summary: WavePositionSummaryResponse
    risk_summary: WaveRiskSummaryResponse
    wave_state: WaveStateDetailResponse


class WaveStatesResponse(BaseModel):
    items: list[WaveStateItemResponse]

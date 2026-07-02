from __future__ import annotations

from fastapi import APIRouter

from app.core.config import load_settings
from app.schemas.risk import RiskSummaryResponse
from app.services.portfolio_service import (
    build_current_risk_summary,
    decimal_dataclass_to_response,
)


router = APIRouter()


@router.get("/api/risk/summary", response_model=RiskSummaryResponse)
def risk_summary() -> dict[str, object]:
    settings = load_settings()
    return decimal_dataclass_to_response(build_current_risk_summary(settings))

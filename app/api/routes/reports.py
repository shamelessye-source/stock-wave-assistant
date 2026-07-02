from __future__ import annotations

from dataclasses import asdict
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query

from app.core.config import load_settings
from app.schemas.llm import ReportExplainRequest, ReportExplainResponse
from app.schemas.report import PrecloseReportResponse
from app.services.portfolio_service import (
    build_current_preclose_report,
    decimal_dataclass_to_response,
)
from app.services.report_explanation_service import explain_preclose_report


router = APIRouter()


@router.get("/api/reports/preclose", response_model=PrecloseReportResponse)
def preclose_report(as_of: str | None = Query(default=None)) -> dict[str, object]:
    settings = load_settings()
    as_of_datetime = _parse_as_of(as_of)
    return decimal_dataclass_to_response(
        build_current_preclose_report(settings, as_of_datetime)
    )


@router.post("/api/reports/preclose/explain", response_model=ReportExplainResponse)
def preclose_report_explain(
    payload: ReportExplainRequest | None = None,
) -> dict[str, object]:
    settings = load_settings()
    if payload is not None and payload.report is not None:
        report = payload.report
    else:
        as_of_datetime = _parse_as_of(payload.as_of if payload else None)
        report = decimal_dataclass_to_response(
            build_current_preclose_report(settings, as_of_datetime)
        )
    return asdict(explain_preclose_report(report, settings=settings))


def _parse_as_of(value: str | None) -> datetime:
    if value is None:
        return datetime.now()
    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail="as_of must use YYYY-MM-DDTHH:MM:SS",
        ) from exc

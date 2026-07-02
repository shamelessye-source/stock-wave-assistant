from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ReportExplainRequest(BaseModel):
    as_of: str | None = None
    report: dict[str, Any] | None = None


class ReportExplainResponse(BaseModel):
    success: bool
    provider: str
    model: str
    duration_ms: int
    text: str
    error: str | None
    exit_code: int | None

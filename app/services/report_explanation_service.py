from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from app.core.config import AppSettings
from app.providers.llm.codex_cli import CodexCliProvider, FakeCodexProvider


@dataclass(frozen=True)
class ReportExplanationResult:
    success: bool
    provider: str
    model: str
    duration_ms: int
    text: str
    error: str | None
    exit_code: int | None


def build_explanation_prompt(report: dict[str, Any]) -> str:
    payload = {
        "prompt_type": "preclose_report_explanation",
        "language": "zh-CN",
        "instructions": [
            "Only explain facts present in report_json.",
            "Do not calculate indicators, risk, scores, or states.",
            "Do not add facts that are absent from report_json.",
            "Use concise Chinese sections for data status, portfolio risk, state distribution, attention items, position review items, data quality notes, and a non-advisory statement.",
        ],
        "report_json": report,
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def explain_preclose_report(
    report: dict[str, Any],
    settings: AppSettings | None = None,
) -> ReportExplanationResult:
    provider_name = "fake"
    provider = FakeCodexProvider()
    if settings is not None and settings.enable_codex_cli:
        provider_name = "codex_cli"
        provider = CodexCliProvider(
            cli_path=settings.codex_cli_path,
            model=settings.codex_model,
            timeout_seconds=settings.codex_timeout_seconds,
            sandbox_mode=settings.codex_sandbox_mode,
        )

    result = provider.run(build_explanation_prompt(report))
    return ReportExplanationResult(
        success=result.success,
        provider=provider_name,
        model=result.model,
        duration_ms=result.duration_ms,
        text=result.text,
        error=result.error,
        exit_code=result.exit_code,
    )

import json

from app.services.report_explanation_service import (
    build_explanation_prompt,
    explain_preclose_report,
)


def report_payload() -> dict[str, object]:
    return {
        "report_type": "preclose_1455",
        "report_status": "partial",
        "as_of_date": "2026-07-01",
        "as_of_time": "14:55:00",
        "market_session_status": {"status": "preclose"},
        "not_advice": True,
        "data_status": "capital_base_missing",
        "portfolio_summary": {"total_market_value": "2533.00", "total_pnl": "1297.77"},
        "risk_flags": ["capital_base_missing"],
        "watchlist_rankings": [],
        "state_distribution": {"position_review_candidate": 1},
        "attention_items": [],
        "rotation_watch_candidates": [],
        "position_review_candidates": [
            {"name": "中天科技", "total_score": "71.25", "reasons": []}
        ],
        "data_quality_notes": ["capital_base_missing"],
        "generated_at": "2026-07-01T14:55:00",
    }


def test_build_explanation_prompt_only_wraps_report_json() -> None:
    prompt = build_explanation_prompt(report_payload())
    payload = json.loads(prompt)

    assert payload["prompt_type"] == "preclose_report_explanation"
    assert payload["instructions"][0] == "Only explain facts present in report_json."
    assert payload["report_json"]["report_type"] == "preclose_1455"


def test_explain_preclose_report_uses_fake_provider_by_default() -> None:
    result = explain_preclose_report(report_payload())

    assert result.success is True
    assert result.provider == "fake"
    assert result.model == "fake-codex"
    assert "数据状态" in result.text
    assert "中天科技" in result.text

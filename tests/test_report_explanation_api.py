from fastapi.testclient import TestClient

from app.main import app


def test_preclose_explain_api_uses_fake_provider_by_default(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "task7.db"))
    monkeypatch.delenv("ENABLE_CODEX_CLI", raising=False)
    client = TestClient(app)

    create_response = client.post(
        "/api/ledger/trades",
        json={
            "instrument_name": "中天科技",
            "instrument_code": "",
            "trade_date": "2026-06-30",
            "side": "increase_position",
            "quantity": "100",
            "price": "12.34",
            "fee": "1.23",
            "note": "manual fact",
        },
    )
    response = client.post(
        "/api/reports/preclose/explain",
        json={"as_of": "2026-07-01T14:55:00"},
    )

    assert create_response.status_code == 200
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["provider"] == "fake"
    assert payload["model"] == "fake-codex"
    assert "数据状态" in payload["text"]
    assert "C:\\" not in str(payload)


def test_preclose_explain_api_accepts_existing_report_json() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/reports/preclose/explain",
        json={
            "report": {
                "report_type": "preclose_1455",
                "report_status": "partial",
                "as_of_date": "2026-07-01",
                "as_of_time": "14:55:00",
                "data_status": "capital_base_missing",
                "portfolio_summary": {
                    "total_market_value": "0.00",
                    "total_pnl": "0.00",
                },
                "state_distribution": {},
                "attention_items": [],
                "position_review_candidates": [],
                "rotation_watch_candidates": [],
                "data_quality_notes": ["capital_base_missing"],
            }
        },
    )

    assert response.status_code == 200
    assert response.json()["provider"] == "fake"

from fastapi.testclient import TestClient

from app.main import app


def test_risk_and_wave_api_return_structured_snapshots(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "task5.db"))
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
    risk_response = client.get("/api/risk/summary")
    wave_response = client.get("/api/wave/states")

    assert create_response.status_code == 200
    assert risk_response.status_code == 200
    assert wave_response.status_code == 200
    risk_payload = risk_response.json()
    wave_payload = wave_response.json()
    assert risk_payload["total_market_value"] != "0.00"
    assert risk_payload["max_single_position"]["risk_status"] in {
        "normal",
        "high_concentration",
    }
    assert wave_payload["items"]
    assert wave_payload["items"][0]["wave_state"]["state"] in {
        "focus_watch",
        "normal_tracking",
        "risk_attention",
        "data_insufficient",
        "position_review_candidate",
        "rotation_watch_candidate",
        "needs_review",
    }
    assert "C:\\" not in str(risk_payload)
    assert "C:\\" not in str(wave_payload)

from fastapi.testclient import TestClient

from app.main import app


def test_ledger_api_creates_lists_and_summarizes_trade_records(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "api-ledger.db"))
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
    list_response = client.get("/api/ledger/trades")
    summary_response = client.get("/api/ledger/summary")

    assert create_response.status_code == 200
    assert create_response.json()["id"] == 1
    assert list_response.status_code == 200
    assert len(list_response.json()["items"]) == 1
    assert summary_response.status_code == 200
    summary = summary_response.json()
    assert summary["items"][0]["instrument_name"] == "中天科技"
    assert summary["items"][0]["quantity"] == "100"
    assert summary["items"][0]["status"] in {"ok", "price_missing"}
    assert "C:\\" not in str(summary)


def test_ledger_api_rejects_invalid_quantity(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "api-ledger.db"))
    client = TestClient(app)

    response = client.post(
        "/api/ledger/trades",
        json={
            "instrument_name": "中天科技",
            "instrument_code": "",
            "trade_date": "2026-06-30",
            "side": "increase_position",
            "quantity": "0",
            "price": "12.34",
            "fee": "1.23",
            "note": "invalid",
        },
    )

    assert response.status_code == 422


def test_ledger_summary_reports_invalid_sequence(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "api-ledger.db"))
    client = TestClient(app)

    response = client.post(
        "/api/ledger/trades",
        json={
            "instrument_name": "中天科技",
            "instrument_code": "",
            "trade_date": "2026-06-30",
            "side": "decrease_position",
            "quantity": "100",
            "price": "12.34",
            "fee": "1.23",
            "note": "manual fact",
        },
    )
    summary_response = client.get("/api/ledger/summary")

    assert response.status_code == 200
    assert summary_response.status_code == 200
    item = summary_response.json()["items"][0]
    assert item["status"] == "invalid_sequence"
    assert "decrease_exceeds_position" in item["errors"]

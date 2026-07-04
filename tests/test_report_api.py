from fastapi.testclient import TestClient

from app.main import app


def test_preclose_report_api_returns_structured_report(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "task6.db"))
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
    response = client.get(
        "/api/reports/preclose?as_of=2026-07-01T14:55:00",
    )

    assert create_response.status_code == 200
    assert response.status_code == 200
    payload = response.json()
    assert payload["report_type"] == "preclose_1455"
    assert payload["as_of_date"] == "2026-07-01"
    assert payload["as_of_time"] == "14:55:00"
    assert payload["market_session_status"]["status"] == "preclose"
    assert payload["not_advice"] is True
    assert payload["portfolio_summary"]["total_market_value"] != "0.00"
    assert "watchlist_rankings" in payload
    assert "state_distribution" in payload
    assert "capital_base_missing" in payload["data_quality_notes"]
    assert "C:\\" not in str(payload)


def test_preclose_report_api_degrades_for_non_trading_day(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "task6.db"))
    client = TestClient(app)

    response = client.get(
        "/api/reports/preclose?as_of=2026-07-04T14:55:00",
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["market_session_status"]["status"] == "non_trading_day"
    assert payload["report_status"] == "blocked"
    assert payload["data_status"] == "non_trading_day"


def test_preclose_report_run_once_api_writes_report_without_path_leak(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "task11.db"))
    monkeypatch.setenv("REPORT_DIR", str(tmp_path / "reports"))
    client = TestClient(app)

    response = client.post(
        "/api/reports/preclose/run-once",
        json={"as_of": "2026-07-01T14:55:00"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "generated"
    assert payload["report_id"] == "preclose_1455-2026-07-01"
    assert payload["file_name"] == "preclose_1455-2026-07-01.json"
    assert payload["relative_path"] == "preclose_1455-2026-07-01.json"
    assert payload["report"]["schema_version"] == "1.0"
    assert payload["report"]["not_advice"] is True
    assert "C:\\" not in str(payload)
    assert (tmp_path / "reports" / payload["file_name"]).exists()


def test_preclose_report_run_once_api_is_idempotent(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "task11.db"))
    monkeypatch.setenv("REPORT_DIR", str(tmp_path / "reports"))
    client = TestClient(app)

    first = client.post(
        "/api/reports/preclose/run-once",
        json={"as_of": "2026-07-01T14:55:00"},
    )
    second = client.post(
        "/api/reports/preclose/run-once",
        json={"as_of": "2026-07-01T14:55:00"},
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["status"] == "generated"
    assert second.json()["status"] == "existing"


def test_preclose_report_run_once_api_handles_corrupt_existing_report(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "task11.db"))
    monkeypatch.setenv("REPORT_DIR", str(tmp_path / "reports"))
    client = TestClient(app)

    first = client.post(
        "/api/reports/preclose/run-once",
        json={"as_of": "2026-07-01T14:55:00"},
    )
    file_name = first.json()["file_name"]
    (tmp_path / "reports" / file_name).write_text("{not-json", encoding="utf-8")

    second = client.post(
        "/api/reports/preclose/run-once",
        json={"as_of": "2026-07-01T14:55:00"},
    )

    assert first.status_code == 200
    assert second.status_code == 200
    payload = second.json()
    assert payload["status"] == "existing_read_error"
    assert payload["report"] is None
    assert payload["error"] == "existing report could not be read; rerun with force=true"
    assert "C:\\" not in str(payload)


def test_preclose_report_run_once_api_supports_force(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "task11.db"))
    monkeypatch.setenv("REPORT_DIR", str(tmp_path / "reports"))
    client = TestClient(app)

    first = client.post(
        "/api/reports/preclose/run-once",
        json={"as_of": "2026-07-01T14:55:00"},
    )
    second = client.post(
        "/api/reports/preclose/run-once",
        json={"as_of": "2026-07-01T14:55:00", "force": True},
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["status"] == "overwritten"

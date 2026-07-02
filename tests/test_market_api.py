from fastapi.testclient import TestClient

from app.main import app


def test_market_snapshot_api_returns_mock_bars_without_sensitive_paths() -> None:
    client = TestClient(app)

    response = client.get("/api/market/snapshot")

    assert response.status_code == 200
    payload = response.json()
    assert payload["provider"] == "mock"
    assert payload["bar_count"] >= 90
    assert payload["items"]
    first = payload["items"][0]
    assert "name" in first
    assert "symbol" in first
    assert len(first["bars"]) >= 90
    assert "trade_date" in first["bars"][-1]
    assert "C:\\" not in str(payload)


def test_indicators_snapshot_api_returns_core_indicator_fields() -> None:
    client = TestClient(app)

    response = client.get("/api/indicators/snapshot")

    assert response.status_code == 200
    payload = response.json()
    assert payload["provider"] == "mock"
    assert payload["items"]
    first = payload["items"][0]
    assert {
        "name",
        "symbol",
        "latest_trade_date",
        "latest_close",
        "indicators",
        "data_status",
        "degradation_reasons",
    }.issubset(first)
    assert {
        "ma20",
        "ma60",
        "momentum_5d_pct",
        "momentum_10d_pct",
        "momentum_20d_pct",
        "max_drawdown_pct",
        "atr_pct",
        "volume_ratio",
    }.issubset(first["indicators"])
    assert "C:\\" not in str(payload)

from fastapi.testclient import TestClient

from app.main import app


def test_mock_mvp_smoke_endpoints(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "smoke.db"))
    monkeypatch.setenv("ENABLE_CODEX_CLI", "false")
    client = TestClient(app)

    checks = [
        ("health", client.get("/api/health")),
        ("config", client.get("/api/config/status")),
        ("indicators", client.get("/api/indicators/snapshot")),
        ("risk", client.get("/api/risk/summary")),
        ("wave", client.get("/api/wave/states")),
        (
            "preclose",
            client.get("/api/reports/preclose?as_of=2026-07-01T14:55:00"),
        ),
        (
            "explain",
            client.post(
                "/api/reports/preclose/explain",
                json={"as_of": "2026-07-01T14:55:00"},
            ),
        ),
    ]

    for name, response in checks:
        assert response.status_code == 200, name
        assert "C:\\" not in str(response.json())

    assert checks[0][1].json()["status"] == "ok"
    assert checks[1][1].json()["providers"]["market"] == "mock"
    assert checks[2][1].json()["items"]
    assert checks[4][1].json()["items"]
    assert checks[5][1].json()["not_advice"] is True
    assert checks[6][1].json()["provider"] == "fake"

from fastapi.testclient import TestClient

from app.main import app


def test_config_status_reports_loaded_config_without_sensitive_paths(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("CODEX_CLI_PATH", str(tmp_path / "missing.cmd"))
    client = TestClient(app)

    response = client.get("/api/config/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["mode"] == "mock"
    assert payload["providers"] == {
        "market": "mock",
        "llm": "codex_cli",
    }
    assert payload["codex"] == {
        "model": "gpt-5.5",
        "timeout_seconds": 120,
        "sandbox_mode": "read-only",
        "cli_path_configured": True,
        "enabled": False,
        "cli_path_exists": False,
        "version_check": "not_run",
    }
    assert payload["database"] == {
        "engine": "sqlite",
        "configured": True,
    }
    assert payload["reports"] == {
        "configured": True,
    }
    assert "codex.cmd" not in str(payload)
    assert "data/app.db" not in str(payload)
    assert "data/reports" not in str(payload)

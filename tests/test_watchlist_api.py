from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app


def test_watchlist_api_reads_config_without_sensitive_path(
    tmp_path: Path,
    monkeypatch,
) -> None:
    config_dir = write_config_dir(tmp_path)
    patch_settings(monkeypatch, config_dir, tmp_path)
    client = TestClient(app)

    response = client.get("/api/watchlist")

    assert response.status_code == 200
    payload = response.json()
    assert payload["items"][0]["name"] == "示例标的"
    assert payload["items"][0]["symbol"] == "000001.SZ"
    assert "C:\\" not in str(payload)


def test_watchlist_api_updates_config_and_can_read_it_back(tmp_path: Path, monkeypatch) -> None:
    config_dir = write_config_dir(tmp_path)
    patch_settings(monkeypatch, config_dir, tmp_path)
    client = TestClient(app)
    payload = {
        "version": 1,
        "items": [
            {
                "name": "新观察标的",
                "symbol": "600522.SH",
                "market": "SH",
                "group": "观察池",
                "theme": "通信设备",
                "enabled": True,
                "observation_note": "本地编辑验证",
                "risk_note": "数据可能延迟",
            }
        ],
    }

    update = client.put(
        "/api/watchlist",
        json=payload,
    )
    read_back = client.get("/api/watchlist")

    assert update.status_code == 200
    assert read_back.status_code == 200
    assert read_back.json()["items"][0]["name"] == "新观察标的"
    assert read_back.json()["items"][0]["theme"] == "通信设备"


def test_watchlist_validate_api_reports_errors(tmp_path: Path, monkeypatch) -> None:
    config_dir = write_config_dir(tmp_path)
    patch_settings(monkeypatch, config_dir, tmp_path)
    client = TestClient(app)

    response = client.post(
        "/api/watchlist/validate",
        json={
            "version": 1,
            "items": [
                {
                    "name": "",
                    "symbol": "bad-code",
                    "market": "",
                    "group": "",
                    "theme": "",
                    "enabled": True,
                    "observation_note": "",
                    "risk_note": "",
                }
            ],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["valid"] is False
    assert "items[0].name_required" in payload["errors"]
    assert "items[0].symbol_format" in payload["errors"]


def test_watchlist_put_rejects_invalid_payload_without_overwriting(
    tmp_path: Path,
    monkeypatch,
) -> None:
    config_dir = write_config_dir(tmp_path)
    patch_settings(monkeypatch, config_dir, tmp_path)
    original = (config_dir / "watchlist.yaml").read_text(encoding="utf-8")
    client = TestClient(app)

    response = client.put(
        "/api/watchlist",
        json={
            "version": 1,
            "items": [
                {
                    "name": "",
                    "symbol": "bad-code",
                    "market": "",
                    "group": "",
                    "theme": "",
                    "enabled": True,
                    "observation_note": "",
                    "risk_note": "",
                }
            ],
        },
    )

    assert response.status_code == 422
    assert "C:\\" not in str(response.json())
    assert (config_dir / "watchlist.yaml").read_text(encoding="utf-8") == original


@pytest.mark.parametrize(
    ("items", "expected_error"),
    [
        ([], "items_empty"),
        (
            [
                {
                    "name": "Alpha",
                    "symbol": "",
                    "market": "",
                    "group": "",
                    "theme": "",
                    "enabled": True,
                    "observation_note": "",
                    "risk_note": "",
                },
                {
                    "name": " Alpha ",
                    "symbol": "",
                    "market": "",
                    "group": "",
                    "theme": "",
                    "enabled": True,
                    "observation_note": "",
                    "risk_note": "",
                },
            ],
            "name_duplicate:Alpha",
        ),
        (
            [
                {
                    "name": "Alpha",
                    "symbol": "600522.SH",
                    "market": "",
                    "group": "",
                    "theme": "",
                    "enabled": True,
                    "observation_note": "",
                    "risk_note": "",
                },
                {
                    "name": "Beta",
                    "symbol": " 600522.SH ",
                    "market": "",
                    "group": "",
                    "theme": "",
                    "enabled": True,
                    "observation_note": "",
                    "risk_note": "",
                },
            ],
            "symbol_duplicate:600522.SH",
        ),
    ],
)
def test_watchlist_put_rejects_empty_or_duplicate_items_without_overwriting(
    tmp_path: Path,
    monkeypatch,
    items: list[dict[str, object]],
    expected_error: str,
) -> None:
    config_dir = write_config_dir(tmp_path)
    patch_settings(monkeypatch, config_dir, tmp_path)
    original = (config_dir / "watchlist.yaml").read_text(encoding="utf-8")
    client = TestClient(app)

    response = client.put(
        "/api/watchlist",
        json={
            "version": 1,
            "items": items,
        },
    )

    assert response.status_code == 422
    assert expected_error in response.json()["detail"]["errors"]
    assert "C:\\" not in str(response.json())
    assert (config_dir / "watchlist.yaml").read_text(encoding="utf-8") == original


def patch_settings(monkeypatch, config_dir: Path, tmp_path: Path) -> None:
    from app.core.config import load_settings

    def fake_load_settings():
        return load_settings(
            config_dir=config_dir,
            env={
                "MARKET_PROVIDER": "mock",
                "DATABASE_PATH": str(tmp_path / "app.db"),
                "REPORT_DIR": str(tmp_path / "reports"),
            },
        )

    monkeypatch.setattr("app.api.routes.watchlist.load_settings", fake_load_settings)


def write_config_dir(tmp_path: Path) -> Path:
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "watchlist.yaml").write_text(
        """
version: 1
stocks:
  - name: 示例标的
    symbol: 000001.SZ
    market: SZ
    enabled: true
    group: 观察池
    direction: 银行
    watch_reason: 本地验证
    risk_points:
      - 数据可能延迟
""".strip(),
        encoding="utf-8",
    )
    return config_dir

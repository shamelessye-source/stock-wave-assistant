from pathlib import Path

import pytest

from app.core.config import ConfigError, load_settings, load_watchlist_config


def test_load_settings_uses_safe_defaults(tmp_path: Path) -> None:
    settings = load_settings(config_dir=tmp_path, env={})

    assert settings.app_mode == "mock"
    assert settings.market_provider == "mock"
    assert settings.llm_provider == "codex_cli"
    assert settings.codex_model == "gpt-5.5"
    assert settings.codex_timeout_seconds == 120
    assert settings.codex_sandbox_mode == "read-only"
    assert settings.enable_codex_cli is False
    assert settings.database_path == Path("data/app.db")
    assert settings.report_dir == Path("data/reports")
    assert settings.is_mock_mode is True


def test_load_settings_allows_environment_overrides(tmp_path: Path) -> None:
    settings = load_settings(
        config_dir=tmp_path,
        env={
            "APP_MODE": "fake",
            "MARKET_PROVIDER": "fake",
            "CODEX_CLI_PATH": r"C:\Tools\codex.cmd",
            "CODEX_MODEL": "gpt-5.5",
            "CODEX_TIMEOUT_SECONDS": "45",
            "CODEX_SANDBOX_MODE": "read-only",
            "ENABLE_CODEX_CLI": "true",
            "DATABASE_PATH": str(tmp_path / "custom.db"),
            "REPORT_DIR": str(tmp_path / "reports"),
        },
    )

    assert settings.app_mode == "fake"
    assert settings.market_provider == "fake"
    assert settings.codex_cli_path == Path(r"C:\Tools\codex.cmd")
    assert settings.codex_timeout_seconds == 45
    assert settings.enable_codex_cli is True
    assert settings.database_path == tmp_path / "custom.db"
    assert settings.report_dir == tmp_path / "reports"
    assert settings.is_mock_mode is True


def test_load_settings_rejects_invalid_timeout(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="CODEX_TIMEOUT_SECONDS"):
        load_settings(config_dir=tmp_path, env={"CODEX_TIMEOUT_SECONDS": "zero"})


def test_load_watchlist_config_requires_stocks_key(tmp_path: Path) -> None:
    watchlist_path = tmp_path / "watchlist.yaml"
    watchlist_path.write_text("version: 1\n", encoding="utf-8")

    with pytest.raises(ConfigError, match="stocks"):
        load_watchlist_config(watchlist_path)


def test_load_watchlist_config_reads_stock_entries(tmp_path: Path) -> None:
    watchlist_path = tmp_path / "watchlist.yaml"
    watchlist_path.write_text(
        """
version: 1
stocks:
  - symbol: 600000.SH
    name: 示例股票
    market: SH
    enabled: true
    group: 核心观察
    status: 正常跟踪
""".strip(),
        encoding="utf-8",
    )

    config = load_watchlist_config(watchlist_path)

    assert config["version"] == 1
    assert config["stocks"][0]["symbol"] == "600000.SH"
    assert config["stocks"][0]["status"] == "正常跟踪"

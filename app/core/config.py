from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import yaml


DEFAULT_CODEX_CLI_PATH = Path("codex")
DEFAULT_DATABASE_PATH = Path("data/app.db")


class ConfigError(RuntimeError):
    """Raised when local configuration is present but invalid."""


@dataclass(frozen=True)
class AppSettings:
    app_name: str
    app_mode: str
    market_provider: str
    llm_provider: str
    codex_cli_path: Path
    codex_model: str
    codex_timeout_seconds: int
    codex_sandbox_mode: str
    enable_codex_cli: bool
    database_path: Path
    config_dir: Path

    @property
    def is_mock_mode(self) -> bool:
        return self.app_mode in {"mock", "fake"} or self.market_provider in {
            "mock",
            "fake",
        }

    def public_status(self) -> dict[str, Any]:
        return {
            "status": "ok",
            "mode": self.app_mode,
            "providers": {
                "market": self.market_provider,
                "llm": self.llm_provider,
            },
            "codex": {
                "model": self.codex_model,
                "timeout_seconds": self.codex_timeout_seconds,
                "sandbox_mode": self.codex_sandbox_mode,
                "cli_path_configured": bool(str(self.codex_cli_path)),
                "enabled": self.enable_codex_cli,
                "cli_path_exists": self.codex_cli_path.exists(),
                "version_check": "not_run",
            },
            "database": {
                "engine": "sqlite",
                "configured": bool(str(self.database_path)),
            },
        }


def load_settings(
    config_dir: str | Path = "config",
    env: Mapping[str, str] | None = None,
) -> AppSettings:
    env_map = dict(os.environ if env is None else env)
    config_root = Path(config_dir)
    app_config = _read_optional_yaml(config_root / "app.yaml")

    return AppSettings(
        app_name=_env_or_config(env_map, app_config, "APP_NAME", "app.name")
        or "stock-wave-assistant",
        app_mode=_env_or_config(env_map, app_config, "APP_MODE", "app.mode") or "mock",
        market_provider=_env_or_config(
            env_map, app_config, "MARKET_PROVIDER", "providers.market"
        )
        or "mock",
        llm_provider=_env_or_config(env_map, app_config, "LLM_PROVIDER", "providers.llm")
        or "codex_cli",
        codex_cli_path=Path(
            _env_or_config(env_map, app_config, "CODEX_CLI_PATH", "codex.cli_path")
            or str(DEFAULT_CODEX_CLI_PATH)
        ),
        codex_model=_env_or_config(env_map, app_config, "CODEX_MODEL", "codex.model")
        or "gpt-5.5",
        codex_timeout_seconds=_positive_int(
            _env_or_config(
                env_map,
                app_config,
                "CODEX_TIMEOUT_SECONDS",
                "codex.timeout_seconds",
            )
            or "120",
            "CODEX_TIMEOUT_SECONDS",
        ),
        codex_sandbox_mode=_env_or_config(
            env_map, app_config, "CODEX_SANDBOX_MODE", "codex.sandbox_mode"
        )
        or "read-only",
        enable_codex_cli=_bool_value(
            _env_or_config(env_map, app_config, "ENABLE_CODEX_CLI", "codex.enable_cli")
            or "false",
            "ENABLE_CODEX_CLI",
        ),
        database_path=_database_path(env_map, app_config),
        config_dir=config_root,
    )


def load_watchlist_config(path: str | Path) -> dict[str, Any]:
    config_path = Path(path)
    if not config_path.exists():
        raise ConfigError(f"Watchlist config not found: {config_path}")
    data = _read_yaml(config_path)
    if "stocks" not in data:
        raise ConfigError("watchlist config must contain a stocks list")
    if not isinstance(data["stocks"], list):
        raise ConfigError("watchlist config field stocks must be a list")
    return data


def _database_path(env: Mapping[str, str], config: Mapping[str, Any]) -> Path:
    if env.get("DATABASE_PATH"):
        return Path(env["DATABASE_PATH"])
    if env.get("DATABASE_URL"):
        return _sqlite_url_to_path(env["DATABASE_URL"])
    configured = _nested_get(config, "database.path")
    if configured:
        return Path(str(configured))
    configured_url = _nested_get(config, "database.url")
    if configured_url:
        return _sqlite_url_to_path(str(configured_url))
    return DEFAULT_DATABASE_PATH


def _sqlite_url_to_path(value: str) -> Path:
    prefix = "sqlite:///"
    if not value.startswith(prefix):
        raise ConfigError("DATABASE_URL must use sqlite:/// for the local MVP")
    return Path(value[len(prefix) :])


def _read_optional_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return _read_yaml(path)


def _read_yaml(path: Path) -> dict[str, Any]:
    try:
        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ConfigError(f"Invalid YAML in {path}: {exc}") from exc
    if loaded is None:
        return {}
    if not isinstance(loaded, dict):
        raise ConfigError(f"YAML root must be a mapping: {path}")
    return loaded


def _env_or_config(
    env: Mapping[str, str],
    config: Mapping[str, Any],
    env_key: str,
    config_key: str,
) -> str | None:
    if env.get(env_key):
        return env[env_key]
    value = _nested_get(config, config_key)
    if value is None:
        return None
    return str(value)


def _nested_get(config: Mapping[str, Any], dotted_key: str) -> Any:
    current: Any = config
    for part in dotted_key.split("."):
        if not isinstance(current, Mapping) or part not in current:
            return None
        current = current[part]
    return current


def _positive_int(value: str, field_name: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise ConfigError(f"{field_name} must be an integer") from exc
    if parsed <= 0:
        raise ConfigError(f"{field_name} must be greater than zero")
    return parsed


def _bool_value(value: str, field_name: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ConfigError(f"{field_name} must be a boolean")

import json
import shutil
from datetime import datetime
from pathlib import Path

from app.core.config import load_settings
from app.cli.preclose_report import main as preclose_cli_main
from app.services.preclose_report_run import run_preclose_report_once


def test_run_once_generates_preclose_report_on_trading_day(tmp_path: Path) -> None:
    settings = load_settings(
        env={
            "DATABASE_PATH": str(tmp_path / "app.db"),
            "REPORT_DIR": str(tmp_path / "reports"),
            "MARKET_PROVIDER": "mock",
        }
    )

    result = run_preclose_report_once(
        settings,
        datetime.fromisoformat("2026-07-01T14:55:00"),
    )

    report_path = tmp_path / "reports" / result.file_name
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert result.status == "generated"
    assert result.report_id == "preclose_1455-2026-07-01"
    assert result.file_name == "preclose_1455-2026-07-01.json"
    assert result.relative_path == "preclose_1455-2026-07-01.json"
    assert result.report is not None
    assert result.report["schema_version"] == "1.0"
    assert result.report["as_of"] == "2026-07-01T14:55:00"
    assert result.report["not_advice"] is True
    assert payload["schema_version"] == "1.0"
    assert payload["report_type"] == "preclose_1455"
    assert payload["not_advice"] is True


def test_run_once_skips_non_trading_day(tmp_path: Path) -> None:
    settings = load_settings(
        env={
            "DATABASE_PATH": str(tmp_path / "app.db"),
            "REPORT_DIR": str(tmp_path / "reports"),
        }
    )

    result = run_preclose_report_once(
        settings,
        datetime.fromisoformat("2026-07-04T14:55:00"),
    )

    assert result.status == "skipped"
    assert result.skipped_reason == "non_trading_day"
    assert result.report is None
    assert not (tmp_path / "reports").exists()


def test_run_once_skips_configured_closed_date(tmp_path: Path) -> None:
    config_dir = write_config_dir(
        tmp_path,
        preferences="""
version: 1
trading_sessions:
  morning:
    start: "09:30"
    end: "11:30"
  afternoon:
    start: "13:00"
    end: "15:00"
daily_report_time: "14:55"
market:
  closed_dates:
    - "2026-07-01"
""".strip(),
    )
    settings = load_settings(
        config_dir=config_dir,
        env={
            "DATABASE_PATH": str(tmp_path / "app.db"),
            "REPORT_DIR": str(tmp_path / "reports"),
        },
    )

    result = run_preclose_report_once(
        settings,
        datetime.fromisoformat("2026-07-01T14:55:00"),
    )

    assert result.status == "skipped"
    assert result.skipped_reason == "non_trading_day"
    assert result.report is None


def test_run_once_allows_configured_extra_open_date(tmp_path: Path) -> None:
    config_dir = write_config_dir(
        tmp_path,
        preferences="""
version: 1
trading_sessions:
  morning:
    start: "09:30"
    end: "11:30"
  afternoon:
    start: "13:00"
    end: "15:00"
daily_report_time: "14:55"
market:
  extra_open_dates:
    - "2026-07-04"
""".strip(),
    )
    settings = load_settings(
        config_dir=config_dir,
        env={
            "DATABASE_PATH": str(tmp_path / "app.db"),
            "REPORT_DIR": str(tmp_path / "reports"),
            "MARKET_PROVIDER": "mock",
        },
    )

    result = run_preclose_report_once(
        settings,
        datetime.fromisoformat("2026-07-04T14:55:00"),
    )

    assert result.status == "generated"
    assert result.report_id == "preclose_1455-2026-07-04"
    assert result.report is not None
    assert result.report["market_session_status"]["status"] == "preclose"


def test_run_once_skips_non_preclose_time(tmp_path: Path) -> None:
    settings = load_settings(
        env={
            "DATABASE_PATH": str(tmp_path / "app.db"),
            "REPORT_DIR": str(tmp_path / "reports"),
        }
    )

    result = run_preclose_report_once(
        settings,
        datetime.fromisoformat("2026-07-01T14:54:00"),
    )

    assert result.status == "skipped"
    assert result.skipped_reason == "afternoon_session"
    assert result.report is None


def test_run_once_is_idempotent_for_same_report(tmp_path: Path) -> None:
    settings = load_settings(
        env={
            "DATABASE_PATH": str(tmp_path / "app.db"),
            "REPORT_DIR": str(tmp_path / "reports"),
        }
    )
    as_of = datetime.fromisoformat("2026-07-01T14:55:00")

    first = run_preclose_report_once(settings, as_of)
    second = run_preclose_report_once(settings, as_of)

    assert first.status == "generated"
    assert second.status == "existing"
    assert second.report_id == first.report_id
    assert second.file_name == first.file_name
    assert second.report is not None


def test_run_once_force_overwrites_existing_report(tmp_path: Path) -> None:
    settings = load_settings(
        env={
            "DATABASE_PATH": str(tmp_path / "app.db"),
            "REPORT_DIR": str(tmp_path / "reports"),
        }
    )
    as_of = datetime.fromisoformat("2026-07-01T14:55:00")
    first = run_preclose_report_once(settings, as_of)
    report_path = tmp_path / "reports" / first.file_name
    report_path.write_text('{"schema_version":"broken"}', encoding="utf-8")

    second = run_preclose_report_once(settings, as_of, force=True)

    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert second.status == "overwritten"
    assert payload["schema_version"] == "1.0"
    assert payload["not_advice"] is True


def test_run_once_creates_missing_report_dir(tmp_path: Path) -> None:
    report_dir = tmp_path / "missing" / "reports"
    settings = load_settings(
        env={
            "DATABASE_PATH": str(tmp_path / "app.db"),
            "REPORT_DIR": str(report_dir),
        }
    )

    result = run_preclose_report_once(
        settings,
        datetime.fromisoformat("2026-07-01T14:55:00"),
    )

    assert result.status == "generated"
    assert (report_dir / result.file_name).exists()


def test_run_once_uses_default_mock_provider(tmp_path: Path) -> None:
    settings = load_settings(
        env={
            "DATABASE_PATH": str(tmp_path / "app.db"),
            "REPORT_DIR": str(tmp_path / "reports"),
        }
    )

    result = run_preclose_report_once(
        settings,
        datetime.fromisoformat("2026-07-01T14:55:00"),
    )

    assert settings.market_provider == "mock"
    assert result.status == "generated"
    assert result.report is not None
    assert result.report["not_advice"] is True


def test_preclose_report_cli_runs_once(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "app.db"))
    monkeypatch.setenv("REPORT_DIR", str(tmp_path / "reports"))

    exit_code = preclose_cli_main(["--as-of", "2026-07-01T14:55:00"])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["status"] == "generated"
    assert payload["report_id"] == "preclose_1455-2026-07-01"
    assert (tmp_path / "reports" / payload["file_name"]).exists()


def write_config_dir(tmp_path: Path, preferences: str) -> Path:
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    shutil.copyfile(Path("config/watchlist.yaml"), config_dir / "watchlist.yaml")
    shutil.copyfile(Path("config/factors.yaml"), config_dir / "factors.yaml")
    (config_dir / "preferences.yaml").write_text(preferences, encoding="utf-8")
    return config_dir

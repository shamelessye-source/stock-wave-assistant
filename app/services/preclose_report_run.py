from __future__ import annotations

import json
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from app.core.config import AppSettings
from app.domain.trading_calendar import evaluate_market_session
from app.services.portfolio_service import (
    build_current_preclose_report,
    decimal_dataclass_to_response,
)


SCHEMA_VERSION = "1.0"
REPORT_TYPE = "preclose_1455"


@dataclass(frozen=True)
class PrecloseReportRunResult:
    status: str
    report_id: str
    report_type: str
    as_of: str
    file_name: str
    relative_path: str
    skipped_reason: str | None = None
    error: str | None = None
    report: dict[str, Any] | None = None


def run_preclose_report_once(
    settings: AppSettings,
    as_of: datetime,
    *,
    force: bool = False,
) -> PrecloseReportRunResult:
    report_id = f"{REPORT_TYPE}-{as_of.date().isoformat()}"
    file_name = f"{report_id}.json"
    report_path = settings.report_dir / file_name
    result_base = {
        "report_id": report_id,
        "report_type": REPORT_TYPE,
        "as_of": as_of.isoformat(timespec="seconds"),
        "file_name": file_name,
        "relative_path": _safe_relative_path(settings.report_dir, file_name),
    }

    preferences_config = _read_optional_yaml(settings.config_dir / "preferences.yaml")
    market_status = evaluate_market_session(as_of, preferences_config)
    if market_status.status != "preclose":
        return PrecloseReportRunResult(
            status="skipped",
            skipped_reason=market_status.status,
            report=None,
            **result_base,
        )

    if report_path.exists() and not force:
        try:
            existing_report = _read_report(report_path)
        except (json.JSONDecodeError, OSError, ValueError):
            return PrecloseReportRunResult(
                status="existing_read_error",
                error="existing report could not be read; rerun with force=true",
                report=None,
                **result_base,
            )
        return PrecloseReportRunResult(
            status="existing",
            report=existing_report,
            **result_base,
        )

    report = _versioned_report(
        decimal_dataclass_to_response(build_current_preclose_report(settings, as_of)),
        as_of,
    )
    existed_before = report_path.exists()
    _write_json_atomic(report_path, report)
    return PrecloseReportRunResult(
        status="overwritten" if existed_before and force else "generated",
        report=report,
        **result_base,
    )


def _versioned_report(report: dict[str, Any], as_of: datetime) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "as_of": as_of.isoformat(timespec="seconds"),
        **report,
    }


def _read_report(path: Path) -> dict[str, Any]:
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError("report file must contain a JSON object")
    return loaded


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            delete=False,
            dir=path.parent,
            encoding="utf-8",
            prefix=f".{path.stem}.",
            suffix=".tmp",
        ) as handle:
            temp_path = Path(handle.name)
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        temp_path.replace(path)
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()


def _safe_relative_path(report_dir: Path, file_name: str) -> str:
    if report_dir.is_absolute():
        return file_name
    return (report_dir / file_name).as_posix()


def _read_optional_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if loaded is None:
        return {}
    if not isinstance(loaded, dict):
        return {}
    return loaded

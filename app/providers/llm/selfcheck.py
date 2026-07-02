from __future__ import annotations

import subprocess
from dataclasses import dataclass

from app.core.config import AppSettings


@dataclass(frozen=True)
class CodexCliSelfcheck:
    enabled: bool
    model: str
    timeout_seconds: int
    sandbox_mode: str
    cli_path_configured: bool
    cli_path_exists: bool
    version_check: str
    version: str | None

    def as_public_dict(self) -> dict[str, object]:
        return {
            "enabled": self.enabled,
            "model": self.model,
            "timeout_seconds": self.timeout_seconds,
            "sandbox_mode": self.sandbox_mode,
            "cli_path_configured": self.cli_path_configured,
            "cli_path_exists": self.cli_path_exists,
            "version_check": self.version_check,
            "version": self.version,
        }


def check_codex_cli(
    settings: AppSettings,
    *,
    run_version: bool | None = None,
) -> CodexCliSelfcheck:
    cli_path_exists = settings.codex_cli_path.exists()
    should_run_version = settings.enable_codex_cli if run_version is None else run_version
    version_check = "not_run"
    version: str | None = None
    if should_run_version and cli_path_exists:
        try:
            completed = subprocess.run(
                [str(settings.codex_cli_path), "--version"],
                text=True,
                capture_output=True,
                timeout=5,
                check=False,
            )
        except (subprocess.TimeoutExpired, TimeoutError):
            version_check = "timeout"
        else:
            version_check = "ok" if completed.returncode == 0 else "failed"
            version = (completed.stdout or completed.stderr or "").strip() or None

    return CodexCliSelfcheck(
        enabled=settings.enable_codex_cli,
        model=settings.codex_model,
        timeout_seconds=settings.codex_timeout_seconds,
        sandbox_mode=settings.codex_sandbox_mode,
        cli_path_configured=bool(str(settings.codex_cli_path)),
        cli_path_exists=cli_path_exists,
        version_check=version_check,
        version=version,
    )

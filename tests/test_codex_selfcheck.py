from pathlib import Path
from types import SimpleNamespace

from app.core.config import load_settings
from app.providers.llm.selfcheck import check_codex_cli


def test_codex_selfcheck_reports_missing_cli_without_path_leak(tmp_path: Path) -> None:
    settings = load_settings(
        config_dir=tmp_path,
        env={"CODEX_CLI_PATH": str(tmp_path / "missing.cmd")},
    )

    status = check_codex_cli(settings, run_version=False)
    public = status.as_public_dict()

    assert public["enabled"] is False
    assert public["cli_path_exists"] is False
    assert public["version_check"] == "not_run"
    assert str(tmp_path) not in str(public)


def test_codex_selfcheck_can_run_version_when_enabled(tmp_path: Path, monkeypatch) -> None:
    cli_path = tmp_path / "codex.cmd"
    cli_path.write_text("@echo off\n", encoding="utf-8")
    settings = load_settings(
        config_dir=tmp_path,
        env={
            "CODEX_CLI_PATH": str(cli_path),
            "ENABLE_CODEX_CLI": "true",
        },
    )

    def fake_run(args, **kwargs):
        return SimpleNamespace(returncode=0, stdout="codex 1.2.3", stderr="")

    monkeypatch.setattr("app.providers.llm.selfcheck.subprocess.run", fake_run)
    status = check_codex_cli(settings, run_version=True)

    assert status.enabled is True
    assert status.cli_path_exists is True
    assert status.version_check == "ok"
    assert status.version == "codex 1.2.3"

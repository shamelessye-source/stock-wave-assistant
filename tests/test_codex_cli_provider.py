from pathlib import Path
from types import SimpleNamespace

import pytest

from app.providers.llm.codex_cli import CodexCliProvider, FakeCodexProvider


def test_fake_codex_provider_returns_stable_summary() -> None:
    result = FakeCodexProvider(model="fake-codex").run("prompt")

    assert result.success is True
    assert result.model == "fake-codex"
    assert result.exit_code == 0
    assert "数据状态" in result.text
    assert "不构成投资建议" in result.text


def test_codex_cli_provider_reports_missing_path(tmp_path: Path) -> None:
    provider = CodexCliProvider(
        cli_path=tmp_path / "missing.cmd",
        model="gpt-5.5",
        timeout_seconds=3,
        sandbox_mode="read-only",
    )

    result = provider.run("prompt")

    assert result.success is False
    assert result.error == "cli_path_not_found"
    assert result.exit_code is None


def test_codex_cli_provider_uses_argument_array_and_output_file(
    tmp_path: Path,
    monkeypatch,
) -> None:
    cli_path = tmp_path / "codex.cmd"
    cli_path.write_text("@echo off\n", encoding="utf-8")
    captured: dict[str, object] = {}

    def fake_run(args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        output_file = Path(args[args.index("--output-last-message") + 1])
        output_file.write_text("summary text", encoding="utf-8")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr("app.providers.llm.codex_cli.subprocess.run", fake_run)
    provider = CodexCliProvider(
        cli_path=cli_path,
        model="gpt-5.5",
        timeout_seconds=9,
        sandbox_mode="read-only",
    )

    result = provider.run("prompt body")

    assert result.success is True
    assert result.text == "summary text"
    assert captured["args"][:7] == [
        str(cli_path),
        "exec",
        "-m",
        "gpt-5.5",
        "--skip-git-repo-check",
        "--sandbox",
        "read-only",
    ]
    assert "--output-last-message" in captured["args"]
    assert captured["kwargs"]["input"] == "prompt body"
    assert captured["kwargs"]["timeout"] == 9
    assert "shell" not in captured["kwargs"]


def test_codex_cli_provider_handles_timeout(tmp_path: Path, monkeypatch) -> None:
    cli_path = tmp_path / "codex.cmd"
    cli_path.write_text("@echo off\n", encoding="utf-8")

    def fake_run(args, **kwargs):
        raise TimeoutError("expired")

    monkeypatch.setattr("app.providers.llm.codex_cli.subprocess.run", fake_run)
    provider = CodexCliProvider(
        cli_path=cli_path,
        model="gpt-5.5",
        timeout_seconds=1,
        sandbox_mode="read-only",
    )

    result = provider.run("prompt")

    assert result.success is False
    assert result.error == "timeout"
    assert result.exit_code is None
